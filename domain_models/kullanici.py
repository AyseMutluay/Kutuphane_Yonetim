class Kullanici:
    def __init__(self, id: int, ad_soyad: str, eposta: str) -> None:
        self.id = id
        self.ad_soyad = ad_soyad
        self.eposta = eposta


class Ogrenci(Kullanici):
    def __init__(
        self,
        id: int,
        ad_soyad: str,
        eposta: str,
        ogrenci_no: str,
        aktif_odunc_sayisi: int = 0,
    ) -> None:
        super().__init__(id, ad_soyad, eposta)
        self.ogrenci_no = ogrenci_no
        # Saklanan sayaç değil. Depo, açık ödünçleri sayıp buraya yazar.
        self.aktif_odunc_sayisi = aktif_odunc_sayisi


class Yonetici(Kullanici):
    def __init__(self, id: int, ad_soyad: str, eposta: str, personel_kodu: str) -> None:
        super().__init__(id, ad_soyad, eposta)
        self.personel_kodu = personel_kodu
