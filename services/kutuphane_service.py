from dataclasses import dataclass
from datetime import date, timedelta

from domain_models.ceza import ICezaHesapla
from domain_models.kitap import Kitap
from domain_models.kullanici import Ogrenci, Yonetici
from domain_models.odunc import OduncIslemi
from services.ceza_stratejisi import strateji_sec
from services.depo import Depo, VARSAYILAN_DB
from services.gorunum import Hesap, OduncHareketi

ODUNC_SURESI_GUN = 14


@dataclass(frozen=True)
class GecikmeKaydi:
    ogrenci_ad: str
    ogrenci_no: str
    baslik: str
    son_teslim_tarihi: date
    geciken_gun: int
    ceza: float
    strateji_adi: str


class KutuphaneService:
    def __init__(self, depo: Depo) -> None:
        self.depo = depo

    def kitap_ara(self, kelime: str) -> list[Kitap]:
        return self.depo.kitap_ara(kelime)

    def odunc_ver(self, ogrenci_id: int, kitap_id: int) -> OduncIslemi:
        kisi = self.depo.kullanici_getir(ogrenci_id)
        if not isinstance(kisi, Ogrenci):
            raise ValueError("Ödünç alma yalnızca öğrenci hesabıyla yapılır.")
        if self.depo.kitap_getir(kitap_id) is None:
            raise ValueError("Kitap bulunamadı.")
        bugun = date.today()
        return self.depo.yeni_odunc(ogrenci_id, kitap_id, bugun, bugun + timedelta(days=ODUNC_SURESI_GUN))

    def kitap_ekle(self, isbn: str, baslik: str, yazar: str, stok: int) -> Kitap:
        isbn = isbn.strip()
        baslik = baslik.strip()
        yazar = yazar.strip()
        if not isbn or not baslik or not yazar:
            raise ValueError("ISBN, başlık ve yazar zorunludur.")
        if stok < 1:
            raise ValueError("Yeni kitabın en az bir kopyası olmalı.")
        kitap = Kitap(0, isbn, baslik, yazar, stok, stok)
        kitap.id = self.depo.kitap_ekle(kitap)
        return kitap

    def stok_guncelle(self, kitap_id: int, yeni_stok: int) -> Kitap:
        return self.depo.toplam_stok_ayarla(kitap_id, yeni_stok)

    def gecikmeleri_raporla(self, strateji: ICezaHesapla) -> list[GecikmeKaydi]:
        kayitlar = []
        for odunc, ogrenci, kitap in self.depo.geciken_oduncler(date.today()):
            gun = odunc.gecikme_gun_hesapla()
            kayitlar.append(
                GecikmeKaydi(
                    ogrenci_ad=ogrenci.ad_soyad,
                    ogrenci_no=ogrenci.ogrenci_no,
                    baslik=kitap.baslik,
                    son_teslim_tarihi=odunc.son_teslim_tarihi,
                    geciken_gun=gun,
                    ceza=odunc.ceza_hesapla(strateji),
                    strateji_adi=strateji.ad,
                )
            )
        return kayitlar

    def odunc_hareketleri(self) -> list[OduncHareketi]:
        hareketler = []
        for odunc, ogrenci, kitap in self.depo.tum_oduncler():
            hareketler.append(
                OduncHareketi(
                    ogrenci_ad=ogrenci.ad_soyad,
                    ogrenci_no=ogrenci.ogrenci_no,
                    baslik=kitap.baslik,
                    yazar=kitap.yazar,
                    alis_tarihi=odunc.alis_tarihi,
                    son_teslim_tarihi=odunc.son_teslim_tarihi,
                    iade_tarihi=odunc.iade_tarihi,
                    durum=odunc.durum,
                    geciken_gun=odunc.gecikme_gun_hesapla(),
                )
            )
        return hareketler

    def ogrencinin_oduncleri(self, ogrenci_id: int) -> list[tuple[OduncIslemi, Kitap]]:
        kisi = self.depo.kullanici_getir(ogrenci_id)
        if not isinstance(kisi, Ogrenci):
            raise ValueError("Ödünç listesi öğrenci hesabına aittir.")
        return self.depo.ogrencinin_oduncleri(ogrenci_id)

    def giris_yap(self, kimlik: str, parola: str) -> Hesap:
        if not kimlik.strip() or not parola:
            raise ValueError("Kullanıcı adı ve parola zorunludur.")
        kisi = self.depo.giris_dene(kimlik, parola)
        if kisi is None:
            raise ValueError("Kullanıcı adı veya parola hatalı.")
        return self._hesap(kisi)

    def iade_et(self, odunc_id: int, ogrenci_id: int) -> OduncIslemi:
        kayitlar = self.depo.ogrencinin_oduncleri(ogrenci_id)
        sahip = any(odunc.id == odunc_id and odunc.iade_tarihi is None for odunc, _kitap in kayitlar)
        if not sahip:
            raise ValueError("Bu ödünç kaydı size ait değil.")
        return self.depo.iade_kaydet(odunc_id, date.today())

    def hesap_getir(self, kullanici_id: int) -> Hesap | None:
        kisi = self.depo.kullanici_getir(kullanici_id)
        if kisi is None:
            return None
        return self._hesap(kisi)

    def hesaplari_listele(self) -> list[Hesap]:
        return [self._hesap(kisi) for kisi in self.depo.kullanicilari_listele()]

    def strateji(self, anahtar: str) -> ICezaHesapla:
        return strateji_sec(anahtar)

    def _hesap(self, kisi: Ogrenci | Yonetici) -> Hesap:
        if isinstance(kisi, Ogrenci):
            return Hesap(kisi.id, kisi.ad_soyad, kisi.eposta, "ogrenci", kisi.ogrenci_no, kisi.aktif_odunc_sayisi)
        return Hesap(kisi.id, kisi.ad_soyad, kisi.eposta, "yonetici", kisi.personel_kodu, 0)


def servis_olustur(yol=None) -> KutuphaneService:
    return KutuphaneService(Depo(yol or VARSAYILAN_DB))
