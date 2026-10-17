from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from services.ceza_stratejisi import STRATEJILER
from services.kutuphane_service import KutuphaneService, servis_olustur

KOK = Path(__file__).resolve().parent


def olustur(veritabani=None) -> Flask:
    app = Flask(
        "web_layer",
        template_folder=str(KOK / "templates"),
        static_folder=str(KOK / "static"),
    )
    app.config["SECRET_KEY"] = "kutuphane-sinif-ici-demo"
    app.config["SERVIS"] = servis_olustur(veritabani)

    def servis() -> KutuphaneService:
        return app.config["SERVIS"]

    @app.before_request
    def hesap_yukle():
        if request.endpoint in {None, "static", "giris"}:
            g.kullanici = None
            return
        hesap = None
        kullanici_id = session.get("kullanici_id")
        if kullanici_id is not None:
            hesap = servis().hesap_getir(kullanici_id)
        if hesap is None:
            session.pop("kullanici_id", None)
            return redirect(url_for("giris"))
        g.kullanici = hesap

    @app.context_processor
    def baglam():
        return {
            "kullanici": getattr(g, "kullanici", None),
            "stratejiler": STRATEJILER,
        }

    @app.template_filter("tr_tarih")
    def tr_tarih(deger):
        if deger is None:
            return "—"
        return deger.strftime("%d.%m.%Y")

    @app.template_filter("tl")
    def tl(tutar: float) -> str:
        return f"{tutar:.2f} TL".replace(".", ",")

    def yonetici_degilse():
        if g.kullanici.rol != "yonetici":
            flash("Bu işlem yöneticilere açıktır.", "olumsuz")
            return redirect(url_for("kitaplar"))
        return None

    @app.get("/")
    def kitaplar():
        kelime = request.args.get("q", "")
        return render_template("kitaplar.html", kelime=kelime, kitaplar=servis().kitap_ara(kelime))

    @app.post("/odunc-al")
    def odunc_al():
        try:
            kitap_id = int(request.form["kitap_id"])
            servis().odunc_ver(g.kullanici.id, kitap_id)
        except (KeyError, ValueError) as hata:
            flash(str(hata) if isinstance(hata, ValueError) else "Geçersiz kitap.", "olumsuz")
            return redirect(url_for("kitaplar"))
        flash("Kitap ödünç verildi. Son teslim 14 gün sonradır.", "olumlu")
        return redirect(url_for("oduncler"))

    @app.get("/odunclerim")
    def oduncler():
        if g.kullanici.rol != "ogrenci":
            flash("Ödünç listesi öğrenci hesabına aittir.", "olumsuz")
            return redirect(url_for("kitaplar"))
        hesap = servis().hesap_getir(g.kullanici.id)
        kayitlar = servis().ogrencinin_oduncleri(g.kullanici.id)
        return render_template("oduncler.html", hesap=hesap, kayitlar=kayitlar)

    @app.post("/iade")
    def iade():
        try:
            odunc_id = int(request.form["odunc_id"])
            if g.kullanici.rol != "ogrenci":
                raise ValueError("İade yalnızca öğrenci hesabıyla yapılır.")
            servis().iade_et(odunc_id, g.kullanici.id)
        except (KeyError, ValueError) as hata:
            flash(str(hata) if isinstance(hata, ValueError) else "Geçersiz ödünç.", "olumsuz")
        else:
            flash("İade alındı. Kopya rafa döndü.", "olumlu")
        return redirect(url_for("oduncler"))

    @app.get("/gecikmeler")
    def gecikmeler():
        ret = yonetici_degilse()
        if ret:
            return ret
        anahtar = request.args.get("strateji", "standart")
        try:
            strateji = servis().strateji(anahtar)
        except ValueError as hata:
            flash(str(hata), "olumsuz")
            anahtar = "standart"
            strateji = servis().strateji(anahtar)
        return render_template(
            "gecikmeler.html",
            secili=anahtar,
            kayitlar=servis().gecikmeleri_raporla(strateji),
        )

    @app.get("/yonetim")
    def yonetim():
        ret = yonetici_degilse()
        if ret:
            return ret
        return render_template(
            "yonetim.html",
            kitaplar=servis().kitap_ara(""),
            hareketler=servis().odunc_hareketleri(),
        )

    @app.post("/kitap-ekle")
    def kitap_ekle():
        ret = yonetici_degilse()
        if ret:
            return ret
        try:
            stok = int(request.form["stok"])
            servis().kitap_ekle(
                request.form.get("isbn", ""),
                request.form.get("baslik", ""),
                request.form.get("yazar", ""),
                stok,
            )
        except (KeyError, ValueError) as hata:
            flash(str(hata) if isinstance(hata, ValueError) else "Kitap eklenemedi.", "olumsuz")
        else:
            flash("Kitap kataloğa eklendi.", "olumlu")
        return redirect(url_for("yonetim"))

    @app.post("/stok-guncelle")
    def stok_guncelle():
        ret = yonetici_degilse()
        if ret:
            return ret
        try:
            servis().stok_guncelle(int(request.form["kitap_id"]), int(request.form["yeni_stok"]))
        except (KeyError, ValueError) as hata:
            flash(str(hata) if isinstance(hata, ValueError) else "Stok güncellenemedi.", "olumsuz")
        else:
            flash("Toplam stok güncellendi. Mevcut stok, açık ödünçlere göre ayarlandı.", "olumlu")
        return redirect(url_for("yonetim"))

    @app.route("/giris", methods=["GET", "POST"])
    def giris():
        if session.get("kullanici_id") and servis().hesap_getir(session["kullanici_id"]):
            return redirect(url_for("kitaplar"))
        if request.method == "POST":
            try:
                hesap = servis().giris_yap(
                    request.form.get("kimlik", ""),
                    request.form.get("parola", ""),
                )
            except ValueError as hata:
                flash(str(hata), "olumsuz")
            else:
                session["kullanici_id"] = hesap.id
                flash(f"Hoş geldiniz, {hesap.ad_soyad}.", "olumlu")
                return redirect(url_for("kitaplar"))
        return render_template("giris.html")

    @app.post("/cikis")
    def cikis():
        session.pop("kullanici_id", None)
        flash("Oturum kapatıldı.", "olumlu")
        return redirect(url_for("giris"))

    return app


app = olustur()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
