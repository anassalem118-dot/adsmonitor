"""
core/analysis.py
----------------
قواعد التنبيه. بتقارن امس مع معدل اخر 7 ايام لكل حملة.
الحدود (thresholds) بتنقرا من صفحة الاعدادات.
"""
from datetime import date, timedelta
from .database import conn, query_df, get_rules


def analyze(target: date) -> list[dict]:
    rules = get_rules()
    df = query_df("SELECT * FROM insights WHERE date BETWEEN %s AND %s",
                  (target - timedelta(days=7), target))
    if df.empty:
        return []

    alerts: list[dict] = []
    for cid, g in df.groupby("campaign_id"):
        today = g[g["date"] == target]
        if today.empty:
            continue
        t = today.iloc[0]
        base = g[(g["date"] < target) & (g["spend"] > 0)]

        def add(rule, severity, msg):
            alerts.append({"date": target, "account_id": t["account_id"], "campaign_id": cid,
                           "campaign_name": t["campaign_name"], "rule": rule,
                           "severity": severity, "message": msg})

        if t["impressions"] >= rules["min_impressions"] and t["ctr"] < rules["min_ctr"]:
            add("low_ctr", "warning", f"CTR {t['ctr']:.2f}% اقل من {rules['min_ctr']}%")

        if t["frequency"] > rules["max_frequency"]:
            add("high_frequency", "warning", f"التكرار {t['frequency']:.1f} (الحد {rules['max_frequency']})")

        if t["spend"] >= rules["no_conv_spend"] and t["conversions"] == 0:
            add("no_conversions", "critical", f"صرف {t['spend']:.2f} بدون اي نتيجة")

        if not base.empty:
            b_conv = base["conversions"].sum()
            if t["conversions"] > 0 and b_conv > 0:
                base_cpa, cpa = base["spend"].sum() / b_conv, t["spend"] / t["conversions"]
                if cpa > base_cpa * (1 + rules["cpa_spike"]):
                    add("cpa_spike", "critical", f"تكلفة النتيجة {cpa:.2f} مقابل معدل {base_cpa:.2f}")

            b_clicks = base["clicks"].sum()
            if t["clicks"] > 0 and b_clicks > 0:
                base_cpc, cpc = base["spend"].sum() / b_clicks, t["spend"] / t["clicks"]
                if cpc > base_cpc * (1 + rules["cpc_spike"]):
                    add("cpc_spike", "warning", f"تكلفة النقرة {cpc:.2f} مقابل معدل {base_cpc:.2f}")

            avg_spend = base["spend"].mean()
            if avg_spend > 0 and t["spend"] > avg_spend * rules["spend_spike_x"]:
                add("spend_spike", "warning", f"الصرف {t['spend']:.2f} مقابل معدل {avg_spend:.2f}")
    return alerts


def store_new_alerts(alerts: list[dict]) -> list[dict]:
    """بيحفظ التنبيهات وبيرجع الجديدة بس (بدون تكرار)."""
    new = []
    with conn() as con, con.cursor() as cur:
        for a in alerts:
            cur.execute(
                "INSERT INTO alerts (date, account_id, campaign_id, campaign_name, rule, severity, message) "
                "VALUES (%(date)s, %(account_id)s, %(campaign_id)s, %(campaign_name)s, %(rule)s, "
                "%(severity)s, %(message)s) ON CONFLICT (date, campaign_id, rule) DO NOTHING RETURNING id", a)
            row = cur.fetchone()
            if row:
                a["id"] = row["id"]
                new.append(a)
    return new
