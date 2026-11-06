# DataSentry

**CSV Data Quality & Validation CLI**

Python tabanlı, yerel çalışan ve modüler bir veri kalite doğrulama aracı.

> **Durum:** `v0.4.0`. Çekirdek kalite kontrolleri, YAML tabanlı dinamik yapılandırma motoru, şema doğrulama, standart çıkış kodları, modüler JSON dışa aktarma ve Jinja2 tabanlı modern çevrimdışı HTML dashboard hazır. GitHub Actions CI pipeline (Python 3.11 & 3.12 matrix) ve pre-commit hook'ları (Ruff lint + format) eklenmiştir.

---

## Özellikler (v0.4.0)

| Özellik | Açıklama |
|---|---|
| **Dosya doğrulama** | CSV okunabilirlik, encoding (BOM) ve boş dosya kontrolleri |
| **Dinamik yapılandırma** | `--config kurallar.yaml` ile kontrol eşikleri, önem dereceleri ve kuralları yönetebilme |
| **Şema doğrulama** | Zorunlu sütun varlığı, sütun veri tipleri (`int`, `float`, `string`, `bool`) ve `nullable: false` kontrolleri |
| **Eksik değer analizi** | Sütun bazında boş/null/boşluk değer sayısı, yüzdesi, satır konumları ve tolerans eşiği |
| **Tekrarlanan kayıtlar** | Yinelenen satır tespiti, `NaN` duyarlı eşleşme haritası `(Kopya -> Orijinal)` ve tolerans eşiği |
| **Veri tipi kontrolü** | Sayısal sütunlardaki hatalı metin ve tip uyuşmazlıklarının tespiti |
| **Aykırı değer tespiti** | Sayısal ve sayısal ağırlıklı sütunlarda IQR (Interquartile Range) yöntemiyle şüpheli uç değerler (bozuk metin filtreleme ve düşük kardinalite korumalı) |
| **Terminal raporu** | Rich ile renkli ve okunabilir tablo çıktıları |
| **JSON dışa aktarma** | `--format json` veya `-o rapor.json` ile CI/CD, otomasyon ve `jq` uyumlu kararlı şema çıktısı |
| **HTML Dashboard** | `--format html` veya `-o rapor.html` ile tek dosya çalışan, harici CDN bağımsız modern ve interaktif web raporu |
| **Yol gizliliği** | Raporlarda varsayılan olarak yalnızca dosya adı gösterilir; tam yol için `--show-path` bayrağı mevcuttur |
| **Kalite Skoru (%)** | Ağırlıklı ihlal oranına dayalı %0.00 - %100.00 arası genel veri kalite puanı |
| **Standart çıkış kodları** | CI/CD süreçleri için `0` (Başarılı), `1` (Kalite Hatası), `2` (Girdi/Dosya Hatası) ayrımı |
| **GitHub Actions CI** | Push ve PR'larda Python 3.11 & 3.12 matrixi üzerinde otomatik lint + test |
| **Pre-commit hook'ları** | Commit öncesi otomatik Ruff lint ve format kontrolü |

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

### Temel Doğrulama

```bash
# Terminalde renkli tablo raporu
datasentry check samples/valid_sample.csv

# YAML yapılandırma dosyası ile analiz
datasentry check samples/valid_sample.csv --config configs/example.yaml

# Tam dosya yolunu raporda göstermek için (--show-path)
datasentry check samples/valid_sample.csv --show-path

# Farklı karakter kodlaması (Varsayılan: utf-8-sig)
datasentry check dosya.csv --encoding latin-1

# Farklı ayırıcı karakter (örneğin noktalı virgül)
datasentry check dosya.csv --delimiter ";"

# Raporda listelenecek maksimum örnek satır sayısı (Varsayılan: 100)
datasentry check dosya.csv --max-samples 50

# Sürüm bilgisi
datasentry --version
```

### Raporlama ve Dışa Aktarma (v0.3.0 — v0.4.0)

```bash
# HTML dashboard raporu üret (Uzantıdan otomatik tespit)
datasentry check samples/invalid_sample.csv -o rapor.html

# JSON raporu üret (CI/CD ve otomasyon için)
datasentry check samples/invalid_sample.csv -o rapor.json

# -f html verildiğinde varsayılan 'datasentry_report.html' üretilir
datasentry check samples/valid_sample.csv -f html

# Tam yol bilgisiyle JSON raporu oluştur
datasentry check samples/valid_sample.csv -o rapor.json --show-path

# Sessiz mod (-q) ve doğrudan stdout'a saf JSON (jq ile pipeline kullanımı)
datasentry check samples/valid_sample.csv -f json -q | jq .quality_score
```

---

## Kalite Skoru Formülü (Quality Score)

DataSentry, veri setinin genel kalite sağlığını tek bir yüzde skoru (%0.00 - %100.00) olarak özetler:

$$\text{Kalite Skoru} = \max(0.0, 100.0 - \text{Toplam Ceza Puanı})$$

**Ceza Puanı Hesaplama Mantığı:**
- **Satır Bazlı Kritik Hatalar (`ERROR`):** $\left(\frac{\text{Etkilenen Satır}}{\text{Toplam Satır}}\right) \times 40.0$
- **Satır Bazlı Uyarılar (`WARNING`):** $\left(\frac{\text{Etkilenen Satır}}{\text{Toplam Satır}}\right) \times 15.0$
- **Şema / Tablo Düzeyi Hatalar (`ERROR`, `count == 0`):** Sabit 20.0 puan (ör. zorunlu sütun eksikliği)
- **Şema / Tablo Düzeyi Uyarılar (`WARNING`, `count == 0`):** Sabit 5.0 puan
- **Bilgilendirme Bulguları (`INFO`):** 0.0 puan (ceza uygulanmaz)

Skor kartı renklendirmesinde kritik hata varlığı (`is_valid == False`) dikkate alınır: Kritik hata varsa skor asla yeşil gösterilmez (en fazla sarı). Kritik hata yoksa $\ge 90$ yeşil, $\ge 70$ sarı, altı kırmızıdır.

---

## Rapor Formatları

### 1. HTML Dashboard
- **Çevrimdışı Çalışma:** CDN, Google Fonts veya harici JS/CSS gerektirmez. Güvenli ortamlarda (air-gapped) tek dosya olarak açılabilir.
- **İnteraktif Arayüz:** Her kontrolün durum rozeti (`PASSED`, `WARNING`, `FAILED`), etkilenen satırların Excel indeksli konumları, açılır/kapanır (`<details>`) bulgu tabloları.
- **Güvenlik (XSS Koruması):** Jinja2 autoescape ile tüm veri değerleri HTML entity formatında escape edilir.

### 2. JSON Çıktısı Örneği
```json
{
  "datasentry_version": "0.4.0",
  "timestamp": "2026-11-02T13:00:00+00:00",
  "execution_time_ms": 14.8,
  "quality_score": 96.0,
  "is_valid": true,
  "summary": {
    "file_name": "data.csv",
    "file_path": "data.csv",
    "file_size_bytes": 10240,
    "file_size_human": "10.00 KB",
    "total_rows": 100,
    "total_columns": 5,
    "total_errors": 0,
    "total_warnings": 1
  },
  "results": [
    {
      "name": "Eksik Deger Analizi",
      "description": "Sutunlardaki bos veya eksik degerleri tespit eder",
      "status": "PASSED",
      "total_affected_rows": 0,
      "issues": []
    }
  ]
}
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
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI pipeline (Python 3.11 & 3.12 matrix)
├── .pre-commit-config.yaml     # Pre-commit hook'ları (Ruff lint + format)
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
│   ├── test_reporters.py       # JSON, HTML, skor ve CLI entegrasyon testleri
│   ├── test_schema.py          # Şema doğrulama testleri
│   └── test_validators.py      # Kalite kontrol birim testleri
└── datasentry/
    ├── __init__.py             # Paket tanımı ve sürüm bilgisi (v0.4.0)
    ├── __main__.py             # Modül giriş noktası
    ├── cli.py                  # CLI komutları ve terminal arayüzü (Typer + Rich)
    ├── config.py               # Pydantic v2 YAML kural ve doğrulama motoru
    ├── engine.py               # Doğrulama motoru (orkestrasyon, süre ve skor ölçümü)
    ├── loader.py               # CSV yükleme ve dosya özet mantığı
    ├── models.py               # Pydantic veri modelleri, skor hesabı ve rapor sınıfları
    ├── exceptions.py           # Projeye özel hata sınıfları
    ├── reporters/              # Modüler raporlama mimarisi
    │   ├── __init__.py         # Dışa aktarımlar ve kayıt fonksiyonları
    │   ├── base.py             # BaseReporter soyut sınıfı ve registry
    │   ├── console.py          # Rich terminal raporlayıcısı
    │   ├── html_reporter.py    # Jinja2 tek dosya offline HTML dashboard raporlayıcısı
    │   ├── json_reporter.py    # Standart kararlı JSON raporlayıcısı
    │   └── templates/
    │       └── report.html.j2  # Responsive, karanlık/aydınlık uyumlu HTML şablonu
    └── validators/
        ├── duplicates.py       # Tekrarlanan kayıt tespiti (NaN korumalı)
        ├── missing.py          # Eksik değer analizi
        ├── outliers.py         # IQR aykırı değer tespiti (Bozuk metin ve düşük kardinalite korumalı)
        ├── schema.py           # Zorunlu sütun, tip ve nullable şema kontrolü
        └── types.py            # Veri tipi uyuşmazlığı tespiti
```

Tasarım ilkesi: CLI yalnızca giriş ve sunum katmanıdır. Raporlayıcılar ve kalite kontrolleri CLI'dan bağımsız çalışır, böylece çekirdek motor ve raporlar başka kütüphanelerde veya Python kodlarında doğrudan çağrılabilir.

---

## Yol Haritası

| Sürüm | Odak | Planlanan özellikler | Durum |
|---|---|---|---|
| **v0.1.0** | Temel altyapı ve kontrol motoru | CLI, CSV yükleme, eksik değer, tekrar, tip ve aykırı değer kontrolleri, birim testler | ✅ Tamamlandı |
| **v0.2.0** | Dinamik kurallar ve şema | `--config kurallar.yaml` desteği, Pydantic ile kural doğrulama, zorunlu sütun, tip ve nullable şema doğrulaması, standart exit kodları (`0`, `1`, `2`) | ✅ Tamamlandı |
| **v0.3.0** | Raporlama ve dışa aktarma | `--output` ve `--format` ile JSON çıktısı ve Jinja2 şablonları ile modern HTML dashboard desteği | ✅ Tamamlandı |
| **v0.4.0** | Otomasyon ve CI/CD | GitHub Actions ile otomatik test (push/PR) ve pre-commit hook'ları (Ruff) | ✅ Tamamlandı |

---

## Bilinen Sınırlamalar

- Yalnızca CSV desteklenir (Parquet/JSON yol haritasında değerlendirilecektir).
- Veriyi otomatik düzeltme veya silme yapılmaz; araç yalnızca raporlar.

---

## Testleri Çalıştırma

```bash
# Tüm birim ve entegrasyon testlerini koştur (65 test)
pytest -v

# Linter kontrolü
ruff check .
```

---

## CI/CD ve Geliştirici Araçları (v0.4.0)

### GitHub Actions CI

Her `push` ve `main`'e açılan `pull_request`'te otomatik olarak çalışır:

- Python **3.11** ve **3.12** matrixi üzerinde paralel test
- `ruff check .` → lint
- `pytest -v --tb=short` → birim ve entegrasyon testleri

Workflow dosyası: `.github/workflows/ci.yml`

### Pre-commit Hook'ları

Commit öncesi otomatik Ruff lint ve format kontrolü. İlk kurulum:

```bash
# pre-commit kur (dev bağımlılığı olarak zaten pyproject.toml'da)
pip install -e ".[dev]"

# Hook'ları aktif et (repo başına bir kez çalıştırılır)
pre-commit install

# Tüm dosyalarda manuel olarak çalıştır
pre-commit run --all-files
```

Yapılandırma dosyası: `.pre-commit-config.yaml`

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
| Pytest | Birim ve entegrasyon testleri |
| Ruff | Lint ve kod biçimlendirme |

---
