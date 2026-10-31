from pathlib import Path

import pytest

from datasentry.config import ConfigError, DataSentryConfig, load_config


def test_load_config_valid_yaml(tmp_path: Path):
    """Geçerli bir YAML dosyasının doğru yüklendiğini doğrular."""
    config_file = tmp_path / "valid.yaml"
    config_file.write_text(
        """
checks:
  missing_values:
    enabled: true
    max_missing_percent: 10.0
  schema:
    required_columns: ["id", "age"]
""",
        encoding="utf-8",
    )

    cfg = load_config(config_file)
    assert isinstance(cfg, DataSentryConfig)
    assert cfg.checks.missing_values.max_missing_percent == 10.0
    assert cfg.checks.schema_rules.required_columns == ["id", "age"]


def test_load_config_empty_file(tmp_path: Path):
    """Boş YAML dosyası verildiğinde varsayılan ayarların kullanıldığını doğrular."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("", encoding="utf-8")

    cfg = load_config(config_file)
    assert isinstance(cfg, DataSentryConfig)
    assert cfg.checks.missing_values.max_missing_percent == 0.0


def test_load_config_non_existent_file():
    """Olmayan dosya yolunda ConfigError fırlatıldığını doğrular."""
    with pytest.raises(ConfigError) as exc_info:
        load_config("non_existent_config.yaml")
    assert "bulunamadı" in str(exc_info.value)


def test_load_config_invalid_yaml_syntax(tmp_path: Path):
    """Bozuk YAML sözdiziminde ConfigError fırlatıldığını doğrular."""
    config_file = tmp_path / "bad_syntax.yaml"
    config_file.write_text("checks: [unclosed_bracket", encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_file)
    assert "YAML okunamadı" in str(exc_info.value)


def test_load_config_invalid_field_type(tmp_path: Path):
    """Tanımsız anahtar veya hatalı veri tipinde Pydantic doğrulamasının yakaladığını denetler."""
    config_file = tmp_path / "bad_value.yaml"
    config_file.write_text(
        """
checks:
  missing_values:
    max_missing_percent: 150.0 # 100'den büyük olamaz
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_file)
    assert "Yapılandırma geçersiz" in str(exc_info.value)
