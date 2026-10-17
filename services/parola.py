import hashlib
import hmac
import secrets


def ozetle(parola: str, tuz: str | None = None) -> str:
    if tuz is None:
        tuz = secrets.token_hex(16)
    ozet = hashlib.pbkdf2_hmac("sha256", parola.encode("utf-8"), tuz.encode("utf-8"), 120_000)
    return f"{tuz}${ozet.hex()}"


def dogrula(parola: str, saklanan: str) -> bool:
    tuz, ayirac, ozet = saklanan.partition("$")
    if not ayirac or not tuz or not ozet:
        return False
    aday = hashlib.pbkdf2_hmac("sha256", parola.encode("utf-8"), tuz.encode("utf-8"), 120_000).hex()
    return hmac.compare_digest(aday, ozet)
