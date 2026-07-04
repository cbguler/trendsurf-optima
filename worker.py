"""
TrendSurf Optima — Veri Motoru v4 (worker.py)
Calistirma: python worker.py
KAP_SLUG_MAP'ten alinan 771 BIST hissesi + tam listeler
"""
import pandas as pd, numpy as np, os, glob, sys, warnings
warnings.filterwarnings("ignore")

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "optimized_universe.csv")

# ─── 771 BIST (KAP_SLUG_MAP tam listesi) ────────────────────
BIST_TICKERS = [
    "ACSEL","ADEL","ADESE","ADLVY","ADGYO","AFYON","AGHOL","AGESA","AGROT","AAGYO",
    "AHSGY","AHGAZ","AKSFA","AKFK","AKM","AKCVR","AKBNK","AKCNS","AKDFA","AKYHO",
    "AKENR","AKFGY","AKFIS","AKFYE","AKHAN","ATEKS","AKSGY","AKMGY","AKSA","AKSEN",
    "AKGRT","AKSUE","AKTVK","AFB","ALCAR","ALGYO","ALARK","ALBRK","ALCTL","ALFAS",
    "ALJF","ALKIM","ALKA","ALNUS","AYCES","ALTNY","ALKLC","ALVES","ANSGR","AEFES",
    "ANHYT","ASUZU","ANGEN","ANELE","ARCLK","ARDYZ","ARENA","ARFYE","ARMGD","ARSAN",
    "ARSVY","ARTMS","ARZUM","ASGYO","ASELS","ASTOR","ATAGY","ATATR","ATAVK","ATA",
    "ATAKP","AGYO","ATLFA","ATSYH","ATLAS","ATATP","AVOD","AVGYO","AVTUR","AVHOL",
    "AVPGY","AYDEM","AYEN","AYES","AYGAZ","AZTEK","A1CAP","A1YEN","BAGFS","BAHKM",
    "BAKAB","BALAT","BALSU","BNTAS","BANVT","BARMA","BSRFK","BASGZ","BASCM","BEGYO",
    "BTCIM","BSOKE","BYDNR","BAYRK","BERA","BRKT","BRKSN","BESLR","BESTE","BJKAS",
    "BEYAZ","BIENY","BIGTK","BLCYT","BLKOM","BIMAS","BINBN","BIOEN","BRKVY","BRKO",
    "BIGEN","BRLSM","BRMEN","BIZIM","BLUME","BMSTL","BMSCH","BNPPI","BOBET","BORSK",
    "BORLS","BRSAN","BRYAT","BFREN","BOSSA","BRISA","BULGS","BLS","BLSMD","BURCE",
    "BURVA","BRGAN","BUR","BRGFK","BUCIM","BVSAN","BIGCH","CRFSA","CASA","CEMZY",
    "CEOEM","CCOLA","CONSE","COSMO","CRDFA","CVKMD","CWENE","CGCAM","CAGFA","CMSAN",
    "CANTE","CATES","CLEBI","CELHA","CLKMT","CEMAS","CEMTS","CMBTN","CMENT","CIMSA",
    "CUSAN","DVRLK","DYBNK","DAGI","DAPGM","DARDL","DGATE","DCTTR","DGRVK","DMSAS",
    "DENVA","DENGE","DNZEN","DENFA","DNFIN","DZGYO","DERIM","DERHL","DESA","DESPC",
    "DSTKF","DMD","DSYAT","DEVA","DIMES","DNISI","DIRIT","DITAS","DKVRL","DMRGD",
    "DOCO","DOFRB","DOFER","DOHOL","DGNMO","DOGVY","ARASE","DOGUB","DGGYO","DOAS",
    "DFKTR","DOKTA","DURDO","DURKN","DUNYH","DNYVA","DYOBY","EBEBK","ECOGR","ECZYT",
    "EDATA","EDIP","EFOR","EGEEN","EGGUB","EGPRO","EGSER","EPLAS","EGEGY","ECZIP",
    "ECILC","EKER","EKDMR","EKIZ","EKOFA","EKOS","EKSUN","ELITE","EMKEL","EMNIS",
    "EMIRV","EKTVK","DMLKT","EKGYO","EMVAR","EMPAE","ENDAE","ENJSA","ENERY","ENKAI",
    "ENPRA","ENSRI","ERBOS","ERCB","EREGL","ERGLI","KIMMR","ERSU","ESCAR","ESCOM",
    "ESEN","ETILR","EUKYO","EUYO","ETYAT","EUHOL","TEZOL","EUREN","EUPWR","EYGYO",
    "FADE","FMIZP","FENER","FBB","FBBNK","FKPET","FLAP","FONET","FROTO","FORMT",
    "FRMPL","FORTE","FRIGO","FZLGY","GWIND","GSRAY","GARFA","GARFL","GRNYO","GATEG",
    "GEDIK","GEDZA","GLCVY","GENIL","GENTS","GENKM","GEREL","GZNMI","GIPTA","GMTAS",
    "GESAN","GLB","GLBMD","GLYHO","GGBVK","GSIPD","GOODY","GOKNR","GOLTS","GOZDE",
    "GRTHO","GSDDE","GSDHO","GUBRF","GLRYH","GLRMK","GUNDG","GRSEL","GYVAR","SAHOL",
    "HALKF","HLGYO","HLVKS","HALKI","HLY","HRKET","HATEK","HATSN","HAYVK","HDFFL",
    "HDFGS","HEDEF","HDFVK","HDFYB","HYB","HEKTS","HKTM","HTTBT","HOROZ","HUBVC",
    "HUNER","HUZFA","HURGZ","ENTRA","ICB","ICBCT","ICUGS","INGRM","INVEO","IAZ",
    "INVAZ","INVES","ISKPL","IEYHO","IDGYO","IHEVA","IHLGM","IHGZT","IHAAS","IHLAS",
    "IHYAY","IMASM","INDES","INFO","IYF","INTEK","INTEM","ISDMR","ISTFK","ISTVY",
    "ISFAK","ISFIN","ISGYO","ISGSY","ISMEN","IYM","ISYAT","ISBIR","ISSEN","IZINV",
    "IZENR","IZMDC","IZFAS","JANTS","KFEIN","KLKIM","KLSER","KLVKS","KLYPV","KPTGY",
    "KAPLM","KRDMA","KRDMB","KRDMD","KAREL","KARSN","KRTEK","KARTN","KATVK","KTLEV",
    "KATMR","KFILO","KAYSE","KNTFA","KENT","KRVGD","KERVN","TCKRC","KZBGY","KLGYO",
    "KLRHO","KMPUR","KLMSN","KCAER","KOCFN","KCHOL","KOCMT","KSFIN","KLSYN","KNFRT",
    "KONTR","KONYA","KONKA","KGYO","KORDS","KRPLS","KORTS","KOTON","KOPOL","KRGYO",
    "KRSTL","KRONT","KTKVK","KTSVK","KSTUR","KUVVA","KUYAS","KBORU","KZGYO","KUTPO",
    "KTSKR","LIDER","LIDFA","LILAK","LMKDC","LINK","LOGO","LKMNH","LRSHO","LXGYO",
    "LUKSK","LYDHO","LYDYE","MACKO","MAKIM","MAKTK","MANAS","MRBAS","MRS","MAGEN",
    "MRMAG","MARKA","MARMR","MAALT","MRSHL","MRGYO","MARTI","MTRKS","MAVI","MZHLD",
    "MDIAZ","MEDTR","MEGMT","MEGAP","MEKAG","MEKMD","MSA","MNDRS","MEPET","MERCN",
    "MRBKF","MBFTR","MERIT","MERKO","METEN","METRO","MTRYO","MCARD","MEYSU","MHRGY",
    "MIATK","MDASM","MDS","MGROS","MILKS","MINTF","MSGYO","MSY","MSYBN","MPARK",
    "MMCAS","MNGFA","MOBTL","MOGAN","MNDTR","MOPAS","EGEPO","NATEN","NTHOL","NETAS",
    "NETCD","NIBAS","NUHCM","NUGYO","NURVK","NRBNK","NYB","OBAMS","OBASE","ODAS",
    "ODINE","OFSYM","ONCSM","ONRYT","OPET","ORCAY","ORFIN","ORGE","ORMA","OSVKS",
    "OMD","OSMEN","OSTIM","OTKAR","OTOKC","OTOSR","OTTO","OYAKC","OYA","OYYAT",
    "OYAYO","OYLUM","OZKGY","OZATD","OZGYO","OZRDN","OZSUB","OZYSR","PAMEL","PNLSN",
    "PAGYO","PAPIL","PRFFK","PRDGS","PRKME","PARSN","PBT","PBTR","PASEU","PSGYO",
    "PAHOL","PATEK","PCILT","PGSUS","PEKGY","PENGD","PENTA","PSDTC","PETKM","PKENT",
    "PETUN","PINSU","PNSUT","PKART","PLTUR","POLHO","POLTK","PRZMA","QFINF","QYATB",
    "YBQ","QYHOL","FIN","QNBTR","QNBFF","QNBFK","QNBVK","QUAGR","QUFIN","RNPOL",
    "RALYH","RAYSG","REEDR","RYGYO","RYSAS","RODRG","RGYAS","RTALB","RUBNS","RUZYE",
    "SAFKR","SANEL","SNICA","SANFM","SANKO","SAMAT","SARKY","SASA","SVGYO","SAYAS",
    "SDTTR","SEGMN","SEKUR","SELEC","SELVA","SERNT","SRVGY","SEYKM","SILVR","SNGYO",
    "SKYLP","SMRTG","SMART","SODSN","SOKE","SKTAS","SONME","SNPAM","SUMAS","SUNTK",
    "SURGY","SUWEN","SMRFA","SMRVA","SEKFK","SEGYO","SKY","SKYMD","SEK","SKBNK",
    "SOKM","TABGD","TAC","TCRYT","TAMFA","TNZTP","TARKM","TATGD","TATEN","TAVHL",
    "DRPHN","TEBFA","TEKTU","TKFEN","TKNSA","TMPOL","TRFFA","TRHOL","TEVKS","TAE",
    "TRBNK","TERA","TRA","TEHOL","TFNVK","TGSAS","TIMUR","TRYKI","TOASO","TRGYO",
    "TRMET","TRENJ","TLMAN","TSPOR","TDGYO","TRMEN","TVM","TSGYO","TUCLK","TUKAS",
    "TRCAS","TUREX","MARBL","TRKFN","TRILC","TCELL","TRKNT","TMSN","TUPRS","TRALT",
    "THYAO","PRKAB","TTKOM","TTRAK","TBORG","TURGG","GARAN","TGB","HALKB","THL",
    "EXIMB","THR","ISATR","ISBTR","ISCTR","ISKUR","TIB","KLN","KLNMA","TSK",
    "TSKB","TURSG","SISE","TVB","VAKBN","TV8TV","UFUK","ULAS","ULUFA","ULUSE",
    "ULUUN","UMPAS","USAK","UCAYM","ULKER","UNLU","VAKFA","VAKFN","VKGYO","VKFYO",
    "VAKVK","VAKKO","VANGD","VBTYZ","VDFLO","VRGYO","VERUS","VERTU","VESBE","VESTL",
    "VKING","VSNMD","VDFAS","YKFKT","YKFIN","YKR","YKYAT","YKB","YKBNK","YAPRK",
    "YATAS","YATVK","YYLGD","YAYLA","YGGYO","YEOTK","YYAPI","YESIL","YBTAS","YIGIT",
    "YONGA","YKSLN","YUNSA","ZGYO","ZEDUR","ZERGY","ZRGYO","ZKBVK","ZKBVR","ZOREN",
    "BINHO",
]
BIST_TICKERS = list(dict.fromkeys(BIST_TICKERS))  # dedup -> 771

# ─── v2.0.4.5: Dinamik BIST Evreni (Parca B - Yaklasan Halka Arzlar) ────────
# Amac: Bir sirket SPK onayindan gecip fiilen BIST'te islem gormeye
# basladiginda (XHARZ - BIST Halka Arz Endeksi'ne dustugunde), yukaridaki
# SABIT 771 listeye MANUEL ekleme yapmadan otomatik olarak worker'in izledigi
# evrene katilmasi. Kalicilik icin Supabase'de bist_universe_dynamic tablosu
# kullanilir: bir kez tespit edilen ticker, tum gelecek calismalarda buradan
# otomatik yuklenir.
#
# Guvenlik prensibi: Bu blok WORKER'IN CALISMASINI ASLA ENGELLEMEMELI. Supabase
# erisilemezse, SUPABASE_DB_URL tanimli degilse, KAP/halka_arz_client hata
# verirse -> sessizce bos liste donup statik 771 listeyle devam edilir.

def _ensure_dynamic_universe_table(conn):
    """Tablo yoksa olustur + RLS ac (policy tanimlanmadigi icin sadece
    service_role/postgres baglantisi erisebilir - v2.0.2 guvenlik
    sertlestirmesiyle tutarli, anon/authenticated icin erisim YOK)."""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bist_universe_dynamic (
                ticker        TEXT PRIMARY KEY,
                company_name  TEXT,
                added_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source        TEXT DEFAULT 'XHARZ_auto'
            )
        """)
        conn.execute("ALTER TABLE bist_universe_dynamic ENABLE ROW LEVEL SECURITY")
        conn.commit()
    except Exception as e:
        print(f"[dinamik-evren] tablo/RLS kurulumu atlandi (hata, muhtemelen zaten var): {e}")


def _load_dynamic_bist_universe() -> list:
    """Supabase'deki bist_universe_dynamic tablosundan onceki calismalarda
    tespit edilmis (XHARZ mezunu) ticker'lari yukler. Hata durumunda
    SESSIZCE bos liste doner."""
    try:
        from db import get_conn
        conn = get_conn()
        _ensure_dynamic_universe_table(conn)
        rows = conn.execute("SELECT ticker FROM bist_universe_dynamic").fetchall()
        tickers = [str(r["ticker"]).strip().upper() for r in rows if r.get("ticker")]
        conn.close()
        if tickers:
            print(f"[dinamik-evren] Supabase'den {len(tickers)} dinamik BIST ticker yuklendi: {tickers}")
        return tickers
    except Exception as e:
        print(f"[dinamik-evren] Supabase'den yukleme atlandi (hata): {e}")
        return []


def _detect_and_register_new_bist_listings(existing_tickers: list) -> list:
    """halka_arz_client.fetch_ipo_list() ile XHARZ (BIST Halka Arz Endeksi)
    uyelerini ceker - bunlar zaten borsada islem gormeye baslamis (mezun
    olmus) sirketlerdir. existing_tickers'ta OLMAYANLARI yeni mezun sayar,
    Supabase'e kalici kaydeder VE bu calismanin listesine ekler ki ayni gun
    fiyat/skor alabilsinler. Hata durumunda SESSIZCE bos liste doner."""
    try:
        from halka_arz_client import fetch_ipo_list
        df_ipo = fetch_ipo_list()
        if df_ipo.empty or "Ticker" not in df_ipo.columns:
            return []

        # v2.0.4.6: Diger kategorilerin (KRIPTO/DOVIZ/MADEN) ticker kodlariyla
        # CAKISMA KORUMASI. Bugun "LINK" kodu hem BIST'te (Link Bilgisayar
        # Sistemleri) hem KRIPTO'da (Chainlink) aynı anda kullanildigi tespit
        # edildi - worker'in son adimindaki drop_duplicates(keep="last") BIST
        # hissesini sessizce siliyordu (KRIPTO daha sonra islendigi icin
        # kazaniyor). O collision ayrica giderildi (KRIPTO->CLINK), ama
        # GELECEKTE yeni bir BIST mezunu tesaduf yoluyla baska bir kategorinin
        # kodu ile ayni olursa (orn. yeni bir sirket "SOL" veya "TON" ticker'i
        # ile borsaya girerse) ayni sessiz veri kaybi tekrar olusabilir. Bunu
        # onlemek icin: cakisan kod tespit edilirse BIST tarafina ALINMAZ,
        # log'a acikca yazilir - boylece fark edilmeden veri kaybi olmaz.
        other_cat_codes = set()
        try:
            other_cat_codes |= {t.upper() for t, _ in KRIPTO}
            other_cat_codes |= {t.upper() for t, _ in DOVIZ}
            other_cat_codes |= {t.upper() for t, _ in MADEN}
        except Exception:
            pass

        existing_set = set(t.upper() for t in existing_tickers)
        new_rows = []
        skipped_collisions = []
        for _, row in df_ipo.iterrows():
            t = str(row.get("Ticker", "")).strip().upper()
            if not t or len(t) < 2 or len(t) > 8 or not t.isalnum():
                continue
            if t in existing_set:
                continue
            if t in other_cat_codes:
                skipped_collisions.append(t)
                continue
            existing_set.add(t)  # ayni calismada tekrar eklenmesin
            new_rows.append({
                "ticker": t,
                "company_name": str(row.get("Şirket", ""))[:200],
            })

        if skipped_collisions:
            print(f"[dinamik-evren] UYARI: {skipped_collisions} kodlari baska "
                  f"kategorilerle (KRIPTO/DOVIZ/MADEN) cakistigi icin BIST "
                  f"evrenine EKLENMEDI - manuel kontrol gerekebilir")

        if not new_rows:
            return []

        from db import get_conn
        conn = get_conn()
        _ensure_dynamic_universe_table(conn)
        for r in new_rows:
            try:
                conn.execute(
                    "INSERT INTO bist_universe_dynamic (ticker, company_name, source) "
                    "VALUES (?,?,?) ON CONFLICT DO NOTHING",
                    (r["ticker"], r["company_name"], "XHARZ_auto")
                )
            except Exception as e:
                print(f"[dinamik-evren] {r['ticker']} kaydi basarisiz (atlandi): {e}")
        conn.commit()
        conn.close()

        new_tickers = [r["ticker"] for r in new_rows]
        print(f"[dinamik-evren] YENI BIST mezunu(lar) tespit edildi ve kaydedildi: {new_tickers}")
        return new_tickers
    except Exception as e:
        print(f"[dinamik-evren] yeni mezun tespiti atlandi (hata): {e}")
        return []

# ─── 20 Kripto ───────────────────────────────────────────────
KRIPTO = [
    ("BTC","BTC-USD"),("ETH","ETH-USD"),("BNB","BNB-USD"),("SOL","SOL-USD"),
    ("ADA","ADA-USD"),("XRP","XRP-USD"),("DOGE","DOGE-USD"),("DOT","DOT-USD"),
    ("AVAX","AVAX-USD"),("CLINK","LINK-USD"),("LTC","LTC-USD"),("ATOM","ATOM-USD"),
    ("TRX","TRX-USD"),("NEAR","NEAR-USD"),("ICP","ICP-USD"),
("OP","OP-USD"),("INJ","INJ-USD"),("SUI","SUI20947-USD"),("TON","TON11419-USD"),
]

# POL yfinance'de cevap vermezse MATIC-USD ile dene

# ─── 12 Maden / Emtia ────────────────────────────────────────
MADEN = [
    ("ALTIN_TRY","GC=F"),("GUMUS_TRY","SI=F"),("PLATIN_TRY","PL=F"),
    ("PALADYUM_TRY","PA=F"),("BAKIR_TRY","HG=F"),("PETROL_TRY","CL=F"),
    ("DOGALGAZ_TRY","NG=F"),("BRENT_TRY","BZ=F"),("BUGDAY_TRY","ZW=F"),
    ("MISIR_TRY","ZC=F"),("SOYA_TRY","ZS=F"),("KAKAO_TRY","CC=F"),
]

# ─── 16 Döviz (yfinance'de çalışanlar) ───────────────────────
DOVIZ = [
    ("USDTRY","USDTRY=X"),("EURTRY","EURTRY=X"),("GBPTRY","GBPTRY=X"),
    ("JPYTRY","JPYTRY=X"),("CHFTRY","CHFTRY=X"),("AUDTRY","AUDTRY=X"),
    ("CADTRY","CADTRY=X"),("NZDTRY","NZDTRY=X"),("NOKTRY","NOKTRY=X"),
    ("SEKTRY","SEKTRY=X"),("DKKTRY","DKKTRY=X"),("CNYTRY","CNYTRY=X"),
]

OUTPUT = "optimized_universe.csv"



def calc_rsi(s, p=14):
    s = s.dropna()
    if len(s) < p + 1:
        return 50.0
    d = s.diff()
    g = d.where(d > 0, 0.0).rolling(p).mean()
    l = (-d.where(d < 0, 0.0)).rolling(p).mean()
    ll = l.iloc[-1]
    if ll == 0:
        return 100.0
    return round(100 - (100 / (1 + g.iloc[-1] / ll)), 1)


def safe_float(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except:
        try:
            return float(str(v).strip().replace(",", "."))
        except:
            return 0.0


def _rsi_from_ret(ret1m: float, ret3m: float, ret1y: float) -> float:
    """
    Fiyat geçmişi olmadan getiri verilerinden yaklaşık RSI üretir.
    Mantık: güçlü pozitif getiri → yüksek RSI, negatif → düşük RSI.
    Optima Skoru hesabında makul bir başlangıç noktası verir.
    """
    # Ağırlıklı momentum skoru
    momentum = ret1m * 0.5 + ret3m * 0.3 + ret1y * 0.2
    # -30% ile +30% arasını 30-70 RSI bandına mapler
    rsi = 50.0 + (momentum / 30.0) * 20.0
    return round(max(15.0, min(85.0, rsi)), 1)


# ─── TEFAS: Excel'den tam veri okuma ────────────────────────
TEFAS_FILE_KIND = {
    "Menkul_Kiymet": "YAT",
    "Emeklilik":     "EMK",
    "Borsa_Yatirim": "BYF",
}

# Excel sütun isimlerini normalize et
_COL_MAP = {
    "1 Ay (%)":                  "Ret1M_raw",
    "3 Ay (%)":                  "Ret3M_raw",
    "6 Ay (%)":                  "Ret6M_raw",
    "Yılbaşından İtibaren (%)":  "RetYTD_raw",
    "1 Yıl (%)":                 "Ret1Y_raw",
    "3 Yıl (%)":                 "Ret3Y_raw",
    "5 Yıl (%)":                 "Ret5Y_raw",
}


def load_tefas() -> pd.DataFrame:
    """
    1. Excel'den fon listesi + getiri verileri (Ret1M, Ret1Y vb.)
    2. pytefas ile tüm fonların güncel NAV fiyatları
    3. Fiyat yoksa BEFAS Excel fallback
    """
    try:
        from tefas_client import load_excel_all
        df = load_excel_all(os.getcwd())
        if not df.empty:
            fiyatli = (df["Son_Fiyat"] > 0).sum()
            print(f"  {len(df)} TEFAS fonu hazir | Fiyatli: {fiyatli}")
            return df
    except Exception as e:
        print(f"  tefas_client hatasi: {e}")

    # Minimal fallback
    rows = []
    for fpath in sorted(glob.glob("*.xlsx")):
        if "KAP" in fpath.upper() or "Fon_Verileri" in fpath:
            continue
        kind = "YAT"
        for key, val in TEFAS_FILE_KIND.items():
            if key in fpath:
                kind = val
                break
        try:
            df_raw = pd.read_excel(fpath, header=4)
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
            if "Fon Kodu" not in df_raw.columns:
                continue
            for _, row in df_raw.iterrows():
                kod = str(row.get("Fon Kodu","")).strip().upper()
                if not kod or kod == "NAN" or len(kod) > 8:
                    continue
                def _pct(col):
                    v = row.get(col)
                    if v is None or (isinstance(v, float) and pd.isna(v)):
                        return 0.0
                    v = float(v)
                    return round(v*100,4) if abs(v)<=2.0 else round(v,4)
                ret1m = _pct("1 Ay (%)")
                ret3m = _pct("3 Ay (%)")
                ret1y = _pct("1 Yıl (%)")
                rsi = 50.0 + ((ret1m*0.5+ret3m*0.3+ret1y*0.2)/30.0)*20.0
                rows.append({
                    "Ticker": kod, "Ad": str(row.get("Fon Adı",kod))[:80],
                    "Kategori":"TEFAS","TEFAS_Kind":kind,"Son_Fiyat":0.0,
                    "RSI":round(max(15,min(85,rsi)),1),
                    "Ret1M":ret1m,"Ret3M":ret3m,"Ret1Y":ret1y,"YF_Symbol":"",
                })
        except Exception as e:
            print(f"  [{fpath}] hata: {e}")
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates(subset=["Ticker"],keep="last")

def fetch_bist_names_fast(tickers: list) -> dict:
    """
    BIST hisseleri için uzun isimleri 3 kademeli kaynaktan çeker.

    Kademe 1 — KAP_BIST.xlsx  : 771 hissenin resmi KAP adları (anında, birincil)
    Kademe 2 — KAP slug map   : kap_client.KAP_SLUG_MAP üzerinden okunabilir ad
    Kademe 3 — yfinance .info  : Hâlâ eksik kalanlar için paralel (yavaş, fallback)
    """
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, as_completed

    print(f"  BIST uzun isimler cekiliyor ({len(tickers)} hisse, 3 katmanli)...")

    # ── Kademe 1: KAP_BIST.xlsx ──────────────────────────────
    def _load_kap_excel() -> dict:
        """
        KAP_BIST.xlsx'ten ticker → şirket adı eşlemesi.
        Virgülle ayrılmış çoklu ticker satırlarını da doğru parse eder.
        Örn: "GARAN, TGB" → ikisi de "TÜRKİYE GARANTİ BANKASI A.Ş." olarak eşlenir.
        """
        import glob, os
        result = {}
        # worker.py ile aynı klasörde ara
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = (
            glob.glob(os.path.join(base_dir, "KAP_BIST.xlsx")) +
            glob.glob(os.path.join(base_dir, "KAP_BIST*.xlsx")) +
            glob.glob(os.path.join(base_dir, "kap_bist*.xlsx"))
        )
        if not candidates:
            return result
        try:
            df = pd.read_excel(candidates[0], header=None)
            for _, row in df.iterrows():
                raw = str(row.iloc[0]).strip()
                name = str(row.iloc[1]).strip()
                if raw in ("nan", "") or name in ("nan", ""):
                    continue
                for t in raw.split(","):
                    t = t.strip().upper()
                    if t:
                        result[t] = name
            print(f"    K1 KAP_BIST.xlsx: {len(result)} eslesme yuklendi.")
        except Exception as e:
            print(f"    K1 KAP_BIST.xlsx okunamadi: {e}")
        return result

    # ── Kademe 2: KAP slug map ────────────────────────────────
    def _fetch_kap_names(missing: list) -> dict:
        result = {}
        try:
            from kap_client import KAP_SLUG_MAP
            for t in missing:
                slug = KAP_SLUG_MAP.get(t, "")
                if slug:
                    result[t] = slug.replace("-", " ").title()
        except Exception:
            pass
        return result

    # ── Kademe 3: yfinance .info (paralel, sadece hâlâ eksikler) ──
    def _fetch_yf_names(missing: list) -> dict:
        result = {}
        if not missing:
            return result

        def _one(t: str) -> tuple:
            try:
                info = yf.Ticker(f"{t}.IS").info
                name = (info.get("longName") or info.get("shortName") or "").strip()
                if name and name.upper() not in (f"{t}.IS", t):
                    return t, name
            except Exception:
                pass
            return t, ""

        with ThreadPoolExecutor(max_workers=30) as ex:
            futures = {ex.submit(_one, t): t for t in missing}
            done = 0
            for fut in as_completed(futures):
                t, name = fut.result()
                if name:
                    result[t] = name
                done += 1
                if done % 100 == 0:
                    print(f"    yfinance isim: {done}/{len(missing)} islendi...")
        return result

    # ── Birleştir ─────────────────────────────────────────────
    names = {}

    # K1: KAP Excel
    kap_excel = _load_kap_excel()
    for t in tickers:
        if t in kap_excel:
            names[t] = kap_excel[t]
    missing_k1 = [t for t in tickers if t not in names]
    print(f"    K1 sonrasi: {len(names)} isim. Kalan: {len(missing_k1)}")

    # K2: KAP slug
    if missing_k1:
        kap_slug = _fetch_kap_names(missing_k1)
        for t, n in kap_slug.items():
            names[t] = n
        missing_k2 = [t for t in tickers if t not in names]
        print(f"    K2 KAP slug: +{len(kap_slug)} isim. Kalan: {len(missing_k2)}")
    else:
        missing_k2 = []

    # K3: yfinance (sadece hâlâ eksikler)
    if missing_k2:
        yf_names = _fetch_yf_names(missing_k2)
        for t, n in yf_names.items():
            names[t] = n
        missing_final = [t for t in tickers if t not in names]
        print(f"    K3 yfinance: +{len(yf_names)} isim. "
              f"Cozulemeyen: {len(missing_final)}")
    else:
        missing_final = []

    # Son fallback: ticker adını kullan
    for t in missing_final:
        names[t] = t

    total_named = sum(1 for t in tickers if names.get(t, t) != t)
    print(f"  BIST isim sonucu: {total_named}/{len(tickers)} gercek isim alindi.")
    return names



def batch_bist(tickers):
    """Tüm BIST'i batch download ile indir — RSI + Ret1M dahil."""
    import yfinance as yf
    print(f"  BIST batch download ({len(tickers)} hisse)...")
    result = {}
    chunk_size = 200
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        syms = [f"{t}.IS" for t in chunk]
        try:
            raw = yf.download(syms, period="3mo", progress=False,
                              auto_adjust=True, group_by="ticker")
            for t, sym in zip(chunk, syms):
                try:
                    if len(syms) == 1:
                        col = raw["Close"].dropna()
                        if hasattr(col, "squeeze"):
                            col = col.squeeze()
                    else:
                        if sym in raw.columns.get_level_values(0):
                            col = raw[sym]["Close"].dropna()
                            if hasattr(col, "squeeze"):
                                col = col.squeeze()
                        else:
                            col = pd.Series()
                    if col.empty:
                        result[t] = {"price": 0.0, "rsi": 50.0, "ret1m": 0.0, "vol": 30.0}
                        continue
                    p = round(float(col.iloc[-1]), 4)
                    rsi = calc_rsi(col)
                    ret1m = round((col.iloc[-1] / col.iloc[-22] - 1) * 100, 2) if len(col) >= 22 else 0.0
                    # Yıllık volatilite (%)
                    rets = col.pct_change().dropna()
                    vol = round(float(rets.std() * (252 ** 0.5) * 100), 1) if len(rets) > 10 else 30.0
                    result[t] = {"price": p, "rsi": rsi, "ret1m": ret1m, "vol": vol}
                except:
                    result[t] = {"price": 0.0, "rsi": 50.0, "ret1m": 0.0, "vol": 30.0}
        except Exception as e:
            print(f"  Chunk {i // chunk_size + 1} hata: {e}")
            for t in chunk:
                result[t] = {"price": 0.0, "rsi": 50.0, "ret1m": 0.0, "vol": 30.0}
    return result


def single_full(yf_sym, label="", period="1y"):
    """
    Tek sembol için fiyat + RSI + Ret1M.
    yfinance 1.4.x uyumlu: period yerine start= kullan (döviz için kritik).
    """
    import yfinance as yf
    from datetime import datetime, timedelta

    syms_to_try = [yf_sym]
    if (not yf_sym.endswith("=X") and not yf_sym.endswith("-USD")
            and "=F" not in yf_sym and "=X" not in yf_sym):
        syms_to_try.append(yf_sym + "=X")

    # start/end tarihi ile çek — period= ile bazı pariteler sadece 1 gün veriyor
    period_days = {"1mo": 35, "3mo": 100, "6mo": 185, "1y": 400, "5y": 1830}
    days = period_days.get(period, 400)
    start_dt = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_dt   = datetime.now().strftime("%Y-%m-%d")

    for sym in syms_to_try:
        try:
            # start/end ile çek — döviz çiftleri için çok daha güvenilir
            h = yf.download(sym, start=start_dt, end=end_dt,
                            auto_adjust=True, progress=False)
            if h.empty:
                # Fallback: period= dene
                h = yf.Ticker(sym).history(period=period, auto_adjust=True)
            if h.empty:
                continue
            pr = h["Close"].dropna()
            if hasattr(pr, "squeeze"):
                pr = pr.squeeze()   # MultiIndex → Series (yf 1.4.x)
            if len(pr) < 2:
                continue
            price = round(float(pr.iloc[-1]), 6)
            rsi   = calc_rsi(pr)
            ret1m = round((float(pr.iloc[-1]) / float(pr.iloc[-22]) - 1) * 100, 2) if len(pr) >= 22 else 0.0
            rets  = pr.pct_change().dropna()
            vol   = round(float(rets.std() * (252 ** 0.5) * 100), 1) if len(rets) > 10 else 30.0
            return price, rsi, ret1m, vol
        except Exception as e:
            continue
    return 0.0, 50.0, 0.0, 30.0




def get_cross_rate_hist(ticker: str, yf_sym: str,
                         start: str, end: str) -> "pd.Series":
    """
    JPYTRY, AUDTRY, CADTRY gibi doğrudan yfinance'de güvenilmez olan çiftler için
    USD üzerinden cross rate hesaplar.
    JPYTRY = USDTRY / USDJPY
    AUDTRY = AUDUSD * USDTRY
    CADTRY = USDCAD^-1 * USDTRY  (veya CADUSD * USDTRY)
    """
    import yfinance as yf

    cross_map = {
        "JPYTRY=X": ("USDTRY=X", "JPY=X",    "div"),   # USDTRY / USDJPY
        "AUDTRY=X": ("USDTRY=X", "AUDUSD=X",  "mul"),   # AUDUSD * USDTRY
        "CADTRY=X": ("USDTRY=X", "CAD=X",     "div"),   # USDTRY / USDCAD
        "NZDTRY=X": ("USDTRY=X", "NZDUSD=X",  "mul"),
        "NOKTRY=X": ("USDTRY=X", "NOK=X",     "div"),   # USDTRY / USDNOK
        "SEKTRY=X": ("USDTRY=X", "SEK=X",     "div"),   # USDTRY / USDSEK
        "DKKTRY=X": ("USDTRY=X", "DKK=X",     "div"),   # USDTRY / USDDKK
        "CNYTRY=X": ("USDTRY=X", "CNY=X",     "div"),   # USDTRY / USDCNY
    }

    if yf_sym not in cross_map:
        return pd.Series(dtype=float)

    sym_a, sym_b, op = cross_map[yf_sym]
    try:
        raw = yf.download([sym_a, sym_b], start=start, end=end,
                          auto_adjust=True, progress=False, group_by="ticker")
        if raw.empty:
            return pd.Series(dtype=float)
        ca = raw[sym_a]["Close"].dropna().squeeze() if sym_a in raw.columns.get_level_values(0) else pd.Series()
        cb = raw[sym_b]["Close"].dropna().squeeze() if sym_b in raw.columns.get_level_values(0) else pd.Series()
        if ca.empty or cb.empty:
            return pd.Series(dtype=float)
        # Ortak tarihler
        idx = ca.index.intersection(cb.index)
        ca, cb = ca.loc[idx], cb.loc[idx]
        if op == "div":
            result = ca / cb
        else:
            result = ca * cb
        return result.dropna()
    except:
        return pd.Series(dtype=float)

def build():
    global BIST_TICKERS

    # v2.0.4.5: Dinamik BIST evreni - Supabase'den daha once tespit edilen
    # ticker'lari yukle, sonra XHARZ'da yeni mezun var mi kontrol et. Ikisi de
    # BIST_TICKERS'a eklenir (statik 771 + dinamik). Herhangi bir adimda hata
    # olursa sessizce atlanir, statik 771 ile devam edilir - worker asla cokmez.
    _dyn_existing = _load_dynamic_bist_universe()
    _combined = list(dict.fromkeys(BIST_TICKERS + _dyn_existing))
    _new_grads = _detect_and_register_new_bist_listings(_combined)
    if _new_grads or _dyn_existing:
        BIST_TICKERS = list(dict.fromkeys(_combined + _new_grads))
        print(f"[dinamik-evren] Toplam BIST evreni: {len(BIST_TICKERS)} "
              f"(statik 771 + dinamik {len(BIST_TICKERS) - 771})")

    print("\n" + "=" * 60)
    print("  TrendSurf Optima — Evren Olusturma v7")
    print(f"  BIST: {len(BIST_TICKERS)} | Kripto: {len(KRIPTO)} | "
          f"Maden: {len(MADEN)} | Doviz: {len(DOVIZ)}")
    print("=" * 60)
    all_rows = []

    # ── 1. TEFAS ─────────────────────────────────────────────
    print("\n[1/4] TEFAS verisi hazirlanıyor...")
    df_t = load_tefas()
    if not df_t.empty:
        # pytefas ile güncel fiyatları güncelle
        try:
            from tefas_client import fetch_all_current_prices
            fund_list = df_t[["Ticker","TEFAS_Kind"]].to_dict("records")
            pytefas_prices = fetch_all_current_prices(fund_list)
            if pytefas_prices:
                df_t["Son_Fiyat"] = df_t["Ticker"].map(pytefas_prices).combine_first(df_t["Son_Fiyat"])
                ok = (df_t["Son_Fiyat"] > 0).sum()
                print(f"  pytefas fiyat guncellendi: {ok}/{len(df_t)} fon")
        except Exception as e:
            print(f"  pytefas fiyat guncelleme atlandi: {e}")
        all_rows += df_t.to_dict("records")
        fiyatli = (df_t["Son_Fiyat"] > 0).sum()
        print(f"  {len(df_t)} TEFAS fonu eklendi | Fiyatli: {fiyatli}")
    else:
        print("  TEFAS Excel bulunamadi! Klasorde xlsx dosyasi var mi?")

    # ── 2. BIST ───────────────────────────────────────────────
    print(f"\n[2/4] {len(BIST_TICKERS)} BIST hissesi (batch)...")
    bist_data = batch_bist(BIST_TICKERS)

    # Sadece fiyat gelen hisseler için isim çek
    priced_tickers = [t for t in BIST_TICKERS if bist_data.get(t, {}).get("price", 0) > 0]
    bist_names = fetch_bist_names_fast(priced_tickers)
    for t in BIST_TICKERS:
        if t not in bist_names:
            # Fiyat gelen ama isim gelemeyen hisseler
            if bist_data.get(t, {}).get("price", 0) > 0:
                bist_names[t] = t  # Ticker'ı ad olarak kullan
            else:
                bist_names[t] = f"{t} (islem gormuyor)"

    for t in BIST_TICKERS:
        d = bist_data.get(t, {})
        all_rows.append({
            "Ticker":    t,
            "Ad":        bist_names.get(t, t),
            "Kategori":  "BIST",
            "Son_Fiyat": d.get("price", 0.0),
            "RSI":       d.get("rsi", 50.0),
            "Ret1M":     d.get("ret1m", 0.0),
            "Vol":       d.get("vol", 30.0),
            "YF_Symbol": f"{t}.IS",
        })
    ok_bist = sum(1 for r in all_rows if r["Kategori"] == "BIST" and r["Son_Fiyat"] > 0)
    print(f"  {ok_bist}/{len(BIST_TICKERS)} fiyat alindi. "
          f"Kalan {len(BIST_TICKERS) - ok_bist} borsada islem gormuyordur.")

    # ── BIST cache yediği: fiyat 0 olan hisseleri son CSV'den tamamla ──
    bist_cache_ok = 0
    if os.path.exists(CSV_PATH):
        try:
            _df_cache = pd.read_csv(CSV_PATH).set_index("Ticker")
            for r in all_rows:
                if r.get("Kategori") == "BIST" and r.get("Son_Fiyat", 0) == 0:
                    t = r["Ticker"]
                    if t in _df_cache.index:
                        _cr = _df_cache.loc[t]
                        cached_p = float(_cr.get("Son_Fiyat", 0))
                        if cached_p > 0:
                            r["Son_Fiyat"] = cached_p
                            r["RSI"]       = float(_cr.get("RSI", 50))
                            r["Ret1M"]     = float(_cr.get("Ret1M", 0))
                            r["_cache"]    = True
                            bist_cache_ok += 1
            if bist_cache_ok:
                print(f"  [cache] {bist_cache_ok} BIST fiyati son CSV'den tamamlandi.")
        except Exception as _ce:
            print(f"  [cache] BIST cache atlanıyor: {_ce}")

    # ── 3. Kripto ─────────────────────────────────────────────
    KRIPTO_ADLAR = {
        "BTC": "Bitcoin", "ETH": "Ethereum", "BNB": "BNB",
        "SOL": "Solana", "ADA": "Cardano", "XRP": "XRP",
        "DOGE": "Dogecoin", "DOT": "Polkadot", "AVAX": "Avalanche",
        "CLINK": "Chainlink", "LTC": "Litecoin", "ATOM": "Cosmos",
        "TRX": "TRON", "NEAR": "NEAR Protocol", "ICP": "Internet Computer",
        "OP": "Optimism", "INJ": "Injective",
        "SUI": "Sui", "TON": "Toncoin",
    }
    print(f"\n[3/4] {len(KRIPTO)} kripto varlik (toplu download)...")
    import yfinance as yf
    from datetime import datetime, timedelta
    kripto_start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
    kripto_end   = datetime.now().strftime("%Y-%m-%d")
    kripto_syms  = [yf_s for _, yf_s in KRIPTO]
    kripto_map   = {yf_s: t for t, yf_s in KRIPTO}

    try:
        raw_k = yf.download(kripto_syms, start=kripto_start, end=kripto_end,
                            auto_adjust=True, progress=False, group_by="ticker")
    except Exception as e:
        print(f"  Kripto toplu download hatasi: {e}")
        raw_k = pd.DataFrame()

    kripto_results = {}
    for yf_s in kripto_syms:
        t = kripto_map[yf_s]
        try:
            if raw_k.empty:
                raise ValueError("bos")
            if len(kripto_syms) == 1:
                col = raw_k["Close"].dropna()
            else:
                col = raw_k[yf_s]["Close"].dropna() if yf_s in raw_k.columns.get_level_values(0) else pd.Series()
            if hasattr(col, "squeeze"):
                col = col.squeeze()
            if col.empty or len(col) < 2:
                raise ValueError("yetersiz veri")
            p    = round(float(col.iloc[-1]), 6)
            rsi  = calc_rsi(col)
            ret  = round((float(col.iloc[-1]) / float(col.iloc[-22]) - 1) * 100, 2) if len(col) >= 22 else 0.0
            rets_k = col.pct_change().dropna()
            vol_k  = round(float(rets_k.std() * (252 ** 0.5) * 100), 1) if len(rets_k) > 10 else 60.0
            kripto_results[yf_s] = (p, rsi, ret, vol_k)
        except:
            # Fallback: tek tek dene
            p2, rsi2, ret2, vol2 = single_full(yf_s, t)
            kripto_results[yf_s] = (p2, rsi2, ret2, vol2)

    for t, yf_s in KRIPTO:
        p, rsi, ret, vol_v = kripto_results.get(yf_s, (0.0, 50.0, 0.0, 30.0))
        all_rows.append({
            "Ticker": t, "Ad": KRIPTO_ADLAR.get(t, t),
            "Kategori": "KRIPTO", "Son_Fiyat": p,
            "RSI": rsi, "Ret1M": ret, "Vol": vol_v, "YF_Symbol": yf_s,
        })
    ok_k = sum(1 for r in all_rows if r["Kategori"] == "KRIPTO" and r["Son_Fiyat"] > 0)
    print(f"  {ok_k}/{len(KRIPTO)} kripto fiyati alindi.")

    # ── 4. Maden + Döviz ─────────────────────────────────────
    MADEN_ADLAR = {
        "ALTIN_TRY": "Altin (TL)", "GUMUS_TRY": "Gumus (TL)",
        "PLATIN_TRY": "Platin (TL)", "PALADYUM_TRY": "Paladyum (TL)",
        "BAKIR_TRY": "Bakir (TL)", "PETROL_TRY": "Ham Petrol WTI (TL)",
        "DOGALGAZ_TRY": "Dogal Gaz (TL)", "BRENT_TRY": "Brent Petrol (TL)",
        "BUGDAY_TRY": "Bugday (TL)", "MISIR_TRY": "Misir (TL)",
        "SOYA_TRY": "Soya Fasulyesi (TL)", "KAKAO_TRY": "Kakao (TL)",
    }
    DOVIZ_ADLAR = {
        "USDTRY": "Amerikan Dolari / Turk Lirasi",
        "EURTRY": "Euro / Turk Lirasi",
        "GBPTRY": "Ingiliz Sterlini / Turk Lirasi",
        "JPYTRY": "Japon Yeni / Turk Lirasi",
        "CHFTRY": "Isvicre Frangi / Turk Lirasi",
        "AUDTRY": "Avustralya Dolari / Turk Lirasi",
        "CADTRY": "Kanada Dolari / Turk Lirasi",
        "NZDTRY": "Yeni Zelanda Dolari / Turk Lirasi",
        "NOKTRY": "Norvec Kronu / Turk Lirasi",
        "SEKTRY": "Isvec Kronu / Turk Lirasi",
        "DKKTRY": "Danimarka Kronu / Turk Lirasi",
        "CNYTRY": "Cin Yuani / Turk Lirasi",
    }
    print(f"\n[4/4] {len(MADEN)} maden + {len(DOVIZ)} doviz (toplu download)...")
    maden_start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")

    # Maden toplu
    maden_syms = [yf_s for _, yf_s in MADEN]
    maden_map  = {yf_s: t for t, yf_s in MADEN}
    try:
        raw_m = yf.download(maden_syms, start=maden_start, end=kripto_end,
                            auto_adjust=True, progress=False, group_by="ticker")
    except:
        raw_m = pd.DataFrame()

    # USDTRY kuru — döviz bölümünden al, yoksa yfinance'den çek
    try:
        usdtry_rows = [r for r in all_rows if r.get("Ticker") == "USDTRY"]
        usdtry_rate = float(usdtry_rows[-1]["Son_Fiyat"]) if usdtry_rows else 0.0
    except Exception:
        usdtry_rate = 0.0
    if usdtry_rate <= 0:
        try:
            import yfinance as _yf2
            _s = _yf2.download("USDTRY=X", period="5d", progress=False, auto_adjust=True)
            usdtry_rate = float(_s["Close"].dropna().iloc[-1]) if not _s.empty else 38.0
        except Exception:
            usdtry_rate = 38.0

    # Bigpara'dan maden TL fiyatlarını çek (birincil kaynak)
    bp_maden = {}
    try:
        from bigpara_client import fetch_all_bigpara
        bp_maden = fetch_all_bigpara(usdtry=usdtry_rate)
        bp_ok = sum(1 for k in ["ALTIN_TRY","GUMUS_TRY","BRENT_TRY","PETROL_TRY"] if bp_maden.get(k, 0) > 0)
        if bp_ok:
            print(f"  [Bigpara] {bp_ok} maden fiyati Bigpara'dan alindi.")
    except Exception as _bp_err:
        print(f"  [Bigpara] Atlanıyor: {_bp_err}")

    # Gram dönüşüm katsayıları (ons → gram veya diğer birimler)
    # GC=F (Altın): ons/troy ounce → gram: 1 troy oz = 31.1035 gram
    # SI=F (Gümüş): ons → gram: 1 troy oz = 31.1035 gram
    # PL=F (Platin), PA=F (Paladyum): ons → gram
    ONS_TO_GRAM = {"GC=F", "SI=F", "PL=F", "PA=F"}

    for t, yf_s in MADEN:
        p, rsi, ret, vol_v = 0.0, 50.0, 0.0, 25.0

        # Kademe 1: Bigpara TL fiyatı (gram bazlı, direkt TL)
        bp_p = bp_maden.get(t, 0.0)
        if isinstance(bp_p, float) and bp_p > 0:
            p = bp_p
            rsi  = 50.0  # Bigpara'dan RSI geçmişi yok, nötr
            ret  = 0.0
            vol_v = 25.0
            print(f"    [Bigpara] {t}: {p:,.4f} TL (birincil)")

        # Kademe 2: yfinance USD fiyatı → TRY dönüşümü
        if p == 0.0:
            try:
                if raw_m.empty:
                    raise ValueError("bos")
                if len(maden_syms) == 1:
                    col = raw_m["Close"].dropna()
                else:
                    col = raw_m[yf_s]["Close"].dropna() if yf_s in raw_m.columns.get_level_values(0) else pd.Series()
                if hasattr(col, "squeeze"):
                    col = col.squeeze()
                if col.empty or len(col) < 2:
                    raise ValueError("yetersiz")
                p_usd = round(float(col.iloc[-1]), 4)
                rsi   = calc_rsi(col)
                ret   = round((float(col.iloc[-1]) / float(col.iloc[-22]) - 1) * 100, 2) if len(col) >= 22 else 0.0
                rets_m = col.pct_change().dropna()
                vol_v  = round(float(rets_m.std() * (252 ** 0.5) * 100), 1) if len(rets_m) > 10 else 25.0
                # USD → TRY dönüşümü + ons → gram (gerekiyorsa)
                if yf_s in ONS_TO_GRAM:
                    p = round(p_usd * usdtry_rate / 31.1035, 4)
                else:
                    p = round(p_usd * usdtry_rate, 4)
            except Exception:
                p2, rsi, ret, vol_v = single_full(yf_s, t)
                if p2 > 0:
                    if yf_s in ONS_TO_GRAM:
                        p = round(p2 * usdtry_rate / 31.1035, 4)
                    else:
                        p = round(p2 * usdtry_rate, 4)

        # Kademe 3: Son CSV'den tamamla
        if p == 0.0 and os.path.exists(CSV_PATH):
            try:
                _df_c = pd.read_csv(CSV_PATH)
                _row  = _df_c[_df_c["Ticker"] == t]
                if not _row.empty:
                    p     = float(_row["Son_Fiyat"].iloc[0])
                    rsi   = float(_row["RSI"].iloc[0])
                    ret   = float(_row["Ret1M"].iloc[0])
                    vol_v = float(_row.get("Vol", pd.Series([25.0])).iloc[0])
                    print(f"    [cache] {t} maden fiyati CSV'den alindi.")
            except Exception:
                pass

        all_rows.append({"Ticker": t, "Ad": MADEN_ADLAR.get(t, t),
                         "Kategori": "MADEN", "Son_Fiyat": p,
                         "RSI": rsi, "Ret1M": ret, "Vol": vol_v, "YF_Symbol": yf_s})

    # Döviz — her parite ayrı çek (=X pariteler toplu download'da sorunlu)
    # JPYTRY, AUDTRY, CADTRY için cross rate hesabı kullan
    CROSS_PAIRS = {"JPYTRY=X", "AUDTRY=X", "CADTRY=X", "NZDTRY=X",
                     "NOKTRY=X", "SEKTRY=X", "DKKTRY=X", "CNYTRY=X"}
    print(f"  Doviz: {len(DOVIZ)} parite (cross rate destekli)...")
    ok_d = 0
    for t, yf_s in DOVIZ:
        p, rsi, ret, vol_v = 0.0, 50.0, 0.0, 30.0
        if yf_s in CROSS_PAIRS:
            # Cross rate ile hesapla
            pr = get_cross_rate_hist(t, yf_s, maden_start, kripto_end)
            if len(pr) >= 2:
                p   = round(float(pr.iloc[-1]), 6)
                rsi = calc_rsi(pr)
                ret = round((float(pr.iloc[-1]) / float(pr.iloc[-22]) - 1) * 100, 2) if len(pr) >= 22 else 0.0
                rets_x = pr.pct_change().dropna()
                vol_v  = round(float(rets_x.std() * (252 ** 0.5) * 100), 1) if len(rets_x) > 10 else 10.0
        if p == 0.0:
            # Normal çekim dene
            p, rsi, ret, vol_v = single_full(yf_s, t)
        if p > 0:
            ok_d += 1
        all_rows.append({"Ticker": t, "Ad": DOVIZ_ADLAR.get(t, t),
                         "Kategori": "DOVIZ", "Son_Fiyat": p,
                         "RSI": rsi, "Ret1M": ret, "Vol": vol_v, "YF_Symbol": yf_s})
    print(f"  {ok_d}/{len(DOVIZ)} doviz fiyati alindi.")

    # ── TCMB yedek: yfinance'den gelemeyen kurları TCMB ile tamamla ──
    try:
        from tcmb_client import enrich_worker_doviz
        all_rows = enrich_worker_doviz(all_rows)
        tcmb_ok = sum(1 for r in all_rows
                      if r.get("Kategori") == "DOVIZ"
                      and r.get("_tcmb_guncellendi"))
        if tcmb_ok:
            print(f"  [TCMB] {tcmb_ok} kur TCMB ile guncellendi/tamamlandi.")
    except Exception as _tcmb_ex:
        print(f"  [TCMB] Atlanıyor: {_tcmb_ex}")

    # ── Kaydet ────────────────────────────────────────────────
    df = pd.DataFrame(all_rows)
    for col in ["RSI", "Ret1M"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(50.0 if col == "RSI" else 0.0)
    for col in ["Ret3M", "Ret1Y"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "Vol" not in df.columns:
        df["Vol"] = 30.0
    df["Vol"] = pd.to_numeric(df["Vol"], errors="coerce").fillna(30.0)
    if "YF_Symbol" not in df.columns:
        df["YF_Symbol"] = ""
    if "TEFAS_Kind" not in df.columns:
        df["TEFAS_Kind"] = ""
    df = df.drop_duplicates(subset=["Ticker"], keep="last").reset_index(drop=True)
    df.to_csv(OUTPUT, index=False, encoding="utf-8")

    # ── v2.0.4.8: Yaklasan Halka Arzlar + Fiyat Tespit Raporu cache'i ────────
    # Bu adim optimized_universe.csv'yi ETKILEMEZ - ayri bir cache dosyasina
    # (upcoming_ipo_cache/*.json) yazar. app.py bu cache'i OKUR, kendisi asla
    # PDF indirip OCR yapmaz - boylece Streamlit Cloud'da sayfa acilisi
    # yavaslamaz. force_refresh=True: KAP izahname listesi her gece taze
    # cekilir; PDF indirme/OCR ise kendi ic cache'i (fiyat_tespit_sonuclari.json)
    # sayesinde sadece DAHA ONCE ISLENMEMIS raporlar icin yapilir.
    # Hata durumunda (KAP erisilemez, tesseract kurulu degil vb.) SESSIZCE
    # atlanir - worker asla bu yuzden cokmez, ana CSV zaten kaydedildi.
    try:
        from upcoming_ipo_client import fetch_upcoming_ipos
        _df_ipo = fetch_upcoming_ipos(force_refresh=True)
        print(f"  [Yaklasan Halka Arz] {len(_df_ipo)} kayit cache'e yazildi.")
    except Exception as e:
        print(f"  [Yaklasan Halka Arz] Atlaniyor (hata): {e}")

    print("\n" + "=" * 60)
    print(f"  TAMAM: {len(df)} varlik -> {OUTPUT}")
    for cat, cnt in df.groupby("Kategori").size().sort_values(ascending=False).items():
        fiyatli = df[(df["Kategori"] == cat) & (df["Son_Fiyat"] > 0)]
        ret_ok  = df[(df["Kategori"] == cat) & (df.get("Ret1M", pd.Series(0)) != 0)] if "Ret1M" in df else pd.DataFrame()
        print(f"    {cat:10}: {cnt:5} toplam  |  {len(fiyatli):5} fiyatli")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    build()
