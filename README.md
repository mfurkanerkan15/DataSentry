# DataSentry

**CSV Data Quality & Validation CLI**

Python tabanlı, yerel çalışan ve modüler bir veri kalite doğrulama aracı.

> **Durum:** `v0.1.0` (MVP). Çekirdek kontroller ve terminal raporu hazır. YAML yapılandırma, JSON/HTML raporlama ve CI/CD otomasyonu [yol haritasında](#yol-haritası).

---

## Özellikler (v0.1.0)

| Özellik | Açıklama |
|---|---|
| Dosya doğrulama | CSV okunabilirlik, encoding (BOM) ve boş dosya kontrolleri |
| Eksik değer analizi | Sütun bazında boş/null değer sayısı, yüzdesi ve satır konumları |
| Tekrarlanan kayıtlar | Yinelenen satır tespiti ve eşleşme haritası `(Kopya -> Orijinal)` |
| Veri tipi kontrolü | Sayısal sütunlardaki hatalı metin ve tip uyuşmazlıklarının tespiti |
| Aykırı değer tespiti | Sayısal sütunlarda IQR (Interquartile Range) yöntemiyle şüpheli uç değerler |
| Terminal raporu | Rich ile renkli ve okunabilir tablo çıktıları |
| Çıkış kodu | Kalite sorunu bulunduğunda `1` çıkış kodu ile CI süreçlerinde kullanılabilir |

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
datasentry check samples/valid_sample.csv  #datasentry check <dosya yolu>

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

## Proje Yapısı

```
DataSentry/
├── .gitignore
├── pyproject.toml              # Paketleme, bağımlılıklar ve araç yapılandırmaları
├── README.md
├── samples/                    # Örnek CSV verileri
│   ├── valid_sample.csv        # Temiz, geçerli veri örneği
│   └── invalid_sample.csv      # Hatalı/eksik veri örneği  
├── tests/
│   └── test_validators.py      # Kalite kontrol birim testleri
└── datasentry/
    ├── __init__.py             # Paket tanımı ve sürüm bilgisi
    ├── cli.py                  # CLI komutları ve terminal arayüzü (Typer + Rich)
    ├── engine.py               # Doğrulama motoru (orkestrasyon)
    ├── loader.py               # CSV yükleme ve dosya özet mantığı
    ├── models.py               # Pydantic veri modelleri ve rapor sınıfları
    ├── exceptions.py           # Projeye özel hata sınıfları
    └── validators/
        ├── missing.py          # Eksik değer analizi
        ├── duplicates.py       # Tekrarlanan kayıt tespiti
        ├── types.py            # Veri tipi uyuşmazlığı tespiti
        └── outliers.py         # IQR aykırı değer tespiti
```

Tasarım ilkesi: CLI yalnızca giriş ve sunum katmanıdır. Kalite kontrolleri CLI'dan bağımsız çalışır, böylece çekirdek motor başka arayüzlerde de yeniden kullanılabilir.

---

## Yol Haritası

| Sürüm | Odak | Planlanan özellikler | Durum |
|---|---|---|---|
| **v0.1.0** | Temel altyapı ve kontrol motoru | CLI, CSV yükleme, eksik değer, tekrar, tip ve aykırı değer kontrolleri, birim testler | ✅ Tamamlandı |
| **v0.2.0** | Dinamik kurallar | `--config kurallar.yaml` desteği, Pydantic ile kural doğrulama (ör. negatif eşik reddi), zorunlu sütun ve nullable kontrolü için şema doğrulama | 🔜 Planlandı |
| **v0.3.0** | Raporlama ve entegrasyon | `--report json` ve `--report html` (Jinja2), kural bazlı çıkış kodları (`0` başarılı, `1` kalite hatası, `2` kullanım/dosya hatası) | 🔜 Planlandı |
| **v0.4.0** | Otomasyon | GitHub Actions ile otomatik test (push/PR), pre-commit hook'ları (Ruff) | 🔜 Planlandı |

Planlanan örnek yapılandırma (v0.2.0 hedefi, henüz çalışmaz):

```yaml
checks:
  missing_values:
    enabled: true
    max_missing_percent: 5
  duplicates:
    enabled: true
    max_duplicate_percent: 0
  schema:
    required_columns: [customer_id, age, monthly_charges]
  outliers:
    method: iqr
    severity: warning
```

---

## Bilinen Sınırlamalar

- Yalnızca CSV desteklenir.
- Kalite kuralları şu an kod içinde sabittir; yapılandırma v0.2.0 ile gelecek.
- Rapor çıktısı şimdilik yalnızca terminaldir.
- Veriyi otomatik düzeltme veya silme yapılmaz; araç yalnızca raporlar.

---

## Testleri Çalıştırma

```bash
pytest -v
```

---

## Teknoloji Stack

| Teknoloji | Kullanım amacı |
|---|---|
| Python 3.11+ | Geniş ekosistem ve okunabilir kod |
| Pandas | CSV okuma ve veri analizi |
| Typer | Tip güvenli CLI komutları |
| Rich | Terminal tabloları ve renkli raporlama |
| Pydantic v2 | Veri modelleri ve doğrulama |
| Pytest | Birim testleri |
| Ruff | Lint ve kod biçimlendirme |

---
