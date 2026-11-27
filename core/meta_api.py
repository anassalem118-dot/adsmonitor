"""
core/meta_api.py
----------------
كل الكلام مع Meta Graph API:
  - check_token()        : يتأكد التوكن شغال
  - discover_accounts()  : يجيب كل الحسابات الاعلانية المربوطة بالتوكن (اضافة اوتوماتيكية)
  - fetch_insights()     : يجيب ارقام الحملات اليومية
"""
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import META_API_VERSION

BASE = f"https://graph.facebook.com/{META_API_VERSION}"


class MetaError(RuntimeError):
    pass


def _session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))))
    return s


def _get(url: str, params: dict | None = None) -> dict:
    r = _session().get(url, params=params, timeout=60)
    try:
        data = r.json()
    except ValueError:
        raise MetaError(f"رد غير مفهوم من Meta ({r.status_code})")
    if r.status_code != 200 or "error" in data:
        raise MetaError(data.get("error", {}).get("message", r.text))
    return data


def check_token(token: str) -> str:
    """بيرجع اسم صاحب التوكن لو شغال، وبيرمي MetaError لو لا."""
    return _get(f"{BASE}/me", {"fields": "name", "access_token": token}).get("name", "OK")


def discover_accounts(token: str) -> list[dict]:
    """كل الحسابات الاعلانية اللي التوكن يوصلها."""
    out, url = [], f"{BASE}/me/adaccounts"
    params = {"fields": "account_id,name,currency,account_status", "limit": 100, "access_token": token}
    while url:
        data = _get(url, params)
        for a in data.get("data", []):
            out.append({
                "account_id": a["account_id"],
                "name": a.get("name") or a["account_id"],
                "currency": a.get("currency", ""),
                "status": a.get("account_status"),
            })
        url, params = data.get("paging", {}).get("next"), None
    return out


def _count_conversions(actions, conv_types: set) -> float:
    if not actions:
        return 0.0
    return sum(float(a.get("value", 0)) for a in actions if a.get("action_type") in conv_types)


def fetch_insights(token: str, account_id: str, since, until, conv_types: set) -> list[dict]:
    url = f"{BASE}/act_{account_id}/insights"
    params = {
        "level": "campaign",
        "time_increment": 1,
        "time_range": json.dumps({"since": str(since), "until": str(until)}),
        "fields": "campaign_id,campaign_name,spend,impressions,clicks,ctr,cpc,cpm,frequency,actions",
        "limit": 200,
        "access_token": token,
    }
    rows = []
    while url:
        data = _get(url, params)
        for r in data.get("data", []):
            rows.append({
                "date": r["date_start"], "account_id": account_id,
                "campaign_id": r["campaign_id"], "campaign_name": r.get("campaign_name", ""),
                "spend": float(r.get("spend", 0)), "impressions": int(r.get("impressions", 0)),
                "clicks": int(r.get("clicks", 0)), "ctr": float(r.get("ctr", 0)),
                "cpc": float(r.get("cpc", 0)), "cpm": float(r.get("cpm", 0)),
                "frequency": float(r.get("frequency", 0)),
                "conversions": _count_conversions(r.get("actions"), conv_types),
            })
        url, params = data.get("paging", {}).get("next"), None
    return rows
