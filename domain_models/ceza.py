from abc import ABC, abstractmethod


class ICezaHesapla(ABC):
    """Ödünç işleminin kullandığı ceza sözleşmesi.

    Arayüz alan paketindedir. Somut cezalar servis paketindedir.
    Böylece servis alana bağlanır, alan servise bağlanmaz.
    """

    ad: str

    @abstractmethod
    def hesapla(self, geciken_gun: int) -> float:
        raise NotImplementedError
