"""
core/jobs.py
------------
المهمة اليومية: جلب ← تحليل ← تنبيه.
بتنادى من:  run_daily.py (GitHub Actions)  ومن زر «جلب الآن» في اللوحة.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import DEFAULT_TZ
from .database import (list_accounts, account_token, get_conv_types, get_setting, set_setting,
                       mark_sync, save_insights, mark_alerts_sent)
from .meta_api import fetch_insights
from .analysis import analyze, store_new_alerts
from .telegram_service import notify_alerts, send_message

log = logging.getLogger("ads_monitor")


def local_now() -> datetime:
    return datetime.now(ZoneInfo(get_setting("timezone", DEFAULT_TZ)))


def yesterday():
    return local_now().date() - timedelta(days=1)


def sync_accounts(days: int = 2) -> dict:
    """بيجيب البيانات لكل الحسابات الفعالة. بيرجع {rows, errors}."""
    target = yesterday()
    since = target - timedelta(days=days - 1)
    conv = get_conv_types()
    rows_total, errors = 0, []
    for acc in list_accounts(active_only=True):
        token = account_token(acc)
        if not token:
            mark_sync(acc["account_id"], "ما في توكن")
            errors.append(f"{acc['name']}: ما في توكن")
            continue
        try:
            rows = fetch_insights(token, acc["account_id"], since, target, conv)
            save_insights(rows)
            rows_total += len(rows)
            mark_sync(acc["account_id"], None)
        except Exception as e:  # noqa: BLE001
            mark_sync(acc["account_id"], str(e))
            errors.append(f"{acc['name']}: {e}")
    return {"rows": rows_total, "errors": errors}


def run_job(days: int = 2, alert: bool = True) -> dict:
    target = yesterday()
    res = sync_accounts(days)
    new_alerts = []
    if alert:
        new_alerts = store_new_alerts(analyze(target))
        if notify_alerts(new_alerts, target):
            mark_alerts_sent([a["id"] for a in new_alerts])
    # رسالة الخطأ مرة وحدة باليوم (عشان ما نزعجك كل ساعة)
    today = str(local_now().date())
    if res["errors"] and get_setting("last_error_notice") != today:
        if send_message("⚠️ <b>مشكلة في جلب البيانات</b>\n" + "\n".join(res["errors"][:5])):
            set_setting("last_error_notice", today)
    res["alerts"] = len(new_alerts)
    log.info("job done: %s", res)
    return res
