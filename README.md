# DataSentry

CSV Data Quality & Validation CLI

Python tabanlı, yerel çalışan, modüler ve yapılandırılabilir veri kalite doğrulama aracı.

---

## Özellikler

| Özellik | Açıklama |
|---|---|
| Dosya Doğrulama | CSV okunabilirlik, encoding (BOM) ve boş dosya kontrolleri |
| Eksik Değer Analisi | Sütun bazında boş/null değer sayısı, yüzdesi ve satır konumları |
| Tekrarlanan Kayıtlar | Yinelenen satır tespiti ve ikiz satır eşleşme haritası `(Kopya -> Orijinal)` |
| Veri Tipi Kontrolü | Sayısal sütunlardaki hatalı metin ve tip uyuşmazlıklarının tespiti |
| Aykırı Değer Tespiti | Sayısal sütunlarda IQR (Interquartile Range) yöntemiyle şüpheli uç değerler |
| Zengin Terminal Raporu | Rich kütüphanesi ile renkli, anlaşılır ve detaylı tablo çıktıları |
| CI/CD Modu | Otomasyon hatasında 1 çıkış kodu (Exit Code 1) ile pipeline durdurma |

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

### Komut Seçenekleri

```bash
# Farklı karakter kodlaması (Varsayılan: utf-8-sig)
datasentry check dosya.csv --encoding latin-1

# Farklı ayırıcı karakter (örneğin noktalı virgül)
datasentry check dosya.csv --delimiter ";"

# Raporda listelenecek maksimum örnek satır sayısını belirleme (Varsayılan: 100)
datasentry check dosya.csv --max-samples 50

# Sürüm bilgisi
datasentry --version
```

---

## Proje Yapısı

```text
DataSentry/
├── .gitignore                  # Git tarafından takip edilmeyecek dosyalar
├── pyproject.toml              # Proje paketleme, bağımlılıklar ve araç yapılandırmaları
├── README.md                   # Proje dökümantasyonu
├── samples/                    # Örnek CSV test verileri
│   ├── valid_sample.csv        # Temiz, geçerli veri örneği
│   ├── invalid_sample.csv      # Hatalı/eksik veri örneği
│   └── finans_ilk_deneme.csv   # Gerçek dünya finansal verisi örneği
├── tests/                      # Birim testleri
│   └── test_validators.py      # Kalite kontrol motoru Pytest birim testleri
└── datasentry/                 # Kaynak kod paketi
    ├── __init__.py             # Paket tanımı ve sürüm bilgisi
    ├── cli.py                  # CLI komutları ve terminal arayüzü (Typer + Rich)
    ├── engine.py               # Doğrulama motoru (orkestrasyon)
    ├── loader.py               # CSV yükleme ve dosya özet mantığı
    ├── models.py               # Pydantic veri modelleri ve rapor sınıfları
    ├── exceptions.py           # Projeye özel hata sınıfları
    └── validators/             # Kalite kontrol fonksiyonları
        ├── __init__.py
        ├── missing.py          # Eksik değer analizi
        ├── duplicates.py       # Tekrarlanan kayıt tespiti ve eşleşme haritası
        ├── types.py            # Veri tipi uyuşmazlığı tespiti
        └── outliers.py         # IQR aykırı değer tespiti
```

---

## Testleri Çalıştırma

Projedeki birim testleri koşturmak için:

```bash
pytest -v
```

---

## Teknoloji Stack

| Teknoloji | Kullanım Amacı |
|---|---|
| Python 3.11+ | Geniş ekosistem ve tip güvenliği |
| Pandas | Yüksek performanslı CSV ve veri analizi |
| Typer | Modern ve tip güvenli CLI komut yapısı |
| Rich | Gelişmiş terminal tabloları ve renkli raporlama |
| Pydantic v2 | Veri modelleri, şema ve rapor doğrulama |
| Pytest | Birim (Unit) test mimarisi |
| Ruff | Linting ve kod biçimlendirme |

---

## Lisans

MIT