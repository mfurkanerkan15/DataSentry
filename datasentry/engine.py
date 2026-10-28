"""DataSentry doğrulama motoru — tüm kontrolleri çalıştırıp rapor üretir."""

from pathlib import Path
import pandas as pd

from datasentry.models import ValidationReport
from datasentry.validators import (
    check_duplicate_rows,
    check_missing_values,
    check_outliers_iqr,
    check_type_mismatches,
)


def run_validations(
    df: pd.DataFrame, 
    file_path: str,
    max_row_samples: int = 100,
    outlier_multiplier: float = 1.5,
    type_threshold: float = 0.5
) -> ValidationReport:
    """Verilen DataFrame üzerinde tanımlı tüm kalite kontrollerini koşturur.

    Args:
        df: Doğrulanacak veri seti.
        file_path: Dosya yolu.
        max_row_samples: Raporda listelenecek maksimum örnek satır sayısı.
        outlier_multiplier: IQR aykırı değer çarpanı (varsayılan: 1.5).
        type_threshold: Veri tipi uyuşmazlığı sayısal eşik oranı (varsayılan: 0.5).

    Returns:
        ValidationReport nesnesi.
    """
    path = Path(file_path)

    # Dosya diskte varsa boyutunu al, yoksa 0 varsay
    file_size = path.stat().st_size if path.exists() else 0

    results = [
        check_missing_values(df, max_row_samples=max_row_samples),
        check_duplicate_rows(df, max_row_samples=max_row_samples),
        check_type_mismatches(df, threshold=type_threshold, max_row_samples=max_row_samples),
        check_outliers_iqr(df, multiplier=outlier_multiplier, max_row_samples=max_row_samples),
    ]

    return ValidationReport(
        file_name=path.name,
        file_path=str(path.resolve()),
        file_size_bytes=file_size,
        total_rows=len(df),
        total_columns=len(df.columns),
        results=results,
    )