# 📡 مستندات جامع REST API در XForwarder

مستندات کامل وب‌سرویس **XForwarder** برای یکپارچه‌سازی با اسکریپت‌ها، ربات‌ها، پنل‌های مدیریت، سیستم‌های فروش و مانیتورینگ.

> [!NOTE]
> **قرارداد آدرس‌های فرضی در تمام مثال‌های این مستند:**  
> تمامی آدرس‌های شبکه در این سند کاملاً فرضی (مطابق استانداردهای RFC 5737 / RFC 3849) هستند:
> - آی‌پی فرضی سرور واسط (ایران): `203.0.113.10`
> - آی‌پی‌های فرضی سرورهای مقصد (خارج - IPv4): `198.51.100.20`، `198.51.100.21`، `192.0.2.50`
> - آی‌پی‌های فرضی سرورهای مقصد (خارج - IPv6): `2001:db8:1::10`، `2001:db8:2::20`
> - آی‌پی‌های فرضی داخل تونل (L3): `10.200.1.2`، `10.200.1.3`، `10.200.2.2`
> - دامنه فرضی: `exit1.example.net`

---

## فهرست مطالب
1. [آدرس پایه و نسخه‌بندی مسیرها](#1-آدرس-پایه-و-نسخه‌بندی-مسیرها)
2. [احراز هویت و سطوح دسترسی (Scopes)](#2-احراز-هویت-و-سطوح-دسترسی-scopes)
3. [مدیریت کلیدهای API (`/api/v1/api-keys`)](#3-مدیریت-کلیدهای-api)
4. [ساختار داده قوانین فوروارد و تمام حالت‌های مسیر](#4-ساختار-داده-قوانین-فوروارد-و-تمام-حالت‌های-مسیر)
5. [اندپوینت‌های مدیریت قوانین (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`)](#5-اندپوینت‌های-مدیریت-قوانین)
6. [کنترل فیل‌اور، Override و فعال/غیرفعال‌سازی مسیرها](#6-کنترل-فیل‌اور-override-و-فعالغیرفعال‌سازی-مسیرها)
7. [تنظیمات سراسری موتور فیل‌اور (`/api/v1/settings`)](#7-تنظیمات-سراسری-موتور-فیل‌اور)
8. [تست زنده مسیر، پکت‌لاس ۵۰ تایی و لاگ‌های تصمیم‌گیری](#8-تست-زنده-مسیر-پکت‌لاس-۵۰-تایی-و-لاگ‌های-تصمیم‌گیری)
9. [آمار ترافیک و پهنای باند (`/api/v1/traffic/*`)](#9-آمار-ترافیک-و-پهنای-باند)
10. [شناسایی خودکار، درون‌ریزی و پشتیبان‌گیری](#10-شناسایی-خودکار-درون‌ریزی-و-پشتیبان‌گیری)
11. [سرویس‌های رله، شبکه و آپدیت سیستم](#11-سرویس‌های-رله-شبکه-و-آپدیت-سیستم)
12. [مشخصات OpenAPI 3.0.3 و کدهای خطا](#12-مشخصات-openapi-303-و-کدهای-خطا)

---

## 1. آدرس پایه و نسخه‌بندی مسیرها

تمام اندپوینت‌ها هم با پیشوند `/api/...` و هم با پیشوند نسخه‌دار `/api/v1/...` قابل فراخوانی هستند:

- بدون `secret_path`:
  - `https://203.0.113.10:8090/api/v1/...`
- همراه با `secret_path` (مثلاً `xfwd-admin`):
  - برای **ورود با نام کاربری و رمز عبور** (`/api/v1/login`): باید پیشوند مسیر مخفی را بگذارید:  
    `https://203.0.113.10:8090/xfwd-admin/api/v1/login`
  - برای **کلیدهای API** (`Bearer` یا `X-API-Key`): هر دو حالت مستقیم `/api/v1/...` و با مسیر مخفی `/xfwd-admin/api/v1/...` کار می‌کنند.

متدهای پشتیبانی‌شده: `GET` · `POST` · `PUT` · `PATCH` · `DELETE` · `OPTIONS`

---

## 2. احراز هویت و سطوح دسترسی (Scopes)

XForwarder از دو روش احراز هویت پشتیبانی می‌کند:

### روش اول: کلید API اختصاصی (پیشنهادی برای اسکریپت‌ها و ربات‌ها)
کلید را در داشبورد وب (**امنیت ← کلیدهای API**) یا از طریق API بسازید و در یکی از دو هدر زیر ارسال کنید:

```http
Authorization: Bearer xfwd_key_a1b2c3d4_0123456789abcdef0123456789abcdef
```
یا:
```http
X-API-Key: xfwd_key_a1b2c3d4_0123456789abcdef0123456789abcdef
```

#### سطوح دسترسی کلید (Scopes):
| سطح (`scope`) | مجوزها |
| :--- | :--- |
| `read` | فقط متدهای خواندنی (`GET`): وضعیت کلی، لیست قوانین، آمار ترافیک، تاریخچه پکت‌لاس، لاگ تصمیمات، خروجی بکاپ، سرویس‌ها، شبکه و OpenAPI. |
| `write` | تمام مجوزهای `read` + ایجاد/ویرایش/حذف قوانین، Override، روشن/خاموش کردن مسیرها، همگام‌سازی، تست زنده، ریست ترافیک، ایمپورت و کشف قوانین. |
| `admin` | دسترسی کامل: تمام مجوزهای `write` + مدیریت کلیدهای API، تنظیمات سراسری موتور، ریستارت سرویس‌ها، تنظیمات پنل، تغییر رمز و آپدیت سیستم. |

> [!IMPORTANT]
> هنگام درخواست با `API Key` و بدون کوکی مرورگر، بررسی CSRF Origin به‌صورت خودکار برای کلاینت‌های غیرمرورگری (curl، Python، PHP، Go و ...) عبور داده می‌شود.

### روش دوم: نشست موقت با نام کاربری و رمز عبور (`Session Token`)
1. ورود با `POST /xfwd-admin/api/v1/login` (محدودیت امنیتی: ۵ تلاش ناموفق در ۵ دقیقه = مسدودسازی IP به مدت ۱۵ دقیقه با کد `429`):

```bash
curl -s -X POST "https://203.0.113.10:8090/xfwd-admin/api/v1/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPassword!123"}'
```

**پاسخ موفق (`200 OK`):**
```json
{
  "ok": true,
  "token": "9f8e7d6c5b4a...",
  "username": "admin"
}
```

2. ارسال توکن در درخواست‌های بعدی با هدر `X-Session-Token: <token>` یا کوکی `xfwd_session=<token>`.
3. بررسی وضعیت نشست یا کلید فعلی:

```bash
curl -s -H "Authorization: Bearer xfwd_key_a1b2c3d4_..." \
  "https://203.0.113.10:8090/api/v1/me"
```

**پاسخ (`200 OK`):**
```json
{
  "authenticated": true,
  "username": "admin",
  "auth_type": "api_key",
  "scope": "write",
  "key_id": "key_a1b2c3d4",
  "key_name": "Automation Bot"
}
```

4. خروج از نشست:
```bash
curl -s -X POST -H "X-Session-Token: <token>" \
  "https://203.0.113.10:8090/api/v1/logout"
```

---

## 3. مدیریت کلیدهای API

تمام اندپوینت‌های این بخش نیازمند سطح دسترسی **`admin`** هستند. مسیر جایگزین `/api/security/api-keys` نیز پشتیبانی می‌شود.

### 3.1 لیست کلیدهای API (`GET /api/v1/api-keys`)
```bash
curl -s -H "Authorization: Bearer <ADMIN_KEY>" \
  "https://203.0.113.10:8090/api/v1/api-keys"
```
**پاسخ (`200 OK`):**
```json
{
  "ok": true,
  "count": 1,
  "api_keys": [
    {
      "id": "key_a1b2c3d4",
      "name": "WHMCS Panel",
      "prefix": "xfwd_key_a1b2c3d4_0123...",
      "scope": "write",
      "enabled": true,
      "expired": false,
      "created_at": 1764000000.0,
      "expires_at": 1771776000.0,
      "last_used_at": 1764003600.0
    }
  ]
}
```

### 3.2 ساخت کلید جدید (`POST /api/v1/api-keys`)
- `name` (الزامی): نام کلید (حداکثر ۶۴ کاراکتر)
- `scope` (اختیاری، پیش‌فرض `admin`): یکی از `read`، `write` یا `admin`
- `expires_in_days` (اختیاری، پیش‌فرض `0` به معنی بدون انقضا): تعداد روز اعتبار (`0` تا `3650`)

```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/api-keys" \
  -H "Authorization: Bearer <ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monitoring ReadOnly",
    "scope": "read",
    "expires_in_days": 90
  }'
```

**پاسخ (`201 Created`):**
```json
{
  "ok": true,
  "api_key": "xfwd_key_f0e1d2c3_aabbccddeeff00112233445566778899aabbccddeeff0011",
  "key": {
    "id": "key_f0e1d2c3",
    "name": "Monitoring ReadOnly",
    "prefix": "xfwd_key_f0e1d2c3_aabb...",
    "scope": "read",
    "enabled": true,
    "expired": false,
    "created_at": 1764005000.0,
    "expires_at": 1771781000.0,
    "last_used_at": 0.0
  }
}
```
> [!WARNING]
> مقدار `api_key` فقط یک‌بار در پاسخ `201 Created` برگردانده می‌شود و در سرور به‌صورت هش نمک‌دار (`sha256$salt$digest`) ذخیره می‌گردد.

### 3.3 ویرایش کلید (`PATCH /api/v1/api-keys/{id}`)
```bash
curl -s -X PATCH "https://203.0.113.10:8090/api/v1/api-keys/key_f0e1d2c3" \
  -H "Authorization: Bearer <ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Monitoring V2","scope":"write","enabled":false}'
```

### 3.4 ابطال و حذف کلید (`DELETE /api/v1/api-keys/{id}`)
```bash
curl -s -X DELETE "https://203.0.113.10:8090/api/v1/api-keys/key_f0e1d2c3" \
  -H "Authorization: Bearer <ADMIN_KEY>"
```

---

## 4. ساختار داده قوانین فوروارد و تمام حالت‌های مسیر

یک قانون (`Rule`) می‌تواند تک‌پورت، بازه پورت (`port_range`) یا استثنای پورت (`excluded_ports`) باشد و چندین مسیر مقصد با اولویت (`priority: 1..N`) داشته باشد.

### فیلدهای اصلی قانون:
| فیلد | نوع | توضیح |
| :--- | :--- | :--- |
| `id` | `string` | اختیاری (به‌صورت خودکار مثل `rule-443` یا `rule-10000-20000` ساخته می‌شود). |
| `port` | `integer \| string` | پورت ورودی (`1` تا `65535`) یا دستور کوتاه `"!= 22, 443"`. |
| `port_range` | `string` | بازه پورت به شکل `"10000-20000"` (مخصوص `nftables`). |
| `excluded_ports` | `array<int>` | لیست پورت‌های مستثنی‌شده (معمولاً با `port_range: "1-65535"`، فقط `nftables`). |
| `protocol` | `string` | `"tcp"` \| `"udp"` \| `"both"` (پیش‌فرض `"both"`). |
| `category` | `string` | نام دسته‌بندی اختیاری (حداکثر ۴۸ کاراکتر). |
| `force_override` | `integer` | `0` برای حالت خودکار، یا `1..N` برای قفل دستی روی اولویت مشخص. |
| `max_primary_latency_ms` | `integer` | اختیاری (`50` تا `1000`): سقف پینگ اولویت ۱ برای این قانون. |
| `destinations` | `array<Destination>` | حداقل یک مقصد مرتب‌شده بر اساس `priority`. |

### حالت‌های مختلف `type` در `destinations`:
1. **`haproxy`**: رله مستقیم لایه ۴ (بدون تونل) — **فقط آی‌پی IPv6 معتبر** قبول می‌کند. پشتیبانی از `proxy_protocol: true/false`.
2. **`nginx`**: پروکسی stream با کارایی بالا (IPv4، IPv6 یا Hostname) — پشتیبانی از `proxy_protocol` و **Load Balancing** (`lb_enabled`, `lb_mode`: `ip_hash` / `least_conn` / `round_robin` / `random`, `lb_targets`).
3. **`nftables`**: فورواردینگ کرنل لایه ۳ (IPv4 یا IPv6 عددی) روی اینترفیس تونل (`tunnel_iface`) یا مسیر مستقیم؛ پشتیبانی از بازه پورت ۱:۱، `excluded_ports` و **Load Balancing** (`ip_hash` / `round_robin` / `random`).
4. **`nftables_dsr`**: حالت DSR بدون حالت (Stateless Direct Server Return) روی سرور ایران — `port` مقصد باید با پورت ورودی یکسان باشد؛ `spoof_ip` و `tunnel_iface` اختیاری هستند.
5. **`nftables_dsr_relay`**: رله میانی DSR — نیازمند `spoof_ip` (آی‌پی عمومی سرور ورودی/ایران)، با `ingress_iface` و `snat_ip` اختیاری.
6. **`nftables_dsr_synack`**: حالت DSR مبتنی بر SYN-ACK — تک‌پورت `protocol: "tcp"` و مقصد IPv4 فقط.
7. **`nftables_dsr_direct`**: دریافت مستقیم DSR روی سرور مقصد خارج — تک‌پورت `protocol: "tcp"`، مقصد IPv4، نیازمند `spoof_ip` و `ingress_iface`.

---

## 5. اندپوینت‌های مدیریت قوانین

### 5.1 دریافت لیست قوانین (`GET /api/v1/rules`) — Scope: `read`
پارامترهای فیلتر اختیاری در Query String:
- `category`: فیلتر نام دسته‌بندی (یا `__uncategorized__` برای بدون دسته)
- `protocol`: `tcp` | `udp` | `both`
- `type`: نوع مقصد (مثل `haproxy`، `nftables`، `nginx`)
- `port`: شماره پورت (پیدا کردن قانونی که آن پورت را پوشش می‌دهد، حتی در بازه‌ها)
- `include_runtime`: `true` (پیش‌فرض) یا `false` برای حذف آمار زنده

```bash
curl -s -H "Authorization: Bearer <READ_KEY>" \
  "https://203.0.113.10:8090/api/v1/rules?protocol=both&include_runtime=true"
```

### 5.2 دریافت جزئیات یک قانون (`GET /api/v1/rules/{id}`) — Scope: `read`
می‌توانید هم شناسه (`rule-443`) و هم شماره پورت (`443`) را ارسال کنید:
```bash
curl -s -H "Authorization: Bearer <READ_KEY>" \
  "https://203.0.113.10:8090/api/v1/rules/rule-443"
```

### 5.3 ایجاد قانون جدید (`POST /api/v1/rules` یا Upsert با `POST /api/v1/rule`) — Scope: `write`
> تفاوت: `POST /api/v1/rules` در صورت تکراری بودن شناسه کد `409 Conflict` می‌دهد و هنگام ساخت کد `201 Created` برمی‌گرداند؛ اما `POST /api/v1/rule` در صورت وجود، قانون را جایگزین (Upsert) کرده و `200 OK` برمی‌گرداند.

#### مثال ۱: قانون چندمسیره (اولویت ۱ HAProxy IPv6 + اولویت ۲ تونل NFTables با `is_relay`)
```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "port": 443,
    "protocol": "both",
    "category": "Main Relays",
    "destinations": [
      {
        "priority": 1,
        "type": "haproxy",
        "target": "2001:db8:1::10",
        "port": 443,
        "proxy_protocol": false,
        "is_relay": false,
        "enabled": true,
        "comment": "Primary IPv6 Exit"
      },
      {
        "priority": 2,
        "type": "nftables",
        "target": "10.200.1.2",
        "port": 443,
        "tunnel_iface": "gre1",
        "is_relay": true,
        "enabled": true,
        "comment": "Backup GRE Tunnel"
      }
    ]
  }'
```

#### مثال ۲: قانون بازه پورت ۱:۱ در NFTables (`10000-20000`)
```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "port_range": "10000-20000",
    "protocol": "both",
    "category": "UDP Ranges",
    "destinations": [
      {
        "priority": 1,
        "type": "nftables",
        "target": "10.200.2.2",
        "port_range": "10000-20000",
        "tunnel_iface": "awg0",
        "comment": "1:1 Gaming & Voice Range"
      }
    ]
  }'
```

#### مثال ۳: فوروارد همه پورت‌ها به‌جز پورت‌های مستثنی (`!= 22, 443, 8090`)
```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "port_range": "1-65535",
    "excluded_ports": [22, 443, 8090],
    "protocol": "both",
    "destinations": [
      {
        "priority": 1,
        "type": "nftables",
        "target": "10.200.1.2",
        "tunnel_iface": "gre1",
        "comment": "Wildcard All-Except"
      }
    ]
  }'
```

#### مثال ۴: استخر Load Balancing در Nginx یا NFTables (با وزن‌دهی)
```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "port": 2083,
    "protocol": "tcp",
    "category": "LB Pool",
    "destinations": [
      {
        "priority": 1,
        "type": "nginx",
        "lb_enabled": true,
        "lb_mode": "ip_hash",
        "lb_targets": [
          {"target": "198.51.100.20", "port": 2083, "weight": 2, "enabled": true, "comment": "Node A"},
          {"target": "198.51.100.21", "port": 2083, "weight": 1, "enabled": true, "comment": "Node B"}
        ]
      }
    ]
  }'
```

#### مثال ۵: حالت DSR Relay و DSR Direct
```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "port": 8443,
    "protocol": "tcp",
    "destinations": [
      {
        "priority": 1,
        "type": "nftables_dsr_relay",
        "target": "10.200.1.2",
        "port": 8443,
        "spoof_ip": "203.0.113.10",
        "ingress_iface": "ipip1",
        "snat_ip": "192.0.2.50",
        "comment": "DSR Relay Leg"
      }
    ]
  }'
```

### 5.4 جایگزینی کامل قانون (`PUT /api/v1/rules/{id}`) — Scope: `write`
```bash
curl -s -X PUT "https://203.0.113.10:8090/api/v1/rules/rule-443" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "port": 443,
    "protocol": "tcp",
    "category": "Updated",
    "destinations": [
      {"priority": 1, "type": "nginx", "target": "198.51.100.20", "port": 443}
    ]
  }'
```

### 5.5 ویرایش جزئی قانون (`PATCH /api/v1/rules/{id}`) — Scope: `write`
فقط فیلدهای ارسالی را تغییر می‌دهد و بقیه ساختار قانون حفظ می‌شود:
```bash
curl -s -X PATCH "https://203.0.113.10:8090/api/v1/rules/rule-443" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"category":"VIP Relays","max_primary_latency_ms":180}'
```

### 5.6 حذف تک‌قانون و حذف گروهی — Scope: `write`
```bash
# حذف تک‌قانون:
curl -s -X DELETE "https://203.0.113.10:8090/api/v1/rules/rule-443" \
  -H "Authorization: Bearer <WRITE_KEY>"

# حذف گروهی:
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules/bulk-delete" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"rule_ids":["rule-443","rule-2083"]}'
```

---

## 6. کنترل فیل‌اور، Override و فعال/غیرفعال‌سازی مسیرها

### 6.1 اجبار اولویت یا بازگشت به Auto Failover
- `POST /api/v1/rules/{id}/override` (یا `POST /api/v1/override` با `rule_id` در بدنه)
- مقدار `force_override`: `0` برای حالت خودکار، یا `1..N` برای قفل روی اولویت مشخص (با Flush هوشمند Conntrack).

```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules/rule-443/override" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"force_override":2}'
```

### 6.2 تغییر حالت دسته‌جمعی (`POST /api/v1/override/batch`)
```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/override/batch" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"force_override":0}'
```

### 6.3 روشن یا خاموش کردن یک مسیر اولویت (`Toggle Destination`)
- `POST /api/v1/rules/{id}/destinations/{priority}/toggle`
- یا `POST /api/v1/rule/toggle-destination` با `{"rule_id":"rule-443","priority":2,"enabled":false}`
- اگر `enabled` ارسال نشود، وضعیت فعلی برعکس (Toggle) می‌شود.

```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules/rule-443/destinations/2/toggle" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"enabled":false}'
```

### 6.4 همگام‌سازی فوری و بیدار کردن موتور (`POST /api/v1/sync`)
```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/sync" \
  -H "Authorization: Bearer <WRITE_KEY>"
```

---

## 7. تنظیمات سراسری موتور فیل‌اور

- خواندن تنظیمات: `GET /api/v1/settings` (Scope: `read`)
- جایگزینی/ویرایش تنظیمات: `PUT /api/v1/settings` و `PATCH /api/v1/settings` (Scope: `admin`)

```bash
curl -s -X PATCH "https://203.0.113.10:8090/api/v1/settings" \
  -H "Authorization: Bearer <ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "wan_interface": "auto",
    "check_interval_seconds": 8,
    "probe_count": 10,
    "target_probe_interval_seconds": 60,
    "fast_liveness_interval_seconds": 15,
    "min_hold_seconds": 600,
    "switch_confirm_seconds": 120,
    "max_primary_latency_ms": 150,
    "hysteresis_percent": 20,
    "fast_failover_enabled": true
  }'
```

---

## 8. تست زنده مسیر، پکت‌لاس ۵۰ تایی و لاگ‌های تصمیم‌گیری

### 8.1 تست زنده مقصد (`POST /api/v1/test-target`) — Scope: `write`
```bash
# تست اتصال و تاخیر معمولی (10 بسته):
curl -s -X POST "https://203.0.113.10:8090/api/v1/test-target" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"target":"198.51.100.20","port":443,"type":"nginx","protocol":"tcp","packets":10}'

# تست دقیق 50 پکتی (mode: "loss_50"):
curl -s -X POST "https://203.0.113.10:8090/api/v1/test-target" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"target":"10.200.1.2","port":443,"type":"nftables","tunnel_iface":"gre1","mode":"loss_50"}'
```

### 8.2 تست ۵۰ تایی پکت‌لاس، اجرای راند و دریافت تاریخچه
- `POST /api/v1/test-loss` (`write`): `{"target":"198.51.100.20"}`
- `POST /api/v1/metrics/trigger-round` (`write`): اجرای تست ۵۰ تایی برای همه مقصدهای یکتا
- `GET /api/v1/metrics/loss-history?target=all&range=24h` (`read`): بازه‌های `24h`, `7d`, `30d`
- `GET /api/v1/logs/switches?rule_id=rule-443&limit=50` (`read`): لاگ تصمیم‌گیری تغییر مسیرها

---

## 9. آمار ترافیک و پهنای باند

- خلاصه مصرف: `GET /api/v1/traffic/summary?period=24h&entity_type=port&entity_id=443` (`read`)
- سری زمانی نمودار: `GET /api/v1/traffic/timeseries?period=7d&entity_type=all&entity_id=all` (`read`)
  - مقادیر `period`: `24h` | `7d` | `30d` | `12m`
  - مقادیر `entity_type`: `all` | `port` | `tunnel` | `method` | `tunnel_type`
- ریست شمارنده دوره یا حذف تاریخچه (`POST /api/v1/traffic/reset` — Scope: `write`):

```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/traffic/reset" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"entity_type":"port","entity_id":"443","wipe_history":false}'
```

---

## 10. شناسایی خودکار، درون‌ریزی و پشتیبان‌گیری

| متد و مسیر | Scope | توضیح |
| :--- | :--- | :--- |
| `GET /api/v1/import/discover` | `read` | کشف قوانین مدیریت‌نشده HAProxy، Nginx و NFTables/iptables |
| `POST /api/v1/import/haproxy` | `write` | درون‌ریزی قوانین HAProxy کشف‌شده |
| `POST /api/v1/import/nftables` | `write` | درون‌ریزی قوانین NFTables همراه بکاپ و حذف تداخل با Handle دقیق |
| `POST /api/v1/import/all` | `write` | درون‌ریزی همه قوانین کشف‌شده |
| `GET /api/v1/config/export` | `read` | دانلود فایل بکاپ JSON (بدون اطلاعات رمز عبور و کلیدهای API) |
| `POST /api/v1/config/import` | `write` | درون‌ریزی فایل بکاپ کامل، آرایه قوانین یا تک‌قانون (`mode`: `"merge"` یا `"replace"`) |

```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/config/import" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"merge","config":{"rules":[{"port":8080,"protocol":"tcp","destinations":[{"priority":1,"type":"nginx","target":"198.51.100.20","port":8080}]}]}}'
```

---

## 11. سرویس‌های رله، شبکه و آپدیت سیستم

- `GET /api/v1/health` (`read`) — سلامت سبک سرویس وب و نسخه نصب‌شده
- `GET /api/v1/status` (`read`) — اسنپ‌شات جامع تمام بخش‌ها (کانفیگ بدون هش، وضعیت زنده، CPU/RAM، سرویس‌ها، شبکه و ترافیک)
- `GET /api/v1/services/status` (`read`) — وضعیت نصب، نسخه و پورت‌های فعال `nftables`، `haproxy`، `nginx`
- `GET /api/v1/network/interfaces` (`read`) — آی‌پی‌های WAN و لیست اینترفیس‌های تونل روی سرور
- `POST /api/v1/services/restart` (`admin`) — مقادیر مجاز `service`:
  `all` · `engine` · `web` · `haproxy` · `haproxy_restart` · `nginx` · `nginx_sync` · `nginx_pull` · `nginx_restart` · `nftables` · `nftables_restart`
- `GET /api/v1/system/version?check=1` (`read`)
- `GET /api/v1/system/update/transports` (`read`)
- `POST /api/v1/system/update/transports` (`admin`) — تنظیم روش اتصال به گیت‌هاب (`auto` | `direct` | `iface` | `proxy` | `mirror`)
- `POST /api/v1/system/update` (`admin`) — شروع آپدیت غیرمسدودکننده با `systemd-run`
- `GET /api/v1/system/update/status` (`read`) — وضعیت و لاگ لحظه‌ای آپدیت
- `POST /api/v1/security/credentials` (`admin`) — تغییر نام کاربری و رمز عبور ادمین
- `POST /api/v1/security/panel` (`admin`) — تغییر پورت و `secret_path` پنل وب

### مثال پایتون کامل (کتابخانه استاندارد `urllib.request`):
```python
import json
import urllib.request

BASE = "https://203.0.113.10:8090/api/v1"
API_KEY = "xfwd_key_a1b2c3d4_example_secret"

def api_call(method: str, path: str, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

print(api_call("GET", "/rules"))
```

---

## 12. مشخصات OpenAPI 3.0.3 و کدهای خطا

برای دریافت فایل استاندارد ماشین‌خوان OpenAPI جهت وارد کردن در Postman، Insomnia یا Swagger UI:
```bash
curl -s -H "Authorization: Bearer <READ_KEY>" \
  "https://203.0.113.10:8090/api/v1/openapi.json" -o xforwarder-openapi.json
```

### کدهای وضعیت HTTP:
| کد | معنی | توضیح |
| :--- | :--- | :--- |
| `200` | OK | درخواست با موفقیت انجام شد. |
| `201` | Created | منبع جدید (قانون یا کلید API) با موفقیت ایجاد شد. |
| `204` | No Content | پاسخ موفق برای `OPTIONS` Preflight. |
| `400` | Bad Request | خطای اعتبارسنجی ورودی (پورت نامعتبر، فرمت اشتباه، نوع مقصد ناسازگار و...). |
| `401` | Unauthorized | توکن یا کلید API ارسال نشده، منقضی شده یا نامعتبر است. |
| `403` | Forbidden | سطح دسترسی کلید (`scope`) کافی نیست یا هدر CSRF نامعتبر است. |
| `404` | Not Found | قانون، کلید API یا مسیر مورد نظر یافت نشد. |
| `409` | Conflict | تداخل پورت با قانون دیگر، پورت پنل وب یا سرویس سیستم. |
| `413` | Payload Too Large | حجم بدنه درخواست بیشتر از حد مجاز ۶۴ کیلوبایت است. |
| `429` | Too Many Requests | قفل موقت ۱۵ دقیقه‌ای به دلیل تلاش‌های ناموفق ورود فعال شده است. |
| `500` | Internal Server Error | خطا در ذخیره‌سازی یا همگام‌سازی سرویس‌های سیستم. |
