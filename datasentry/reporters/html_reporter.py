"""DataSentry tek dosya, çevrimdışı ve interaktif HTML raporlayıcısı."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from datasentry import __version__
from datasentry.exceptions import ReportError
from datasentry.models import ValidationReport
from datasentry.reporters.base import BaseReporter, register_reporter

# Kalite skoru renk eşikleri — tek kaynak (tek yerde tanımlı, testler buraya bağlanır).
# Tuple formatı: (minimum_skor, css_class)
# is_valid=True iken tam yeşil/sarı/kırmızı skalası;
# is_valid=False iken yeşil asla kullanılmaz (en fazla sarı).
_SCORE_THRESHOLDS: list[tuple[float, str]] = [
    (90.0, "score-pass"),
    (70.0, "score-warn"),
    (0.0, "score-fail"),
]


def score_color_class(quality_score: float, is_valid: bool) -> str:
    """Kalite skoruna ve doğrulama sonucuna göre CSS sınıfını belirler.

    Kural:
        - is_valid=True  → ≥90 yeşil, ≥70 sarı, altı kırmızı
        - is_valid=False → hiçbir zaman yeşil olamaz; en fazla sarı.

    Args:
        quality_score: 0.0 - 100.0 arasında kalite skoru.
        is_valid: Kritik hata yoksa True.

    Returns:
        CSS sınıfı: 'score-pass', 'score-warn' veya 'score-fail'.
    """
    for threshold, css_class in _SCORE_THRESHOLDS:
        if quality_score >= threshold:
            # is_valid=False iken yeşil sınıfını sarıya indir
            if not is_valid and css_class == "score-pass":
                return "score-warn"
            return css_class
    return "score-fail"


@register_reporter("html")
class HtmlReporter(BaseReporter):
    """Jinja2 tabanlı modern HTML raporlayıcısı."""

    def __init__(
        self,
        template_dir: Path | None = None,
        show_path: bool = False,
    ) -> None:
        self.template_dir = template_dir or (Path(__file__).parent / "templates")
        self.show_path = show_path
        if not self.template_dir.exists():
            raise ReportError(f"HTML şablon dizini bulunamadı: {self.template_dir}")

        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
        )

    def render(self, report: ValidationReport) -> str:
        """Raporu tek dosyalık bağımsız HTML içeriğine dönüştürür."""
        try:
            template = self.env.get_template("report.html.j2")
            display_path = report.file_path if self.show_path else report.file_name
            return template.render(
                report=report,
                datasentry_version=__version__,
                display_path=display_path,
                quality_score_class=score_color_class(
                    report.quality_score, report.is_valid
                ),
            )
        except Exception as e:
            raise ReportError(f"HTML raporu oluşturulurken hata: {e}") from e
