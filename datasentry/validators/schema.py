"""Şema doğrulama: zorunlu sütunlar, sütun tipleri ve nullable kuralları."""

import numpy as np
import pandas as pd

from datasentry.config import SchemaConfig
from datasentry.models import CheckResult, CheckStatus, Severity, ValidationIssue

CHECK_ID = "schema"
_BOOL_VALUES = {"true", "false", "1", "0", "yes", "no"}


def _row_numbers(mask: pd.Series, limit: int) -> list[int]:
    """Boolean maskeden CSV satır numaralarını üretir (başlık=1, ilk veri=2)."""
    positions = np.flatnonzero(mask.to_numpy())
    return (positions[:limit] + 2).tolist()


def _invalid_type_mask(series: pd.Series, expected: str) -> pd.Series:
    """Beklenen tipe uymayan (boş olmayan) değerleri işaretler."""
    not_null = series.notna()

    if expected == "string":
        return pd.Series(False, index=series.index)

    if expected in ("int", "float"):
        numeric = pd.to_numeric(series, errors="coerce")
        invalid = not_null & numeric.isna()
        if expected == "int":
            invalid = invalid | (not_null & numeric.notna() & (numeric % 1 != 0))
        return invalid

    # bool
    lowered = series.astype(str).str.strip().str.lower()
    return not_null & ~lowered.isin(_BOOL_VALUES)


def _make_issue(
    column: str,
    message: str,
    mask: pd.Series,
    series: pd.Series,
    total_rows: int,
    max_row_samples: int,
) -> ValidationIssue:
    count = int(mask.sum())
    return ValidationIssue(
        check_id=CHECK_ID,
        column=column,
        severity=Severity.ERROR,
        message=message,
        count=count,
        percentage=round(count / total_rows * 100, 2) if total_rows else None,
        row_numbers=_row_numbers(mask, max_row_samples),
        sample_values=[str(v) for v in series[mask].head(5).tolist()],
    )


def check_schema(
    df: pd.DataFrame,
    config: SchemaConfig,
    max_row_samples: int = 100,
) -> CheckResult:
    """Veri setini şema kurallarına göre doğrular.

    Args:
        df: Doğrulanacak veri seti.
        config: Şema kuralları (zorunlu sütunlar ve sütun kuralları).
        max_row_samples: Raporda listelenecek maksimum satır numarası.
    """
    issues: list[ValidationIssue] = []
    total_rows = len(df)
    present = {str(c) for c in df.columns}
    normalized = {str(c).strip().lower(): str(c) for c in df.columns}

    # 1. Zorunlu sütunlar
    for name in config.required_columns:
        if name in present:
            continue
        message = f"Zorunlu sutun bulunamadi: '{name}'."
        similar = normalized.get(name.strip().lower())
        if similar:
            message += (
                f" Benzer bir sutun var: '{similar}' (buyuk/kucuk harf veya bosluk farki)."
            )
        issues.append(
            ValidationIssue(
                check_id=CHECK_ID,
                column=name,
                severity=Severity.ERROR,
                message=message,
                count=0,
            )
        )

    # 2. Sütun bazlı tip ve nullable kuralları (yalnızca mevcut sütunlar)
    for name, rule in config.columns.items():
        if name not in present:
            continue
        series = df[name]

        if not rule.nullable:
            null_mask = series.isna()
            if series.dtype == "object" or pd.api.types.is_string_dtype(series):
                string_nulls = series.astype(str).str.strip().eq("")
                null_mask = null_mask | string_nulls
            if null_mask.any():
                issues.append(
                    _make_issue(
                        name,
                        "Bos olamaz (nullable: false) ama bos deger iceriyor.",
                        null_mask,
                        series,
                        total_rows,
                        max_row_samples,
                    )
                )

        if rule.type is not None:
            type_mask = _invalid_type_mask(series, rule.type)
            if type_mask.any():
                issues.append(
                    _make_issue(
                        name,
                        f"Beklenen tip '{rule.type}' ile uyusmayan degerler var.",
                        type_mask,
                        series,
                        total_rows,
                        max_row_samples,
                    )
                )

    status = (
        CheckStatus.FAILED
        if any(i.severity == Severity.ERROR for i in issues)
        else CheckStatus.PASSED
    )

    return CheckResult(
        name="Sema Dogrulama",
        description="Zorunlu sutunlar, veri tipleri ve nullable kurallari",
        status=status,
        issues=issues,
    )
