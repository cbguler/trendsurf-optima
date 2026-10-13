# -*- coding: utf-8 -*-
"""v2.0.7.414: init_db() deadlock'ta yeniden dener. Calistir: python3 test_init_db_deadlock.py
Mantik testleri agsiz; es zamanli test yerel Postgres ister (127.0.0.1:54329, yoksa SKIP). Gercek Supabase'e baglanmaz."""
import os
import subprocess
import sys

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


import db


class _DL(Exception):
    pgcode = "40P01"


class DeadlockDetected(Exception):
    pass


ok(db._kilitlenme_mi(_DL("x")) and db._kilitlenme_mi(DeadlockDetected("x")) and db._kilitlenme_mi(Exception("ERROR: deadlock detected")),
   "kilitlenme tanimlanir (pgcode, sinif adi, metin)")
ok(not db._kilitlenme_mi(ValueError("baska hata")), "baska hata kilitlenme sayilmaz")

# ---- yeniden deneme mantigi (sahte tek-deneme govdesi, bekleme kisaltilir)
import time
_orj, _uyku = db._init_db_bir_kez, time.sleep
cagri = []
time.sleep = lambda s: cagri.append(("uyku", s))
try:
    sayac = {"n": 0}

    def iki_kez_kilitlen():
        sayac["n"] += 1
        if sayac["n"] <= 2:
            raise DeadlockDetected("deadlock detected\nDETAIL: ...")
        return "tamam"
    db._init_db_bir_kez = iki_kez_kilitlen
    ok(db.init_db() == "tamam" and sayac["n"] == 3 and len(cagri) == 2, f"2 kilitlenmeden sonra 3. denemede basarir {sayac} {cagri}")

    sayac["n"] = 0; cagri.clear()

    def hep_kilitlen():
        sayac["n"] += 1
        raise DeadlockDetected("deadlock detected")
    db._init_db_bir_kez = hep_kilitlen
    try:
        db.init_db(); hata = None
    except DeadlockDetected as e:
        hata = e
    ok(hata is not None and sayac["n"] == db.INIT_DB_DENEME, f"hep kilitlenirse {db.INIT_DB_DENEME} denemeden sonra hata verir ({sayac['n']})")

    sayac["n"] = 0; cagri.clear()

    def baska_hata():
        sayac["n"] += 1
        raise ValueError("kilit degil")
    db._init_db_bir_kez = baska_hata
    try:
        db.init_db(); hata = None
    except ValueError as e:
        hata = e
    ok(hata is not None and sayac["n"] == 1 and not cagri, "kilitlenme disindaki hata yeniden denenmez")
finally:
    db._init_db_bir_kez, time.sleep = _orj, _uyku

# ---- gercek es zamanli init_db (yerel Postgres)
DB_URL = os.environ.get("TEST_DB_URL", "postgresql://postgres@127.0.0.1:54329/postgres")
try:
    import psycopg2
    ana = psycopg2.connect(DB_URL, connect_timeout=3)
    ana.autocommit = True
    c = ana.cursor()
    c.execute("DROP DATABASE IF EXISTS deadlock_test")
    c.execute("CREATE DATABASE deadlock_test")
    ana.close()
    PG = True
except Exception as e:
    print(f"SKIP es zamanli test ({e})")
    PG = False
if PG:
    url = DB_URL.rsplit("/", 1)[0] + "/deadlock_test"
    env = dict(os.environ, SUPABASE_DB_URL=url)
    hazir = subprocess.run([sys.executable, "-c",
        "import db; c=db.get_conn(); c.execute('CREATE TABLE IF NOT EXISTS ipo_valuations (disclosure_index BIGINT PRIMARY KEY)'); c.commit(); db.init_db()"],
        env=env, capture_output=True, text=True, timeout=180)
    ok(hazir.returncode == 0, "ilk kurulum basarili " + hazir.stderr[-300:])
    kod = "import db,sys\ntry:\n    db.init_db(); print('SONUC:OK')\nexcept Exception as e:\n    print('SONUC:HATA', type(e).__name__)\n"
    # 8 surec ayni anda
    sureclar = [subprocess.Popen([sys.executable, "-c", kod], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(8)]
    sonuc = [p.communicate(timeout=240) for p in sureclar]
    basarili = sum("SONUC:OK" in o for o, _ in sonuc)
    kilit_yeniden = sum("kilitlenme (deadlock)" in e for _, e in sonuc)
    print(f"  es zamanli 8 init_db: {basarili}/8 basarili, {kilit_yeniden} surec kilitlenmeyi yeniden denedi")
    ok(basarili == 8, "es zamanli 8 init_db'nin hepsi basarili: " + str([o.strip() for o, _ in sonuc]))

print(f"test_init_db_deadlock: {_n['ok']}/{_n['ok']} OK")
