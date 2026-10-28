# DataSentry

CSV Data Quality & Validation CLI

Python tabanli, yerel calisan, yapilandirilabilir veri kalite araci.

---

## Ozellikler

| Ozellik | Aciklama |
|---|---|
| Dosya dogrulama | CSV okunabilir mi, gerekli sutunlar var mi? |
| Eksik deger analizi | Sutun bazinda bos deger sayisi ve yuzdesi |
| Tekrarlanan kayitlar | Yinelenen satirlarin sayisi ve orani |
| Veri tipi kontrolu | Beklenen tiplerle uyusmayan degerleri bulma |
| Sema dogrulama | Zorunlu sutunlar, tipler ve nullable kurallari |
| Aykiri deger tespiti | Sayisal sutunlarda IQR yontemiyle suphe li degerleri isaretleme |
| Raporlama | Terminal, JSON ve HTML ciktisi |
| CI/CD modu | Belirlenen kurallar basarisizsa sifir olmayan cikis kodu |

---

## Kurulum

### Gereksinimler

- Python 3.11 veya ustu

### Adimlar

```bash
# 1. Repoyu klonla
git clone https://github.com/mfurkanerkan15/DataSentry.git
cd DataSentry

# 2. Sanal ortam olustur
python -m venv .venv

# 3. Sanal ortami aktif et
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Projeyi kur
pip install -e ".[dev]"
```

---

## Kullanim

### Temel kontrol

```bash
datasentry check samples/valid_sample.csv
```

### Ornek cikti

```
+-------------- DataSentry Check ---------------+
| Dosya: samples/valid_sample.csv                |
+------------------------------------------------+

         Dosya Ozeti
+----------------+------------------+
| Ozellik        | Deger            |
+----------------+------------------+
| Dosya Adi      | valid_sample.csv |
| Boyut          | 0.55 KB          |
| Satir Sayisi   | 10               |
| Sutun Sayisi   | 6                |
+----------------+------------------+
```

### Secenekler

```bash
# Farkli karakter kodlamasi
datasentry check dosya.csv --encoding latin-1

# Farkli ayirici karakter (ornegin noktali virgul)
datasentry check dosya.csv --delimiter ";"

# Versiyon bilgisi
datasentry --version
```

---

## Proje Yapisi

```
DataSentry/
├── .gitignore              # Git tarafından takip edilmeyecek dosyalar
├── pyproject.toml          # Proje paketleme, bağımlılıklar ve araç yapılandırmaları
├── README.md               # Proje dökümantasyonu
├── samples/                # Örnek CSV test verileri
│   ├── valid_sample.csv    # Temiz, geçerli veri örneği
│   └── invalid_sample.csv  # Hatalı/eksik veri örneği (testler için)
└── src/
    └── datasentry/         # Kaynak kod paketi
        ├── __init__.py     # Paket tanımı ve sürüm bilgisi
        ├── cli.py          # CLI komutları ve terminal arayüzü (Typer + Rich)
        ├── loader.py       # CSV yükleme, okuma ve dosya boyutu/özet mantığı
        └── exceptions.py   # Projeye özel hata sınıfları
```

---

## Teknoloji

| Teknoloji | Neden? |
|---|---|
| Python 3.11+ | Genis ekosistem ve okunabilir kod |
| Pandas | CSV okuma ve veri analizi |
| Typer | Tip guvenli, anlasilir CLI komutlari |
| Rich | Tablo ve terminal raporlari |
| Pydantic | Sema ve yapilandirma dogrulama |
| Jinja2 | HTML raporu olusturma |
| Pytest | Birim ve entegrasyon testleri |
| Ruff | Lint ve kod bicimlendirme |

---

## Lisans

MIT
