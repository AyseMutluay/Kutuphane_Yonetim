import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from domain_models.kitap import Kitap
from domain_models.kullanici import Kullanici, Ogrenci, Yonetici
from domain_models.odunc import OduncIslemi
from services.parola import dogrula, ozetle

KOK = Path(__file__).resolve().parents[1]
VARSAYILAN_DB = KOK / "library.db"

_SEMA = """
CREATE TABLE IF NOT EXISTS kullanicilar (
    id INTEGER PRIMARY KEY,
    ad_soyad TEXT NOT NULL,
    eposta TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('ogrenci', 'yonetici')),
    ogrenci_no TEXT,
    personel_kodu TEXT,
    parola_ozeti TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kitaplar (
    id INTEGER PRIMARY KEY,
    isbn TEXT NOT NULL,
    baslik TEXT NOT NULL,
    yazar TEXT NOT NULL,
    toplam_stok INTEGER NOT NULL,
    mevcut_stok INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS odunc_islemleri (
    id INTEGER PRIMARY KEY,
    ogrenci_id INTEGER NOT NULL REFERENCES kullanicilar(id),
    kitap_id INTEGER NOT NULL REFERENCES kitaplar(id),
    alis_tarihi TEXT NOT NULL,
    son_teslim_tarihi TEXT NOT NULL,
    iade_tarihi TEXT
);
"""


def _tarih(deger: str | None) -> date | None:
    if not deger:
        return None
    return date.fromisoformat(deger)


class Depo:
    def __init__(self, yol: Path | None = None) -> None:
        self.yol = Path(yol) if yol else VARSAYILAN_DB
        self._hazirla()

    @contextmanager
    def _baglan(self):
        conn = sqlite3.connect(self.yol)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _hazirla(self) -> None:
        with self._baglan() as conn:
            conn.executescript(_SEMA)
            self._parola_sutunu(conn)
            sayi = conn.execute("SELECT COUNT(*) AS n FROM kullanicilar").fetchone()["n"]
            if sayi == 0:
                self._tohum(conn)
            else:
                self._bos_parolalari_doldur(conn)

    def _tohum(self, conn: sqlite3.Connection) -> None:
        # Nesne diyagramı: Ali, kitap 50, ödünç 101. İkinci kitap ödünç denemesi,
        # üçüncüsü stoksuz red, yönetici ise kitap ekleme içindir.
        conn.executemany(
            """
            INSERT INTO kullanicilar
                (id, ad_soyad, eposta, rol, ogrenci_no, personel_kodu, parola_ozeti)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "Ali Kaya", "ali@ogr.edu.tr", "ogrenci", "2024101", None, ozetle("ali123")),
                (2, "Selin Demir", "selin@kutuphane.edu.tr", "yonetici", None, "P-07", ozetle("yonetici")),
                (3, "Ece Arslan", "ece@ogr.edu.tr", "ogrenci", "2024088", None, ozetle("ece123")),
            ],
        )
        conn.executemany(
            """
            INSERT INTO kitaplar
                (id, isbn, baslik, yazar, toplam_stok, mevcut_stok)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (50, "978-605-1234", "Python ile Veri Yapilari", "Mustafa Yilmaz", 5, 4),
                (51, "978-975-0400", "İlişkisel Veritabanları", "Nesrin Aksoy", 3, 3),
                (52, "978-605-8801", "İşletim Sistemleri", "Kerem Aydın", 1, 0),
            ],
        )
        conn.executemany(
            """
            INSERT INTO odunc_islemleri
                (id, ogrenci_id, kitap_id, alis_tarihi, son_teslim_tarihi, iade_tarihi)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (101, 1, 50, "2026-10-01", "2026-10-15", None),
                (102, 3, 52, "2026-10-10", "2026-10-24", None),
            ],
        )

    def _parola_sutunu(self, conn: sqlite3.Connection) -> None:
        sutunlar = [satir["name"] for satir in conn.execute("PRAGMA table_info(kullanicilar)")]
        if "parola_ozeti" not in sutunlar:
            conn.execute("ALTER TABLE kullanicilar ADD COLUMN parola_ozeti TEXT")

    def _bos_parolalari_doldur(self, conn: sqlite3.Connection) -> None:
        demolar = {"2024101": "ali123", "2024088": "ece123", "P-07": "yonetici"}
        rows = conn.execute(
            "SELECT id, ogrenci_no, personel_kodu, parola_ozeti FROM kullanicilar"
        ).fetchall()
        for row in rows:
            if row["parola_ozeti"]:
                continue
            kod = row["ogrenci_no"] or row["personel_kodu"] or ""
            parola = demolar.get(kod, "kutuphane")
            conn.execute(
                "UPDATE kullanicilar SET parola_ozeti = ? WHERE id = ?",
                (ozetle(parola), row["id"]),
            )

    def giris_dene(self, kimlik: str, parola: str) -> Kullanici | None:
        anahtar = kimlik.strip().casefold()
        if not anahtar or not parola:
            return None
        with self._baglan() as conn:
            rows = conn.execute("SELECT * FROM kullanicilar").fetchall()
            for row in rows:
                adaylar = {
                    (row["eposta"] or "").casefold(),
                    (row["ogrenci_no"] or "").casefold(),
                    (row["personel_kodu"] or "").casefold(),
                }
                adaylar.discard("")
                if anahtar not in adaylar:
                    continue
                if dogrula(parola, row["parola_ozeti"] or ""):
                    return self._kullanici(conn, row)
                return None
            return None

    def _aktif_say(self, conn: sqlite3.Connection, ogrenci_id: int) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM odunc_islemleri
            WHERE ogrenci_id = ? AND iade_tarihi IS NULL
            """,
            (ogrenci_id,),
        ).fetchone()
        return int(row["n"])

    def _kullanici(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Kullanici:
        if row["rol"] == "ogrenci":
            return Ogrenci(
                row["id"],
                row["ad_soyad"],
                row["eposta"],
                row["ogrenci_no"],
                self._aktif_say(conn, row["id"]),
            )
        return Yonetici(row["id"], row["ad_soyad"], row["eposta"], row["personel_kodu"])

    def _kitap(self, row: sqlite3.Row) -> Kitap:
        return Kitap(
            row["id"],
            row["isbn"],
            row["baslik"],
            row["yazar"],
            row["toplam_stok"],
            row["mevcut_stok"],
        )

    def _odunc_alanlardan(
        self,
        id: int,
        ogrenci_id: int,
        kitap_id: int,
        alis_tarihi: str,
        son_teslim_tarihi: str,
        iade_tarihi: str | None,
    ) -> OduncIslemi:
        return OduncIslemi(
            id,
            ogrenci_id,
            kitap_id,
            _tarih(alis_tarihi),
            _tarih(son_teslim_tarihi),
            _tarih(iade_tarihi),
        )

    def kullanici_getir(self, kullanici_id: int) -> Kullanici | None:
        with self._baglan() as conn:
            row = conn.execute(
                "SELECT * FROM kullanicilar WHERE id = ?",
                (kullanici_id,),
            ).fetchone()
            if row is None:
                return None
            return self._kullanici(conn, row)

    def kullanicilari_listele(self) -> list[Kullanici]:
        with self._baglan() as conn:
            rows = conn.execute("SELECT * FROM kullanicilar ORDER BY id").fetchall()
            return [self._kullanici(conn, row) for row in rows]

    def kitap_getir(self, kitap_id: int) -> Kitap | None:
        with self._baglan() as conn:
            row = conn.execute("SELECT * FROM kitaplar WHERE id = ?", (kitap_id,)).fetchone()
            if row is None:
                return None
            return self._kitap(row)

    def kitap_ara(self, kelime: str) -> list[Kitap]:
        with self._baglan() as conn:
            rows = conn.execute("SELECT * FROM kitaplar ORDER BY baslik").fetchall()
        kitaplar = [self._kitap(row) for row in rows]
        terim = kelime.strip().casefold()
        if not terim:
            return kitaplar
        return [
            kitap
            for kitap in kitaplar
            if terim in kitap.baslik.casefold()
            or terim in kitap.yazar.casefold()
            or terim in kitap.isbn.casefold()
        ]

    def kitap_ekle(self, kitap: Kitap) -> int:
        with self._baglan() as conn:
            cur = conn.execute(
                """
                INSERT INTO kitaplar (isbn, baslik, yazar, toplam_stok, mevcut_stok)
                VALUES (?, ?, ?, ?, ?)
                """,
                (kitap.isbn, kitap.baslik, kitap.yazar, kitap.toplam_stok, kitap.mevcut_stok),
            )
            return int(cur.lastrowid)

    def acik_odunc_sayisi(self, kitap_id: int) -> int:
        with self._baglan() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM odunc_islemleri
                WHERE kitap_id = ? AND iade_tarihi IS NULL
                """,
                (kitap_id,),
            ).fetchone()
            return int(row["n"])

    def yeni_odunc(self, ogrenci_id: int, kitap_id: int, alis: date, son_teslim: date) -> OduncIslemi:
        with self._baglan() as conn:
            kisi = conn.execute(
                "SELECT rol FROM kullanicilar WHERE id = ?",
                (ogrenci_id,),
            ).fetchone()
            if kisi is None or kisi["rol"] != "ogrenci":
                raise ValueError("Ödünç alma yalnızca öğrenci hesabıyla yapılır.")
            row = conn.execute("SELECT * FROM kitaplar WHERE id = ?", (kitap_id,)).fetchone()
            if row is None:
                raise ValueError("Kitap bulunamadı.")
            kitap = self._kitap(row)
            if not kitap.stok_dusur():
                raise ValueError("Rafta uygun kopya yok.")
            cur = conn.execute(
                """
                INSERT INTO odunc_islemleri
                    (ogrenci_id, kitap_id, alis_tarihi, son_teslim_tarihi, iade_tarihi)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (ogrenci_id, kitap_id, alis.isoformat(), son_teslim.isoformat()),
            )
            conn.execute(
                "UPDATE kitaplar SET mevcut_stok = ? WHERE id = ?",
                (kitap.mevcut_stok, kitap.id),
            )
            return OduncIslemi(int(cur.lastrowid), ogrenci_id, kitap_id, alis, son_teslim, None)

    def iade_kaydet(self, odunc_id: int, tarih: date) -> OduncIslemi:
        with self._baglan() as conn:
            row = conn.execute(
                """
                SELECT o.id AS odunc_id, o.ogrenci_id, o.kitap_id,
                       o.alis_tarihi, o.son_teslim_tarihi, o.iade_tarihi,
                       k.id AS kitap_pk, k.isbn, k.baslik, k.yazar,
                       k.toplam_stok, k.mevcut_stok
                FROM odunc_islemleri o
                JOIN kitaplar k ON k.id = o.kitap_id
                WHERE o.id = ?
                """,
                (odunc_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Ödünç kaydı bulunamadı.")
            odunc = self._odunc_alanlardan(
                row["odunc_id"],
                row["ogrenci_id"],
                row["kitap_id"],
                row["alis_tarihi"],
                row["son_teslim_tarihi"],
                row["iade_tarihi"],
            )
            kitap = Kitap(
                row["kitap_pk"],
                row["isbn"],
                row["baslik"],
                row["yazar"],
                row["toplam_stok"],
                row["mevcut_stok"],
            )
            odunc.iade_al(tarih)
            kitap.stok_artir()
            conn.execute(
                "UPDATE odunc_islemleri SET iade_tarihi = ? WHERE id = ?",
                (odunc.iade_tarihi.isoformat(), odunc.id),
            )
            conn.execute(
                "UPDATE kitaplar SET mevcut_stok = ? WHERE id = ?",
                (kitap.mevcut_stok, kitap.id),
            )
            return odunc

    def toplam_stok_ayarla(self, kitap_id: int, yeni_toplam: int) -> Kitap:
        with self._baglan() as conn:
            row = conn.execute("SELECT * FROM kitaplar WHERE id = ?", (kitap_id,)).fetchone()
            if row is None:
                raise ValueError("Kitap bulunamadı.")
            acik_row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM odunc_islemleri
                WHERE kitap_id = ? AND iade_tarihi IS NULL
                """,
                (kitap_id,),
            ).fetchone()
            kitap = self._kitap(row)
            kitap.toplam_stogu_ayarla(yeni_toplam, int(acik_row["n"]))
            conn.execute(
                """
                UPDATE kitaplar
                SET toplam_stok = ?, mevcut_stok = ?
                WHERE id = ?
                """,
                (kitap.toplam_stok, kitap.mevcut_stok, kitap.id),
            )
            return kitap

    def ogrencinin_oduncleri(self, ogrenci_id: int) -> list[tuple[OduncIslemi, Kitap]]:
        with self._baglan() as conn:
            rows = conn.execute(
                """
                SELECT o.id AS odunc_id, o.ogrenci_id, o.kitap_id,
                       o.alis_tarihi, o.son_teslim_tarihi, o.iade_tarihi,
                       k.id AS kitap_pk, k.isbn, k.baslik, k.yazar,
                       k.toplam_stok, k.mevcut_stok
                FROM odunc_islemleri o
                JOIN kitaplar k ON k.id = o.kitap_id
                WHERE o.ogrenci_id = ?
                ORDER BY o.alis_tarihi DESC, o.id DESC
                """,
                (ogrenci_id,),
            ).fetchall()
            sonuc = []
            for row in rows:
                odunc = self._odunc_alanlardan(
                    row["odunc_id"],
                    row["ogrenci_id"],
                    row["kitap_id"],
                    row["alis_tarihi"],
                    row["son_teslim_tarihi"],
                    row["iade_tarihi"],
                )
                kitap = Kitap(
                    row["kitap_pk"],
                    row["isbn"],
                    row["baslik"],
                    row["yazar"],
                    row["toplam_stok"],
                    row["mevcut_stok"],
                )
                sonuc.append((odunc, kitap))
            return sonuc

    def tum_oduncler(self) -> list[tuple[OduncIslemi, Ogrenci, Kitap]]:
        with self._baglan() as conn:
            rows = conn.execute(
                """
                SELECT o.id AS odunc_id, o.ogrenci_id, o.kitap_id,
                       o.alis_tarihi, o.son_teslim_tarihi, o.iade_tarihi,
                       u.ad_soyad, u.eposta, u.ogrenci_no,
                       k.id AS kitap_pk, k.isbn, k.baslik, k.yazar,
                       k.toplam_stok, k.mevcut_stok
                FROM odunc_islemleri o
                JOIN kullanicilar u ON u.id = o.ogrenci_id
                JOIN kitaplar k ON k.id = o.kitap_id
                ORDER BY CASE WHEN o.iade_tarihi IS NULL THEN 0 ELSE 1 END,
                         o.alis_tarihi DESC, o.id DESC
                """
            ).fetchall()
            sonuc = []
            for row in rows:
                odunc = self._odunc_alanlardan(
                    row["odunc_id"],
                    row["ogrenci_id"],
                    row["kitap_id"],
                    row["alis_tarihi"],
                    row["son_teslim_tarihi"],
                    row["iade_tarihi"],
                )
                ogrenci = Ogrenci(
                    row["ogrenci_id"],
                    row["ad_soyad"],
                    row["eposta"],
                    row["ogrenci_no"],
                    self._aktif_say(conn, row["ogrenci_id"]),
                )
                kitap = Kitap(
                    row["kitap_pk"],
                    row["isbn"],
                    row["baslik"],
                    row["yazar"],
                    row["toplam_stok"],
                    row["mevcut_stok"],
                )
                sonuc.append((odunc, ogrenci, kitap))
            return sonuc

    def geciken_oduncler(self, bugun: date) -> list[tuple[OduncIslemi, Ogrenci, Kitap]]:
        with self._baglan() as conn:
            rows = conn.execute(
                """
                SELECT o.id AS odunc_id, o.ogrenci_id, o.kitap_id,
                       o.alis_tarihi, o.son_teslim_tarihi, o.iade_tarihi,
                       u.ad_soyad, u.eposta, u.ogrenci_no,
                       k.id AS kitap_pk, k.isbn, k.baslik, k.yazar,
                       k.toplam_stok, k.mevcut_stok
                FROM odunc_islemleri o
                JOIN kullanicilar u ON u.id = o.ogrenci_id
                JOIN kitaplar k ON k.id = o.kitap_id
                WHERE o.iade_tarihi IS NULL AND o.son_teslim_tarihi < ?
                ORDER BY o.son_teslim_tarihi
                """,
                (bugun.isoformat(),),
            ).fetchall()
            sonuc = []
            for row in rows:
                odunc = self._odunc_alanlardan(
                    row["odunc_id"],
                    row["ogrenci_id"],
                    row["kitap_id"],
                    row["alis_tarihi"],
                    row["son_teslim_tarihi"],
                    row["iade_tarihi"],
                )
                ogrenci = Ogrenci(
                    row["ogrenci_id"],
                    row["ad_soyad"],
                    row["eposta"],
                    row["ogrenci_no"],
                    self._aktif_say(conn, row["ogrenci_id"]),
                )
                kitap = Kitap(
                    row["kitap_pk"],
                    row["isbn"],
                    row["baslik"],
                    row["yazar"],
                    row["toplam_stok"],
                    row["mevcut_stok"],
                )
                sonuc.append((odunc, ogrenci, kitap))
            return sonuc
