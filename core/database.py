"""
core/database.py
----------------
قاعدة Postgres (Supabase) وكل الجداول + دوال القراءة والكتابة.
الجداول: users, settings, accounts, insights, alerts
ملاحظة امان: بنفعّل Row Level Security على كل الجداول عشان ما حدا يوصلها
من خلال Supabase REST API (الاتصال تبعنا مباشر وبتجاوز RLS).
"""
import json
from contextlib import contextmanager

import pandas as pd
import psycopg2
import psycopg2.extras

from .config import secret, DEFAULT_RULES, DEFAULT_CONV_TYPES
from .security import encrypt, decrypt, hash_password


class MissingDatabaseUrl(RuntimeError):
    pass


@contextmanager
def conn():
    url = secret("DATABASE_URL")
    if not url:
        raise MissingDatabaseUrl("DATABASE_URL")
    con = psycopg2.connect(url, connect_timeout=15, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def execute(sql: str, params=None) -> int:
    with conn() as con, con.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def fetchall(sql: str, params=None) -> list[dict]:
    with conn() as con, con.cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def fetchone(sql: str, params=None):
    with conn() as con, con.cursor() as cur:
        cur.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r else None


def query_df(sql: str, params=None) -> pd.DataFrame:
    return pd.DataFrame(fetchall(sql, params))


_TABLES = ["users", "settings", "accounts", "insights", "alerts"]


def init_db() -> None:
    with conn() as con, con.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            account_id TEXT UNIQUE NOT NULL,
            name TEXT,
            currency TEXT,
            token_enc TEXT,
            active BOOLEAN DEFAULT TRUE,
            last_sync TIMESTAMPTZ,
            last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS insights (
            date DATE, account_id TEXT, campaign_id TEXT, campaign_name TEXT,
            spend DOUBLE PRECISION, impressions BIGINT, clicks BIGINT,
            ctr DOUBLE PRECISION, cpc DOUBLE PRECISION, cpm DOUBLE PRECISION,
            frequency DOUBLE PRECISION, conversions DOUBLE PRECISION,
            PRIMARY KEY (date, campaign_id)
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            date DATE, account_id TEXT, campaign_id TEXT, campaign_name TEXT,
            rule TEXT, severity TEXT, message TEXT, sent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (date, campaign_id, rule)
        );
        """)
        for t in _TABLES:
            cur.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")


# ---------- users ----------
def users_count() -> int:
    return fetchone("SELECT COUNT(*) AS n FROM users")["n"]


def create_user(username: str, password: str) -> None:
    execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username.strip().lower(), hash_password(password)))


def get_user(username: str):
    return fetchone("SELECT * FROM users WHERE username=%s", (username.strip().lower(),))


# ---------- settings ----------
def get_setting(key: str, default=None):
    row = fetchone("SELECT value FROM settings WHERE key=%s", (key,))
    return row["value"] if row else default


def set_setting(key: str, value) -> None:
    execute("INSERT INTO settings (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, str(value)))


def get_secret(key: str):
    v = get_setting(key)
    return decrypt(v) if v else None


def set_secret(key: str, value: str) -> None:
    set_setting(key, encrypt(value))


def get_rules() -> dict:
    raw = get_setting("rules")
    rules = dict(DEFAULT_RULES)
    if raw:
        rules.update(json.loads(raw))
    return rules


def save_rules(rules: dict) -> None:
    set_setting("rules", json.dumps(rules))


def get_conv_types() -> set:
    raw = get_setting("conv_types", DEFAULT_CONV_TYPES)
    return {t.strip() for t in raw.split(",") if t.strip()}


# ---------- accounts ----------
def upsert_account(account_id: str, name: str, currency: str, token: str | None = None) -> None:
    account_id = account_id.replace("act_", "").strip()
    execute("""
        INSERT INTO accounts (account_id, name, currency, token_enc)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (account_id) DO UPDATE SET
            name=EXCLUDED.name, currency=EXCLUDED.currency,
            token_enc=COALESCE(EXCLUDED.token_enc, accounts.token_enc)
    """, (account_id, name, currency, encrypt(token) if token else None))


def list_accounts(active_only: bool = False) -> list[dict]:
    return fetchall("SELECT * FROM accounts" + (" WHERE active" if active_only else "") + " ORDER BY name")


def set_account_active(account_id: str, active: bool) -> None:
    execute("UPDATE accounts SET active=%s WHERE account_id=%s", (active, account_id))


def delete_account(account_id: str) -> None:
    with conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM accounts WHERE account_id=%s", (account_id,))
        cur.execute("DELETE FROM insights WHERE account_id=%s", (account_id,))
        cur.execute("DELETE FROM alerts WHERE account_id=%s", (account_id,))


def mark_sync(account_id: str, error: str | None) -> None:
    execute("UPDATE accounts SET last_sync=NOW(), last_error=%s WHERE account_id=%s", (error, account_id))


def account_token(row) -> str | None:
    """توكن الحساب لو موجود، غير هيك التوكن العام."""
    if row["token_enc"]:
        return decrypt(row["token_enc"])
    return get_secret("meta_token")


# ---------- insights / alerts ----------
def save_insights(rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in ("date", "campaign_id"))
    sql = (f"INSERT INTO insights ({', '.join(cols)}) VALUES %s "
           f"ON CONFLICT (date, campaign_id) DO UPDATE SET {updates}")
    with conn() as con, con.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, [tuple(r[c] for c in cols) for r in rows])


def mark_alerts_sent(ids: list[int]) -> None:
    if ids:
        execute("UPDATE alerts SET sent=TRUE WHERE id = ANY(%s)", (ids,))
