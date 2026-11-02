"""Aykırı değer kontrol modülü — IQR yöntemi."""

from typing import Any

import pandas as pd

from datasentry.models import CheckResult, CheckStatus, Severity, ValidationIssue


def check_outliers_iqr(
    df: pd.DataFrame,
    multiplier: float = 1.5,
    max_row_samples: int = 100,
    numeric_ratio_threshold: float = 0.8,
) -> CheckResult:
    """Sayısal ve sayısal ağırlıklı sütunlarda IQR yöntemiyle aykırı değerleri tespit eder."""
    total_rows = len(df)
    issues: list[ValidationIssue] = []

    if total_rows == 0:
        return CheckResult(
            name="Aykiri Deger Tespiti (IQR)",
            description="Sayisal sutunlarda IQR yontemiyle supheli uc degerleri isaretler",
            status=CheckStatus.PASSED,
            issues=[],
        )

    for col in df.columns:
        # Sayısal dtype kontrolü veya sayısal aday analizi
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_series = pd.to_numeric(df[col], errors="coerce")
        else:
            series_non_null = df[col].dropna()
            if series_non_null.empty:
                continue
            converted = pd.to_numeric(series_non_null, errors="coerce")
            valid_count = int(converted.notna().sum())
            # Sayısal aday sayılma kriteri (örn. >= %80)
            if (valid_count / len(series_non_null)) < numeric_ratio_threshold:
                continue
            numeric_series = pd.to_numeric(df[col], errors="coerce")

        # Geçerli sayısal değerler üzerinden IQR sınırlarını hesapla
        valid_numbers = numeric_series.dropna()
        if len(valid_numbers) < 4 or valid_numbers.nunique() <= 5:
            continue

        q1 = valid_numbers.quantile(0.25)
        q3 = valid_numbers.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - (multiplier * iqr)
        upper_bound = q3 + (multiplier * iqr)

        # Bozuk metinler ve NaN hesaplamaya girmesin; yalnızca geçerli sayılar
        outlier_mask = (numeric_series < lower_bound) | (numeric_series > upper_bound)
        outlier_count = int(outlier_mask.sum())

        if outlier_count > 0:
            # Toplam satır sayısına göre oran hesabı
            pct = round((outlier_count / total_rows) * 100, 2)

            # Örnek aykırı değerler (ilk 5 değer)
            sample_outliers: list[Any] = df.loc[outlier_mask, col].head(5).tolist()

            # Pozisyonel indeks sırasıyla CSV satır numaraları hesabı (Excel indeksli)
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
                        f"'{col}' sutununda {outlier_count} adet supheli aykiri deger (%{pct}) "
                        f"tespit edildi. [Guvenli aralik: {lower_bound:.2f} ile "
                        f"{upper_bound:.2f}]{truncated_msg}"
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
