"""DataSentry yapılandırma modelleri ve YAML yükleyici.

Hiç yapılandırma verilmezse `DataSentryConfig()` varsayılanları v0.1.0
davranışıyla aynıdır: tüm kontroller açık, eşik toleransı yok.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from datasentry.exceptions import ConfigError


class _Strict(BaseModel):
    """Tanımsız anahtarları reddeder; böylece yazım hataları sessizce yok sayılmaz."""

    model_config = ConfigDict(extra="forbid")


class _CheckBase(_Strict):
    """Tüm kontrollerin ortak ayarları."""

    enabled: bool = Field(True, description="Kontrol çalıştırılsın mı?")
    severity: Literal["error", "warning"] | None = Field(
        None,
        description="Bulguların önem derecesini zorla. Boşsa kontrolün kendi değeri kullanılır.",
    )

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value):
        """'Warning', 'WARNING' gibi yazımları kabul eder."""
        return value.lower() if isinstance(value, str) else value


class MissingValuesConfig(_CheckBase):
    max_missing_percent: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Bu orana kadar eksik değer tolere edilir (%).",
    )


class DuplicatesConfig(_CheckBase):
    max_duplicate_percent: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Bu orana kadar yinelenen satır tolere edilir (%).",
    )


class TypeMismatchConfig(_CheckBase):
    numeric_threshold: float = Field(
        0.5,
        gt=0,
        le=1,
        description="Bir sütunun sayısal sayılması için gereken minimum sayısal değer oranı.",
    )


class OutliersConfig(_CheckBase):
    method: Literal["iqr"] = "iqr"
    multiplier: float = Field(1.5, gt=0, description="IQR çarpanı.")


class ColumnRule(_Strict):
    """Tek bir sütun için tip ve nullable kuralı."""

    type: Literal["int", "float", "string", "bool"] | None = None
    nullable: bool = True


class SchemaConfig(_CheckBase):
    required_columns: list[str] = Field(default_factory=list)
    columns: dict[str, ColumnRule] = Field(default_factory=dict)

    @field_validator("required_columns")
    @classmethod
    def _no_blank_names(cls, value: list[str]) -> list[str]:
        if any(not name.strip() for name in value):
            raise ValueError("Sütun adı boş olamaz.")
        return value

    @property
    def has_rules(self) -> bool:
        """Çalıştırılacak herhangi bir şema kuralı var mı?"""
        return bool(self.required_columns or self.columns)


class ChecksConfig(_Strict):
    # `schema` pydantic'te ayrılmış bir isim olduğu için alan adı schema_rules,
    # YAML anahtarı ise "schema" (alias) olarak kullanılır.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    missing_values: MissingValuesConfig = Field(default_factory=MissingValuesConfig)
    duplicates: DuplicatesConfig = Field(default_factory=DuplicatesConfig)
    type_mismatch: TypeMismatchConfig = Field(default_factory=TypeMismatchConfig)
    outliers: OutliersConfig = Field(default_factory=OutliersConfig)
    schema_rules: SchemaConfig = Field(default_factory=SchemaConfig, alias="schema")


class DataSentryConfig(_Strict):
    checks: ChecksConfig = Field(default_factory=ChecksConfig)


def _format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"Yapılandırma geçersiz: {path}"]
    for err in error.errors():
        location = ".".join(str(part) for part in err["loc"]) or "(kök)"
        if err["type"] == "extra_forbidden":
            detail = "tanımsız anahtar (yazım hatası olabilir)"
        else:
            detail = err["msg"]
        lines.append(f"  - {location}: {detail}")
    return "\n".join(lines)


def load_config(path: str | Path) -> DataSentryConfig:
    """YAML dosyasını okur ve doğrulanmış yapılandırma döndürür.

    Raises:
        ConfigError: Dosya yoksa, okunamıyorsa veya kurallar geçersizse.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Yapılandırma dosyası bulunamadı: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8-sig"))
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML okunamadı: {config_path} — {e}") from e
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError(f"Yapılandırma dosyası okunamadı: {config_path} — {e}") from e

    # Boş dosya: varsayılanlarla devam et
    if raw is None:
        return DataSentryConfig()

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Yapılandırmanın kökü bir sözlük olmalı ('checks:' ile başlamalı): {config_path}"
        )

    try:
        return DataSentryConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(_format_validation_error(config_path, e)) from e
