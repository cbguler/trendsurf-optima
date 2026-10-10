"""v2.0.7.395: SPK bulten izleme --groq-test modu (Groq 400 nedenini loglamak icin). Ag erisimi yok: sahte requests."""
import sys, types, io, contextlib, os

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


class _Yanit:
    def __init__(self, kod, metin):
        self.status_code, self.text = kod, metin

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests as _r
            e = _r.HTTPError(f"{self.status_code} Client Error")
            e.response = self
            raise e

    def json(self):
        import json
        return json.loads(self.text)


def _sahte_requests(yanitlar, cagrilar):
    m = types.ModuleType("requests")
    def post(url, headers=None, json=None, timeout=None):
        cagrilar.append({"url": url, "yuk": json, "auth": (headers or {}).get("Authorization")})
        return yanitlar.pop(0)
    m.post = post
    class HTTPError(Exception):
        pass
    m.HTTPError = HTTPError
    return m


def test_yuk_ortak_ve_dogru():
    import spk_bulten_izleme as s
    y = s._groq_yuk("merhaba json")
    ok(y["model"] == "openai/gpt-oss-120b" and y["response_format"] == {"type": "json_object"}, "model/format")
    ok(y["max_completion_tokens"] == 4000 and y["temperature"] == 0.2, "token/sicaklik degismedi")
    ok(y["messages"] == [{"role": "user", "content": "merhaba json"}], "mesaj")


def _liste_yok(s):
    s.bulten_listesi_cek = lambda yil: []


def test_teshis_iki_istek_ve_govde_loglar():
    import spk_bulten_izleme as s
    _liste_yok(s)
    os.environ["GROQ_API_KEY"] = "anahtar-test"
    cagrilar = []
    govde = '{"error":{"message":"Failed to generate JSON","code":"json_validate_failed"}}'
    sys.modules["requests"] = _sahte_requests([_Yanit(200, "{}"), _Yanit(400, govde)], cagrilar)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        kod = s.groq_teshis()
    cikti = buf.getvalue()
    ok(kod == 1, "400 varsa cikis kodu 1")
    ok(len(cagrilar) == 2, "iki istek atildi")
    ok(all(c["url"].endswith("/openai/v1/chat/completions") for c in cagrilar), "Groq adresi")
    ok(all(c["yuk"]["response_format"] == {"type": "json_object"} for c in cagrilar), "ayni yuk")
    ok("HTTP 200" in cikti and "HTTP 400" in cikti, "iki HTTP kodu loglandi")
    ok("json_validate_failed" in cikti, "400 govdesi loglandi")
    ok("Bearer anahtar-test" == cagrilar[0]["auth"], "anahtar Authorization basliginda")
    ok("anahtar-test" not in cikti, "anahtar loga yazilmaz")
    ok("kararlar" in cagrilar[1]["yuk"]["messages"][0]["content"], "B: gercek AI_PROMPT kullanildi")


def test_ikisi_200_cikis_0_ve_anahtar_yok():
    import spk_bulten_izleme as s
    _liste_yok(s)
    os.environ["GROQ_API_KEY"] = "x"
    sys.modules["requests"] = _sahte_requests([_Yanit(200, "{}"), _Yanit(200, "{}")], [])
    with contextlib.redirect_stdout(io.StringIO()):
        ok(s.groq_teshis() == 0, "ikisi de 200 -> 0")
    os.environ["GROQ_API_KEY"] = ""
    with contextlib.redirect_stdout(io.StringIO()):
        ok(s.groq_teshis() == 1, "anahtar yok -> 1")


def test_gercek_bulten_adimi_C():
    import spk_bulten_izleme as s
    from datetime import date
    os.environ["GROQ_API_KEY"] = "x"
    liste = [{"no": "2026/70", "tarih": date(2026, 10, 9), "url": "u70"},
             {"no": "2026/69", "tarih": date(2026, 10, 2), "url": "u69"},
             {"no": "2026/68", "tarih": date(2026, 9, 25), "url": "u68"},
             {"no": "2026/67", "tarih": date(2026, 9, 18), "url": "u67"}]
    s.bulten_listesi_cek = lambda yil: liste
    metinler = {"u70": "x" * 200,                                                   # AI penceresi bos
                "u69": ("SPK Kurulunun karari: ORNEK FON isleme kapatilmistir tasfiye. " * 6),
                "u68": ""}
    s.pdf_metni_cek = lambda url: metinler.get(url, "")
    s._ai_pencereleri = lambda duz, n: "PENCERE METNI " * 50 if "ORNEK" in duz else ""
    cagrilar = []
    govde400 = '{"error":{"message":"json_validate_failed","code":"json_validate_failed","failed_generation":"{"}}'
    ok_yanit = _Yanit(200, '{"choices":[{"message":{"content":"{\\"kararlar\\":[]}"},"finish_reason":"stop"}],'
                           '"usage":{"completion_tokens":1200,"total_tokens":3000}}')
    sys.modules["requests"] = _sahte_requests([_Yanit(200, "{}"), _Yanit(200, "{}"), _Yanit(400, govde400)], cagrilar)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        kod = s.groq_teshis()
    cikti = buf.getvalue()
    ok(kod == 1, "C adiminda 400 -> cikis 1")
    ok(len(cagrilar) == 3, "A, B ve yalniz AI penceresi dolu OLAN bir gercek bulten (3 istek)")
    ok("[C 2026/70]" in cikti and "AI penceresi bos" in cikti, "pencere bos bulten atlandi ve loglandi")
    ok("[C 2026/68]" in cikti and "alinamadi" in cikti, "metni alinamayan bulten loglandi")
    ok("[C 2026/69]: HTTP 400" in cikti and "json_validate_failed" in cikti, "gercek bultende 400 govdesi loglandi")
    ok("2026/67" not in cikti, "yalniz en yeni 3 bulten denenir")
    ok("PENCERE METNI" in cagrilar[2]["yuk"]["messages"][0]["content"], "C: gercek pencere AI_PROMPT icinde gonderildi")
    # 200 yolu: finish_reason, usage ve JSON gecerliligi loglanir
    sys.modules["requests"] = _sahte_requests([_Yanit(200, "{}"), _Yanit(200, "{}"), ok_yanit], [])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        kod = s.groq_teshis()
    c2 = buf.getvalue()
    ok(kod == 0, "hepsi 200 -> cikis 0")
    ok("finish_reason=stop" in c2 and "completion_tokens" in c2 and "gecerli JSON: evet" in c2, "200: finish_reason/usage/gecerlilik loglandi")


def test_normal_cagri_ayni_yuku_kullanir():
    import spk_bulten_izleme as s
    os.environ["GROQ_API_KEY"] = "x"
    os.environ["GEMINI_API_KEY"] = ""
    cagrilar = []
    icerik = '{"kararlar":[]}'
    yanit = _Yanit(200, '{"choices":[{"message":{"content":"' + icerik.replace('"', '\\"') + '"}}]}')
    sys.modules["requests"] = _sahte_requests([yanit], cagrilar)
    with contextlib.redirect_stdout(io.StringIO()):
        sonuc = s.ai_cagir_gercek("istem json", db_mod=None)
    ok(sonuc == {"kararlar": []}, "normal yol hala calisiyor")
    ok(cagrilar[0]["yuk"] == s._groq_yuk("istem json"), "normal cagri ortak yuku kullanir")


def test_workflow_girdisi_var():
    w = open(".github/workflows/spk_bulten_izleme.yml", encoding="utf-8").read()
    ok("groq_test:" in w and "--groq-test" in w, "workflow groq_test girdisi ve bayragi")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_groq_teshis: {_n['ok']}/{_n['ok']} OK")
