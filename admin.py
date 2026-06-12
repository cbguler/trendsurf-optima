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
