"""
app.py  —  الصفحة الرئيسية (لوحة المتابعة)
شغّلها:  streamlit run app.py
"""
import pandas as pd
import streamlit as st

from core.boot import require_login
from core.database import query_df, list_accounts, get_secret, get_setting
from core.jobs import run_job

st.set_page_config(page_title="لوحة المتابعة", page_icon="📊", layout="wide")
require_login()


@st.cache_data(ttl=60, show_spinner=False)
def load_insights() -> pd.DataFrame:
    return query_df("SELECT * FROM insights")


st.title("📊 لوحة المتابعة")

accounts = list_accounts()
has_token = bool(get_secret("meta_token"))
has_tg = bool(get_secret("tg_token") and get_setting("tg_chat_id"))

# ---- قائمة الاعداد (بتظهر لحد ما تكمل) ----
if not (has_token and accounts and has_tg):
    st.subheader("خطوات الاعداد")
    st.markdown(f"""
{'✅' if has_token else '⬜'} **1.** ربط توكن ميتا — صفحة *Accounts*  
{'✅' if accounts else '⬜'} **2.** اضافة الحسابات الاعلانية — صفحة *Accounts*  
{'✅' if has_tg else '⬜'} **3.** ربط بوت تيليجرام — صفحة *Telegram*
""")

with st.sidebar:
    st.header("تحكم")
    days = st.slider("عدد الايام للعرض", 7, 90, 14)
    if st.button("🔄 جلب البيانات الآن", use_container_width=True):
        with st.spinner("عم بجيب البيانات من ميتا..."):
            res = run_job(days=3)
        load_insights.clear()
        if res["errors"]:
            st.error("\n".join(res["errors"]))
        else:
            st.success(f"{res['rows']} سطر، {res['alerts']} تنبيه جديد")

st.sidebar.caption(f"آخر تشغيل يومي: {get_setting('last_run_date', '—')}")

df = load_insights()

if df.empty:
    st.info("ما في بيانات لسا. اضف حساب من صفحة Accounts ومن هناك اعمل «تحميل آخر 30 يوم».")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
names = {a["account_id"]: a["name"] for a in accounts}
df["account"] = df["account_id"].map(names).fillna(df["account_id"])
chosen = st.multiselect("الحسابات", sorted(df["account"].unique()), default=sorted(df["account"].unique()))
cutoff = df["date"].max() - pd.Timedelta(days=days - 1)
df = df[df["account"].isin(chosen) & (df["date"] >= cutoff)]

spend, clicks = df["spend"].sum(), df["clicks"].sum()
impr, conv = df["impressions"].sum(), df["conversions"].sum()
c = st.columns(5)
c[0].metric("الصرف", f"{spend:,.2f}")
c[1].metric("الظهور", f"{impr:,}")
c[2].metric("CTR", f"{(clicks / impr * 100) if impr else 0:.2f}%")
c[3].metric("النتائج", f"{conv:,.0f}")
c[4].metric("تكلفة النتيجة", f"{(spend / conv) if conv else 0:,.2f}")

daily = df.groupby("date", as_index=False)[["spend", "conversions"]].sum().set_index("date")
a, b = st.columns(2)
a.subheader("الصرف اليومي")
a.bar_chart(daily["spend"])
b.subheader("النتائج اليومية")
b.line_chart(daily["conversions"])

st.subheader("الحملات")
camp = df.groupby(["account", "campaign_name"], as_index=False).agg(
    spend=("spend", "sum"), impressions=("impressions", "sum"), clicks=("clicks", "sum"),
    conversions=("conversions", "sum"), frequency=("frequency", "mean"))
camp["ctr_%"] = (camp["clicks"] / camp["impressions"].replace(0, pd.NA) * 100).round(2)
camp["cpc"] = (camp["spend"] / camp["clicks"].replace(0, pd.NA)).round(2)
camp["cpa"] = (camp["spend"] / camp["conversions"].replace(0, pd.NA)).round(2)
camp["frequency"] = camp["frequency"].round(2)
st.dataframe(camp.sort_values("spend", ascending=False), use_container_width=True, hide_index=True)
