"""
pages/2_Telegram.py  —  ربط بوت تيليجرام من داخل المنصة
"""
import streamlit as st

from core.boot import require_login
from core.database import get_secret, set_secret, get_setting, set_setting
from core.telegram_service import verify_bot, detect_chat, send_message

st.set_page_config(page_title="تيليجرام", page_icon="✈️", layout="wide")
require_login()
st.title("✈️ ربط بوت تيليجرام")

tok = get_secret("tg_token")
chat = get_setting("tg_chat_id")

st.subheader("1) توكن البوت")
st.caption("افتح @BotFather في تيليجرام ← /newbot ← انسخ التوكن.")
if tok:
    st.success(f"البوت مربوط: {get_setting('tg_bot_name', '')}")
with st.form("bot"):
    new = st.text_input("Bot Token", type="password")
    if st.form_submit_button("تحقق واحفظ") and new.strip():
        try:
            name = verify_bot(new.strip())
            set_secret("tg_token", new.strip())
            set_setting("tg_bot_name", name)
            st.success(f"تم ✅ {name}")
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"التوكن غلط: {e}")

st.subheader("2) ربط المحادثة")
if not tok:
    st.caption("احفظ توكن البوت اول.")
else:
    st.markdown(f"ابعت **/start** للبوت {get_setting('tg_bot_name', '')} (او اضفه لغروب وابعت اي رسالة)، "
                "بعدين اضغط الزر:")
    if st.button("🔎 التقط المحادثة اوتوماتيك"):
        try:
            found = detect_chat(tok)
            if found:
                set_setting("tg_chat_id", found[0])
                st.success(f"تم ربط: {found[1]}")
                st.rerun()
            else:
                st.warning("ما وصلتني رسائل. ابعت /start للبوت وجرب مرة ثانية.")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
    if chat:
        st.info(f"Chat ID الحالي: `{chat}`")
        if st.button("📨 ارسل رسالة تجريبية"):
            ok = send_message("✅ المنصة مربوطة بنجاح بتيليجرام")
            st.success("وصلت الرسالة") if ok else st.error("فشل الارسال")
