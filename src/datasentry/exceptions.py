"""DataSentry özel hata sınıfları."""


class DataSentryError(Exception):
    """DataSentry temel hata sınıfı."""


class FileNotFoundError(DataSentryError):
    """Belirtilen dosya bulunamadığında fırlatılır."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Dosya bulunamadı: {path}")


class FileReadError(DataSentryError):
    """Dosya okunamadığında fırlatılır (bozuk encoding, izin hatası vb.)."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Dosya okunamadı: {path} — {reason}")


class EmptyFileError(DataSentryError):
    """Dosya boş olduğunda fırlatılır."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Dosya boş: {path}")


class InvalidCSVError(DataSentryError):
    """Dosya geçerli bir CSV formatında olmadığında fırlatılır."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Geçersiz CSV: {path} — {reason}")
