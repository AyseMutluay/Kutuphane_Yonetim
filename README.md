# Online Kütüphane Yönetim Sistemi

Üniversite öğrencisinin kitap aradığı, ödünç aldığı ve iade ettiği küçük bir kütüphane. Stok izlenir, geciken ödünçler raporlanır, yönetici kitap ekler.

Diyagramlar ile kod aynı modeli kullanır.

## Diyagramlar

Kaynaklar `diyagramlar/` altındadır. PNG ve SVG çıktıları `diyagramlar/cikti/` içindedir.

- `sinif.puml` — sınıf diyagramı, ilişkiler ve çokluklar
- `nesne.puml` — Ali Kaya'nın 1 Ekim 2026'da aldığı kitabın 17 Ekim anı
- `paket.puml` — üç mantıksal paket
- `deployment.puml` — tarayıcı, Flask uygulaması ve SQLite

## Paketler

- `domain_models` — `Kullanici`, `Ogrenci`, `Yonetici`, `Kitap`, `OduncIslemi`, `ICezaHesapla`
- `services` — `KutuphaneService`, iki ceza sınıfı, `Depo`
- `web_layer` — Flask sayfaları

Ok yönü tektir: `web_layer` servisi çağırır, servis alan modelini kullanır. Web katmanı `library.db` dosyasını açmaz.

`ICezaHesapla` alan paketindedir. `OduncIslemi` yalnızca sözleşmeyi bilir. `StandartOgrenciCezasi` ve `AkademikIndirimCezasi` servis paketindedir. Ters bağımlılık oluşmaz.

## İş kuralları

- Ödünç süresi 14 gündür.
- Rafta kopya yoksa ödünç verilmez.
- İade, kopyayı rafa geri koyar.
- `mevcut_stok = toplam_stok - açık ödünç sayısı`
- Gecikme saklanmaz. İade tarihi boş ve son teslim bugünden önceyse ödünç gecikmiştir.
- `/aktif_odunc_sayisi` açık ödünçlerden hesaplanır.
- Standart ceza günde 2 TL, akademik indirim günde 1 TL'dir.

## Çalıştırma

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m web_layer.app
```

Tarayıcıda `http://127.0.0.1:5000` adresini açın.

İlk açılışta `library.db` oluşur ve nesne diyagramındaki kayıtları yükler. Diyagram anına dönmek için bu dosyayı silip uygulamayı yeniden başlatın.

## Demo hesapları

Uygulama giriş sayfasıyla açılır. Kullanıcı adı öğrenci numarası, personel kodu veya e-postadır.

- Ali Kaya, öğrenci: `2024101` / `ali123` — gecikmiş ödünç `101`
- Ece Arslan, öğrenci: `2024088` / `ece123` — süresi devam eden ödünç
- Selin Demir, yönetici: `P-07` / `yonetici` — kitap ekler, stok günceller, gecikme raporunu açar
