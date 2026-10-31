"""DataSentry kalite kontrol motoru birim testleri."""

import pandas as pd

from datasentry.models import CheckStatus, Severity
from datasentry.validators import (
    check_duplicate_rows,
    check_missing_values,
    check_outliers_iqr,
    check_type_mismatches,
)


def test_missing_values_detection():
    """Eksik değerlerin doğru tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "ad": ["Ali", None, "Veli"],
            "yas": [25, 30, None],
        }
    )
    result = check_missing_values(df)

    assert result.status == CheckStatus.FAILED
    assert len(result.issues) == 2
    assert result.issues[0].column == "ad"
    assert result.issues[0].count == 1
    assert result.issues[0].severity == Severity.ERROR


def test_missing_values_clean_data():
    """Temiz veride eksik değer kontrolünün PASSED döndüğünü doğrular."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = check_missing_values(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0


def test_duplicate_rows_detection():
    """Yinelenen satırların ve eşleşmelerinin doğru tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 2, 3],
            "deger": ["a", "b", "b", "c"],
        }
    )
    result = check_duplicate_rows(df)

    assert result.status == CheckStatus.FAILED
    assert len(result.issues) == 1
    assert result.issues[0].count == 1
    assert result.issues[0].percentage == 25.0
    # CSV başlık hesabı nedeniyle (0. indeks = 2. satır) eşleşme (4 -> 3) olarak döner
    assert "(4 -> 3)" in result.issues[0].message


def test_duplicate_rows_with_nan():
    """NaN içeren tekrarlanan kayıtların dropna=False ile doğru tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 2],
            "aciklama": ["ilk", None, None],
        }
    )
    result = check_duplicate_rows(df)

    assert result.status == CheckStatus.FAILED
    assert len(result.issues) == 1
    assert result.issues[0].count == 1
    # Satır 4 kopya, satır 3 orijinal -> (4 -> 3)
    assert "(4 -> 3)" in result.issues[0].message


def test_duplicate_rows_clean_data():
    """Tekil satırlardan oluşan veride PASSED döndüğünü doğrular."""
    df = pd.DataFrame({"id": [1, 2, 3], "deger": ["a", "b", "c"]})
    result = check_duplicate_rows(df)

    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0


def test_type_mismatch_detection():
    """Sayısal sütundaki metin uyuşmazlığının tespit edildiğini doğrular."""
    df = pd.DataFrame(
        {
            "yas": ["25", "30", "otuz bes", "40", "ellibir"],
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
