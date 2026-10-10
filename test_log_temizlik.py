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
    ok("[tefas-hist-TESHIS]" not in src, "app.py de [tefas-hist-TESHIS] log etiketi yok")
    ok(src.count("[tefas-hist]") == 7, "7 hata yolu satiri kalici etiketle duruyor")


def test_rutin_satirlar_silindi():
    src = open("app.py", encoding="utf-8").read()
    log_satirlari = " ".join(l for l in src.splitlines() if "[tefas-hist" in l)
    # print'in mesaji sonraki satira tasabilir: print satirlarindan sonraki 1 satiri da ekle
    satirlar = src.splitlines()
    for i, l in enumerate(satirlar):
        if "[tefas-hist" in l and i + 1 < len(satirlar):
            log_satirlari += " " + satirlar[i + 1]
    for s in ("KALICI ARSIVDEN", "YEREL DISK ONBELLEGINDEN", "KISMI ARSIV", "BASARILI,"):
        ok(s not in log_satirlari, f"rutin log satiri silindi: {s}")


def test_hata_yolu_satirlari_duruyor():
    src = open("app.py", encoding="utf-8").read()
    for s in ("HIZ SINIRI", "c.fetch() HATASI", "DIS try/except HATASI", "arsiv okuma hatasi"):
        ok(s in src, f"hata satiri duruyor: {s}")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_log_temizlik: {_n['ok']}/{_n['ok']} OK")
