"""
core/config.py
--------------
قراءة الاسرار والاعدادات. ما في ملفات: القيم بتجي من
  - Streamlit Cloud Secrets   (للوحة)
  - GitHub Actions Secrets    (للمهمة اليومية، بتوصل كمتغيرات بيئة)
بس اثنين لازم تنحط: DATABASE_URL و SECRET_KEY. كل شي ثاني من داخل المنصة.
"""
import os


def secret(name: str, default=None):
    v = os.getenv(name)
    if v:
        return v
    try:  # داخل Streamlit
        import streamlit as st
        v = st.secrets.get(name)
        if v:
            return str(v)
    except Exception:  # noqa: BLE001  (ما في streamlit او ما في secrets.toml)
        pass
    return default


META_API_VERSION = secret("META_API_VERSION", "v23.0")
DEFAULT_TZ = secret("TIMEZONE", "Asia/Amman")

# القيم الافتراضية للقواعد (بتتعدل من صفحة الاعدادات داخل المنصة)
DEFAULT_RULES = {
    "min_impressions": 1000,
    "min_ctr": 1.0,
    "max_frequency": 3.5,
    "no_conv_spend": 20.0,
    "cpa_spike": 0.5,
    "cpc_spike": 0.4,
    "spend_spike_x": 2.0,
}

DEFAULT_CONV_TYPES = "lead,purchase,onsite_conversion.messaging_conversation_started_7d"
