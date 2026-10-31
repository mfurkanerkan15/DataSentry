"""Veri tipi uyuşmazlığı kontrol modülü."""

from typing import Any

import pandas as pd

from datasentry.models import CheckResult, CheckStatus, Severity, ValidationIssue


def check_type_mismatches(
    df: pd.DataFrame,
    threshold: float = 0.5,
    max_row_samples: int = 100,
) -> CheckResult:
    """String olarak yüklenmiş ancak çoğunluğu sayısal olan sütunlardaki
    bozuk değerleri tespit eder.
    """
    total_rows = len(df)
    issues: list[ValidationIssue] = []

    if total_rows == 0:
        return CheckResult(
            name="Veri Tipi Uyusmazligi",
            description="Sayisal sutunlardaki hatali metin vb. tipleri tespit eder",
            status=CheckStatus.PASSED,
            issues=[],
        )

    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue

        if pd.api.types.is_numeric_dtype(series):
            continue

        converted = pd.to_numeric(series, errors="coerce")
        numeric_count = int(converted.notna().sum())

        # Orijinal df üzerinden maske oluşturarak indeks eşleşmesini garantiye alıyoruz
        invalid_mask = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
        invalid_count = int(invalid_mask.sum())

        if len(series) > 0 and (numeric_count / len(series)) >= threshold and invalid_count > 0:
            pct = round((invalid_count / total_rows) * 100, 2)

            # Örnek geçersiz değerler (ilk 5 değer)
            invalid_samples: list[Any] = df.loc[invalid_mask, col].head(5).tolist()

            # Pozisyonel indeks sırasıyla CSV satır numaraları hesabı
            invalid_positions = invalid_mask.to_numpy().nonzero()[0]
            all_invalid_rows = (invalid_positions + 2).tolist()

            # Satır sınırlaması
            if max_row_samples and len(all_invalid_rows) > max_row_samples:
                invalid_rows = all_invalid_rows[:max_row_samples]
                truncated_msg = f" (İlk {max_row_samples} satır numarası listelendi)"
            else:
                invalid_rows = all_invalid_rows
                truncated_msg = ""

            issues.append(
                ValidationIssue(
                    check_id="type_mismatch",
                    column=str(col),
                    severity=Severity.ERROR,
                    message=(
                        f"'{col}' sutunu sayisal olmali fakat {invalid_count} adet "
                        f"gecersiz metin degeri iceriyor (%{pct}).{truncated_msg}"
                    ),
                    count=invalid_count,
                    percentage=pct,
                    row_numbers=invalid_rows,
                    sample_values=invalid_samples,
                )
            )

    status = CheckStatus.FAILED if len(issues) > 0 else CheckStatus.PASSED

    return CheckResult(
        name="Veri Tipi Uyusmazligi",
        description="Sayisal sutunlardaki hatali metin vb. tipleri tespit eder",
        status=status,
        issues=issues,
    )
