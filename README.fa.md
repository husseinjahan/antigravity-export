# ابزار خروجی‌گیر آنتی‌گرویتی (Antigravity Export - agexport)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

یک ابزار قدرتمند خط فرمان (CLI) و کتابخانه پایتون جهت اتصال مستقیم به **Language Server در حال اجرای Google Antigravity** (`language_server`)، بررسی وضعیت اتصال، و گرفتن خروجی از تمامی گفتگوها، تغییرات فایل‌ها، دیف‌ها (Git Patches) و زنجیره تفکر مدل (Thinking) در قالب فرمت‌های **Markdown**، **HTML تعاملی مستقل** و **JSON**. همچنین این ابزار دارای موتور **بازیابی اطلاعات پس از کرش (Crash Recovery)** است که گفتگوهای مفقود شده را از پایگاه‌داده‌های SQLite و لاگ‌های مغز سیستم بازگردانی می‌کند.

---

## 🌟 قابلیت‌ها و ویژگی‌های کلیدی

- 🛰️ **اتصال زنده به Language Server**: شناسایی خودکار پروسه‌های در حال اجرای Language Server، اسکن پورت‌های محلی، استخراج توکن امنیتی CSRF و برقراری ارتباط از طریق پروتکل gRPC-Web / HTTP Connect.
- 📋 **مشاهده لیست گفتگوها (Chat List)**: نمایش و فیلتر گفتگوها بر اساس پروژه، مسیر محیط کاری، تاریخ یا تعداد گام‌ها در محیط ترمینال با جداول زیبا و رنگی (Rich).
- 📁 **خروجی تفکیک‌شده بر اساس پروژه**: استخراج همه گفتگوها به تفکیک پوشه‌های هر پروژه یا گرفتن خروجی از یک پروژه یا شناسه گفتگوی خاص (Conversation ID).
- 📝 **خروجی مارک‌داون (`.md`)**: ایجاد فایل‌های استاندارد GitHub-Flavored Markdown همراه با متاداده، ورودی‌های کاربر، تگ‌های بازشونده `<details>` برای زنجیره تفکر هوش مصنوعی و نمایش دستورات خط فرمان.
- 🌐 **خروجی اچ‌تی‌ام‌ال تعاملی (`.html`)**: صفحات وب مستقل، واکنش‌گرا و زیبا با تم تاریک، هایلایت خط به خط تغییرات فایل (Unified Diffs)، آکاردئون‌های جمع‌شونده برای فرآیند تفکر، بدون نیاز به اینترنت و بدون وابستگی به CDN خارجی (۱۰۰٪ آفلاین).
- 📑 **فهرست جامع و داشبورد تعاملی (`index.html`)**: ساخت خودکار صفحه فهرست مطالب (Table of Contents) هنگام استخراج گفتگوها. شامل فیلد جستجوی زنده، دکمه‌های فیلتر بر اساس پروژه، کارت‌های آمار کلی (تعداد گفتگوها، پروژه‌ها، گام‌ها، سطرهای تغییر یافته) و لینک‌های دسترسی سریع به فایل‌های HTML, MD, JSON و Diff.
- 📊 **خروجی ساختاریافته جیسون (`.json`)**: ارائه ساختار کامل داده‌ای برای آرشیو، تحلیل، سنجش و بازخوانی در پایگاه‌های داده.
- 🔍 **خروجی اختصاصی تغییرات فایل و پچ‌های گیت (`.patch`)**: استخراج تمامی فایل‌های ساخته شده یا ویرایش شده همراه با دیف کامل گیت و تولید فایل استاندارد پچ قابل اعمال با `git apply`.
- 🛡️ **بازیابی گفتگوهای از دست رفته (Crash Recovery)**: اسکن لاگ‌های کرش (`~/.gemini/antigravity/crashes/`)، پایگاه‌داده‌های SQLite (`conversation_summaries.db`, `conversations/*.db`) و ترنسکریپت‌های لاگ سیستم (`transcript_full.jsonl`) جهت بازیابی کامل نشست‌های قطع‌شده یا ثبت‌نشده.
- ⚡ **امکان نصب سراسری به عنوان CLI**: قابل اجرا در سراسر سیستم با دستورات `agexport` و `antigravity-export` یا استفاده مستقیم به صورت پکیج در کدهای پایتون.

---

## 🚀 راهنمای نصب و راه‌اندازی

### روش اول: راه‌اندازی با محیط مجازی پایتون (`venv`)

```bash
# ۱. وارد پوشه پروژه شوید
cd /path/to/antigravity-export

# ۲. ایجاد و فعال‌سازی محیط مجازی
python -m venv venv

# در ویندوز (PowerShell):
.\venv\Scripts\Activate.ps1
# در مک یا لینوکس:
source venv/bin/activate

# ۳. نصب پکیج‌های پیش‌نیاز
pip install -r requirements.txt

# ۴. نصب پکیج در حالت توسعه (Editable)
pip install -e .
```

### روش دوم: نصب سراسری در کل سیستم (Global CLI)

برای استفاده از دستور `agexport` در هر مسیری از ترمینال:

```bash
# نصب با pip
pip install .

# یا با استفاده از pipx (پیشنهاد شده برای ابزارهای خط فرمان ایزوله)
pipx install .
```

---

## 💻 راهنمای دستورات خط فرمان (CLI Reference)

پس از نصب، ابزار با هر دو دستور `agexport` و `antigravity-export` در دسترس است.

### ۱. بررسی وضعیت اتصال به Language Server (`status` / `info`)
بررسی اینکه آیا پروسه سرور در حال اجراست، شناسه PID، پورت فعال، توکن CSRF و آمار گفتگوهای ذخیره‌شده:

```bash
agexport status
# یا
agexport info
```

*نمونه خروجی:*
```
Antigravity Language Server Status v1.0.0

┌───────────────────────────┬─────────────────────────────────────────────────┐
│ Connection State          │ CONNECTED                                       │
│ Process State             │ RUNNING                                         │
│ Process ID (PID)          │ 32808                                           │
│ Active Port               │ 63316                                           │
│ CSRF Token                │ f442deef-118...                                 │
│ IDE Name / Version        │ antigravity 2.26.0                              │
│ App Data Directory        │ C:\Users\user\.gemini\antigravity               │
│ Stored Conversations (DB) │ 6                                               │
│ Crash Dumps Detected      │ 4                                               │
└───────────────────────────┴─────────────────────────────────────────────────┘

[OK] Ready for export and real-time interaction (1 active endpoint(s))
```

---

### ۲. نمایش لیست گفتگوها (`list`)
نمایش جدول گفتگوهای فعال و ذخیره شده با متاداده، نام پروژه، تعداد گام‌ها و تعداد ویرایش‌های فایل:

```bash
# مشاهده آخرین گفتگوها
agexport list

# فیلتر کردن بر اساس نام یک پروژه مشخص
agexport list --project adswinger-ai

# نمایش گفتگوهای امروز
agexport list --today

# خروجی به صورت JSON (مناسب برای اسکریپت‌نویسی و پایپ به ابزارهای دیگر)
agexport list --json
```

---

### ۳. نمایش لیست پروژه‌ها (`projects`)
مشاهده خلاصه وضعیت پروژه‌ها، فضاهای کاری، تعداد گفتگوها و مجموع تغییرات فایل‌ها:

```bash
agexport projects
```

---

### ۴. گرفتن خروجی از گفتگوها (`export`)

گرفتن خروجی در فرمت‌های Markdown، HTML، JSON و تغییرات فایل:

```bash
# خروجی گرفتن از تمام گفتگوهای همه پروژه‌ها (تفکیک شده در پوشه هر پروژه)
agexport export --all-projects -o ./my_exports

# خروجی گرفتن از گفتگوهای یک پروژه خاص
agexport export -p adswinger-ai -o ./my_exports

# خروجی گرفتن از یک گفتگوی خاص با شناسه (Conversation ID)
agexport export --id c13776f9-5e3b-49e6-9532-3f19ab2a568a -o ./single_chat

# خروجی فقط با فرمت Markdown
agexport export -f md -o ./markdown_only

# خروجی فقط با فرمت HTML تعاملی
agexport export -f html -o ./html_only

# خروجی فقط با فرمت JSON
agexport export -f json -o ./json_only

# حذف بخش تفکر داخلی هوش مصنوعی (Thinking) برای خروجی‌های خلاصه‌تر
agexport export --no-thinking -o ./concise_exports

# خروجی به صورت آفلاین مستقیم از لاگ‌های محلی و SQLite (حتی در صورت خاموش بودن سرور)
agexport export --all-projects --offline -o ./offline_exports
```

---

### ۵. خروجی کامل و یکباره (`export-all`)
دستور میانبر جهت استخراج تمامی گفتگوها برای تمامی پروژه‌ها در کلیه فرمت‌ها (MD, HTML, JSON و Patches):

```bash
agexport export-all -o ./antigravity_export
```

---

### ۶. خروجی اختصاصی تغییرات فایل و پچ‌های گیت (`export-changes`)
استخراج تغییرات کد، دیف‌های یکپارچه و ساخت فایل‌های استاندارد `.patch`:

```bash
# استخراج کلیه تغییرات فایل‌ها در تمام پروژه‌ها
agexport export-changes -o ./patches

# استخراج تغییرات فایل‌های یک پروژه خاص
agexport export-changes -p antigravity-export -o ./patches
```

فایل‌های تولید شده در این حالت:
- `<Title>_<ID>_file_changes.md`: گزارش زمانی تغییرات به همراه دیف‌ها.
- `<Title>_<ID>.patch`: فایل پچ استاندارد گیت قابل اعمال با `git apply`.
- `<Project>_project_file_changes.md`: خلاصه تغییرات فایل‌ها در سطح کل پروژه.

---

### ۷. بازیابی گفتگوهای از دست رفته پس از کرش/به‌روزرسانی (`recover`)
اسکن خودکار لاگ‌های کرش (`~/.gemini/antigravity/crashes/`)، پایگاه‌های داده SQLite و لاگ‌های ترنسکریپت برای احیای نشست‌های مفقود شده:

```bash
# ۱. پیش‌نمایش گفتگوهای قابل بازیابی بدون نوشتن فایل (Dry Run)
agexport recover --dry-run

# ۲. بازیابی گفتگوهای ثبت‌نشده یا قطع‌شده
agexport recover -o ./recovered_chats

# ۳. اجبار به بازیابی آفلاین تمام نشست‌های موجود روی دیسک
agexport recover --all --force-offline -o ./full_recovery
```

---

## 🐍 استفاده به عنوان کتابخانه در کدهای پایتون

شما می‌توانید ماژول‌های این پروژه را مستقیماً در کدهای پایتون خود استفاده کنید:

```python
from pathlib import Path
from antigravity_export import (
    LanguageServerManager,
    LanguageServerClient,
    ConversationRecovery,
)
from antigravity_export.exporters import HTMLExporter, MarkdownExporter, JSONExporter

# ۱. بررسی وضعیت سرور
mgr = LanguageServerManager()
status = mgr.get_status()
print(f"Server Running: {status.is_running}, Port: {status.port}")

# ۲. دریافت گفتگوها از طریق کلاینت
endpoints = mgr.find_all_endpoints()
client = LanguageServerClient()
summaries, _, _ = client.get_all_trajectories_merged(endpoints)

# ۳. بازیابی گفتگوی کرش شده
recovery = ConversationRecovery()
conversation = recovery.recover_conversation("c13776f9-5e3b-49e6-9532-3f19ab2a568a")

if conversation:
    print(f"گفتگو: {conversation.title} | تعداد تغییرات فایل: {len(conversation.file_changes)}")
    
    # تولید خروجی HTML
    html_exporter = HTMLExporter(include_thinking=True)
    html_exporter.save(conversation, output_dir=Path("./exports"))
```

---

## 📁 ساختار پوشه‌بندی پروژه

```
antigravity-export/
├── src/
│   └── antigravity_export/
│       ├── __init__.py           # شناسه پکیج و متاداده نگارش
│       ├── __main__.py           # اجرای مستقیم با python -m antigravity_export
│       ├── cli.py                # پیاده‌سازی خط فرمان با Typer و Rich
│       ├── config.py             # مسیرهای سیستمی و تنظیمات پیش‌فرض
│       ├── connection.py         # اسکن پروسه‌ها، پورت‌ها و تست سلامت اتصال
│       ├── api_client.py         # کلاینت ارتباط با پروتکل gRPC-Web / Connect
│       ├── models.py             # مدل‌های داده‌ای Conversation, Message, FileChange
│       ├── parser.py             # پردازشگر گام‌ها و تولید دیف‌های یکپارچه
│       ├── storage.py            # خواندن مستقیم داده‌ها از SQLite و لاگ‌های مغز
│       ├── recovery.py           # موتور بازیابی گفتگوهای مفقود و لاگ‌های کرش
│       └── exporters/
│           ├── __init__.py
│           ├── markdown_exporter.py    # خروجی مارک‌داون
│           ├── html_exporter.py        # خروجی اچ‌تی‌ام‌ال تعاملی مستقل
│           ├── json_exporter.py        # خروجی جیسون ساختاریافته
│           └── file_changes_exporter.py# خروجی تغییرات کد و پچ‌های گیت
├── tests/                        # تست‌های خودکار واحد با Pytest
│   ├── test_models.py
│   ├── test_parser.py
│   ├── test_exporters.py
│   └── test_recovery.py
├── pyproject.toml                # تنظیمات مدرن بیلد پایتون (PEP 621)
├── setup.py                      # اسکریپت سنتی ستاپ جهت سازگاری
├── requirements.txt              # وابستگی‌های مورد نیاز
├── README.md                     # مستندات انگلیسی
└── README.fa.md                  # مستندات فارسی
```

---

## 🧪 اجرای تست‌های واحد

جهت اجرای آزمون‌های خودکار سیستم:

```bash
pytest
```

---

## 📄 لایسنس

این پروژه تحت لایسنس **MIT** منتشر شده است.
