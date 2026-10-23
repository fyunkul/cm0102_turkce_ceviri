# CM 01/02 Türkçe Çeviri Editörü

CM 01/02 için İngilizce–Türkçe çeviri kontrolü ve eski sürüm (v65) çeviri alternatifleriyle karşılaştırma projesi.

## Durum

- Ana çeviri kaynağı: `language_EN_TR_v66.csv` (10.010 kayıt).
- v65 İngilizce karşılaştırması, alternatif çeviri adayları ve denetim raporları.
- Son masaüstü editör: koyu temalı v8 (Python/Tkinter).
- Metin kutuları alt alta, üç tema, durum etiketleri, otomatik yedek, değişken ve karakter kontrolü.
- CSV düzenleme desteklenir; oyun `.ldb` dosyasına doğrudan yazma henüz desteklenmez.

## Dosya düzeni (hedef)

- `editor/` — uygulama ve başlatıcı
- `data/` — çeviri verileri ve eşleştirme raporları
- `reports/` — belirsiz eşleşmeler ve denetim sonuçları
- `archive/` — eski editör sürümleri
- `docs/` — kullanım notları ve tasarım

**Not:** Bu depoya şu an yalnızca proje açıklaması eklenmiştir. Kaynak kodu ve veri dosyalarının GitHub'a yüklendiği henüz doğrulanmamıştır. Yerel kaynak arşivi ayrı sunulmaktadır.

## Kullanım

Python 3 gerekir. Tam editör arşivinde `baslat.bat` çalıştırılarak başlatılabilir.

## Dikkat

Çeviri alternatiflerinin bir kısmı yalnızca aday niteliğindedir. Oyun yer tutucuları (`<%s ...>` gibi) korunmadan uygulamayın. Telif hakkına tabi oyun ikili dosyalarını herkese açık depoya koymadan önce paylaşım hakkını kontrol edin.
