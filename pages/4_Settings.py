"""
pages/4_Settings.py  —  حدود التنبيه، وقت التشغيل، تعريف النتيجة، المستخدمين
"""
import streamlit as st

from zoneinfo import ZoneInfo

from core.boot import require_login
from core.config import DEFAULT_TZ, DEFAULT_CONV_TYPES
from core.database import (get_rules, save_rules, get_setting, set_setting, create_user)

st.set_page_config(page_title="الاعدادات", page_icon="⚙️", layout="wide")
require_login()
st.title("⚙️ الاعدادات")

# ---- الجدولة ----
st.subheader("وقت التشغيل اليومي")
st.caption("GitHub بيفحص كل ساعة، وبيشغّل المهمة اول مرة بعد الساعة اللي بتحددها (ممكن يتأخر شوي). "
           f"آخر تشغيل ناجح: {get_setting('last_run_date', '—')}")
with st.form("sched"):
    hour = st.number_input("الساعة (0-23)", 0, 23, int(get_setting("alert_hour", 8)))
    tz = st.text_input("المنطقة الزمنية", get_setting("timezone", DEFAULT_TZ))
    if st.form_submit_button("حفظ"):
        try:
            ZoneInfo(tz.strip())
            set_setting("alert_hour", int(hour))
            set_setting("timezone", tz.strip())
            st.success("تم الحفظ")
        except Exception:  # noqa: BLE001
            st.error("منطقة زمنية غلط. مثال: Asia/Amman او Asia/Riyadh")

# ---- تعريف النتيجة ----
st.subheader("شو تعتبر «نتيجة»؟")
st.caption("action types مفصولة بفاصلة. مثال: lead, purchase, onsite_conversion.messaging_conversation_started_7d")
with st.form("conv"):
    ct = st.text_input("Conversion action types", get_setting("conv_types", DEFAULT_CONV_TYPES))
    if st.form_submit_button("حفظ"):
        set_setting("conv_types", ct.strip())
        st.success("تم الحفظ")

# ---- القواعد ----
st.subheader("حدود التنبيه")
r = get_rules()
with st.form("rules"):
    c = st.columns(2)
    r["min_impressions"] = c[0].number_input("اقل ظهور لحساب CTR", 0, 1_000_000, int(r["min_impressions"]))
    r["min_ctr"] = c[1].number_input("اقل CTR %", 0.0, 100.0, float(r["min_ctr"]), 0.1)
    r["max_frequency"] = c[0].number_input("اقصى تكرار", 0.0, 50.0, float(r["max_frequency"]), 0.1)
    r["no_conv_spend"] = c[1].number_input("صرف بدون نتائج (تنبيه عند)", 0.0, 1e6, float(r["no_conv_spend"]), 5.0)
    r["cpa_spike"] = c[0].number_input("ارتفاع تكلفة النتيجة (0.5 = +50%)", 0.0, 10.0, float(r["cpa_spike"]), 0.1)
    r["cpc_spike"] = c[1].number_input("ارتفاع تكلفة النقرة (0.4 = +40%)", 0.0, 10.0, float(r["cpc_spike"]), 0.1)
    r["spend_spike_x"] = c[0].number_input("قفزة الصرف (x المعدل)", 1.0, 20.0, float(r["spend_spike_x"]), 0.1)
    if st.form_submit_button("حفظ الحدود"):
        save_rules(r)
        st.success("تم الحفظ")

# ---- مستخدمين ----
st.subheader("اضافة مستخدم")
with st.form("newuser"):
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور (8+)", type="password")
    if st.form_submit_button("اضف"):
        if u.strip() and len(p) >= 8:
            try:
                create_user(u, p)
                st.success("تمت الاضافة")
            except Exception:  # noqa: BLE001
                st.error("الاسم مستخدم من قبل")
        else:
            st.error("اسم مطلوب وكلمة مرور 8 احرف على الاقل")
