"""v2.0.7.394: gecici '[tefas-hist-TESHIS]' log satirlari temizlendi. Rutin (basari/onbellek) satirlari silindi,
hata yolu satirlari kalici '[tefas-hist]' etiketiyle duruyor."""
import ast

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def test_teshis_etiketi_kalmadi():
    src = open("app.py", encoding="utf-8").read()
    ast.parse(src)
    ok("TESHIS" not in src, "app.py'de TESHIS etiketi yok")
    ok(src.count("[tefas-hist]") == 7, "7 hata yolu satiri kalici etiketle duruyor")


def test_rutin_satirlar_silindi():
    src = open("app.py", encoding="utf-8").read()
    for s in ("KALICI ARSIVDEN", "YEREL DISK ONBELLEGINDEN", "KISMI ARSIV", "BASARILI,"):
        ok(s not in src, f"rutin satir silindi: {s}")


def test_hata_yolu_satirlari_duruyor():
    src = open("app.py", encoding="utf-8").read()
    for s in ("HIZ SINIRI", "c.fetch() HATASI", "DIS try/except HATASI", "arsiv okuma hatasi"):
        ok(s in src, f"hata satiri duruyor: {s}")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_log_temizlik: {_n['ok']}/{_n['ok']} OK")
