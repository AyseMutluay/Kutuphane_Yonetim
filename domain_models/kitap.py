class Kitap:
    def __init__(
        self,
        id: int,
        isbn: str,
        baslik: str,
        yazar: str,
        toplam_stok: int,
        mevcut_stok: int,
    ) -> None:
        self.id = id
        self.isbn = isbn
        self.baslik = baslik
        self.yazar = yazar
        self.toplam_stok = toplam_stok
        self.mevcut_stok = mevcut_stok

    def musait_mi(self) -> bool:
        return self.mevcut_stok > 0

    def stok_dusur(self) -> bool:
        if not self.musait_mi():
            return False
        self.mevcut_stok -= 1
        return True

    def stok_artir(self) -> None:
        if self.mevcut_stok >= self.toplam_stok:
            raise ValueError("Mevcut stok toplam stoku aşamaz.")
        self.mevcut_stok += 1

    def toplam_stogu_ayarla(self, yeni_toplam: int, acik_odunc: int) -> None:
        if yeni_toplam < 0:
            raise ValueError("Toplam stok negatif olamaz.")
        if yeni_toplam < acik_odunc:
            raise ValueError("Toplam stok, açık ödünç sayısından küçük olamaz.")
        self.toplam_stok = yeni_toplam
        self.mevcut_stok = yeni_toplam - acik_odunc
