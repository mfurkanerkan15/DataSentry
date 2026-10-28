"""CSV dosya yükleme ve ön doğrulama modülü."""

from pathlib import Path
import pandas as pd

from datasentry.exceptions import (
    EmptyFileError,
    FileNotFoundError as DataSentryFileNotFoundError,
    FileReadError,
    InvalidCSVError,
)


def load_csv(path: str, encoding: str = "utf-8-sig", delimiter: str = ",") -> pd.DataFrame:
    """CSV dosyasını yükler ve temel doğrulamalardan geçirir.

    Args:
        path: CSV dosyasının yolu.
        encoding: Dosya karakter kodlaması (varsayılan: utf-8-sig / Excel BOM uyumlu).
        delimiter: Sütun ayırıcı karakter (varsayılan: virgül).

    Returns:
        pandas DataFrame olarak yüklenmiş veri.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        EmptyFileError: Dosya boşsa.
        FileReadError: Dosya okunamazsa.
        InvalidCSVError: Geçerli CSV formatında değilse.
    """
    file_path = Path(path)

    # 1. Dosya var mı?
    if not file_path.exists():
        raise DataSentryFileNotFoundError(str(file_path))

    # 2. Dosya fiziksel olarak boş mu? (0 Byte)
    if file_path.stat().st_size == 0:
        raise EmptyFileError(str(file_path))

    # 3. Dosyayı oku
    try:
        df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
    except UnicodeDecodeError as e:
        raise FileReadError(str(file_path), f"Karakter kodlama hatası: {e}. Farklı bir encoding (--encoding latin-1) deneyin.") from e
    except PermissionError as e:
        raise FileReadError(str(file_path), f"Erişim izni reddedildi: {e}") from e
    except pd.errors.ParserError as e:
        raise InvalidCSVError(str(file_path), f"CSV ayrıştırma hatası: {e}") from e
    except Exception as e:
        raise FileReadError(str(file_path), str(e)) from e

    # 4. DataFrame boş mu? (başlık var ama 0 satır veri var)
    if df.empty:
        raise EmptyFileError(str(file_path))

    return df


def get_file_summary(df: pd.DataFrame, path: str) -> dict:
    """Yüklenen CSV hakkında özet bilgi döndürür.

    Args:
        df: Yüklenmiş DataFrame.
        path: Dosya yolu (gösterim için).

    Returns:
        Dosya özet bilgilerini içeren sözlük.
    """
    file_path = Path(path)
    size_bytes = file_path.stat().st_size

    return {
        "dosya_adi": file_path.name,
        "dosya_yolu": str(file_path.resolve()),
        "dosya_boyutu_bytes": size_bytes,
        "dosya_boyutu_kb": round(size_bytes / 1024, 2),
        "satir_sayisi": len(df),
        "sutun_sayisi": len(df.columns),
        "sutunlar": list(df.columns),
    }