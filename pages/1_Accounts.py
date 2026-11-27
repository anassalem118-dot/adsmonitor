"""
pages/1_Accounts.py  —  ربط ميتا واضافة الحسابات اوتوماتيك
"""
import pandas as pd
import streamlit as st

from core.boot import require_login
from core.database import (set_secret, get_secret, upsert_account, list_accounts,
                           set_account_active, delete_account)
from core.meta_api import check_token, discover_accounts, MetaError
from core.jobs import run_job

st.set_page_config(page_title="الحسابات", page_icon="🔗", layout="wide")
require_login()
st.title("🔗 حسابات ميتا")

# ---------- 1) التوكن ----------
st.subheader("1) توكن ميتا")
if get_secret("meta_token"):
    st.success("التوكن محفوظ (مشفّر). بتقدر تبدله بتوكن جديد تحت.")
with st.form("token_form"):
    tok = st.text_input("Access Token (صلاحية ads_read)", type="password")
    if st.form_submit_button("تحقق واحفظ"):
        try:
            who = check_token(tok.strip())
            set_secret("meta_token", tok.strip())
            st.success(f"تم الربط ✅ ({who})")
            st.session_state.pop("found", None)
        except MetaError as e:
            st.error(f"التوكن مش شغال: {e}")

# ---------- 2) اكتشاف الحسابات ----------
st.subheader("2) اضافة الحسابات اوتوماتيك")
if get_secret("meta_token"):
    if st.button("🔍 اجلب كل حساباتي الاعلانية"):
        try:
            st.session_state["found"] = discover_accounts(get_secret("meta_token"))
        except MetaError as e:
            st.error(str(e))

    found = st.session_state.get("found")
    if found:
        existing = {a["account_id"] for a in list_accounts()}
        df = pd.DataFrame(found)
        df["اضافة"] = ~df["account_id"].isin(existing)
        edited = st.data_editor(df, hide_index=True, use_container_width=True,
                                disabled=["account_id", "name", "currency", "status"])
        if st.button("➕ اضف المحدد"):
            sel = edited[edited["اضافة"]]
            for _, r in sel.iterrows():
                upsert_account(r["account_id"], r["name"], r["currency"])
            st.success(f"تمت اضافة {len(sel)} حساب")
            st.rerun()
    elif found == []:
        st.warning("ما لقيت حسابات. تأكد ان التوكن عنده صلاحية ads_read وانك مدير على الحساب.")
else:
    st.caption("احفظ التوكن اول.")

with st.expander("اضافة حساب يدوي (بالـ ID)"):
    with st.form("manual"):
        aid = st.text_input("Ad Account ID (بدون act_)")
        nm = st.text_input("اسم للتعريف")
        if st.form_submit_button("اضف") and aid.strip():
            upsert_account(aid.strip(), nm.strip() or aid.strip(), "")
            st.rerun()

# ---------- 3) الحسابات المضافة ----------
st.subheader("3) الحسابات المضافة")
accs = list_accounts()
if not accs:
    st.info("ما في حسابات بعد.")
for a in accs:
    c = st.columns([3, 1, 2, 1])
    c[0].markdown(f"**{a['name']}**  \n`{a['account_id']}` {a['currency'] or ''}")
    active = c[1].toggle("فعّال", value=bool(a["active"]), key=f"act_{a['account_id']}")
    if active != bool(a["active"]):
        set_account_active(a["account_id"], active)
        st.rerun()
    c[2].caption(f"آخر مزامنة: {a['last_sync'] or '—'}")
    if a["last_error"]:
        c[2].error(a["last_error"])
    if c[3].button("🗑️", key=f"del_{a['account_id']}"):
        delete_account(a["account_id"])
        st.rerun()

if accs and st.button("⏪ تحميل آخر 30 يوم (بدون تنبيهات)"):
    with st.spinner("عم بحمّل..."):
        res = run_job(days=30, alert=False)
    st.success(f"تم تحميل {res['rows']} سطر") if not res["errors"] else st.error("\n".join(res["errors"]))
