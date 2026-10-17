from domain_models.ceza import ICezaHesapla


class StandartOgrenciCezasi(ICezaHesapla):
    ad = "Standart öğrenci cezası (2 TL/gün)"

    def hesapla(self, geciken_gun: int) -> float:
        if geciken_gun < 0:
            raise ValueError("Geciken gün negatif olamaz.")
        return float(geciken_gun) * 2.0


class AkademikIndirimCezasi(ICezaHesapla):
    ad = "Akademik indirim (1 TL/gün)"

    def hesapla(self, geciken_gun: int) -> float:
        if geciken_gun < 0:
            raise ValueError("Geciken gün negatif olamaz.")
        return float(geciken_gun) * 1.0


STRATEJILER: dict[str, ICezaHesapla] = {
    "standart": StandartOgrenciCezasi(),
    "akademik": AkademikIndirimCezasi(),
}


def strateji_sec(anahtar: str) -> ICezaHesapla:
    try:
        return STRATEJILER[anahtar]
    except KeyError as hata:
        raise ValueError("Bilinmeyen ceza stratejisi.") from hata
