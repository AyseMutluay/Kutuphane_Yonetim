from datetime import date

from domain_models.ceza import ICezaHesapla


class OduncIslemi:
    def __init__(
        self,
        id: int,
        ogrenci_id: int,
        kitap_id: int,
        alis_tarihi: date,
        son_teslim_tarihi: date,
        iade_tarihi: date | None = None,
    ) -> None:
        self.id = id
        self.ogrenci_id = ogrenci_id
        self.kitap_id = kitap_id
        self.alis_tarihi = alis_tarihi
        self.son_teslim_tarihi = son_teslim_tarihi
        self.iade_tarihi = iade_tarihi

    @property
    def durum(self) -> str:
        if self.iade_tarihi is not None:
            return "İade edildi"
        if self.gecikti_mi():
            return "Gecikmede"
        return "Ödünçte"

    def iade_al(self, tarih: date | None = None) -> None:
        if self.iade_tarihi is not None:
            raise ValueError("Bu ödünç zaten iade edilmiş.")
        self.iade_tarihi = tarih or date.today()

    def gecikti_mi(self, bugun: date | None = None) -> bool:
        bugun = bugun or date.today()
        return self.iade_tarihi is None and self.son_teslim_tarihi < bugun

    def gecikme_gun_hesapla(self, bugun: date | None = None) -> int:
        if not self.gecikti_mi(bugun):
            return 0
        bugun = bugun or date.today()
        return (bugun - self.son_teslim_tarihi).days

    def ceza_hesapla(self, strateji: ICezaHesapla, bugun: date | None = None) -> float:
        return strateji.hesapla(self.gecikme_gun_hesapla(bugun))
