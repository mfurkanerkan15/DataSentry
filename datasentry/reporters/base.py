"""DataSentry temel raporlayıcı arayüzü ve kayıt mekanizması."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from datasentry.exceptions import ReportError
from datasentry.models import ValidationReport

_REPORTERS: dict[str, type["BaseReporter"]] = {}


class BaseReporter(ABC):
    """Tüm raporlayıcılar için temel soyut sınıf."""

    @abstractmethod
    def render(self, report: ValidationReport) -> str:
        """Raporu ilgili formatta metin/içerik olarak oluşturur."""
        pass

    def write(self, report: ValidationReport, path: str | Path) -> Path:
        """Raporu belirtilen dosya yoluna UTF-8 olarak kaydeder."""
        output_path = Path(path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            content = self.render(report)
            output_path.write_text(content, encoding="utf-8")
            return output_path
        except Exception as e:
            if isinstance(e, ReportError):
                raise
            raise ReportError(f"Rapor dosyası yazılamadı: {output_path} — {e}") from e


def register_reporter(*names: str):
    """Raporlayıcı sınıfını bir veya birden fazla isimle kaydeder."""

    def decorator(cls: type[BaseReporter]) -> type[BaseReporter]:
        for name in names:
            _REPORTERS[name.lower()] = cls
        return cls

    return decorator


def get_reporter(name: str, **kwargs: Any) -> BaseReporter:
    """Format adına göre kayıtlı raporlayıcı örneğini döndürür."""
    key = name.lower()
    if key not in _REPORTERS:
        available = ", ".join(sorted(set(_REPORTERS.keys())))
        raise ReportError(
            f"Bilinmeyen rapor formatı: '{name}'. Desteklenen formatlar: {available}"
        )
    return _REPORTERS[key](**kwargs)

