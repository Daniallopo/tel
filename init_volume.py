import os
import json
import shutil

# فقط اولین بار که Volume خالیه اجرا میشه
if os.environ.get("RAILWAY_VOLUME_INIT") and os.path.getsize("data.json") < 100:
    print("Volume خالی بود – فایل‌های جدید کپی میشن...")
    for file in ["data.json", "pending.json", "users.txt"]:
        if os.path.exists(f"/app/{file}"):
            shutil.copy(f"/app/{file}", "file")  # از Volume به پوشه اصلی
    print("فایل‌ها با موفقیت به Volume منتقل شدن")
