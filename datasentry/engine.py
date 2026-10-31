"""DataSentry doğrulama motoru — tüm kontrolleri çalıştırıp rapor üretir."""

from pathlib import Path

import pandas as pd

from datasentry.config import DataSentryConfig
from datasentry.models import (
    CheckResult,
    CheckStatus,
    Severity,
    ValidationIssue,
    ValidationReport,
)
from datasentry.validators import (
    check_duplicate_rows,
    check_missing_values,
    check_outliers_iqr,
    check_type_mismatches,
)
from datasentry.validators.schema import check_schema


def _issue_percentage(issue: ValidationIssue, total_rows: int) -> float:
    """Bulgunun toplam satıra oranını (%) döndürür."""
    if issue.percentage is not None:
        return issue.percentage
    return issue.count / total_rows * 100 if total_rows else 0.0


def _derive_status(issues: list[ValidationIssue]) -> CheckStatus:
    if any(i.severity == Severity.ERROR for i in issues):
        return CheckStatus.FAILED
    if any(i.severity == Severity.WARNING for i in issues):
        return CheckStatus.WARNING
    return CheckStatus.PASSED


def _apply_rules(
    result: CheckResult,
    total_rows: int,
    max_percent: float | None = None,
    severity: str | None = None,
) -> CheckResult:
    """Yapılandırma kurallarını bir kontrol sonucuna uygular.

    - max_percent: Oranı bu eşiğin altındaki bulgular INFO'ya düşürülür
      (raporda görünür kalır ama kontrolü başarısız yapmaz).
    - severity: Eşiği aşan bulguların önem derecesini zorlar.

    Hiçbir bulgu değişmezse sonuç aynen döndürülür.
    """
    severity_override = Severity(severity.upper()) if severity else None
    new_issues: list[ValidationIssue] = []
    changed = False

    for issue in result.issues:
        updated = issue
        if issue.severity != Severity.INFO:
            pct = _issue_percentage(issue, total_rows)
            if max_percent is not None and max_percent > 0 and pct <= max_percent:
                updated = issue.model_copy(
                    update={
                        "severity": Severity.INFO,
                        "message": (
                            f"{issue.message} "
                            f"(esik icinde: %{pct:.2f} <= %{max_percent:g})"
                        ),
                    }
                )
            elif severity_override and issue.severity != severity_override:
                updated = issue.model_copy(update={"severity": severity_override})

        if updated is not issue:
            changed = True
        new_issues.append(updated)

    if not changed:
        return result

    return result.model_copy(
        update={"issues": new_issues, "status": _derive_status(new_issues)}
    )


def run_validations(
    df: pd.DataFrame,
    file_path: str,
    max_row_samples: int = 100,
    outlier_multiplier: float = 1.5,
    type_threshold: float = 0.5,
    config: DataSentryConfig | None = None,
) -> ValidationReport:
    """Verilen DataFrame üzerinde tanımlı tüm kalite kontrollerini koşturur.

    Args:
        df: Doğrulanacak veri seti.
        file_path: Dosya yolu.
        max_row_samples: Raporda listelenecek maksimum örnek satır sayısı.
        outlier_multiplier: IQR çarpanı. Yalnızca `config` verilmediğinde kullanılır.
        type_threshold: Sayısal eşik oranı. Yalnızca `config` verilmediğinde kullanılır.
        config: Yapılandırma. Verilirse eşikler ve kurallar buradan okunur.

    Returns:
        ValidationReport nesnesi.
    """
    if config is None:
        config = DataSentryConfig()
        config.checks.outliers.multiplier = outlier_multiplier
        config.checks.type_mismatch.numeric_threshold = type_threshold

    checks = config.checks
    total_rows = len(df)
    path = Path(file_path)

    # Dosya diskte varsa boyutunu al, yoksa 0 varsay
    file_size = path.stat().st_size if path.exists() else 0

    results: list[CheckResult] = []

    if checks.missing_values.enabled:
        results.append(
            _apply_rules(
                check_missing_values(df, max_row_samples=max_row_samples),
                total_rows,
                max_percent=checks.missing_values.max_missing_percent,
                severity=checks.missing_values.severity,
            )
        )

    if checks.duplicates.enabled:
        results.append(
            _apply_rules(
                check_duplicate_rows(df, max_row_samples=max_row_samples),
                total_rows,
                max_percent=checks.duplicates.max_duplicate_percent,
                severity=checks.duplicates.severity,
            )
        )

    if checks.type_mismatch.enabled:
        results.append(
            _apply_rules(
                check_type_mismatches(
                    df,
                    threshold=checks.type_mismatch.numeric_threshold,
                    max_row_samples=max_row_samples,
                ),
                total_rows,
                severity=checks.type_mismatch.severity,
            )
        )

    if checks.outliers.enabled:
        results.append(
            _apply_rules(
                check_outliers_iqr(
                    df,
                    multiplier=checks.outliers.multiplier,
                    max_row_samples=max_row_samples,
                ),
                total_rows,
                severity=checks.outliers.severity,
            )
        )

    # Şema kontrolü yalnızca kural tanımlanmışsa çalışır
    if checks.schema_rules.enabled and checks.schema_rules.has_rules:
        results.append(
            _apply_rules(
                check_schema(
                    df, checks.schema_rules, max_row_samples=max_row_samples
                ),
                total_rows,
                severity=checks.schema_rules.severity,
            )
        )

    return ValidationReport(
        file_name=path.name,
        file_path=str(path.resolve()),
        file_size_bytes=file_size,
        total_rows=total_rows,
        total_columns=len(df.columns),
        results=results,
    )
