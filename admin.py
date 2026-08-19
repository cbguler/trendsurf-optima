"""
TrendSurf Optima — Admin Paneli (admin.py)
"""
import streamlit as st
from db import get_conn
from auth import get_current_user

def render_admin_panel():
    user = get_current_user()
    if not user or not user["is_admin"]:
        st.error("Bu sayfaya erisim yetkiniz yok.")
        return

    st.title("Admin Paneli")

    conn = get_conn()
    users = conn.execute(
        "SELECT id, email, full_name, plan, is_active, is_admin, created_at "
        "FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    # ── Onay bekleyenler ─────────────────────────────────────────────────────
    pending = [u for u in users if not u["is_active"]]
    if pending:
        st.subheader(f"Onay Bekleyenler ({len(pending)})")
        for u in pending:
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            c1.write(f"**{u['full_name']}**  `{u['email']}`")
            new_plan = c2.selectbox("Plan", ["free", "pro", "premium"],
                                    key=f"plan_p_{u['id']}")
            if c3.button("Onayla", key=f"approve_{u['id']}"):
                _approve_user(u["id"], new_plan)
                st.rerun()
            if c4.button("Reddet", key=f"reject_{u['id']}"):
                _delete_user(u["id"])
                st.rerun()
        st.divider()

    # ── Tum kullanicilar ─────────────────────────────────────────────────────
    active = [u for u in users if u["is_active"]]
    st.subheader(f"Aktif Kullanicilar ({len(active)})")
    for u in active:
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        prefix = "[Admin] " if u["is_admin"] else ""
        c1.markdown(f"**{prefix}{u['full_name']}**  `{u['email']}`")
        new_plan = c2.selectbox(
            "Plan", ["free", "pro", "premium"],
            index=["free", "pro", "premium"].index(u["plan"]),
            key=f"plan_a_{u['id']}"
        )
        if c3.button("Kaydet", key=f"save_{u['id']}"):
            _update_plan(u["id"], new_plan)
            st.success("Guncellendi.")
        if not u["is_admin"] and c4.button("Sil", key=f"del_{u['id']}"):
            _delete_user(u["id"])
            st.rerun()
    st.divider()
    _render_kalip_yonetimi()

# ── Kalıp Yönetimi (v2.0.7.162, Bahri'nin talebi, 19 Ağustos 2026 —
# "anahtar kelime ön-filtresi ve kalıplara daha sonra ekleme yapılabilir
# hale getirilebilir mi ... hangi varlıkların Optima Skorları hangi
# oranda etkilenecektir tabloda bunları da görmek isterdim") ─────────────
_KATEGORILER = ["MADEN", "DOVIZ", "BIST", "KRIPTO"]
_KATEGORI_ADI = {"MADEN": "Değerli Maden", "DOVIZ": "Döviz", "BIST": "BIST",
                 "KRIPTO": "Kripto"}


def _render_kalip_yonetimi():
    import pandas as pd
    from db import get_kaliplar

    st.subheader("Kalıp Yönetimi (Beklenti Modu)")
    st.caption(
        "haber_izleme.py'nin haberleri sınıflandırmak için kullandığı "
        "kalıplar. Buradaki değişiklikler KOD DEĞİŞİKLİĞİ/DEPLOY "
        "GEREKTİRMEZ - en geç 10 dakika içinde (bir sonraki haber "
        "taraması) devreye girer."
    )
    kaliplar = get_kaliplar(sadece_aktif=False)

    # ── Bahri'nin istediği etki tablosu ─────────────────────────────
    st.markdown("**Kalıp → Kategori Etki Tablosu**")
    if kaliplar:
        satirlar = []
        for k in kaliplar:
            satir = {"Kalıp": k["ad"] + ("" if k["aktif"] else " (PASİF)")}
            for kat in _KATEGORILER:
                puan = k["etkiler"].get(kat)
                satir[_KATEGORI_ADI[kat]] = f"{puan:+.1f}" if puan is not None else "—"
            satirlar.append(satir)
        st.dataframe(pd.DataFrame(satirlar), width='stretch', hide_index=True)
        st.caption(
            "Pozitif = o kategorinin Optima Skoru ARTAR, negatif = AZALIR, "
            "'—' = bu kalıp o kategoriyi etkilemiyor. Gösterilen değer "
            "HAM puandır - onaya sunulmadan önce Şiddet (Düşük/Orta/"
            "Yüksek) ve Risk Toleransı çarpanlarıyla ölçeklenir."
        )
    else:
        st.info("Henüz hiç kalıp yok.")
    st.divider()

    # ── Her kalıp için düzenleme paneli ─────────────────────────────
    for k in kaliplar:
        _baslik = k["ad"] + ("  (PASİF)" if not k["aktif"] else "")
        with st.expander(_baslik):
            _render_kalip_detay(k)

    st.divider()
    with st.expander("Yeni Kalıp Ekle"):
        st.caption(
            "Anahtar, kod içinde kullanılan kimliktir - küçük harf, "
            "boşluksuz (örn. 'doviz_krizi'). Oluşturduktan sonra bu "
            "listeye geri dönüp kelime ve etki puanı ekleyin - kelimesiz/"
            "etkisiz bir kalıp hiçbir şeyi tetiklemez."
        )
        _yk = st.text_input("Anahtar", key="yeni_kalip_key")
        _ya = st.text_input("Görünen ad", key="yeni_kalip_ad")
        _yac = st.text_area("Açıklama / istatistiksel dayanak (opsiyonel)",
                            key="yeni_kalip_aciklama")
        if st.button("Kalıbı Oluştur", key="yeni_kalip_olustur"):
            if not _yk.strip() or not _ya.strip():
                st.error("Anahtar ve ad zorunlu.")
            else:
                from db import kalip_ekle
                _kk = _yk.strip().lower().replace(" ", "_")
                if kalip_ekle(_kk, _ya.strip(), _yac.strip()):
                    st.cache_data.clear()
                    st.success(f"'{_ya}' oluşturuldu.")
                    st.rerun()
                else:
                    st.error("Oluşturulamadı - bu anahtar zaten kullanılıyor olabilir.")


def _render_kalip_detay(k):
    from db import (kalip_kelime_ekle, kalip_kelime_sil, kalip_etki_kaydet,
                    kalip_aktif_durum_degistir, kalip_sil)
    kk = k["kalip_key"]

    _c1, _c2 = st.columns([3, 1])
    _yeni_aktif = _c1.toggle("Aktif", value=k["aktif"], key=f"aktif_{kk}")
    if _yeni_aktif != k["aktif"]:
        kalip_aktif_durum_degistir(kk, _yeni_aktif)
        st.cache_data.clear()
        st.rerun()
    st.caption(k["aciklama"] or "(açıklama yok)")

    st.markdown("**Anahtar kelimeler**")
    st.caption(
        "Kelime SINIRINA saygılı eşleştirme kullanılır - 'war' kelimesi "
        "'warning' içinde YAKALANMAZ (bkz. v2.0.7.161 düzeltmesi). Türkçe "
        "kelimeler çekim ekleriyle de eşleşir (savaş → savaşı/savaşta), "
        "İngilizce SADECE çoğuluyla eşleşir."
    )
    for _dil, _dil_ad in [("tr", "Türkçe"), ("en", "İngilizce")]:
        st.caption(_dil_ad)
        _kelimeler = k["kelimeler"].get(_dil, [])
        if _kelimeler:
            _cols = st.columns(4)
            for _i, _kel in enumerate(_kelimeler):
                with _cols[_i % 4]:
                    if st.button(f"✕ {_kel}", key=f"kel_sil_{kk}_{_dil}_{_i}"):
                        kalip_kelime_sil(kk, _dil, _kel)
                        st.cache_data.clear()
                        st.rerun()
        _ec1, _ec2 = st.columns([3, 1])
        _yeni_kelime = _ec1.text_input(
            "Yeni kelime", key=f"yeni_kel_{kk}_{_dil}",
            label_visibility="collapsed", placeholder=f"{_dil_ad} kelime ekle...")
        if _ec2.button("Ekle", key=f"kel_ekle_{kk}_{_dil}"):
            if _yeni_kelime.strip():
                kalip_kelime_ekle(kk, _dil, _yeni_kelime.strip())
                st.cache_data.clear()
                st.rerun()

    st.divider()
    st.markdown("**Kategori Etki Puanları**")
    st.caption("Pozitif = Optima Skoru artar, negatif = azalır, 0 = etkisiz (satır silinir).")
    _cols2 = st.columns(4)
    _yeni_etkiler = {}
    for _i2, _kat in enumerate(_KATEGORILER):
        _mevcut = k["etkiler"].get(_kat, 0.0)
        with _cols2[_i2]:
            _yeni_etkiler[_kat] = st.number_input(
                _KATEGORI_ADI[_kat], value=float(_mevcut), step=0.5,
                key=f"etki_{kk}_{_kat}")
    if st.button("Puanları Kaydet", key=f"etki_kaydet_{kk}"):
        for _kat, _puan in _yeni_etkiler.items():
            kalip_etki_kaydet(kk, _kat, _puan)
        st.cache_data.clear()
        st.success("Kaydedildi.")
        st.rerun()

    st.divider()
    if st.button("Bu Kalıbı Kalıcı Olarak Sil", key=f"kalip_sil_btn_{kk}"):
        st.session_state[f"sil_onay_{kk}"] = True
    if st.session_state.get(f"sil_onay_{kk}"):
        st.warning(
            f"'{k['ad']}' kalıbı ve TÜM kelimeleri/etki puanları KALICI "
            f"OLARAK silinecek. Bu geri alınamaz. Emin misiniz?")
        _sc1, _sc2 = st.columns(2)
        if _sc1.button("Evet, Sil", key=f"sil_evet_{kk}"):
            kalip_sil(kk)
            st.cache_data.clear()
            st.session_state.pop(f"sil_onay_{kk}", None)
            st.rerun()
        if _sc2.button("Vazgeç", key=f"sil_vazgec_{kk}"):
            st.session_state.pop(f"sil_onay_{kk}", None)
            st.rerun()

# ── DB yardimcilari ──────────────────────────────────────────────────────────
def _approve_user(user_id: int, plan: str):
    conn = get_conn()
    conn.execute("UPDATE users SET is_active=1, plan=? WHERE id=?", (plan, user_id))
    conn.commit(); conn.close()

def _update_plan(user_id: int, plan: str):
    conn = get_conn()
    conn.execute("UPDATE users SET plan=? WHERE id=?", (plan, user_id))
    conn.commit(); conn.close()

def _delete_user(user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit(); conn.close()
