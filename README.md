# 🌐 XForwarder

<p align="center">
  <strong>موتور هوشمند اولویت‌بندی، رله بدون تونل و فیل‌اور خودکار چندمسیره روی سرورهای واسط لینوکس</strong>
  <br>
  <em>Intelligent Multi-Path Priority Failover Engine & 24/7 Web Dashboard for Linux Relay Servers</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Python-3.8%2B%20Native-blue.svg" alt="Python 3 Native">
  <img src="https://img.shields.io/badge/RAM-%3C15MB-brightgreen.svg" alt="RAM Usage">
  <img src="https://img.shields.io/badge/OS-Debian%20%7C%20Ubuntu-orange.svg" alt="OS Compatibility">
  <img src="https://img.shields.io/badge/Forwarding-HAProxy%20%7C%20NFTables%20DNAT%20%7C%20Nginx-purple.svg" alt="Forwarding Engine">
  <img src="https://img.shields.io/badge/Version-1.4.0-success.svg" alt="Version">
</p>

---

## ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install)

برای نصب سریع و کامل **XForwarder** روی سرور لینوکس (ایران)، کافیست دستور تک‌خطی زیر را با دسترسی `root` در ترمینال اجرا کنید:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/PouryaDe/XForwarder/main/xforwarder.sh)
```

یا برای اجرای مستقیم فرآیند نصب بدون باز شدن منو:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/PouryaDe/XForwarder/main/xforwarder.sh) install
```

> [!TIP]
> **مراحل ویزارد نصب:**  
> اسکریپت به‌صورت خودکار کارت شبکه اصلی (`WAN`)، پکیج‌های مورد نیاز (`haproxy`, `nftables`, `nginx`, `python3`) و فورواردینگ کرنل (`net.ipv4.ip_forward = 1`) را آماده کرده و موارد زیر را از شما می‌پرسد:
> 1. پورت پنل وب (پیش‌فرض: `8090`)
> 2. نام کاربری ادمین (پیش‌فرض: `admin`)
> 3. رمز عبور ورود به پنل وب
> 4. مسیر امنیتی اختصاصی پنل / Security Path (پیش‌فرض: `xfwd-admin`)

---

## 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update)

برای آپدیت به آخرین نسخه با حفظ ۱۰۰٪ قوانین فورواردینگ، اطلاعات احراز هویت و انجام خودکار مایگریشن کانفیگ:

### روش اول — از طریق ترمینال سرور:
```bash
sudo xforwarder update
# یا نام کوتاه:
sudo xfwd update
```

### روش دوم — با دستور تک‌خطی از گیت‌هاب:
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/PouryaDe/XForwarder/main/xforwarder.sh) update
```

> [!NOTE]
> در هر فرآیند آپدیت، نسخه پشتیبان از کانفیگ با برچسب زمانی (`config.json.bak.<timestamp>`) تهیه شده و سرویس‌ها بدون کوچک‌ترین قطعی در اتصالات کاربران بروز می‌شوند.

---

## 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture)

**XForwarder** برای سرورهای واسط لینوکس (مانند سرور ایران) طراحی شده است تا ترافیک کاربران را با بیشترین پایداری و کمترین تاخیر به سرورهای خارج هدایت کند.

```text
                               ترافیک ورودی کاربران (Client Traffic)
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │       سرور واسط لینوکس (Iran VPS)      │
                             │                                       │
                             │   ┌───────────────────────────────┐   │
                             │   │  Core Failover Daemon (<15MB) │   │
                             │   │  - Socket Health Prober       │   │
                             │   │  - Zero-Collision Syncer      │   │
                             │   └───────────────┬───────────────┘   │
                             └───────────────────┼───────────────────┘
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        │                                                 │
                        ▼                                                 ▼
        [ اولویت ۱ - مسیر مستقیم / HAProxy ]             [ اولویت ۲ - تونل لایه ۳ / NFTables ]
        • رله مستقیم IPv4 به IPv6 بدون تونل              • فورواردینگ کرنل (Kernel DNAT)
        • پروکسی لایه ۴ کاربر (TCP/UDP)                 • تونل‌های GRE, IPIP, FakeTCP, AmneziaWG
        • پینگ حداقل و حداکثر پهنای باند                 • فعال‌سازی فوری در زمان قطعی اولویت ۱
```

### قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):
یک پورت **هرگز** نباید هم‌زمان توسط HAProxy و NFTables فوروارد شود:
- هنگامی که **Priority 1 (HAProxy)** فعال و پایدار است، فقط HAProxy روی پورت گوش می‌دهد و رول‌های NFTables حذف می‌شوند.
- در صورت بروز اختلال در مسیر اصلی، سرویس بلافاصله HAProxy را از روی پورت آزاد کرده و رول لایه ۳ در جدول ایزوله `table ip xfwd_orchestrator` در NFTables ترافیک را به تونل پشتیبان هدایت می‌کند.
- پس از بازگشت پایداری مسیر اصلی، ترافیک بدون نیاز به دخالت دست خودکار به اولویت ۱ بازمی‌گردد (**Failback**).

---

## 🚀 ۴. ویژگی‌های کلیدی (Key Features)

- **سبک و فوق‌العاده کم‌مصرف:** نوشته‌شده کاملاً با کتابخانه‌های استاندارد پایتون ۳ (بدون نیاز به کتابخانه‌های سنگین خارجی، نودجی‌اس یا داکر). مصرف رم کل سیستم کمتر از **۱۵ مگابایت**.
- **داشبورد وب ۲۴/۷ پایدار:** کنترل‌پنل مدرن به زبان انگلیسی با طراحی تاریک (Glassmorphism)، احراز هویت امن بر پایه توکن، و اجرا به عنوان سرویس مستقل در Systemd.
- **تغییر اولویت با Drag & Drop:** قابلیت تغییر ترتیب اولویت مسیرها مستقیماً از روی کارت‌های پورت با کشیدن و رها کردن (Drag and Drop) و ذخیره‌سازی خودکار.
- **پایش لحظه‌ای موتورهای رله (Relay Engines Health Bar):** نوار وضعیت زنده سلامت و در دسترس بودن NFTables (کرنل)، HAProxy و Nginx به همراه اعلام هشدار پکیج‌های مفقود.
- **تغییر حالت هوشمند (Per-Port Mode Selector):**
  - `Auto Failover`: پایش ۲۴ ساعته پینگ و سوئیچ خودکار بر اساس سلامت سرور مقصد.
  - `Force: Priority 1`: قفل ترافیک روی مسیر اول (HAProxy).
  - `Force: Priority 2`: قفل ترافیک روی مسیر دوم (NFTables Tunnel).
- **فایروال کاملاً ایزوله:** تمامی رول‌های کرنل در جدول مستقل `table ip xfwd_orchestrator` قرار دارند و هرگز به فایروال اصلی لینوکس یا سرویس‌هایی مانند UFW دست نمی‌زنند.
- **پشتیبانی از انواع تونل‌ها:** سازگار با FakeTCP/Phantun، AmneziaWG، WireGuard، GRE، IPIP، FOU، VXLAN و XDP.

---

## 🛠 ۵. دستورات خط فرمان (CLI Commands)

پس از نصب، دستور سراسری `xforwarder` و نام کوتاه `xfwd` در دسترس شماست:

| دستور | دستور کوتاه | عملکرد |
| :--- | :--- | :--- |
| `sudo xforwarder` | `sudo xfwd` | باز کردن منوی تعاملی مدیریتی |
| `sudo xforwarder url` | `sudo xfwd url` | نمایش آدرس ورود کامل به همراه مسیر امنیتی و اطلاعات دسترسی |
| `sudo xforwarder status` | `sudo xfwd status` | نمایش جدول زنده وضعیت پورت‌ها، تاخیر (Latency)، سرویس‌های رله و اولویت فعال |
| `sudo xforwarder check-deps` | `sudo xfwd deps` | بررسی و نصب خودکار پکیج‌های رله (NFTables, HAProxy, Nginx) |
| `sudo xforwarder settings` | `sudo xfwd settings` | منوی جامع تنظیمات وب (پورت، یوزرنیم، پسورد و مسیر امنیتی) |
| `sudo xforwarder port` | `sudo xfwd port` | تغییر سریع پورت پنل وب |
| `sudo xforwarder username` | `sudo xfwd username` | تغییر سریع نام‌کاربری ادمین |
| `sudo xforwarder password` | `sudo xfwd password` | تغییر سریع رمز عبور ادمین |
| `sudo xforwarder path` | `sudo xfwd path` | تغییر سریع مسیر امنیتی (Security Secret Slug) |
| `sudo xforwarder restart` | `sudo xfwd restart` | راه‌اندازی مجدد سرویس هسته و سرویس وب |
| `sudo xforwarder logs` | `sudo xfwd logs` | مشاهده لاگ لحظه‌ای پایش سلامت و تصمیمات سوئیچینگ |
| `sudo xforwarder update` | `sudo xfwd update` | دریافت آخرین آپدیت با حفظ قوانین و مایگریشن خودکار |

> [!NOTE]
> برای سازگاری با اسکریپت‌های گذشته، دستورات قدیمی `forward-manager` و `fwdman` نیز همچنان معتبر هستند.

---

## 🖥 ۶. راهنمای استفاده از داشبورد وب (Web UI Guide)

1. در مرورگر آدرس سرور را به همراه پورت و مسیر امنیتی وارد کنید:  
   `http://YOUR_SERVER_IP:8090/xfwd-admin/`
2. نام کاربری و رمز عبور تعیین‌شده در مرحله نصب را وارد کنید.
3. **تعریف قانون پورت جدید (Add Forwarding Rule):**
   - **Port:** شماره پورت ورودی (مثلاً `443` یا `2083`).
   - **Protocol:** نوع پروتکل (`TCP`, `UDP`, یا `TCP + UDP`).
   - **Priority 1 (Primary):** انتخاب نوع `HAProxy` و وارد کردن آدرس سرور مقصد (مثلاً آی‌پی IPv6 خارج).
   - **Priority 2 (Failover Tunnel):** انتخاب نوع `NFTables` و وارد کردن آی‌پی تونل مقصد (مثلاً `10.88.1.2`).
   - **Mode:** حالت `Auto Failover` برای سوئیچ خودکار هوشمند.
4. با زدن دکمه ذخیره، رول‌ها بلافاصله بدون قطعی در هسته اعمال و فعال می‌شوند.

---

## 📋 ۷. پیش‌نیازهای سیستمی (Prerequisites)

- **سیستم‌عامل:** Ubuntu 20.04 / 22.04 / 24.04 یا Debian 11 / 12
- **دسترسی:** کاربر ریشه (`root` یا دسترسی `sudo`)
- **حداقل سخت‌افزار:** ۱ هسته پردازنده، ۵۱۲ مگابایت رم (کل مصرف هسته کمتر از ۱۵ مگابایت است)

---

## 📦 ۸. نصب دستی از طریق گیت (Manual Installation)

در صورت تمایل به کلون کردن سورس‌کد:

```bash
git clone https://github.com/PouryaDe/XForwarder.git
cd XForwarder
chmod +x xforwarder.sh
sudo ./xforwarder.sh install
```

---

## 📄 لایسنس (License)

این پروژه تحت لایسنس **MIT** منتشر شده است و استفاده از آن برای عموم آزاد و رایگان می‌باشد.
