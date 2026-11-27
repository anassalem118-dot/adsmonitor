"""
core/boot.py
------------
كل صفحة بتنادي require_login() اول شي. هاي بتعمل:
  1) تتأكد ان DATABASE_URL و SECRET_KEY موجودين (وبتساعدك تولّد المفتاح)
  2) تجهّز الجداول مرة وحدة
  3) شاشة انشاء المدير (اول مرة) وشاشة تسجيل الدخول
"""
import streamlit as st

from .config import secret
from .security import check_password, new_key


@st.cache_resource(show_spinner=False)
def _init_once() -> bool:
    from .database import init_db
    init_db()
    return True


def _check_secrets() -> None:
    if not secret("DATABASE_URL"):
        st.title("⚙️ خطوة اعداد واحدة ناقصة")
        st.error("ما لقيت DATABASE_URL")
        st.markdown("حطه في **Streamlit Cloud ← App settings ← Secrets** بهالشكل:")
        st.code('DATABASE_URL = "postgresql://postgres.xxxx:PASSWORD@aws-0-xx.pooler.supabase.com:5432/postgres"',
                language="toml")
        st.caption("لازم رابط **Session pooler** من Supabase (مش Direct connection). التفاصيل في README.")
        st.stop()
    if not secret("SECRET_KEY"):
        st.title("⚙️ خطوة اعداد واحدة ناقصة")
        st.error("ما لقيت SECRET_KEY (مفتاح تشفير التوكنات)")
        if "gen_key" not in st.session_state:
            st.session_state["gen_key"] = new_key()
        st.markdown("انسخ هالسطر وحطه في **Secrets** (وبنفس القيمة بالضبط في GitHub Secrets):")
        st.code(f'SECRET_KEY = "{st.session_state["gen_key"]}"', language="toml")
        st.warning("احفظ المفتاح بمكان امين. اذا ضاع بتضطر تلصق التوكنات من جديد.")
        st.stop()


def require_login() -> None:
    _check_secrets()
    try:
        _init_once()
    except Exception as e:  # noqa: BLE001
        st.error(f"ما قدرت اتصل بقاعدة البيانات: {e}")
        st.caption("تأكد انك استخدمت رابط Session pooler وان كلمة المرور صح.")
        st.stop()

    from .database import users_count, create_user, get_user

    if st.session_state.get("user"):
        st.markdown("<style>.block-container{direction:rtl;text-align:right}</style>",
                    unsafe_allow_html=True)
        with st.sidebar:
            st.caption(f"👤 {st.session_state['user']}")
            if st.button("تسجيل خروج", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        return

    st.title("📊 منصة مراقبة اعلانات ميتا")

    # اول مرة: انشاء حساب المدير
    if users_count() == 0:
        st.info("اهلا! هاي اول مرة. انشئ حساب المدير.")
        with st.form("setup"):
            u = st.text_input("اسم المستخدم")
            p1 = st.text_input("كلمة المرور (8 احرف على الاقل)", type="password")
            p2 = st.text_input("تأكيد كلمة المرور", type="password")
            if st.form_submit_button("انشاء الحساب"):
                if not u.strip() or len(p1) < 8:
                    st.error("اسم مستخدم مطلوب وكلمة مرور 8 احرف على الاقل")
                elif p1 != p2:
                    st.error("كلمتا المرور مختلفتان")
                else:
                    create_user(u, p1)
                    st.session_state["user"] = u.strip().lower()
                    st.rerun()
        st.stop()

    with st.form("login"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول"):
            row = get_user(u)
            if row and check_password(p, row["password_hash"]):
                st.session_state["user"] = row["username"]
                st.rerun()
            else:
                st.error("بيانات الدخول غلط")
    st.stop()
