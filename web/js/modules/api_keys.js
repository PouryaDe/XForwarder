// ============================================================================
// XForwarder - API Keys & Interactive REST API Documentation (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { showToast, escapeHtml, copyText, askConfirm } from "./utils.js";
import { t, getCurrentLang } from "./i18n.js";

const API_DOCS_ENDPOINTS = [
    {
        cat: "auth",
        method: "POST",
        path: "/api/v1/login",
        scope: "public",
        summaryEn: "Authenticate with admin username/password to get session token & cookie.",
        summaryFa: "ورود با نام کاربری و رمز عبور ادمین برای دریافت توکن نشست.",
        curl: `curl -X POST "https://203.0.113.10:8090/xfwd-admin/api/v1/login" \\\n  -H "Content-Type: application/json" \\\n  -d '{"username":"admin","password":"StrongPassword!123"}'`
    },
    {
        cat: "auth",
        method: "GET",
        path: "/api/v1/me",
        scope: "read",
        summaryEn: "Inspect active authentication context (session or API key, scope, key_id).",
        summaryFa: "بررسی وضعیت احراز هویت فعلی (نوع توکن، سطح دسترسی و شناسه کلید).",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/me"`
    },
    {
        cat: "auth",
        method: "GET",
        path: "/api/v1/api-keys",
        scope: "admin",
        summaryEn: "List all configured API keys (prefix, scope, status, last used).",
        summaryFa: "دریافت لیست کلیدهای API تعریف‌شده به همراه سطح دسترسی و وضعیت.",
        curl: `curl -H "X-API-Key: xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/api-keys"`
    },
    {
        cat: "auth",
        method: "POST",
        path: "/api/v1/api-keys",
        scope: "admin",
        summaryEn: "Create a new scoped API key (read | write | admin). Secret is returned once.",
        summaryFa: "ساخت کلید API جدید با سطح دسترسی مشخص. متن کلید فقط یک‌بار نمایش داده می‌شود.",
        curl: `curl -X POST -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"name":"Billing Bot","scope":"write","expires_in_days":90}' \\\n  "https://203.0.113.10:8090/api/v1/api-keys"`
    },
    {
        cat: "auth",
        method: "PATCH",
        path: "/api/v1/api-keys/{id}",
        scope: "admin",
        summaryEn: "Rename, change scope, or enable/disable an existing API key.",
        summaryFa: "ویرایش نام، سطح دسترسی یا فعال/غیرفعال کردن کلید API.",
        curl: `curl -X PATCH -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"enabled":false}' \\\n  "https://203.0.113.10:8090/api/v1/api-keys/key_a1b2c3d4"`
    },
    {
        cat: "auth",
        method: "DELETE",
        path: "/api/v1/api-keys/{id}",
        scope: "admin",
        summaryEn: "Permanently revoke and delete an API key.",
        summaryFa: "ابطال و حذف دائمی کلید API.",
        curl: `curl -X DELETE -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/api-keys/key_a1b2c3d4"`
    },
    {
        cat: "rules",
        method: "GET",
        path: "/api/v1/rules",
        scope: "read",
        summaryEn: "List all rules with optional ?category=, ?protocol=, ?type=, ?port= filters.",
        summaryFa: "دریافت فهرست تمام قوانین فورواردینگ با امکان فیلتر دسته‌بندی، پروتکل و پورت.",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/rules?protocol=both"`
    },
    {
        cat: "rules",
        method: "GET",
        path: "/api/v1/rules/{id}",
        scope: "read",
        summaryEn: "Get a single forwarding rule by ID or port along with live runtime stats.",
        summaryFa: "دریافت جزئیات یک قانون فورواردینگ به همراه آمار زنده مسیرها.",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/rules/rule-443"`
    },
    {
        cat: "rules",
        method: "POST",
        path: "/api/v1/rules",
        scope: "write",
        summaryEn: "Create a new multi-path rule (HAProxy/Nginx/NFTables/DSR/LB/Port Ranges).",
        summaryFa: "ایجاد قانون جدید با پشتیبانی از تمام مدها (HAProxy، Nginx، NFTables، DSR و LB).",
        curl: `curl -X POST -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"port":443,"protocol":"both","category":"Main","destinations":[{"priority":1,"type":"haproxy","target":"2001:db8:1::10","port":443},{"priority":2,"type":"nftables","target":"10.200.1.2","port":443,"tunnel_iface":"gre1","is_relay":true}]}' \\\n  "https://203.0.113.10:8090/api/v1/rules"`
    },
    {
        cat: "rules",
        method: "PUT",
        path: "/api/v1/rules/{id}",
        scope: "write",
        summaryEn: "Replace an existing forwarding rule completely and resynchronize engines.",
        summaryFa: "جایگزینی کامل یک قانون موجود و همگام‌سازی فوری سرویس‌های رله.",
        curl: `curl -X PUT -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"port":443,"protocol":"tcp","destinations":[{"priority":1,"type":"nginx","target":"198.51.100.20","port":443}]}' \\\n  "https://203.0.113.10:8090/api/v1/rules/rule-443"`
    },
    {
        cat: "rules",
        method: "PATCH",
        path: "/api/v1/rules/{id}",
        scope: "write",
        summaryEn: "Partially update specific fields (e.g. category, protocol, destinations).",
        summaryFa: "ویرایش جزئی فیلدهای یک قانون بدون نیاز به ارسال کل آبجکت.",
        curl: `curl -X PATCH -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"category":"VIP Relays","max_primary_latency_ms":180}' \\\n  "https://203.0.113.10:8090/api/v1/rules/rule-443"`
    },
    {
        cat: "rules",
        method: "DELETE",
        path: "/api/v1/rules/{id}",
        scope: "write",
        summaryEn: "Delete a forwarding rule by ID or port and purge its kernel/proxy bindings.",
        summaryFa: "حذف قانون بر اساس شناسه یا پورت و پاکسازی تنظیمات کرنل و پروکسی.",
        curl: `curl -X DELETE -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/rules/rule-443"`
    },
    {
        cat: "failover",
        method: "POST",
        path: "/api/v1/rules/{id}/override",
        scope: "write",
        summaryEn: "Force a priority (force_override: 1..N) or restore Auto Failover (0).",
        summaryFa: "قفل کردن ترافیک روی یک اولویت خاص یا بازگردانی به حالت خودکار (0).",
        curl: `curl -X POST -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"force_override":2}' \\\n  "https://203.0.113.10:8090/api/v1/rules/rule-443/override"`
    },
    {
        cat: "failover",
        method: "POST",
        path: "/api/v1/rules/{id}/destinations/{priority}/toggle",
        scope: "write",
        summaryEn: "Enable or disable an individual priority path within a rule.",
        summaryFa: "روشن یا خاموش کردن یکی از مسیرهای اولویت داخل یک قانون.",
        curl: `curl -X POST -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"enabled":false}' \\\n  "https://203.0.113.10:8090/api/v1/rules/rule-443/destinations/2/toggle"`
    },
    {
        cat: "failover",
        method: "POST",
        path: "/api/v1/test-target",
        scope: "write",
        summaryEn: "Run live probe (ICMP/L4 TCP or 50-packet loss test) on any destination.",
        summaryFa: "اجرای تست زنده پینگ، اتصال L4 یا تست ۵۰ پکتی افت بسته روی مقصد.",
        curl: `curl -X POST -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"target":"198.51.100.20","port":443,"type":"nginx","protocol":"tcp","packets":10}' \\\n  "https://203.0.113.10:8090/api/v1/test-target"`
    },
    {
        cat: "failover",
        method: "GET",
        path: "/api/v1/logs/switches",
        scope: "read",
        summaryEn: "Fetch recent automated failover switch decisions & metrics reasons.",
        summaryFa: "دریافت لاگ تصمیم‌گیری‌های تغییر مسیر خودکار و دلایل آن.",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/logs/switches?limit=20"`
    },
    {
        cat: "traffic",
        method: "GET",
        path: "/api/v1/traffic/summary",
        scope: "read",
        summaryEn: "Retrieve RX/TX/total traffic accounting across ports, methods, and tunnels.",
        summaryFa: "دریافت خلاصه مصرف ترافیک (آپلود/دانلود/کل) روی پورت‌ها و تونل‌ها.",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/traffic/summary?period=24h"`
    },
    {
        cat: "traffic",
        method: "POST",
        path: "/api/v1/traffic/reset",
        scope: "write",
        summaryEn: "Reset billing cycle counter for all entities, a specific port, or a tunnel.",
        summaryFa: "ریست کردن شمارنده دوره جاری برای کل سرور، یک پورت یا یک اینترفیس تونل.",
        curl: `curl -X POST -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"entity_type":"port","entity_id":"443","wipe_history":false}' \\\n  "https://203.0.113.10:8090/api/v1/traffic/reset"`
    },
    {
        cat: "traffic",
        method: "GET",
        path: "/api/v1/metrics/loss-history",
        scope: "read",
        summaryEn: "Query 30-day 50-probe packet loss and latency timeline.",
        summaryFa: "دریافت تاریخچه ۳۰ روزه تست‌های پکت‌لاس ۵۰ تایی و لتنسی.",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/metrics/loss-history?target=all&range=24h"`
    },
    {
        cat: "system",
        method: "GET",
        path: "/api/v1/status",
        scope: "read",
        summaryEn: "Full system snapshot (config, runtime state, CPU/RAM, services, network, traffic).",
        summaryFa: "وضعیت جامع سیستم (تنظیمات، وضعیت زنده مسیرها، منابع، سرویس‌ها و ترافیک).",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/status"`
    },
    {
        cat: "system",
        method: "PATCH",
        path: "/api/v1/settings",
        scope: "admin",
        summaryEn: "Update global failover, probing, and hold/cooldown engine thresholds.",
        summaryFa: "تغییر پارامترهای سراسری موتور فیل‌اور، بازه‌های پروب و آستانه‌های سوئیچ.",
        curl: `curl -X PATCH -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"max_primary_latency_ms":150,"min_hold_seconds":600}' \\\n  "https://203.0.113.10:8090/api/v1/settings"`
    },
    {
        cat: "system",
        method: "POST",
        path: "/api/v1/services/restart",
        scope: "admin",
        summaryEn: "Reload or restart haproxy, nginx, nftables, engine, web, or all.",
        summaryFa: "بارگذاری مجدد یا ریستارت کنترل‌شده سرویس‌های رله، هسته یا پنل وب.",
        curl: `curl -X POST -H "Authorization: Bearer xfwd_key_example_secret" \\\n  -H "Content-Type: application/json" \\\n  -d '{"service":"haproxy"}' \\\n  "https://203.0.113.10:8090/api/v1/services/restart"`
    },
    {
        cat: "system",
        method: "GET",
        path: "/api/v1/openapi.json",
        scope: "read",
        summaryEn: "Download complete OpenAPI 3.0.3 machine-readable specification.",
        summaryFa: "دریافت فایل استاندارد OpenAPI 3.0.3 برای ایمپورت در Postman یا Swagger.",
        curl: `curl -H "Authorization: Bearer xfwd_key_example_secret" \\\n  "https://203.0.113.10:8090/api/v1/openapi.json"`
    }
];

let currentDocsFilter = "all";

function formatShortTime(ts) {
    if (!ts || Number(ts) <= 0) return t("api.never", {}, "Never");
    try {
        return new Date(Number(ts) * 1000).toLocaleString();
    } catch (_) {
        return "-";
    }
}

export async function fetchApiKeys() {
    const listEl = document.getElementById("apiKeysList");
    if (!listEl) return;
    try {
        const res = await fetch(`${API_BASE}/api-keys`, { headers: { "Accept": "application/json" } });
        if (!res.ok) return;
        const data = await res.json();
        renderApiKeysList(Array.isArray(data.api_keys) ? data.api_keys : []);
    } catch (_) {}
}

function renderApiKeysList(keys) {
    const listEl = document.getElementById("apiKeysList");
    if (!listEl) return;
    if (!keys.length) {
        listEl.innerHTML = `<div class="api-keys-empty">${escapeHtml(t("api.empty", {}, "No API keys created yet. Generate one above for scripts or external integrations."))}</div>`;
        return;
    }

    listEl.innerHTML = keys.map((k) => {
        const statusClass = k.expired ? "badge-warn" : (k.enabled ? "badge-good" : "badge-neutral");
        const statusText = k.expired
            ? t("api.status_expired", {}, "EXPIRED")
            : (k.enabled ? t("status.active", {}, "ACTIVE") : t("status.inactive", {}, "INACTIVE"));
        const scopeLabel = String(k.scope || "admin").toUpperCase();
        const toggleLabel = k.enabled ? t("api.disable_btn", {}, "Disable") : t("api.enable_btn", {}, "Enable");
        const expStr = k.expires_at > 0 ? formatShortTime(k.expires_at) : t("api.no_expiry", {}, "No expiry");

        return `
            <div class="api-key-row" data-key-id="${escapeHtml(k.id)}">
                <div class="api-key-row-main">
                    <div class="api-key-row-title">
                        <strong>${escapeHtml(k.name)}</strong>
                        <span class="api-scope-badge scope-${escapeHtml(k.scope)}">${escapeHtml(scopeLabel)}</span>
                        <span class="stat-badge ${statusClass}">${escapeHtml(statusText)}</span>
                    </div>
                    <div class="api-key-row-meta">
                        <code class="font-mono ltr-mono">${escapeHtml(k.prefix)}</code>
                        <span>&middot;</span>
                        <span>${escapeHtml(t("api.last_used", {}, "Last used:"))} <span class="font-mono">${escapeHtml(formatShortTime(k.last_used_at))}</span></span>
                        <span>&middot;</span>
                        <span>${escapeHtml(t("api.expires", {}, "Expires:"))} <span class="font-mono">${escapeHtml(expStr)}</span></span>
                    </div>
                </div>
                <div class="api-key-row-actions">
                    <button type="button" class="btn btn-secondary btn-xs btn-toggle-apikey" data-id="${escapeHtml(k.id)}" data-enabled="${k.enabled ? "1" : "0"}">${escapeHtml(toggleLabel)}</button>
                    <button type="button" class="btn btn-danger-ghost btn-xs btn-delete-apikey" data-id="${escapeHtml(k.id)}" data-name="${escapeHtml(k.name)}">${escapeHtml(t("api.revoke_btn", {}, "Revoke"))}</button>
                </div>
            </div>
        `;
    }).join("");

    listEl.querySelectorAll(".btn-toggle-apikey").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.id;
            const curEnabled = btn.dataset.enabled === "1";
            btn.disabled = true;
            try {
                const res = await fetch(`${API_BASE}/api-keys/${encodeURIComponent(id)}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json", "Accept": "application/json" },
                    body: JSON.stringify({ enabled: !curEnabled })
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data.ok) {
                    showToast(t("api.updated_toast", {}, "API key updated"), "success");
                    await fetchApiKeys();
                } else {
                    showToast(data.error || "Failed to update API key", "error");
                }
            } catch (_) {
                showToast("Network error", "error");
            } finally {
                btn.disabled = false;
            }
        });
    });

    listEl.querySelectorAll(".btn-delete-apikey").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.id;
            const name = btn.dataset.name || id;
            const confirmed = await askConfirm(
                t("api.revoke_confirm_title", {}, "Revoke API Key?"),
                t("api.revoke_confirm_msg", { name }, `Revoke API key "${name}"? Any integration using it will immediately receive 401 Unauthorized.`),
                { confirmText: t("api.revoke_btn", {}, "Revoke"), variant: "danger" }
            );
            if (!confirmed) return;
            try {
                const res = await fetch(`${API_BASE}/api-keys/${encodeURIComponent(id)}`, { method: "DELETE" });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data.ok) {
                    showToast(t("api.revoked_toast", {}, "API key revoked"), "success");
                    await fetchApiKeys();
                } else {
                    showToast(data.error || "Failed to revoke API key", "error");
                }
            } catch (_) {
                showToast("Network error", "error");
            }
        });
    });
}

function renderApiDocsEndpoints() {
    const listEl = document.getElementById("apiDocsEndpointsList");
    if (!listEl) return;
    const isFa = getCurrentLang() === "fa";
    const items = API_DOCS_ENDPOINTS.filter((ep) => currentDocsFilter === "all" || ep.cat === currentDocsFilter);

    listEl.innerHTML = items.map((ep, idx) => {
        const desc = isFa ? ep.summaryFa : ep.summaryEn;
        const mLow = ep.method.toLowerCase();
        return `
            <div class="api-docs-endpoint-card">
                <div class="api-docs-endpoint-head">
                    <div class="api-docs-endpoint-sig">
                        <span class="api-method-badge method-${escapeHtml(mLow)}">${escapeHtml(ep.method)}</span>
                        <code class="font-mono ltr-mono api-endpoint-path">${escapeHtml(ep.path)}</code>
                    </div>
                    <div class="api-docs-endpoint-meta">
                        <span class="api-scope-badge scope-${escapeHtml(ep.scope)}">${escapeHtml(ep.scope.toUpperCase())}</span>
                        <button type="button" class="btn btn-secondary btn-xs btn-copy-apicurl" data-idx="${idx}" title="Copy cURL example">cURL</button>
                    </div>
                </div>
                <p class="api-docs-endpoint-desc">${escapeHtml(desc)}</p>
                <pre class="api-docs-code font-mono ltr-mono"><code>${escapeHtml(ep.curl)}</code></pre>
            </div>
        `;
    }).join("");

    listEl.querySelectorAll(".btn-copy-apicurl").forEach((btn) => {
        btn.addEventListener("click", () => {
            const ep = items[Number(btn.dataset.idx)];
            if (ep) copyText(ep.curl, "cURL example copied!");
        });
    });
}

export function openApiDocsModal() {
    const modal = document.getElementById("apiDocsModal");
    const baseUrlEl = document.getElementById("apiDocsBaseUrl");
    if (baseUrlEl) {
        baseUrlEl.textContent = `${window.location.origin}${API_BASE}/v1`;
    }
    renderApiDocsEndpoints();
    if (modal) modal.classList.add("show");
}

export function closeApiDocsModal() {
    const modal = document.getElementById("apiDocsModal");
    if (modal) modal.classList.remove("show");
}

export function initApiKeysManager() {
    const form = document.getElementById("apiKeyCreateForm");
    const nameInput = document.getElementById("inpApiKeyName");
    const scopeSel = document.getElementById("selApiKeyScope");
    const expSel = document.getElementById("selApiKeyExpiry");
    const submitBtn = document.getElementById("btnCreateApiKey");
    const revealBox = document.getElementById("apiKeyRevealBox");
    const revealVal = document.getElementById("apiKeyRevealValue");
    const btnCopySecret = document.getElementById("btnCopyApiKeySecret");
    const btnDismissReveal = document.getElementById("btnDismissApiKeyReveal");
    const btnOpenDocs = document.getElementById("btnOpenApiDocsModal");
    const btnDownloadOpenApi = document.getElementById("btnDownloadOpenApi");
    const btnCloseDocs = document.getElementById("btnCloseApiDocsModal");
    const btnCloseDocsFooter = document.getElementById("btnCloseApiDocsModalFooter");

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = nameInput ? nameInput.value.trim() : "";
            const scope = scopeSel ? scopeSel.value : "admin";
            const expires_in_days = expSel ? parseInt(expSel.value, 10) || 0 : 0;
            if (!name) {
                showToast(t("api.name_required", {}, "Please enter an API key name"), "error");
                return;
            }
            if (submitBtn) submitBtn.disabled = true;
            try {
                const res = await fetch(`${API_BASE}/api-keys`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Accept": "application/json" },
                    body: JSON.stringify({ name, scope, expires_in_days })
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data.ok && data.api_key) {
                    if (nameInput) nameInput.value = "";
                    if (revealVal) revealVal.textContent = data.api_key;
                    if (revealBox) revealBox.style.display = "flex";
                    showToast(t("api.created_toast", {}, "API key generated! Copy it now."), "success");
                    await fetchApiKeys();
                } else {
                    showToast(data.error || "Failed to generate API key", "error");
                }
            } catch (_) {
                showToast("Network error communicating with server", "error");
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }

    if (btnCopySecret && revealVal) {
        btnCopySecret.addEventListener("click", () => {
            const val = revealVal.textContent.trim();
            if (val) copyText(val, t("api.copied_secret", {}, "API key copied to clipboard!"));
        });
    }

    if (btnDismissReveal && revealBox) {
        btnDismissReveal.addEventListener("click", () => {
            revealBox.style.display = "none";
            if (revealVal) revealVal.textContent = "";
        });
    }

    if (btnOpenDocs) btnOpenDocs.addEventListener("click", openApiDocsModal);
    if (btnCloseDocs) btnCloseDocs.addEventListener("click", closeApiDocsModal);
    if (btnCloseDocsFooter) btnCloseDocsFooter.addEventListener("click", closeApiDocsModal);

    if (btnDownloadOpenApi) {
        btnDownloadOpenApi.addEventListener("click", async () => {
            try {
                const res = await fetch(`${API_BASE}/openapi.json`, { headers: { "Accept": "application/json" } });
                if (!res.ok) throw new Error("Failed");
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "xforwarder-openapi.json";
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
                showToast(t("api.openapi_downloaded", {}, "OpenAPI 3.0 spec downloaded"), "success");
            } catch (_) {
                showToast("Failed to download OpenAPI specification", "error");
            }
        });
    }

    const tabsWrap = document.getElementById("apiDocsFilterTabs");
    if (tabsWrap) {
        tabsWrap.querySelectorAll("[data-doc-cat]").forEach((tab) => {
            tab.addEventListener("click", () => {
                tabsWrap.querySelectorAll("[data-doc-cat]").forEach((tEl) => tEl.classList.remove("active"));
                tab.classList.add("active");
                currentDocsFilter = tab.dataset.docCat || "all";
                renderApiDocsEndpoints();
            });
        });
    }
}
