"""Eksik değer kontrol modülü."""

import pandas as pd

from datasentry.models import CheckResult, CheckStatus, Severity, ValidationIssue


def check_missing_values(
    df: pd.DataFrame, 
    max_row_samples: int = 100, 
    trim_strings: bool = True
) -> CheckResult:
    """Veri setindeki sütun bazlı eksik değerleri (NaN / None / Boş String) analiz eder."""
    total_rows = len(df)
    issues: list[ValidationIssue] = []

    if total_rows == 0:
        return CheckResult(
            name="Eksik Deger Analizi",
            description="Sutunlardaki bos (null/NaN) degerleri tespit eder",
            status=CheckStatus.PASSED,
            issues=[],
        )

    for col in df.columns:
        series = df[col]
        
        # Standart NaN/None kontrolü
        null_mask = series.isna()
        
        # Object veya String tipindeki sütunlarda sadece boşluk içeren "   " veya "" değerleri de NaN say
        if trim_strings and (series.dtype == "object" or pd.api.types.is_string_dtype(series)):
            string_nulls = series.astype(str).str.strip().eq("")
            null_mask = null_mask | string_nulls

        null_count = int(null_mask.sum())
        
        if null_count > 0:
            pct = round((null_count / total_rows) * 100, 2)
            
            # Pozisyonel dizi sırasıyla CSV satır numaraları hesabı
            null_positions = null_mask.to_numpy().nonzero()[0]
            all_null_rows = (null_positions + 2).tolist()
            
            # Satır sınırlaması
            if max_row_samples and len(all_null_rows) > max_row_samples:
                null_rows = all_null_rows[:max_row_samples]
                truncated_msg = f" (İlk {max_row_samples} satır numarası listelendi)"
            else:
                null_rows = all_null_rows
                truncated_msg = ""

            # Standartlaştırma: Diğer modüllerle uyum için sembolik eksik değer örneği
            sample_nulls = ["<Eksik / Null>"]

            issues.append(
                ValidationIssue(
                    check_id="missing_values",
                    column=str(col),
                    severity=Severity.ERROR,
                    message=f"'{col}' sutununda {null_count} eksik deger (%{pct}) bulundu.{truncated_msg}",
                    count=null_count,
                    percentage=pct,
                    row_numbers=null_rows,
                    sample_values=sample_nulls,
                )
            )

    status = CheckStatus.FAILED if len(issues) > 0 else CheckStatus.PASSED

    return CheckResult(
        name="Eksik Deger Analizi",
        description="Sutunlardaki bos (null/NaN) degerleri tespit eder",
        status=status,
        issues=issues,
    )