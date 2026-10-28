"""Aykırı değer kontrol modülü — IQR yöntemi."""

from typing import Any
import pandas as pd

from datasentry.models import CheckResult, CheckStatus, Severity, ValidationIssue


def check_outliers_iqr(
    df: pd.DataFrame, 
    multiplier: float = 1.5, 
    max_row_samples: int = 100
) -> CheckResult:
    """Sayısal sütunlarda IQR yöntemiyle aykırı değerleri tespit eder."""
    total_rows = len(df)
    issues: list[ValidationIssue] = []

    if total_rows == 0:
        return CheckResult(
            name="Aykiri Deger Tespiti (IQR)",
            description="Sayisal sutunlarda IQR yontemiyle supheli uc degerleri isaretler",
            status=CheckStatus.PASSED,
            issues=[],
        )

    numeric_cols = df.select_dtypes(include=["number"]).columns

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 4:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - (multiplier * iqr)
        upper_bound = q3 + (multiplier * iqr)

        # Standart sınır kontrolü
        outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
        outlier_count = int(outlier_mask.sum())

        if outlier_count > 0:
            # Toplam satır sayısına göre oran hesabı
            pct = round((outlier_count / total_rows) * 100, 2)
            
            # Örnek aykırı değerler (ilk 5 değer)
            sample_outliers: list[Any] = df.loc[outlier_mask, col].head(5).tolist()
            
            # Pozisyonel indeks sırasıyla CSV satır numaraları hesabı
            outlier_positions = outlier_mask.to_numpy().nonzero()[0]
            all_outlier_rows = (outlier_positions + 2).tolist()

            # Satır sınırlaması
            if max_row_samples and len(all_outlier_rows) > max_row_samples:
                outlier_rows = all_outlier_rows[:max_row_samples]
                truncated_msg = f" (İlk {max_row_samples} satır numarası listelendi)"
            else:
                outlier_rows = all_outlier_rows
                truncated_msg = ""

            issues.append(
                ValidationIssue(
                    check_id="outliers_iqr",
                    column=str(col),
                    severity=Severity.WARNING,
                    message=(
                        f"'{col}' sutununda {outlier_count} adet supheli aykiri deger (%{pct}) tespit edildi. "
                        f"[Guvenli aralik: {lower_bound:.2f} ile {upper_bound:.2f}]{truncated_msg}"
                    ),
                    count=outlier_count,
                    percentage=pct,
                    row_numbers=outlier_rows,
                    sample_values=sample_outliers,
                )
            )

    status = CheckStatus.WARNING if len(issues) > 0 else CheckStatus.PASSED

    return CheckResult(
        name="Aykiri Deger Tespiti (IQR)",
        description="Sayisal sutunlarda IQR yontemiyle supheli uc degerleri isaretler",
        status=status,
        issues=issues,
    )