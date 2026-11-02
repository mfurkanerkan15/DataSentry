"""Validatör modülleri birim testleri."""

import pandas as pd

from datasentry.models import CheckStatus, Severity
from datasentry.validators import (
    check_duplicate_rows,
    check_missing_values,
    check_outliers_iqr,
    check_type_mismatches,
)


def test_missing_values_detection():
    """Eksik değerlerin (None/NaN/'') tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "isim": ["Ali", None, "Ahmet"],
            "not": ["100", "   ", "85"],
        }
    )
    result = check_missing_values(df)

    assert result.status == CheckStatus.FAILED
    assert len(result.issues) == 2
    assert result.issues[0].column == "isim"
    assert result.issues[0].count == 1
    assert result.issues[1].column == "not"
    assert result.issues[1].count == 1


def test_missing_values_clean_data():
    """Eksik değer olmayan veri setinde PASSED döndüğünü doğrular."""
    df = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})
    result = check_missing_values(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0


def test_duplicate_rows_detection():
    """Birebir yinelenen satırların indeksleriyle tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 1, 3],
            "isim": ["Ali", "Veli", "Ali", "Can"],
        }
    )
    result = check_duplicate_rows(df)

    assert result.status == CheckStatus.FAILED
    assert len(result.issues) == 1
    assert result.issues[0].count == 1
    # Yinelenen satır indeksi (2. satır, 0-tabanlı) CSV'de 4. satıra denk gelir
    assert 4 in result.issues[0].row_numbers


def test_duplicate_rows_with_nan():
    """NaN içeren tekrarlanan satırların da doğru tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "id": [1, 1],
            "isim": [None, None],
        }
    )
    result = check_duplicate_rows(df)

    assert result.status == CheckStatus.FAILED
    assert result.issues[0].count == 1


def test_duplicate_rows_clean_data():
    """Tekrarsız veri setinde PASSED döndüğünü doğrular."""
    df = pd.DataFrame({"id": [1, 2, 3], "isim": ["A", "B", "C"]})
    result = check_duplicate_rows(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0


def test_type_mismatch_detection():
    """Sayısal sütunda metin bulunmasını tespit ettiğini doğrular."""
    df = pd.DataFrame(
        {
            "yas": [25, "otuz bes", 40, "elli", 60, 70, 80],
        }
    )
    result = check_type_mismatches(df)

    assert result.status == CheckStatus.FAILED
    assert len(result.issues) == 1
    assert result.issues[0].column == "yas"
    assert result.issues[0].count == 2
    assert "otuz bes" in result.issues[0].sample_values


def test_type_mismatch_clean_data():
    """Düzgün metin ve sayı sütunlarında hata vermediğini doğrular."""
    df = pd.DataFrame({"metin": ["ali", "veli"], "sayi": [10, 20]})
    result = check_type_mismatches(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0


def test_outliers_iqr_detection():
    """IQR yöntemiyle aşırı uç değerlerin WARNING olarak tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "maas": [10000, 11000, 12000, 10500, 11500, 12500, 1000000]
        }
    )
    result = check_outliers_iqr(df)

    assert result.status == CheckStatus.WARNING
    assert len(result.issues) == 1
    assert result.issues[0].severity == Severity.WARNING
    assert result.issues[0].count == 1
    assert 1000000 in result.issues[0].sample_values


def test_outliers_low_cardinality_ignored():
    """İkili flag veya 5'ten az tekil değere sahip sütunların IQR'da
    aykırı sayılmadığını doğrular.
    """
    df = pd.DataFrame({"is_active": [1, 1, 1, 1, 1, 1, 1, 0]})
    result = check_outliers_iqr(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0


def test_outliers_clean_data():
    """Uç değer bulunmayan veri setinde PASSED döndüğünü doğrular."""
    df = pd.DataFrame({"puan": [50, 52, 48, 51, 49, 53, 50]})
    result = check_outliers_iqr(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0


def test_outliers_mixed_numeric_with_corrupt_strings_and_extremes():
    """Bozuk metin ('abc') içeren sayısal ağırlıklı sütunda IQR'ın 2 aykırı değeri tespit ettiğini,
    bozuk metnin IQR hesabına ve aykırı değer listesine dahil edilmediğini ve satır numaralarının
    orijinal Excel indeksli sırada korunduğunu doğrular.
    """
    # 10 satırlık DataFrame:
    # 0 -> 100 (satır 2)
    # 1 -> 110 (satır 3)
    # 2 -> 120 (satır 4)
    # 3 -> 130 (satır 5)
    # 4 -> 140 (satır 6)
    # 5 -> 150 (satır 7)
    # 6 -> 160 (satır 8)
    # 7 -> "abc" (satır 9) - bozuk metin
    # 8 -> 5000 (satır 10) - aşırı uç değer
    # 9 -> 4500 (satır 11) - aşırı uç değer
    df = pd.DataFrame(
        {
            "MİKTAR": [100, 110, 120, 130, 140, 150, 160, "abc", 5000, 4500]
        }
    )
    result = check_outliers_iqr(df)

    assert result.status == CheckStatus.WARNING
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.column == "MİKTAR"
    assert issue.severity == Severity.WARNING
    assert issue.count == 2
    # Excel indeksli satır numaraları: satır 10 ve satır 11
    assert issue.row_numbers == [10, 11]
    # "abc" değerinin aykırı değer örneklerinde yer almadığını doğrula
    assert "abc" not in issue.sample_values
    assert 5000 in issue.sample_values or "5000" in [str(x) for x in issue.sample_values]
    assert 4500 in issue.sample_values or "4500" in [str(x) for x in issue.sample_values]


def test_outliers_pure_text_column_ignored():
    """Tamamen metin/tarih sütunlarının sayısal aday sayılmayıp atlandığını doğrular."""
    df = pd.DataFrame(
        {
            "sehir": ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana"],
            "tarih": [
                "2025.01.01",
                "2025.01.02",
                "2025.01.03",
                "2025.01.04",
                "2025.01.05",
                "2025.01.06",
            ],
        }
    )
    result = check_outliers_iqr(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0
