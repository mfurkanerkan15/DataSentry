"""DataSentry ortak sonuç ve veri modelleri."""

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
        """Bu kontrolden etkilenen toplam kayıt/satır sayısı."""
        return sum(i.count for i in self.issues)

    @property
    def has_errors(self) -> bool:
        """Kritik hata var mı?"""
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Uyarı var mı?"""
        return any(i.severity == Severity.WARNING for i in self.issues)


class ValidationReport(BaseModel):
    """Tüm kontrolleri kapsayan nihai doğrulama raporu."""

    file_name: str
    file_path: str
    file_size_bytes: int = Field(0, description="Bayt cinsinden dosya boyutu")
    total_rows: int
    total_columns: int
    results: list[CheckResult] = Field(default_factory=list)

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
