# DataSentry

**CSV Data Quality & Validation CLI**

Python tabanlı, yerel çalışan ve modüler bir veri kalite doğrulama aracı.

> **Durum:** `v0.2.0`. Çekirdek kalite kontrolleri, YAML tabanlı dinamik yapılandırma motoru, şema doğrulama ve standart çıkış kodları hazır. JSON/HTML raporlama ve CI/CD otomasyonu [yol haritasında](#yol-haritası).

---

## Özellikler (v0.2.0)

| Özellik | Açıklama |
|---|---|
| **Dosya doğrulama** | CSV okunabilirlik, encoding (BOM) ve boş dosya kontrolleri |
| **Dinamik yapılandırma** | `--config kurallar.yaml` ile kontrol eşikleri, önem dereceleri ve kuralları yönetebilme |
| **Şema doğrulama** | Zorunlu sütun varlığı, sütun veri tipleri (`int`, `float`, `string`, `bool`) ve `nullable: false` kontrolleri |
| **Eksik değer analizi** | Sütun bazında boş/null/boşluk değer sayısı, yüzdesi, satır konumları ve tolerans eşiği |
| **Tekrarlanan kayıtlar** | Yinelenen satır tespiti, `NaN` duyarlı eşleşme haritası `(Kopya -> Orijinal)` ve tolerans eşiği |
| **Veri tipi kontrolü** | Sayısal sütunlardaki hatalı metin ve tip uyuşmazlıklarının tespiti |
| **Aykırı değer tespiti** | Sayısal sütunlarda IQR (Interquartile Range) yöntemiyle şüpheli uç değerler (düşük kardinalite korumalı) |
| **Terminal raporu** | Rich ile renkli ve okunabilir tablo çıktıları |
| **Standart çıkış kodları** | CI/CD süreçleri için `0` (Başarılı), `1` (Kalite Hatası), `2` (Girdi/Dosya Hatası) ayrımı |

> **Not:** Aykırı değer, otomatik olarak hatalı veri demek değildir. Bu kontrol şüpheli değerleri işaretler; nihai karar kullanıcıya aittir.

---

## Kurulum

### Gereksinimler

- Python 3.11 veya üstü

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/mfurkanerkan15/DataSentry.git
cd DataSentry

# 2. Sanal ortam oluştur
python -m venv .venv

# 3. Sanal ortamı aktif et
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Projeyi geliştirici modunda kur
pip install -e ".[dev]"
```

---

## Kullanım

```bash
# Temel analiz
datasentry check samples/valid_sample.csv

# YAML yapılandırma dosyası ile analiz
datasentry check samples/valid_sample.csv --config configs/example.yaml

# Farklı karakter kodlaması (Varsayılan: utf-8-sig)
datasentry check dosya.csv --encoding latin-1

# Farklı ayırıcı karakter (örneğin noktalı virgül)
datasentry check dosya.csv --delimiter ";"

# Raporda listelenecek maksimum örnek satır sayısı (Varsayılan: 100)
datasentry check dosya.csv --max-samples 50

# Sürüm bilgisi
datasentry --version
```

---

## Yapılandırma Dosyası Örneği (YAML)

`configs/example.yaml` örneği:

```yaml
checks:
  missing_values:
    enabled: true
    max_missing_percent: 5.0 # %5'e kadar olan eksik değerleri tolere et (INFO seviyesine düşür)

  duplicates:
    enabled: true
    max_duplicate_percent: 0.0

  schema:
    enabled: true
    required_columns:
      - id
      - yas
    columns:
      id:
        type: int
        nullable: false
      yas:
        type: int
        nullable: false

  outliers:
    enabled: true
    multiplier: 1.5
```

---

## Proje Yapısı

```
DataSentry/
├── .gitignore
├── pyproject.toml              # Paketleme, bağımlılıklar ve araç yapılandırmaları
├── README.md
├── configs/                    # Örnek kural yapılandırmaları
│   └── example.yaml
├── samples/                    # Örnek CSV verileri
│   ├── valid_sample.csv        # Temiz, geçerli veri örneği
│   └── invalid_sample.csv      # Hatalı/eksik veri örneği  
├── tests/
│   ├── test_config.py          # Yapılandırma ve YAML testleri
│   ├── test_schema.py          # Şema doğrulama testleri
│   └── test_validators.py      # Kalite kontrol birim testleri
└── datasentry/
    ├── __init__.py             # Paket tanımı ve sürüm bilgisi (v0.2.0)
    ├── __main__.py             # Modül giriş noktası
    ├── cli.py                  # CLI komutları ve terminal arayüzü (Typer + Rich)
    ├── config.py               # Pydantic v2 YAML kural ve doğrulama motoru
    ├── engine.py               # Doğrulama motoru (orkestrasyon)
    ├── loader.py               # CSV yükleme ve dosya özet mantığı
    ├── models.py               # Pydantic veri modelleri ve rapor sınıfları
    ├── exceptions.py           # Projeye özel hata sınıfları
    └── validators/
        ├── duplicates.py       # Tekrarlanan kayıt tespiti (NaN korumalı)
        ├── missing.py          # Eksik değer analizi
        ├── outliers.py         # IQR aykırı değer tespiti (Düşük kardinalite korumalı)
        ├── schema.py           # Zorunlu sütun, tip ve nullable şema kontrolü
        └── types.py            # Veri tipi uyuşmazlığı tespiti
```

Tasarım ilkesi: CLI yalnızca giriş ve sunum katmanıdır. Kalite kontrolleri CLI'dan bağımsız çalışır, böylece çekirdek motor başka arayüzlerde veya Python kodlarında yeniden kullanılabilir.

---

## Yol Haritası

| Sürüm | Odak | Planlanan özellikler | Durum |
|---|---|---|---|
| **v0.1.0** | Temel altyapı ve kontrol motoru | CLI, CSV yükleme, eksik değer, tekrar, tip ve aykırı değer kontrolleri, birim testler | ✅ Tamamlandı |
| **v0.2.0** | Dinamik kurallar ve şema | `--config kurallar.yaml` desteği, Pydantic ile kural doğrulama, zorunlu sütun, tip ve nullable şema doğrulaması, standart exit kodları (`0`, `1`, `2`) | ✅ Tamamlandı |
| **v0.3.0** | Raporlama ve dışa aktarma | `--report json` ve `--report html` (Jinja2 şablonları ile modern dashboard) desteği | 🔜 Planlandı |
| **v0.4.0** | Otomasyon ve CI/CD | GitHub Actions ile otomatik test (push/PR) ve pre-commit hook'ları (Ruff) | 🔜 Planlandı |

---

## Bilinen Sınırlamalar

- Yalnızca CSV desteklenir (Parquet/JSON yol haritasında değerlendirilecektir).
- Rapor çıktısı şimdilik yalnızca terminal tablolardır (JSON/HTML raporları v0.3.0 ile gelecektir).
- Veriyi otomatik düzeltme veya silme yapılmaz; araç yalnızca raporlar.

---

## Testleri Çalıştırma

```bash
# Tüm birim testlerini koştur
pytest -v

# Linter kontrolü
ruff check .
```

---

## Teknoloji Stack

| Teknoloji | Kullanım amacı |
|---|---|
| Python 3.11+ | Geniş ekosistem ve okunabilir kod |
| Pandas | CSV okuma ve veri analizi |
| Typer | Tip güvenli CLI komutları |
| Rich | Terminal tabloları ve renkli raporlama |
| Pydantic v2 | Veri ve yapılandırma modelleri |
| PyYAML | Yapılandırma dosyası ayrıştırma |
| Jinja2 | HTML raporlama şablonları |
| Pytest | Birim testleri |
| Ruff | Lint ve kod biçimlendirme |

---
