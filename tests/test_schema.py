import pandas as pd

from datasentry.config import ColumnRule, SchemaConfig
from datasentry.models import CheckStatus
from datasentry.validators.schema import check_schema


def test_schema_missing_required_column():
    """Eksik zorunlu sütun tespit edildiğinde FAILED döndüğünü denetler."""
    df = pd.DataFrame({"id": [1, 2], "name": ["Ali", "Veli"]})
    config = SchemaConfig(required_columns=["id", "age"])

    result = check_schema(df, config)
    assert result.status == CheckStatus.FAILED
    assert len(result.issues) == 1
    assert result.issues[0].column == "age"


def test_schema_nullable_false_with_nulls():
    """Boş olmaması gereken sütunda boş değer olduğunda FAILED döndüğünü denetler."""
    df = pd.DataFrame({"id": [1, None], "name": ["Ali", "Veli"]})
    config = SchemaConfig(columns={"id": ColumnRule(nullable=False)})

    result = check_schema(df, config)
    assert result.status == CheckStatus.FAILED
    assert "Bos olamaz" in result.issues[0].message


def test_schema_nullable_false_with_empty_strings():
    """Boş olmaması gereken sütunda sadece boşluk olan string olduğunda
    FAILED döndüğünü denetler.
    """
    df = pd.DataFrame({"id": [1, 2], "name": ["Ali", "   "]})
    config = SchemaConfig(columns={"name": ColumnRule(nullable=False)})

    result = check_schema(df, config)
    assert result.status == CheckStatus.FAILED
    assert "Bos olamaz" in result.issues[0].message


def test_schema_type_mismatch():
    """Tipi int beklenen sütunda metin olduğunda hata ürettiğini denetler."""
    df = pd.DataFrame({"age": ["20", "yirmi_bes"]})
    config = SchemaConfig(columns={"age": ColumnRule(type="int")})

    result = check_schema(df, config)
    assert result.status == CheckStatus.FAILED
    assert "Beklenen tip 'int'" in result.issues[0].message


def test_schema_all_passed():
    """Tüm kurallara uyan veri setinde PASSED döndüğünü denetler."""
    df = pd.DataFrame({"id": [1, 2], "age": [20, 30]})
    config = SchemaConfig(
        required_columns=["id", "age"],
        columns={"id": ColumnRule(type="int", nullable=False)},
    )

    result = check_schema(df, config)
    assert result.status == CheckStatus.PASSED
    assert len(result.issues) == 0
