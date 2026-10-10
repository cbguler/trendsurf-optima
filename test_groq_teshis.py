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


def test_teshis_iki_istek_ve_govde_loglar():
    import spk_bulten_izleme as s
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
    os.environ["GROQ_API_KEY"] = "x"
    sys.modules["requests"] = _sahte_requests([_Yanit(200, "{}"), _Yanit(200, "{}")], [])
    with contextlib.redirect_stdout(io.StringIO()):
        ok(s.groq_teshis() == 0, "ikisi de 200 -> 0")
    os.environ["GROQ_API_KEY"] = ""
    with contextlib.redirect_stdout(io.StringIO()):
        ok(s.groq_teshis() == 1, "anahtar yok -> 1")


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
