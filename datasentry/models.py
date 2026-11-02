"""DataSentry ortak sonuç ve veri modelleri."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Bulgunun önem derecesi."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CheckStatus(StrEnum):
    """Tek bir kontrolün tamamlanma durumu."""

    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


def format_percentage(value: float | None) -> str | None:
    """Yüzde değerini 2 ondalık basamakla biçimlendirir.

    Tüm raporlayıcılar (terminal, JSON, HTML) bu fonksiyonu kullanır;
    böylece yuvarlama tutarlı kalır.

    Args:
        value: Biçimlendirilecek yüzde değeri (örn: 10.0, 0.95).

    Returns:
        '%X.XX' biçiminde dizi veya None.
    """
    if value is None:
        return None
    return f"{value:.2f}"


class ValidationIssue(BaseModel):
    """Tespit edilen tekil bir kalite sorunu veya uyarı."""

    check_id: str = Field(..., description="Kontrol kimliği (örn: missing_values)")
    column: str | None = Field(None, description="Sorunun görüldüğü sütun")
    severity: Severity = Field(Severity.ERROR, description="Önem derecesi")
    message: str = Field(..., description="Kullanıcıya gösterilecek açıklama")
    count: int = Field(0, description="Etkilenen satır/kayıt sayısı")
    percentage: float | None = Field(None, description="Toplam satıra oranı (%)")
    row_numbers: list[int] = Field(
        default_factory=list,
        description="CSV dosyasındaki satır numaraları (başlık=1, veriler=2...)",
    )
    sample_values: list[Any] = Field(default_factory=list, description="Örnek sorunlu değerler")


class CheckResult(BaseModel):
    """Bir kontrol modülünün toplu sonucu."""

    name: str = Field(..., description="Kontrolün adı")
    description: str = Field(..., description="Kontrol açıklaması")
    status: CheckStatus = Field(CheckStatus.PASSED, description="Kontrol durumu")
    issues: list[ValidationIssue] = Field(default_factory=list, description="Bulunan sorunlar")

    @property
    def total_affected_rows(self) -> int:
        """Bu kontrolden etkilenen benzersiz satır sayısı.

        Bulgular arasında aynı satır birden fazla sütunda sorunluysa
        (örn. iki sütunda aynı satır eksik) tek sayılır.

        Hesaplama mantığı:
        - Bir bulgunun `row_numbers` listesi doluysa, bu listeden benzersiz satırlar alınır.
        - `row_numbers` boşsa (ör. şema/tablo düzeyi bulgular) yedek olarak `count` kullanılır.
        Tüm bulgulardan elde edilen benzersiz satırlar birleştirilir.
        """
        all_unique_rows: set[int] = set()
        count_fallback = 0

        for issue in self.issues:
            if issue.row_numbers:
                all_unique_rows.update(issue.row_numbers)
            else:
                # row_numbers taşımayan bulgularda (şema/tablo düzeyi)
                # count yedek olarak kullanılır
                count_fallback += issue.count

        return len(all_unique_rows) + count_fallback

    @property
    def has_errors(self) -> bool:
        """Kritik hata var mı?"""
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Uyarı var mı?"""
        return any(i.severity == Severity.WARNING for i in self.issues)


def calculate_quality_score(total_rows: int, results: list[CheckResult]) -> float:
    """Veri seti genel kalite skorunu hesaplar (0.0 - 100.0).

    Hesaplama Formülü:
        Başlangıç skoru 100.0 puandır.
        Her kontrolün bulguları (issues) için önem derecesine ve etkilenen kayıt
        oranına göre ceza puanı kesilir:
        - Satır/Sütun Hataları (ERROR, count > 0): (Etkilenen Satır / Toplam Satır) * 40.0
        - Satır/Sütun Uyarıları (WARNING, count > 0): (Etkilenen Satır / Toplam Satır) * 15.0
        - Tablo/Şema Düzeyi Hatalar (ERROR, count == 0): Sabit 20.0 puan (örn: eksik zorunlu sütun)
        - Tablo/Şema Düzeyi Uyarılar (WARNING, count == 0): Sabit 5.0 puan
        - Bilgilendirmeler (INFO): 0.0 puan (ceza uygulanmaz)

    Skor 0.0 ile 100.0 aralığında sınırlandırılır ve 2 basamağa yuvarlanır.
    """
    total_penalty = 0.0

    for result in results:
        for issue in result.issues:
            if issue.severity == Severity.INFO:
                continue

            if issue.count > 0 and total_rows > 0:
                affected_ratio = min(1.0, issue.count / total_rows)
                if issue.severity == Severity.ERROR:
                    total_penalty += affected_ratio * 40.0
                elif issue.severity == Severity.WARNING:
                    total_penalty += affected_ratio * 15.0
            else:
                # Tablo/şema düzeyi bulgular (örn. zorunlu sütun yokluğu)
                if issue.severity == Severity.ERROR:
                    total_penalty += 20.0
                elif issue.severity == Severity.WARNING:
                    total_penalty += 5.0

    score = max(0.0, min(100.0, 100.0 - total_penalty))
    return round(score, 2)


class ValidationReport(BaseModel):
    """Tüm kontrolleri kapsayan nihai doğrulama raporu."""

    file_name: str
    file_path: str
    file_size_bytes: int = Field(0, description="Bayt cinsinden dosya boyutu")
    total_rows: int
    total_columns: int
    results: list[CheckResult] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Doğrulama zaman damgası (ISO 8601, UTC)",
    )
    execution_time_ms: float = Field(
        0.0, description="Doğrulama motoru çalışma süresi (milisaniye)"
    )
    quality_score: float = Field(
        100.0, description="Genel veri kalite skoru (0.0 - 100.0)"
    )

    @property
    def total_errors(self) -> int:
        """Toplam kritik hata sayısı."""
        return sum(
            1 for r in self.results for i in r.issues if i.severity == Severity.ERROR
        )

    @property
    def total_warnings(self) -> int:
        """Toplam uyarı sayısı."""
        return sum(
            1 for r in self.results for i in r.issues if i.severity == Severity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Kritik hata yoksa veri seti geçerli kabul edilir."""
        return self.total_errors == 0

    @property
    def file_size_human(self) -> str:
        """Dosya boyutunu kullanıcı dostu formata (KB/MB) dönüştürür."""
        size = float(self.file_size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
