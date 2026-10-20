"""Piyasa rejimi bilgi seridi verisi (v2.0.7.426).

AMAC: Turkiye geneli, tek bir varlik/fon hakkinda olmayan piyasa olaylarini (ornegin MSCI'in
endeks dondurmasi) Ana Sayfa / BIST / TEFAS ust kisminda BILGI seridi olarak gostermek.
SKORU DEGISTIRMEZ: hangi hissenin etkilenecegi belli olmayan bir piyasa-geneli olayi tek tek skorlara
carpan olarak yansitmak dayanaksiz olurdu (Bahri ile gorusme, 20 Ekim 2026).

Bu modul saf Python'dur (streamlit yok) - test edilebilir. Gosterim app.py'deki
`_piyasa_rejimi_goster(sayfa)` ile yapilir.

Yeni olay eklemek icin REJIMLER listesine bir sozluk eklenir; sona erince `bitis` tarihi verilir
(YYYY-MM-DD, o gun DAHIL degil - ertesi gunden itibaren gizlenir).
"""
from datetime import date

# kapsam: seridin gosterilecegi sayfalar (app.py'deki sayfa adlari)
REJIMLER = [
    {
        "id": "msci-2026-10-16-dondurma",
        "rozet": "PİYASA REJİMİ",
        "baslik": "MSCI, Türkiye endekslerindeki değişiklikleri dondurdu (16 Ekim 2026)",
        "ozet": (
            "MSCI, Türk hisselerinde yabancı yatırımcı oranı (FIF) veya hisse sayısı (NOS) artışı "
            "uygulamayacak, IMI endeksine yeni hisse eklemeyecek ve büyüklük segmentlerinde üst kategoriye "
            "geçişe izin vermeyecek. Karar bir sonraki duyuruya kadar geçerli."
        ),
        "ayrinti": [
            "Gerekçe: MSCI, kurumsal yatırımcıların küçük ölçekli halka açık şirketlerle yakın ilişkili "
            "fonların paylarıyla olası koordineli işlemlerinden ciddi endişe duyduğunu belirtti; bunun "
            "serbest dolaşım oranı hesaplarının güvenilirliğini ve piyasa bütünlüğünü bozabileceğini vurguladı.",
            "MSCI'ın beklentileri: şirketlerin nihai pay sahiplerine ilişkin ayrıntılı bilgi paylaşımı, "
            "koordineli işlemlere karşı denetim ve yaptırım mekanizmaları, serbest dolaşımı bozulmuş "
            "menkul kıymetlerin tespitine yönelik kurallara dayalı bir sistem. MSCI, Türk yetkililerin bazı ilk "
            "adımlar attığını (nihai sahibi zaten hariç tutulan fon paylarının serbest dolaşımdan düşülmesi "
            "gibi) ancak bunların yeterli olmadığını, güvenilir ve sürdürülebilir bir yaptırım uygulaması "
            "gerektiğini belirtti.",
            "Takvim: Haziran 2027'ye kadar yeterli ilerleme sağlanamazsa MSCI ek tedbirleri değerlendirecek; "
            "bunlar arasında Türkiye endekslerinin yeniden sınıflandırılmasına (Sınır veya Bağımsız Piyasa "
            "statüsü) ilişkin bir istişare başlatmak da var. Türkiye endekslerinin durumu 2027 Yıllık Piyasa "
            "Sınıflandırma İncelemesi kapsamında yeniden değerlendirilecek.",
            "Bu bilgi piyasa geneline aittir: Optima Skor'u DEĞİŞTİRMEZ ve belirli bir hisse ya da fon "
            "hakkında hüküm değildir.",
        ],
        "kaynaklar": [
            ("MSCI - MSCI Implements a Freeze on the MSCI Turkey Indexes (basın duyurusu, 15.10.2026)",
             "https://www.msci.com/downloads/documents/press-releases/media-room/Turkey_PR_Oct_26.pdf"),
        ],
        "kapsam": ("Ana Sayfa", "BIST", "TEFAS"),
        "baslangic": "2026-10-16",
        "bitis": None,
    },
]


def _tarih(s):
    return date.fromisoformat(s) if s else None


def aktif_rejimler(sayfa, bugun=None):
    """Verilen sayfada, `bugun` itibariyle gosterilecek rejim kayitlari (liste, sirali)."""
    bugun = bugun or date.today()
    out = []
    for r in REJIMLER:
        if sayfa not in r.get("kapsam", ()):
            continue
        bas, bit = _tarih(r.get("baslangic")), _tarih(r.get("bitis"))
        if bas and bugun < bas:
            continue
        if bit and bugun >= bit:
            continue
        out.append(r)
    return out
