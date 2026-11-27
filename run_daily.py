"""
run_daily.py  —  المهمة اليومية (بتشتغل على GitHub Actions، مش على اللوحة)
-------------------------------------------------------------------------
GitHub بيشغّلها كل ساعة، وهي بتقرر لحالها:
  - اذا الساعة المحلية >= «ساعة التشغيل» من الاعدادات، ولسا ما اشتغلت اليوم → بتشتغل.
  - غير هيك بتطلع بصمت.
اذا فشل الجلب بتعيد المحاولة بالساعة اللي بعدها، والخطأ بينبعت لتيليجرام مرة باليوم.

خيارات:
  python run_daily.py            # التشغيل العادي (مع الشرط)
  python run_daily.py --force    # شغّل الآن بغض النظر عن الساعة
  python run_daily.py --backfill 30   # حمّل اخر 30 يوم بدون تنبيهات
"""
import argparse
import logging
import sys

from core.database import init_db, get_setting, set_setting
from core.jobs import run_job, local_now

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--backfill", type=int, metavar="DAYS")
    args = ap.parse_args()

    init_db()

    if args.backfill:
        print(run_job(days=args.backfill, alert=False))
        return 0

    now = local_now()
    today = str(now.date())
    if not args.force:
        hour = int(get_setting("alert_hour", 8))
        if now.hour < hour:
            print(f"بدري: الساعة {now:%H:%M}، التشغيل بعد {hour:02d}:00")
            return 0
        if get_setting("last_run_date") == today:
            print("اشتغلت اليوم من قبل")
            return 0

    res = run_job()
    print(res)
    if not res["errors"]:
        set_setting("last_run_date", today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
