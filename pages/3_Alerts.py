"""
pages/3_Alerts.py  —  سجل التنبيهات + تشغيل التحليل يدوي
"""
import streamlit as st

from core.boot import require_login
from core.database import query_df, mark_alerts_sent
from core.analysis import analyze, store_new_alerts
from core.jobs import yesterday
from core.telegram_service import notify_alerts

st.set_page_config(page_title="التنبيهات", page_icon="🚨", layout="wide")
require_login()
st.title("🚨 التنبيهات")

if st.button("▶️ شغّل التحليل على امس وابعت التنبيهات الجديدة"):
    target = yesterday()
    new = store_new_alerts(analyze(target))
    if new and notify_alerts(new, target):
        mark_alerts_sent([a["id"] for a in new])
    st.success(f"{len(new)} تنبيه جديد")

df = query_df("SELECT date, campaign_name, rule, severity, message, sent "
              "FROM alerts ORDER BY id DESC LIMIT 300")
if df.empty:
    st.success("ما في تنبيهات 🎉")
else:
    sev = st.multiselect("الخطورة", ["critical", "warning"], default=["critical", "warning"])
    st.dataframe(df[df["severity"].isin(sev)], use_container_width=True, hide_index=True)
