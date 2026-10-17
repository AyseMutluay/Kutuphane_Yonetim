from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class OduncHareketi:
    ogrenci_ad: str
    ogrenci_no: str
    baslik: str
    yazar: str
    alis_tarihi: date
    son_teslim_tarihi: date
    iade_tarihi: date | None
    durum: str
    geciken_gun: int


@dataclass(frozen=True)
class Hesap:
    """Sayfanın gördüğü kimlik özeti. Alan sınıfı değildir."""

    id: int
    ad_soyad: str
    eposta: str
    rol: str
    kod: str
    aktif_odunc_sayisi: int
