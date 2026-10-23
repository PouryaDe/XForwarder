// XForwarder - Web Panel Logic (English Only)

// Dynamically compute base API prefix (supports custom security secret paths)
const basePath = window.location.pathname.replace(/\/+$/, "");
const API_BASE = basePath ? `${basePath}/api` : "/api";

let currentRules = [];
let lastRuntime = {};
let pollTimer = null;
let searchQuery = "";
let activeFilter = "all";
let currentViewMode = localStorage.getItem("xfwd_rules_view") || "cards";
let currentSort = localStorage.getItem("xfwd_rules_sort") || "port_asc";
let previousPortVal = "";
let confirmResolve = null;

// DOM Elements
const loginScreen = document.getElementById("loginScreen");
const dashboardScreen = document.getElementById("dashboardScreen");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const currentUsernameEl = document.getElementById("currentUsername");
const btnLogout = document.getElementById("btnLogout");

// Pre-populate cached username to prevent UI layout shift or text flicker
try {
    const cachedUser = localStorage.getItem("xfwd_username");
    if (cachedUser) {
        if (currentUsernameEl) currentUsernameEl.innerText = cachedUser;
        const sidebarUsername = document.getElementById("sidebarUsername");
        if (sidebarUsername) sidebarUsername.innerText = cachedUser;
    }
} catch (e) {}

const rulesContainer = document.getElementById("rulesContainer");
const ruleModal = document.getElementById("ruleModal");
const ruleForm = document.getElementById("ruleForm");
const btnOpenAddModal = document.getElementById("btnOpenAddModal");
const btnCloseModal = document.getElementById("btnCloseModal");
const btnCancelModal = document.getElementById("btnCancelModal");
const modalTitle = document.getElementById("modalTitle");

// Stats Elements
const statTotalRules = document.getElementById("statTotalRules");
const statActiveHaproxy = document.getElementById("statActiveHaproxy");
const statActiveNftables = document.getElementById("statActiveNftables");
const engineStatusBadge = document.getElementById("engineStatusBadge");

// Toolbar Elements
const searchInput = document.getElementById("searchInput");
const btnClearSearch = document.getElementById("btnClearSearch");
const filterTabs = document.querySelectorAll(".filter-tab");
const filterCountAll = document.getElementById("filterCountAll");
const filterCountP1 = document.getElementById("filterCountP1");
const filterCountP2 = document.getElementById("filterCountP2");
const filterCountDown = document.getElementById("filterCountDown");
const batchSelect = document.getElementById("batchOverrideSelect");
const selectSortRules = document.getElementById("selectSortRules");
const btnViewCards = document.getElementById("btnViewCards");
const btnViewList = document.getElementById("btnViewList");
const formCategory = document.getElementById("formCategory");
const categoryDatalist = document.getElementById("categoryDatalist");

// Header System Resource Elements
const ramText = document.getElementById("ramText");
const ramPill = document.getElementById("ramPill");
const cpuText = document.getElementById("cpuText");
const cpuPill = document.getElementById("cpuPill");
const loadText = document.getElementById("loadText");
const loadPill = document.getElementById("loadPill");
const trafficText = document.getElementById("trafficText");
const trafficPill = document.getElementById("trafficPill");
const connsText = document.getElementById("connsText");
const connsPill = document.getElementById("connsPill");
const btnManualRefresh = document.getElementById("btnManualRefresh");
const refreshIcon = document.getElementById("refreshIcon");
const pulseDot = document.getElementById("pulseDot");

// Security & Credentials Elements
const btnToggleLoginPwd = document.getElementById("btnToggleLoginPwd");
const loginPasswordInput = document.getElementById("loginPassword");
const eyeIconLogin = document.getElementById("eyeIconLogin");
const capsLockWarning = document.getElementById("capsLockWarning");
const lockoutAlert = document.getElementById("lockoutAlert");
const lockoutText = document.getElementById("lockoutText");
const lockoutTimer = document.getElementById("lockoutTimer");
const btnLogin = document.getElementById("btnLogin");
const loginUsernameInput = document.getElementById("loginUsername");

const securityModal = document.getElementById("securityModal");
const securityForm = document.getElementById("securityForm");
const btnOpenSecurityModal = document.getElementById("btnOpenSecurityModal");
const btnCloseSecurityModal = document.getElementById("btnCloseSecurityModal");
const btnCancelSecurity = document.getElementById("btnCancelSecurity");
const secCurrentPwd = document.getElementById("secCurrentPwd");
const secNewUser = document.getElementById("secNewUser");
const secNewPwd = document.getElementById("secNewPwd");
const secConfirmPwd = document.getElementById("secConfirmPwd");
const btnToggleSecPwd = document.getElementById("btnToggleSecPwd");
const eyeIconSec = document.getElementById("eyeIconSec");
const pwdStrengthContainer = document.getElementById("pwdStrengthContainer");
const pwdStrengthFill = document.getElementById("pwdStrengthFill");
const pwdStrengthLabel = document.getElementById("pwdStrengthLabel");
const securityError = document.getElementById("securityError");

let lockoutCountdownTimer = null;
const EYE_OPEN_SVG = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`;
const EYE_OFF_SVG = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>`;

// Toast helper
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type === "error" ? "toast-error" : ""}`;
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// 1-Click Clipboard Copy
function copyText(text) {
    if (!text) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(`Copied to clipboard: ${text}`);
        }).catch(() => fallbackCopy(text));
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const el = document.createElement("textarea");
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand("copy");
    document.body.removeChild(el);
    showToast(`Copied: ${text}`);
}

// Copy multi-line JSON payload to clipboard without spilling large text in toasts
function copyJsonToClipboard(jsonString, successMsg = "Configuration JSON copied to clipboard!") {
    if (!jsonString) return;
    const notify = () => showToast(successMsg, "success");
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(jsonString).then(notify).catch(() => {
            fallbackCopyRaw(jsonString);
            notify();
        });
    } else {
        fallbackCopyRaw(jsonString);
        notify();
    }
}

function fallbackCopyRaw(text) {
    const el = document.createElement("textarea");
    el.value = text;
    el.style.position = "fixed";
    el.style.opacity = "0";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    el.select();
    try {
        document.execCommand("copy");
    } catch (_) {}
    document.body.removeChild(el);
}

// Safely escape parameters passed inside inline HTML event handlers (e.g. onclick="fn(decodeURIComponent('...'))")
function safeInlineArg(str) {
    return encodeURIComponent(String(str || "")).replace(/'/g, "%27");
}

// Prepare clean sanitized rule for JSON export & import
function getSanitizedRuleForExport(rule) {
    if (!rule) return null;
    const clean = {
        name: rule.name || `Port ${rule.port}`,
        port: parseInt(rule.port, 10),
        protocol: rule.protocol || "both"
    };
    if (rule.category && String(rule.category).trim()) {
        clean.category = String(rule.category).trim();
    }
    if (rule.comment && String(rule.comment).trim()) {
        clean.comment = String(rule.comment).trim();
    }
    if (rule.force_override !== undefined && rule.force_override !== 0) {
        clean.force_override = rule.force_override;
    }
    if (rule.active_priority !== undefined) {
        clean.active_priority = rule.active_priority;
    }

    if (Array.isArray(rule.destinations)) {
        clean.destinations = rule.destinations.map(d => {
            const destPort = parseInt(d.port || rule.port, 10);
            const cd = {
                priority: d.priority || 1,
                type: d.type || "haproxy",
                target: String(d.target || "").trim(),
                port: (destPort > 0 && destPort <= 65535) ? destPort : parseInt(rule.port, 10)
            };
            if (d.proxy_protocol) cd.proxy_protocol = true;
            if (d.is_tunnel) cd.is_tunnel = true;
            if (d.tunnel_iface) cd.tunnel_iface = d.tunnel_iface;
            return cd;
        });
    }
    return clean;
}

// 1-Click Copy Individual Port Rule JSON (ready to import in another panel)
function copyRuleJson(ruleId) {
    if (!Array.isArray(currentRules)) return;
    const rule = currentRules.find(r => String(r.id || `rule-${r.port}`) === String(ruleId));
    if (!rule) {
        showToast("Port rule not found", "error");
        return;
    }
    const cleanRule = getSanitizedRuleForExport(rule);
    const exportPayload = {
        rules: [cleanRule]
    };
    const jsonStr = JSON.stringify(exportPayload, null, 2);
    copyJsonToClipboard(jsonStr, `Port :${rule.port} configuration JSON copied! Ready to import.`);
}

// 1-Click Copy Entire Category Rules JSON (ready to import in another panel)
function copyCategoryJson(catKey) {
    if (!Array.isArray(currentRules)) return;
    const isUncat = (catKey === "__uncategorized__");
    const categoryRules = currentRules.filter(r => {
        const cat = (r.category || "").trim();
        return isUncat ? !cat : cat === catKey;
    });

    if (categoryRules.length === 0) {
        showToast("No rules found in this category", "warning");
        return;
    }

    const cleanRules = categoryRules.map(getSanitizedRuleForExport);
    const exportPayload = {
        rules: cleanRules
    };
    const jsonStr = JSON.stringify(exportPayload, null, 2);
    const catName = isUncat ? "General / Uncategorized" : catKey;
    copyJsonToClipboard(jsonStr, `Category "${catName}" (${categoryRules.length} ports) JSON copied! Ready to import.`);
}

// Latency & Quality Badge Formatter (shows latency, jitter, real packet loss %, and quality score)
function formatLatencyBadge(stat) {
    if (!stat) return '';
    const isHealthy = (stat.status === 'healthy');
    const isDegraded = (stat.status === 'degraded');
    const isCritical = (stat.status === 'critical');
    const isFailed = (stat.status === 'failed' || stat.status === 'down');
    const loss = stat.packet_loss !== undefined && stat.packet_loss !== null ? parseInt(stat.packet_loss) : (isHealthy ? 0 : 100);
    const ms = parseFloat(stat.latency_ms);
    const jitter = stat.jitter_ms !== undefined && stat.jitter_ms !== null ? parseFloat(stat.jitter_ms) : null;
    const score = stat.composite_score !== undefined && stat.composite_score !== null ? stat.composite_score : null;

    let tooltipParts = [];
    if (!isNaN(ms) && ms > 0) tooltipParts.push(`Avg: ${ms} ms`);
    if (jitter !== null && !isNaN(jitter)) tooltipParts.push(`Jitter: ${jitter} ms`);
    tooltipParts.push(`Loss: ${loss}% (5m)`);
    if (score !== null) tooltipParts.push(`Score: ${score}`);
    const tooltipText = tooltipParts.join(' · ');

    if (isFailed || isCritical || (!isHealthy && !isDegraded)) {
        const badgeLabel = isCritical ? `${loss}% critical` : `${loss}% loss`;
        return `<span class="latency-pill latency-bad" title="${escapeHtml(tooltipText)}"><span class="latency-dot"></span>${badgeLabel}</span>`;
    }

    if (isNaN(ms) || ms <= 0) {
        return `<span class="latency-pill latency-good" title="${escapeHtml(tooltipText)}"><span class="latency-dot"></span>0% loss</span>`;
    }

    let cls = "latency-good";
    if (isDegraded || loss > 20 || ms > 250) cls = "latency-bad";
    else if (loss > 0 || ms > 150 || (jitter !== null && jitter > 30)) cls = "latency-medium";

    const label = isDegraded ? `${loss}% loss (Degraded)` : (loss > 0 ? `${ms} ms · ${loss}%` : `${ms} ms`);
    return `<span class="latency-pill ${cls}" title="${escapeHtml(tooltipText)}"><span class="latency-dot"></span>${label}</span>`;
}

// Concise Failure Reason Formatter
function formatConciseReason(rawReason) {
    if (!rawReason) return '';
    const r = String(rawReason).trim();
    if (/routes via WAN|WAN leak/i.test(r)) {
        const m = r.match(/\b(ens\w+|eth\w+|enp\w+|wlan\w+)\b/i);
        return m ? `WAN Leak (${m[1]})` : 'WAN Leak';
    }
    if (/missing or down/i.test(r)) return 'Interface Down';
    if (/kernel fallback/i.test(r)) return 'Invalid Device';
    if (/No route/i.test(r)) return 'No Route';
    if (/Connection refused|ECONNREFUSED/i.test(r)) return 'Conn Refused';
    if (/timed out|timeout/i.test(r)) return 'Timeout';
    if (/unreachable/i.test(r)) return 'Unreachable';
    if (r.length > 28) return r.substring(0, 26) + '...';
    return r;
}

// Security: HTML sanitization to prevent Stored XSS
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Custom Glass Confirmation Modal
function askConfirm(title, message) {
    document.getElementById("confirmTitle").innerText = title;
    document.getElementById("confirmMessage").innerText = message;
    document.getElementById("confirmModal").classList.add("show");
    return new Promise((resolve) => {
        confirmResolve = resolve;
    });
}

document.getElementById("btnCancelConfirm").onclick = () => {
    document.getElementById("confirmModal").classList.remove("show");
    if (confirmResolve) confirmResolve(false);
};

document.getElementById("btnProceedConfirm").onclick = () => {
    document.getElementById("confirmModal").classList.remove("show");
    if (confirmResolve) confirmResolve(true);
};

// Check session authentication on initial load
async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/me`);
        if (res.ok) {
            const data = await res.json();
            if (data.authenticated) {
                showDashboard(data.username);
                return;
            }
        }
    } catch (e) {}
    showLogin();
}

function showLogin() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    document.documentElement.classList.remove("pre-auth");
    try {
        localStorage.removeItem("xfwd_authenticated");
        localStorage.removeItem("xfwd_username");
    } catch (e) {}
    loginScreen.style.display = "flex";
    dashboardScreen.style.display = "none";
}

function showDashboard(username) {
    document.documentElement.classList.add("pre-auth");
    try {
        localStorage.setItem("xfwd_authenticated", "1");
        if (username) localStorage.setItem("xfwd_username", username);
    } catch (e) {}
    loginScreen.style.display = "none";
    dashboardScreen.style.display = "flex";
    if (username) {
        if (currentUsernameEl) currentUsernameEl.innerText = username;
        const sidebarUsername = document.getElementById("sidebarUsername");
        if (sidebarUsername) sidebarUsername.innerText = username;
    }
    const hash = window.location.hash.replace(/^#/, "");
    if (hash && typeof switchSection === "function") {
        switchSection(hash);
    }
    fetchStatus();
    checkImportableRules();
    if (typeof fetchSystemVersionInfo === "function") {
        fetchSystemVersionInfo(false);
    }
    if (!pollTimer) {
        pollTimer = setInterval(fetchStatus, 3000);
    }
}

// ── Smart Visibility-Aware Polling (Throttles to 15s in background, immediate refresh on return) ──
document.addEventListener("visibilitychange", () => {
    if (!dashboardScreen || dashboardScreen.style.display === "none") return;
    if (pollTimer) clearInterval(pollTimer);
    if (document.hidden) {
        pollTimer = setInterval(fetchStatus, 15000);
    } else {
        fetchStatus();
        pollTimer = setInterval(fetchStatus, 3000);
    }
});

// ── Pre-existing Relay Rules Discovery & 1-Click Import ──
async function checkImportableRules() {
    try {
        const res = await fetch(`${API_BASE}/import/discover`);
        if (!res.ok) return;
        const data = await res.json();
        const banner = document.getElementById("importBanner");
        if (!banner) return;
        if (data.available && data.count > 0) {
            const portsStr = data.ports.map(p => `:${p}`).join(", ");
            const bannerText = document.getElementById("importBannerText");
            if (bannerText) {
                const srcCounts = [];
                if (data.sources) {
                    if (data.sources.haproxy > 0) srcCounts.push(`${data.sources.haproxy} HAProxy`);
                    if (data.sources.nftables > 0) srcCounts.push(`${data.sources.nftables} NFTables`);
                }
                const srcLabel = srcCounts.length > 0 ? ` (${srcCounts.join(" + ")})` : "";
                bannerText.innerText = `Discovered ${data.count} existing forwarding port(s) on this server (${portsStr})${srcLabel}. Import them to manage failover in the dashboard.`;
            }
            banner.style.display = "flex";
        } else {
            banner.style.display = "none";
        }
    } catch (e) {}
}

const btnImportHaproxy = document.getElementById("btnImportHaproxy");
if (btnImportHaproxy) {
    btnImportHaproxy.addEventListener("click", async () => {
        btnImportHaproxy.disabled = true;
        btnImportHaproxy.innerHTML = '<span class="btn-spinner"></span> <span>Importing...</span>';
        try {
            const res = await fetch(`${API_BASE}/import/all`, { method: "POST" });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.ok) {
                showToast(`Successfully imported ${data.imported_count} relay port rules!`);
                const banner = document.getElementById("importBanner");
                if (banner) banner.style.display = "none";
                fetchStatus();
            } else {
                showToast(data.error || "Failed to import rules", "error");
            }
        } catch (e) {
            showToast("Error communicating with server", "error");
        } finally {
            btnImportHaproxy.disabled = false;
            btnImportHaproxy.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                <span>Import All Rules</span>
            `;
        }
    });
}

const btnDismissImportBanner = document.getElementById("btnDismissImportBanner");
if (btnDismissImportBanner) {
    btnDismissImportBanner.addEventListener("click", () => {
        const banner = document.getElementById("importBanner");
        if (banner) banner.style.display = "none";
    });
}

const btnDismissServicesWarning = document.getElementById("btnDismissServicesWarning");
if (btnDismissServicesWarning) {
    btnDismissServicesWarning.addEventListener("click", () => {
        sessionStorage.setItem("xfwd_dismiss_services_warning", "1");
        const banner = document.getElementById("servicesWarningBanner");
        if (banner) banner.style.display = "none";
    });
}

// ── Password Visibility Toggles ──
function setupPasswordToggle(button, input, icon) {
    if (!button || !input || !icon) return;
    button.addEventListener("click", () => {
        const isPwd = input.getAttribute("type") === "password";
        input.setAttribute("type", isPwd ? "text" : "password");
        icon.innerHTML = isPwd ? EYE_OFF_SVG : EYE_OPEN_SVG;
    });
}
setupPasswordToggle(btnToggleLoginPwd, loginPasswordInput, eyeIconLogin);
setupPasswordToggle(btnToggleSecPwd, secNewPwd, eyeIconSec);

// ── Caps Lock Detection ──
function setupCapsLockDetection(input, warningEl) {
    if (!input || !warningEl) return;
    const checkCaps = (e) => {
        if (e.getModifierState && e.getModifierState("CapsLock")) {
            warningEl.style.display = "flex";
        } else {
            warningEl.style.display = "none";
        }
    };
    input.addEventListener("keyup", checkCaps);
    input.addEventListener("keydown", checkCaps);
}
setupCapsLockDetection(loginPasswordInput, capsLockWarning);

// ── Lockout Countdown Timer ──
function startLockoutTimer(remainingSeconds) {
    if (lockoutCountdownTimer) clearInterval(lockoutCountdownTimer);
    let secondsLeft = remainingSeconds;

    loginUsernameInput.disabled = true;
    loginPasswordInput.disabled = true;
    btnLogin.disabled = true;
    lockoutAlert.style.display = "block";

    const updateDisplay = () => {
        const m = Math.floor(secondsLeft / 60);
        const s = secondsLeft % 60;
        lockoutTimer.innerText = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    };

    updateDisplay();
    lockoutCountdownTimer = setInterval(() => {
        secondsLeft--;
        if (secondsLeft <= 0) {
            clearInterval(lockoutCountdownTimer);
            lockoutCountdownTimer = null;
            lockoutAlert.style.display = "none";
            loginUsernameInput.disabled = false;
            loginPasswordInput.disabled = false;
            btnLogin.disabled = false;
            loginError.style.display = "none";
            showToast("Temporary lockout lifted. You may now attempt to log in.");
        } else {
            updateDisplay();
        }
    }, 1000);
}

// ── Password Strength Evaluator ──
function evaluatePasswordStrength(pwd) {
    if (!pwd) return { score: 0, text: "--", labelClass: "" };
    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.length >= 12) score++;
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score++;
    if (/\d/.test(pwd)) score++;
    if (/[^a-zA-Z0-9]/.test(pwd)) score++;

    if (score <= 2) {
        return { score: 1, text: "Weak", fillClass: "strength-weak", labelClass: "label-weak" };
    } else if (score <= 4) {
        return { score: 2, text: "Medium", fillClass: "strength-medium", labelClass: "label-medium" };
    } else {
        return { score: 3, text: "Strong", fillClass: "strength-strong", labelClass: "label-strong" };
    }
}

// ── Security Credentials Modal ──
if (btnOpenSecurityModal) {
    btnOpenSecurityModal.addEventListener("click", () => {
        securityForm.reset();
        securityError.style.display = "none";
        pwdStrengthContainer.style.display = "none";
        const sbUser = document.getElementById("sidebarUsername");
        secNewUser.value = (sbUser && sbUser.innerText) || (currentUsernameEl && currentUsernameEl.innerText) || "";
        securityModal.classList.add("show");
    });
}

function closeSecurityModal() {
    securityModal.classList.remove("show");
    securityForm.reset();
    securityError.style.display = "none";
}

btnCloseSecurityModal.addEventListener("click", closeSecurityModal);
btnCancelSecurity.addEventListener("click", closeSecurityModal);

secNewPwd.addEventListener("input", () => {
    const val = secNewPwd.value;
    if (!val) {
        pwdStrengthContainer.style.display = "none";
        return;
    }
    pwdStrengthContainer.style.display = "flex";
    const res = evaluatePasswordStrength(val);
    pwdStrengthFill.className = `pwd-strength-fill ${res.fillClass}`;
    pwdStrengthLabel.className = `pwd-strength-label ${res.labelClass}`;
    pwdStrengthLabel.innerText = `Strength: ${res.text}`;
});

securityForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    securityError.style.display = "none";

    const current_password = secCurrentPwd.value;
    const new_username = secNewUser.value.trim();
    const new_password = secNewPwd.value;
    const confirm_password = secConfirmPwd.value;

    if (new_password) {
        if (new_password.length < 8) {
            securityError.innerText = "New password must be at least 8 characters long";
            securityError.style.display = "block";
            return;
        }
        if (new_password !== confirm_password) {
            securityError.innerText = "New password and confirmation do not match";
            securityError.style.display = "block";
            return;
        }
    }

    const btnSaveSecurity = document.getElementById("btnSaveSecurity");
    const originalSecText = btnSaveSecurity ? btnSaveSecurity.innerText : "Update Credentials";
    if (btnSaveSecurity) {
        btnSaveSecurity.disabled = true;
        btnSaveSecurity.innerHTML = '<span class="btn-spinner"></span> <span>Updating...</span>';
    }

    try {
        const res = await fetch(`${API_BASE}/security/credentials`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                current_password,
                new_username,
                new_password
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            if (data.username) {
                if (currentUsernameEl) currentUsernameEl.innerText = data.username;
                const sbUser = document.getElementById("sidebarUsername");
                if (sbUser) sbUser.innerText = data.username;
            }
            showToast("Security credentials updated successfully!");
            closeSecurityModal();
        } else {
            securityError.innerText = data.error || "Failed to update security credentials";
            securityError.style.display = "block";
        }
    } catch (err) {
        securityError.innerText = "Network error. Please try again.";
        securityError.style.display = "block";
    } finally {
        if (btnSaveSecurity) {
            btnSaveSecurity.disabled = false;
            btnSaveSecurity.innerHTML = originalSecText;
        }
    }
});

// Login Form Submit (Hardened with Lockout & Rate-Limit Shield)
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.style.display = "none";
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;

    const originalBtnHtml = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
        <span>Sign In to Dashboard</span>
    `;

    // Immediate visual feedback to user click
    btnLogin.disabled = true;
    btnLogin.classList.add("is-loading");
    btnLogin.innerHTML = `
        <span class="btn-spinner"></span>
        <span>Authenticating...</span>
    `;

    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json().catch(() => ({}));

        if (res.ok && data.ok) {
            // Success visual confirmation
            btnLogin.classList.remove("is-loading");
            btnLogin.classList.add("is-success");
            btnLogin.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span>Authenticated! Redirecting...</span>
            `;

            if (lockoutCountdownTimer) {
                clearInterval(lockoutCountdownTimer);
                lockoutCountdownTimer = null;
            }
            lockoutAlert.style.display = "none";

            setTimeout(() => {
                btnLogin.classList.remove("is-success");
                btnLogin.disabled = false;
                btnLogin.innerHTML = originalBtnHtml;
                showDashboard(data.username);
                showToast(`Authenticated securely · Welcome, ${data.username}!`);
            }, 250);
            return;
        } else if (res.status === 429) {
            const remaining = data.remaining_seconds || 900;
            startLockoutTimer(remaining);
            loginError.innerText = data.error || "Too many failed attempts. Temporary lockout active.";
            loginError.style.display = "block";
        } else {
            loginError.innerText = data.error || "Invalid username or password";
            loginError.style.display = "block";
            // Tactile shake feedback on error
            const card = document.querySelector(".login-card");
            if (card) {
                card.classList.remove("shake-anim");
                void card.offsetWidth;
                card.classList.add("shake-anim");
            }
        }
    } catch (err) {
        loginError.innerText = "Connection error. Is the service running?";
        loginError.style.display = "block";
    } finally {
        if (!btnLogin.classList.contains("is-success")) {
            btnLogin.classList.remove("is-loading");
            btnLogin.disabled = false;
            btnLogin.innerHTML = originalBtnHtml;
        }
    }
});

// Logout
btnLogout.addEventListener("click", async () => {
    try {
        await fetch(`${API_BASE}/logout`, { method: "POST" });
    } catch (e) {}
    showLogin();
    showToast("Signed out successfully");
});

// Fetch system status from API
async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        if (res.status === 401) {
            showLogin();
            return;
        }
        if (!res.ok) throw new Error("Status fetch failed");
        const data = await res.json();

        const cfg = data.config || {};
        lastRuntime = data.runtime || {};
        currentRules = cfg.rules || [];
        updateCategoryDatalist(currentRules);

        // Reconcile pending optimistic overrides to prevent UI flicker during background polling
        const now = Date.now();
        currentRules.forEach(r => {
            const ruleId = String(r.id || `rule-${r.port}`);
            if (pendingOverrides.has(ruleId)) {
                const pending = pendingOverrides.get(ruleId);
                // Clear pending if server caught up or timeout exceeded (>6s)
                if (r.force_override === pending.force_override || (now - pending.timestamp) > 6000) {
                    pendingOverrides.delete(ruleId);
                } else {
                    // Server hasn't caught up yet: preserve optimistic state
                    r.force_override = pending.force_override;
                    if (pending.active_priority !== undefined) {
                        r.active_priority = pending.active_priority;
                    }
                    if (lastRuntime.rules_state && lastRuntime.rules_state[ruleId]) {
                        lastRuntime.rules_state[ruleId].active_priority = r.active_priority;
                    }
                }
            }
        });

        renderStats(currentRules, lastRuntime);
        renderSystemStats(data.system);
        renderServicesStatus(data.services);
        renderNetworkTopology(data.network);
        renderRules(currentRules, lastRuntime);
        trackFailoverEvents(currentRules, lastRuntime);
    } catch (err) {
        console.warn("Polling error:", err);
    }
}

let previousActivePriorities = {};
let hasInitialLog = false;

function trackFailoverEvents(rules, runtime) {
    if (!rules || rules.length === 0) return;
    if (!hasInitialLog && rules.length > 0) {
        hasInitialLog = true;
        addLogEntry("info", `Engine synced: ${rules.length} port forwarding rule(s) actively monitored.`);
    }

    rules.forEach(rule => {
        const ruleId = String(rule.id || `rule-${rule.port}`);
        const currentPrio = rule.active_priority || 1;
        const prevPrio = previousActivePriorities[ruleId];

        if (prevPrio !== undefined && prevPrio !== currentPrio) {
            if (currentPrio > prevPrio) {
                addLogEntry("fail", `Port :${rule.port} failover triggered! Cascaded from Priority ${prevPrio} to Priority ${currentPrio}`);
            } else {
                addLogEntry("probe", `Port :${rule.port} recovered! Restored to Priority ${currentPrio}`);
            }
        }
        previousActivePriorities[ruleId] = currentPrio;
    });
}

// Render Summary Metrics
function renderStats(rules, runtime) {
    statTotalRules.innerText = rules.length;
    let haproxyCount = 0;
    let nginxCount = 0;
    let nftablesCount = 0;

    let p1ActiveCount = 0;
    let p2ActiveCount = 0;
    let downCount = 0;

    const rulesState = (runtime && runtime.rules_state) ? runtime.rules_state : {};

    rules.forEach(r => {
        const activePrio = r.active_priority || 1;
        const dest = (r.destinations || []).find(d => d.priority === activePrio) || (r.destinations || [])[0];
        if (dest) {
            if (dest.type === "haproxy") haproxyCount++;
            if (dest.type === "nginx") nginxCount++;
            if (dest.type === "nftables") nftablesCount++;
        }

        const rId = String(r.id || `rule-${r.port}`);
        const rState = rulesState[rId] || {};
        const destStats = rState.dest_stats || {};
        const activeStat = destStats[`prio_${activePrio}`] || {};
        const isHealthy = (activeStat.status === 'healthy');

        if (activePrio === 1 && isHealthy) {
            p1ActiveCount++;
        } else if (activePrio > 1) {
            p2ActiveCount++;
        } else {
            downCount++;
        }
    });

    const totalProxies = haproxyCount + nginxCount;
    statActiveHaproxy.innerText = totalProxies;
    const proxyDetailEl = document.getElementById("statActiveProxyDetail");
    if (proxyDetailEl) {
        if (nginxCount > 0 && haproxyCount > 0) {
            proxyDetailEl.innerText = `${haproxyCount} HA · ${nginxCount} Nginx`;
            proxyDetailEl.style.display = "block";
            statActiveHaproxy.title = `${haproxyCount} via HAProxy, ${nginxCount} via Nginx`;
        } else if (nginxCount > 0) {
            proxyDetailEl.innerText = `${nginxCount} Nginx`;
            proxyDetailEl.style.display = "block";
            statActiveHaproxy.title = `${nginxCount} via Nginx`;
        } else {
            proxyDetailEl.style.display = "none";
            statActiveHaproxy.title = `${haproxyCount} via HAProxy`;
        }
    }
    statActiveNftables.innerText = nftablesCount;

    // Update filter badge counts
    filterCountAll.innerText = rules.length;
    filterCountP1.innerText = p1ActiveCount;
    filterCountP2.innerText = p2ActiveCount;
    filterCountDown.innerText = downCount;

    // Update nav and overview counts
    const navRulesCount = document.getElementById("navRulesCount");
    if (navRulesCount) navRulesCount.innerText = rules.length;

    const ovHaproxyCount = document.getElementById("ovHaproxyCount");
    if (ovHaproxyCount) ovHaproxyCount.innerText = `${haproxyCount} rules`;

    const ovNftablesCount = document.getElementById("ovNftablesCount");
    if (ovNftablesCount) ovNftablesCount.innerText = `${nftablesCount} rules`;

    const svcHaproxyBinds = document.getElementById("svcHaproxyBinds");
    if (svcHaproxyBinds) svcHaproxyBinds.innerText = `${haproxyCount} ports`;

    const svcNftablesBinds = document.getElementById("svcNftablesBinds");
    if (svcNftablesBinds) svcNftablesBinds.innerText = `${nftablesCount} ports`;

    const svcNginxBinds = document.getElementById("svcNginxBinds");
    if (svcNginxBinds) svcNginxBinds.innerText = `${nginxCount} ports`;

    if (runtime.active_services) {
        engineStatusBadge.innerText = "SYNCED";
        engineStatusBadge.className = "stat-badge badge-active";
    }
}

let lastSystemStats = null;
let _trafficModeRate = true;

// Render Host System Metrics (RAM %, CPU, System Load, Live Network Speed in MB/s, TCP/UDP Sockets)
function renderSystemStats(sys) {
    if (!sys) return;
    lastSystemStats = sys;

    // 1. CPU Usage
    if (sys.cpu_percent !== undefined) {
        const cpuPct = Number(sys.cpu_percent) || 0;
        if (cpuText) cpuText.textContent = `CPU: ${cpuPct}%`;
        const ovCpuText = document.getElementById("ovCpuText");
        const ovCpuBar = document.getElementById("ovCpuBar");
        if (ovCpuText) ovCpuText.innerText = `${cpuPct}%`;
        if (ovCpuBar) ovCpuBar.style.width = `${Math.min(100, Math.max(0, cpuPct))}%`;
    }

    // 2. RAM Usage (strictly percentage in topbar pill, full breakdown in tooltip)
    if (sys.ram_total_mb > 0) {
        const used = Number(sys.ram_used_mb) || 0;
        const total = Number(sys.ram_total_mb) || 0;
        const pct = Number(sys.ram_percent) || 0;
        if (ramText) ramText.innerHTML = `<span class="ram-full">RAM: ${pct}%</span><span class="ram-short">${pct}%</span>`;
        if (ramPill) ramPill.title = `Memory Usage: ${used} MB / ${total} MB (${pct}%)`;

        const ovRamText = document.getElementById("ovRamText");
        const ovRamBar = document.getElementById("ovRamBar");
        if (ovRamText) ovRamText.innerText = `${used} / ${total} MB (${pct}%)`;
        if (ovRamBar) ovRamBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
    }

    // 3. System Load Average
    if (loadText) {
        const l1 = sys.load_str || (sys.load_1 !== undefined ? Number(sys.load_1).toFixed(2) : "--");
        loadText.textContent = `Load: ${l1}`;
        if (loadPill) {
            const l5 = sys.load_5 !== undefined ? Number(sys.load_5).toFixed(2) : "--";
            const l15 = sys.load_15 !== undefined ? Number(sys.load_15).toFixed(2) : "--";
            loadPill.title = `System Load Average: ${l1} (1m), ${l5} (5m), ${l15} (15m)`;
        }
        const ovLoadText = document.getElementById("ovLoadText");
        if (ovLoadText) {
            const l5 = sys.load_5 !== undefined ? Number(sys.load_5).toFixed(2) : "--";
            const l15 = sys.load_15 !== undefined ? Number(sys.load_15).toFixed(2) : "--";
            ovLoadText.textContent = `${l1} (1m), ${l5} (5m), ${l15} (15m)`;
        }
    }

    // 4. Live Network Bandwidth (strictly download/upload speed per second in MB/s by default)
    if (trafficText) {
        function formatTrafficMB(rawMb) {
            if (rawMb === undefined || rawMb === null || isNaN(rawMb)) return "0.00";
            const num = Number(rawMb);
            if (num < 10) return num.toFixed(2);
            if (num < 100) return num.toFixed(1);
            return Math.round(num).toLocaleString();
        }

        const rawRateRx = sys.net_rx_rate_mb !== undefined ? sys.net_rx_rate_mb : (sys.net_rx_rate_kb ? sys.net_rx_rate_kb / 1024 : 0);
        const rawRateTx = sys.net_tx_rate_mb !== undefined ? sys.net_tx_rate_mb : (sys.net_tx_rate_kb ? sys.net_tx_rate_kb / 1024 : 0);
        const rRx = formatTrafficMB(rawRateRx);
        const rTx = formatTrafficMB(rawRateTx);
        const rxMb = formatTrafficMB(sys.net_rx_mb);
        const txMb = formatTrafficMB(sys.net_tx_mb);

        if (_trafficModeRate) {
            trafficText.textContent = `↓ ${rRx} MB/s · ↑ ${rTx} MB/s`;
        } else {
            trafficText.textContent = `↓ ${rxMb} MB · ↑ ${txMb} MB`;
        }

        const ovTrafficText = document.getElementById("ovTrafficText");
        if (ovTrafficText) {
            ovTrafficText.textContent = `↓ ${rRx} MB/s · ↑ ${rTx} MB/s`;
        }

        if (trafficPill) {
            const modeTip = _trafficModeRate ? "Mode: Live Speed (Click to view Total MB)" : "Mode: Total MB (Click to view Live MB/s)";
            trafficPill.title = `Live Bandwidth: ↓ ${rRx} MB/s, ↑ ${rTx} MB/s | Total Cumulative: ↓ ${rxMb} MB, ↑ ${txMb} MB (${modeTip})`;
            if (!trafficPill._hasToggle) {
                trafficPill._hasToggle = true;
                trafficPill.style.cursor = "pointer";
                trafficPill.addEventListener("click", () => {
                    _trafficModeRate = !_trafficModeRate;
                    if (lastSystemStats) renderSystemStats(lastSystemStats);
                });
            }
        }
    }

    // 5. Active Sockets (TCP & UDP)
    if (connsText) {
        const tcp = sys.tcp_connections !== undefined ? Number(sys.tcp_connections).toLocaleString() : "--";
        const udp = sys.udp_connections !== undefined ? Number(sys.udp_connections).toLocaleString() : "--";
        connsText.textContent = `${tcp} TCP · ${udp} UDP`;
        const ovConnsText = document.getElementById("ovConnsText");
        if (ovConnsText) {
            ovConnsText.textContent = `${tcp} TCP · ${udp} UDP`;
        }
        if (connsPill) {
            connsPill.title = `Active Sockets: ${tcp} TCP connections, ${udp} UDP sockets`;
        }
    }
}

// Helper to format clean, semver-focused engine versions (e.g. 2.4.30-0ubuntu0.22.04.2 -> v2.4.30)
function formatEngineVersion(rawVer) {
    if (!rawVer) return "";
    const str = String(rawVer).trim();
    const base = str.split("-")[0].trim().replace(/^v/i, "");
    return base ? `v${base}` : str;
}

// Helper to format user-friendly protocol badges ('both' -> 'TCP + UDP')
function formatProtoBadge(proto) {
    const p = String(proto || "both").toLowerCase().trim();
    if (p === "both" || p === "tcp+udp" || p === "tcp/udp") return "TCP + UDP";
    if (p === "tcp") return "TCP";
    if (p === "udp") return "UDP";
    return p.toUpperCase();
}

// Render Relay Services & Subsystems (NFTables, HAProxy, Nginx)
function renderServicesStatus(services) {
    if (!services) return;

    const nft = services.nftables || {};
    const ha = services.haproxy || {};
    const ngx = services.nginx || {};

    // 1. Top status pills
    const dotNft = document.getElementById("svcDotNft");
    const valNft = document.getElementById("svcValNft");
    if (dotNft && valNft) {
        if (!nft.installed) {
            dotNft.className = "svc-pill-dot dot-rose";
            valNft.innerText = "Not Installed";
            valNft.className = "svc-pill-val text-rose";
            valNft.title = "";
        } else if (nft.active) {
            dotNft.className = "svc-pill-dot dot-emerald";
            const nftVerShort = formatEngineVersion(nft.version);
            const verStr = nftVerShort ? ` (${nftVerShort})` : "";
            valNft.innerText = nft.table_active ? `Active & Synced${verStr}` : `Active${verStr}`;
            valNft.className = "svc-pill-val";
            valNft.title = nft.version || "";
        } else {
            dotNft.className = "svc-pill-dot dot-amber";
            valNft.innerText = "Inactive";
            valNft.className = "svc-pill-val text-muted";
            valNft.title = "";
        }
    }

    const dotHa = document.getElementById("svcDotHaproxy");
    const valHa = document.getElementById("svcValHaproxy");
    if (dotHa && valHa) {
        const haVerShort = formatEngineVersion(ha.version);
        if (!ha.installed) {
            dotHa.className = "svc-pill-dot dot-rose";
            valHa.innerText = "Not Installed";
            valHa.className = "svc-pill-val text-rose";
            valHa.title = "";
        } else if (ha.active) {
            dotHa.className = "svc-pill-dot dot-emerald";
            valHa.innerText = haVerShort ? `Running (${haVerShort})` : "Running";
            valHa.className = "svc-pill-val";
            valHa.title = ha.version || "";
        } else {
            dotHa.className = "svc-pill-dot dot-amber";
            valHa.innerText = haVerShort ? `Standby (${haVerShort})` : "Standby";
            valHa.className = "svc-pill-val text-muted";
            valHa.title = ha.version || "";
        }
    }

    const dotNgx = document.getElementById("svcDotNginx");
    const valNgx = document.getElementById("svcValNginx");
    if (dotNgx && valNgx) {
        const ngxVerShort = formatEngineVersion(ngx.version);
        if (!ngx.installed) {
            dotNgx.className = "svc-pill-dot dot-rose";
            valNgx.innerText = "Not Installed";
            valNgx.className = "svc-pill-val text-rose";
            valNgx.title = "";
        } else if (ngx.active) {
            dotNgx.className = "svc-pill-dot dot-emerald";
            valNgx.innerText = ngxVerShort ? `Running (${ngxVerShort})` : "Running";
            valNgx.className = "svc-pill-val";
            valNgx.title = ngx.version || "";
        } else {
            dotNgx.className = "svc-pill-dot dot-amber";
            valNgx.innerText = ngxVerShort ? `Standby (${ngxVerShort})` : "Standby";
            valNgx.className = "svc-pill-val text-muted";
            valNgx.title = ngx.version || "";
        }
    }

    // 2. Missing Services Warning Banner
    const warningBanner = document.getElementById("servicesWarningBanner");
    const warningText = document.getElementById("servicesWarningText");
    const missing = [];
    if (!nft.installed) missing.push("NFTables");
    if (!ha.installed) missing.push("HAProxy");
    if (!ngx.installed) missing.push("Nginx");

    if (warningBanner && warningText) {
        if (missing.length > 0 && !sessionStorage.getItem("xfwd_dismiss_services_warning")) {
            warningText.innerText = `The following core packages are missing on this server: ${missing.join(", ")}. Run 'xfwd' in your server terminal or reinstall to auto-configure them.`;
            warningBanner.style.display = "flex";
        } else {
            warningBanner.style.display = "none";
        }
    }

    // Top Relay Active Badge in 2-column header
    const topRelayBadge = document.getElementById("topRelayActiveBadge");
    if (topRelayBadge) {
        if (missing.length > 0) {
            topRelayBadge.className = "stat-badge badge-warn";
            topRelayBadge.innerText = `${3 - missing.length}/3 ACTIVE`;
        } else {
            topRelayBadge.className = "stat-badge badge-active";
            topRelayBadge.innerText = "ALL ACTIVE";
        }
    }

    // 3. Section 2 Overview Card items
    const ovNftStatus = document.getElementById("ovNftStatus");
    if (ovNftStatus) {
        const nftVerShort = formatEngineVersion(nft.version);
        if (!nft.installed) {
            ovNftStatus.innerHTML = `<span class="text-rose">Not Installed</span>`;
            ovNftStatus.title = "";
        } else if (nft.active) {
            ovNftStatus.innerHTML = `<span class="text-emerald">Active (${nftVerShort || "Installed"})</span>`;
            ovNftStatus.title = nft.version || "";
        } else {
            ovNftStatus.innerHTML = `<span class="text-amber">Inactive</span>`;
            ovNftStatus.title = "";
        }
    }

    const ovHaproxyStatus = document.getElementById("ovHaproxyStatus");
    if (ovHaproxyStatus) {
        const haVerShort = formatEngineVersion(ha.version);
        if (!ha.installed) {
            ovHaproxyStatus.innerHTML = `<span class="text-rose">Not Installed</span>`;
            ovHaproxyStatus.title = "";
        } else if (ha.active) {
            ovHaproxyStatus.innerHTML = `<span class="text-emerald">Running (${haVerShort || "v?"})</span>`;
            ovHaproxyStatus.title = ha.version || "";
        } else {
            ovHaproxyStatus.innerHTML = `<span class="text-amber">Standby (${haVerShort || "v?"})</span>`;
            ovHaproxyStatus.title = ha.version || "";
        }
    }

    const ovNginxStatus = document.getElementById("ovNginxStatus");
    if (ovNginxStatus) {
        const ngxVerShort = formatEngineVersion(ngx.version);
        if (!ngx.installed) {
            ovNginxStatus.innerHTML = `<span class="text-rose">Not Installed</span>`;
            ovNginxStatus.title = "";
        } else if (ngx.active) {
            ovNginxStatus.innerHTML = `<span class="text-emerald">Running (${ngxVerShort || "v?"})</span>`;
            ovNginxStatus.title = ngx.version || "";
        } else {
            ovNginxStatus.innerHTML = `<span class="text-amber">Standby (${ngxVerShort || "v?"})</span>`;
            ovNginxStatus.title = ngx.version || "";
        }
    }

    const ovEnginesSummaryBadge = document.getElementById("ovEnginesSummaryBadge");
    if (ovEnginesSummaryBadge) {
        if (missing.length === 0) {
            ovEnginesSummaryBadge.innerText = "ALL READY";
            ovEnginesSummaryBadge.className = "stat-badge badge-active";
        } else {
            ovEnginesSummaryBadge.innerText = `${3 - missing.length}/3 READY`;
            ovEnginesSummaryBadge.className = "stat-badge badge-warn";
        }
    }

    // 4. Section 3 Relay Services Badges & Details
    const badgeHa = document.getElementById("badgeHaproxyStatus");
    if (badgeHa) {
        if (!ha.installed) {
            badgeHa.innerText = "NOT INSTALLED";
            badgeHa.className = "stat-badge badge-fail";
        } else if (ha.active) {
            badgeHa.innerText = "RUNNING";
            badgeHa.className = "stat-badge badge-active";
        } else {
            badgeHa.innerText = "STANDBY";
            badgeHa.className = "stat-badge badge-warn";
        }
    }
    const svcHaproxyInstalled = document.getElementById("svcHaproxyInstalled");
    if (svcHaproxyInstalled) svcHaproxyInstalled.innerText = ha.installed ? "Installed" : "Not Installed";
    const svcHaproxyState = document.getElementById("svcHaproxyState");
    if (svcHaproxyState) {
        svcHaproxyState.innerText = ha.active ? "Active & Running" : (ha.installed ? "Stopped / Standby" : "Not Installed");
        svcHaproxyState.className = ha.active ? "info-value text-emerald font-mono" : "info-value text-amber font-mono";
    }
    const svcHaproxyVersion = document.getElementById("svcHaproxyVersion");
    if (svcHaproxyVersion) svcHaproxyVersion.innerText = ha.version || (ha.installed ? "Installed" : "--");

    const badgeNft = document.getElementById("badgeNftablesStatus");
    if (badgeNft) {
        if (!nft.installed) {
            badgeNft.innerText = "NOT INSTALLED";
            badgeNft.className = "stat-badge badge-fail";
        } else if (nft.active) {
            badgeNft.innerText = nft.table_active ? "ACTIVE & SYNCED" : "KERNEL READY";
            badgeNft.className = "stat-badge badge-active";
        } else {
            badgeNft.innerText = "INACTIVE";
            badgeNft.className = "stat-badge badge-warn";
        }
    }
    const svcNftablesInstalled = document.getElementById("svcNftablesInstalled");
    if (svcNftablesInstalled) svcNftablesInstalled.innerText = nft.installed ? "Installed" : "Not Installed";
    const svcNftablesKernel = document.getElementById("svcNftablesKernel");
    if (svcNftablesKernel) {
        svcNftablesKernel.innerText = nft.active ? (nft.table_active ? "Active (table ip/ip6 xfwd_orchestrator)" : "Active (Kernel ready)") : "Inactive";
        svcNftablesKernel.className = nft.active ? "info-value text-emerald font-mono" : "info-value text-amber font-mono";
    }
    const svcNftablesVersion = document.getElementById("svcNftablesVersion");
    if (svcNftablesVersion) svcNftablesVersion.innerText = nft.version || (nft.installed ? "Installed" : "--");

    const badgeNgx = document.getElementById("badgeNginxStatus");
    if (badgeNgx) {
        if (!ngx.installed) {
            badgeNgx.innerText = "NOT INSTALLED";
            badgeNgx.className = "stat-badge badge-fail";
        } else if (ngx.active) {
            badgeNgx.innerText = "RUNNING";
            badgeNgx.className = "stat-badge badge-active";
        } else {
            badgeNgx.innerText = "STANDBY";
            badgeNgx.className = "stat-badge badge-warn";
        }
    }
    const svcNginxInstalled = document.getElementById("svcNginxInstalled");
    if (svcNginxInstalled) svcNginxInstalled.innerText = ngx.installed ? "Installed" : "Not Installed";
    const svcNginxState = document.getElementById("svcNginxState");
    if (svcNginxState) {
        svcNginxState.innerText = ngx.active ? "Active & Running" : (ngx.installed ? "Stopped / Standby" : "Not Installed");
        svcNginxState.className = ngx.active ? "info-value text-emerald font-mono" : "info-value text-amber font-mono";
    }
    const svcNginxVersion = document.getElementById("svcNginxVersion");
    if (svcNginxVersion) svcNginxVersion.innerText = ngx.version || (ngx.installed ? "Installed" : "--");
}

// Render Server Network & Tunnel Topology
function renderNetworkTopology(network) {
    if (!network) return;

    // 1. Primary WAN interface tag & Server IPs
    const wanTag = document.getElementById("wanIfaceTag");
    if (wanTag) {
        wanTag.innerText = network.primary_interface || "eth0";
    }

    const serverIpsList = document.getElementById("serverIpsList");
    if (serverIpsList) {
        const ips = network.server_ips || [];
        if (ips.length === 0) {
            serverIpsList.innerHTML = `<span class="ip-pill-empty">No public WAN IP detected</span>`;
        } else {
            serverIpsList.innerHTML = ips.map(s => `
                <div class="server-ip-pill" title="Click to copy IP">
                    <span class="ip-ver-badge ${s.version === 6 ? 'ver-6' : 'ver-4'}">IPv${s.version}</span>
                    <span class="ip-address-text">${escapeHtml(s.ip)}</span>
                    <button type="button" class="btn-copy-ip" onclick="copyIpToClipboard('${escapeHtml(s.ip)}', this)" title="Copy ${escapeHtml(s.ip)}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                </div>
            `).join("");
        }
    }

    // 2. Tunnel interfaces list/grid
    const tunnelGrid = document.getElementById("tunnelGrid");
    const activeBadge = document.getElementById("netActiveTunnelsBadge");
    const rawTunnels = network.tunnel_interfaces || [];

    // Filter out Linux kernel default/fallback interfaces and container bridges
    const ignoredIfaces = new Set([
        "lo", "gre0", "gretap0", "erspan0", "tunl0", "sit0",
        "ip6tnl0", "ip6gre0", "ip6erspan0", "dummy0", "teql0"
    ]);
    const tunnels = rawTunnels.filter(t => {
        if (!t || !t.name) return false;
        const name = String(t.name).toLowerCase().trim();
        if (ignoredIfaces.has(name)) return false;
        if (name.startsWith("docker") || name.startsWith("veth") || name.startsWith("virbr") || name.startsWith("br-")) return false;
        if ((!t.ip || t.ip === "No IP assigned") && !t.peer_ip && t.state !== "UP") return false;
        return true;
    });

    if (activeBadge) {
        const onlineCount = tunnels.filter(t => t.state === "UP").length;
        activeBadge.innerText = `${tunnels.length} Tunnel${tunnels.length === 1 ? '' : 's'} (${onlineCount} Active)`;
        if (onlineCount > 0) {
            activeBadge.className = "net-pill-badge badge-active";
        } else {
            activeBadge.className = "net-pill-badge";
        }
    }

    if (tunnelGrid) {
        if (tunnels.length === 0) {
            tunnelGrid.innerHTML = `
                <div class="tunnel-empty-box">
                    <div class="tunnel-empty-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
                    </div>
                    <div>
                        <span class="empty-title">No secondary tunnel interfaces detected</span>
                        <span class="empty-sub">Tunnel interfaces (e.g. <code>ipip1</code>, <code>gre1</code>, <code>awg0</code>) will appear here automatically with real-time ping probes.</span>
                    </div>
                </div>
            `;
        } else {
            tunnelGrid.innerHTML = tunnels.map(t => {
                const isUp = t.state === "UP";
                let pingClass = "lat-down";
                let pingText = "Interface Down";
                if (isUp) {
                    if (t.reachable && t.latency_ms !== null && t.latency_ms > 0) {
                        pingClass = t.latency_ms < 60 ? "lat-good" : (t.latency_ms < 150 ? "lat-mid" : "lat-high");
                        pingText = `${t.latency_ms} ms`;
                    } else if (t.target_to_ping) {
                        pingClass = "lat-unreachable";
                        pingText = "Unreachable";
                    } else {
                        pingClass = "lat-down";
                        pingText = "No Peer Target";
                    }
                }

                return `
                    <div class="tunnel-card ${isUp ? 'is-up' : 'is-down'}">
                        <div class="tunnel-card-top">
                            <div class="tunnel-title-row">
                                <span class="tunnel-name">${escapeHtml(t.name)}</span>
                                <span class="tunnel-type-tag">${escapeHtml(t.type)}</span>
                            </div>
                            <span class="tunnel-status-pill ${isUp ? 'pill-online' : 'pill-offline'}">
                                <span class="pill-dot"></span>
                                ${t.state}
                            </span>
                        </div>
                        <div class="tunnel-body">
                            <div class="tunnel-ip-row">
                                <span class="tunnel-label">Interface IP:</span>
                                <span class="tunnel-val">${escapeHtml(t.ip)}</span>
                            </div>
                            ${t.peer_ip ? `
                            <div class="tunnel-ip-row">
                                <span class="tunnel-label">Peer Endpoint:</span>
                                <span class="tunnel-val text-cyan">${escapeHtml(t.peer_ip)}</span>
                            </div>` : ""}
                        </div>
                        <div class="tunnel-card-footer">
                            <div class="tunnel-ping-pill ${pingClass}" title="Real-time roundtrip latency probe">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                                <span>${pingText}</span>
                            </div>
                            <span class="tunnel-mtu-tag">MTU ${t.mtu || 1500}</span>
                        </div>
                    </div>
                `;
            }).join("");
        }
    }
}

function copyIpToClipboard(ipText, btnEl) {
    if (!ipText) return;
    navigator.clipboard.writeText(ipText).then(() => {
        showToast(`IP ${ipText} copied to clipboard!`, "success");
        if (btnEl) {
            const originalHtml = btnEl.innerHTML;
            btnEl.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
            setTimeout(() => { btnEl.innerHTML = originalHtml; }, 1800);
        }
    }).catch(() => {
        showToast(`Failed to copy ${ipText}`, "error");
    });
}

let lastRenderedRulesFingerprint = "";

// Helper to dynamically populate category autocompletion datalist
function updateCategoryDatalist(rules) {
    const dl = document.getElementById("categoryDatalist");
    if (!dl || !rules) return;
    const cats = new Set();
    rules.forEach(r => {
        const c = String(r.category || "").trim();
        if (c) cats.add(c);
    });
    dl.innerHTML = Array.from(cats).sort().map(c => `<option value="${escapeHtml(c)}">`).join("");
}

// Helper to sort rules based on active sort selector
function sortRulesList(rulesList, sortMode, rulesState) {
    const copy = [...rulesList];
    switch (sortMode) {
        case "port_desc":
            return copy.sort((a, b) => (Number(b.port) || 0) - (Number(a.port) || 0));
        case "date_desc":
            return copy.sort((a, b) => (Number(b.created_at) || 0) - (Number(a.created_at) || 0) || ((Number(a.port) || 0) - (Number(b.port) || 0)));
        case "date_asc":
            return copy.sort((a, b) => (Number(a.created_at) || 0) - (Number(b.created_at) || 0) || ((Number(a.port) || 0) - (Number(b.port) || 0)));
        case "status":
            return copy.sort((a, b) => {
                const aState = (rulesState[String(a.id || `rule-${a.port}`)] || {}).dest_stats || {};
                const bState = (rulesState[String(b.id || `rule-${b.port}`)] || {}).dest_stats || {};
                const aStat = aState[`prio_${a.active_priority || 1}`] || {};
                const bStat = bState[`prio_${b.active_priority || 1}`] || {};
                const aScore = aStat.status === 'healthy' ? 0 : (aStat.status ? 1 : 2);
                const bScore = bStat.status === 'healthy' ? 0 : (bStat.status ? 1 : 2);
                return aScore - bScore || ((Number(a.port) || 0) - (Number(b.port) || 0));
            });
        case "category":
            return copy.sort((a, b) => {
                const catA = String(a.category || "").toLowerCase();
                const catB = String(b.category || "").toLowerCase();
                if (!catA && catB) return 1;
                if (catA && !catB) return -1;
                const cmp = catA.localeCompare(catB);
                return cmp !== 0 ? cmp : ((Number(a.port) || 0) - (Number(b.port) || 0));
            });
        case "port_asc":
        default:
            return copy.sort((a, b) => (Number(a.port) || 0) - (Number(b.port) || 0));
    }
}

function computeRulesFingerprint(filteredRules, rulesState) {
    return filteredRules.map(r => {
        const rId = String(r.id || `rule-${r.port}`);
        const rState = rulesState[rId] || {};
        const destStats = rState.dest_stats || {};
        const destsStr = (r.destinations || []).map(d => {
            const p = d.priority || 1;
            const st = destStats[`prio_${p}`] || {};
            return `${p}:${d.type}:${d.target}:${d.port}:${d.proxy_protocol}:${d.comment || ''}:${st.status}:${st.latency_ms}:${st.jitter_ms || ''}:${st.packet_loss}:${st.composite_score || ''}:${st.reason || ''}`;
        }).join(";");
        return `${rId}|${r.port}|${r.protocol}|${r.category || ''}|${r.created_at || 0}|${r.comment || ''}|${r.active_priority}|${r.force_override}|${rState.hold_remaining || 0}|${rState.cooldown_remaining || 0}|${rState.switch_pending_seconds || 0}|${rState.candidate_priority || 0}|${rState.is_flapping || false}|${destsStr}`;
    }).join("##") + `__f:${activeFilter}__s:${searchQuery}__v:${currentViewMode}__srt:${currentSort}`;
}

// Render individual Rule Card (Card View)
function renderRuleCard(rule, rulesState) {
    const ruleId = String(rule.id || `rule-${rule.port}`);
    const encodedId = safeInlineArg(ruleId);
    const rState = rulesState[ruleId] || {};
    const destStats = rState.dest_stats || {};
    const activePriority = rule.active_priority || 1;
    const forceOverride = rule.force_override || 0;

    const sortedDests = (rule.destinations && rule.destinations.length > 0)
        ? [...rule.destinations].sort((a, b) => (a.priority || 1) - (b.priority || 1))
        : [{ priority: 1, type: 'haproxy', target: 'Not configured', port: rule.port }];

    const copyPortSvg = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;

    // Build dynamic mode buttons for testing (Auto Failover vs Force Priority)
    const modeButtonsHtml = [
        `<button type="button" class="btn-mode-pill ${forceOverride === 0 ? 'is-active auto' : ''}" onclick="handleOverrideChange(decodeURIComponent('${encodedId}'), 0)" title="Automatic Multi-Path Failover (Routes in order of healthy priorities)">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>Auto Failover</span>
        </button>`
    ];

    sortedDests.forEach(d => {
        const p = d.priority || 1;
        const isForcedThis = (forceOverride === p);
        const dType = escapeHtml(String(d.type || 'haproxy').toUpperCase());
        modeButtonsHtml.push(`
            <button type="button" class="btn-mode-pill ${isForcedThis ? 'is-active forced' : ''}" onclick="handleOverrideChange(decodeURIComponent('${encodedId}'), ${p})" title="Manually force #${p} (${dType}) for testing">
                <span class="pill-dot"></span>
                <span>Force #${p}</span>
            </button>
        `);
    });

    // Build dynamic paths list (stacked vertically by priority order)
    const pathsHtml = sortedDests.map((dest, destIndex) => {
        const prio = dest.priority || (destIndex + 1);
        const isPrimary = prio === 1;
        const isActive = prio === activePriority;
        const isFailover = isActive && !isPrimary;

        const stat = destStats[`prio_${prio}`] || {};
        const isHealthy = (stat.status === 'healthy');
        const isDown = (stat.status === 'failed' || stat.status === 'down' || (stat.packet_loss !== undefined && parseInt(stat.packet_loss) >= 100));

        let statusLabel = 'STANDBY';
        let statusClass = 'status-standby';
        if (isHealthy) {
            statusLabel = 'HEALTHY';
            statusClass = 'status-healthy';
        } else if (isDown) {
            statusLabel = 'DOWN';
            statusClass = 'status-failed';
        } else if (stat.status) {
            statusLabel = String(stat.status).toUpperCase();
        }

        const rawTarget = String(dest.target || '');
        const targetDisplay = rawTarget.includes(':') ? `[${escapeHtml(rawTarget)}]` : escapeHtml(rawTarget);
        const latencyBadge = formatLatencyBadge(stat);
        const tagClass = getPrioTagClass(prio);

        // Quick path action button
        let pathActionHtml = '';
        if (forceOverride === prio) {
            pathActionHtml = `
                <button type="button" class="btn-path-test is-forced" onclick="handleOverrideChange(decodeURIComponent('${encodedId}'), 0)" title="Currently forced manually. Click to return to Automatic Failover.">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>
                    <span>Forced</span>
                </button>
            `;
        } else if (!isActive) {
            pathActionHtml = `
                <button type="button" class="btn-path-test" onclick="handleOverrideChange(decodeURIComponent('${encodedId}'), ${prio})" title="Click to manually force #${prio} for testing">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    <span>Force #${prio}</span>
                </button>
            `;
        }

        // Concise meta text (concise reason when down, or comment)
        const fullReason = (stat.reason && isDown) ? String(stat.reason) : '';
        const conciseReason = fullReason ? formatConciseReason(fullReason) : '';
        const commentText = escapeHtml(dest.comment || '');
        let metaText = '';
        if (conciseReason) {
            const prefix = commentText ? `${commentText} · ` : '';
            metaText = `<span class="text-amber" title="${escapeHtml(fullReason)}">${prefix}${escapeHtml(conciseReason)}</span>`;
        } else if (commentText) {
            metaText = commentText;
        }

        const pathBoxClasses = ['path-box'];
        if (isActive) {
            pathBoxClasses.push(isFailover ? 'is-failover' : 'is-active');
        }
        if (isDown) {
            pathBoxClasses.push('is-down');
        }

        return `
            <div class="${pathBoxClasses.join(' ')}"
                 draggable="true"
                 ondragstart="handlePathDragStart(event, decodeURIComponent('${encodedId}'), ${destIndex})"
                 ondragover="handlePathDragOver(event, decodeURIComponent('${encodedId}'), ${destIndex})"
                 ondragleave="handlePathDragLeave(event)"
                 ondrop="handlePathDrop(event, decodeURIComponent('${encodedId}'), ${destIndex})"
                 ondragend="handlePathDragEnd(event)">
                <div class="path-header">
                    <div class="path-header-left">
                        <span class="drag-handle" title="Drag to reorder priority">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/></svg>
                        </span>
                        <span class="path-tag ${tagClass}">#${prio}</span>
                        <span class="path-status ${statusClass}">
                            <span class="status-indicator"></span>
                            ${statusLabel}
                        </span>
                    </div>
                    <div class="path-header-right">
                        <button type="button" class="btn-path-test" onclick="runLivePacketLossTest(decodeURIComponent('${encodedId}'), decodeURIComponent('${encodeURIComponent(rawTarget)}'), ${dest.port || rule.port}, '${dest.type || 'haproxy'}', this)" title="Test live ping, latency and packet loss to this destination">
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                            <span>Test Loss</span>
                        </button>
                        ${pathActionHtml}
                    </div>
                </div>
                <div class="path-dest">
                    <span>${escapeHtml(String(dest.type || 'haproxy').toUpperCase())}: ${targetDisplay}:${escapeHtml(dest.port || rule.port)}</span>
                    <button class="btn-copy" onclick="copyText(decodeURIComponent('${encodeURIComponent(rawTarget)}'))" title="Copy Destination IP">${copyPortSvg}</button>
                </div>
                <div class="path-meta">
                    <span>${metaText}</span>
                    ${latencyBadge}
                </div>
            </div>
        `;
    }).join('');

    return `
        <div class="rule-card" id="rule-card-${encodedId}">
            <div class="rule-top">
                <div class="port-badge">
                    <span class="port-num">:${escapeHtml(rule.port)}</span>
                    <button class="btn-copy" onclick="copyText(decodeURIComponent('${encodeURIComponent(rule.port)}'))" title="Copy Port Number">${copyPortSvg}</button>
                    <span class="proto-pill">${escapeHtml(formatProtoBadge(rule.protocol))}</span>
                    ${rule.category ? `<span class="rule-category-pill" title="Category: ${escapeHtml(rule.category)}"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>${escapeHtml(rule.category)}</span>` : ''}
                    ${rState.switch_pending_seconds > 0 ? `<span class="badge-pending-switch" title="Candidate P${rState.candidate_priority || ''} sustained quality advantage. Switching after streak confirmation."><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>Switch in ${rState.switch_pending_seconds}s</span>` : ''}
                    ${rState.hold_remaining > 0 ? `<span class="badge-cooldown" title="Route held stable to prevent disruption (Min Hold: 10m)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>Hold ${rState.hold_remaining}s</span>` : (rState.cooldown_remaining > 0 ? `<span class="badge-cooldown" title="Post-Critical Cooldown active"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>Cooldown ${rState.cooldown_remaining}s</span>` : '')}
                    ${rState.is_flapping ? `<span class="badge-flapping" title="Repeated route flapping detected. Cooldown extended."><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>Flap Guard</span>` : ''}
                </div>
                <div class="rule-actions">
                    <button class="btn btn-secondary btn-sm btn-rule-copy" onclick="copyRuleJson(decodeURIComponent('${encodedId}'))" title="Copy Port Configuration (JSON)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="editRule(decodeURIComponent('${encodedId}'))" title="Edit Rule">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="deleteRule(decodeURIComponent('${encodedId}'))" title="Delete Rule">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
            </div>

            <div class="rule-test-bar">
                <div class="test-bar-label">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    <span>Forwarding:</span>
                </div>
                <div class="mode-btn-group">
                    ${modeButtonsHtml.join('')}
                </div>
            </div>

            <div class="paths-grid">
                ${pathsHtml}
            </div>
        </div>
    `;
}

// Render individual Rule Row (Compact List View)
function renderRuleListRow(rule, rulesState) {
    const ruleId = String(rule.id || `rule-${rule.port}`);
    const encodedId = safeInlineArg(ruleId);
    const rState = rulesState[ruleId] || {};
    const destStats = rState.dest_stats || {};
    const activePriority = rule.active_priority || 1;
    const forceOverride = rule.force_override || 0;

    const sortedDests = (rule.destinations && rule.destinations.length > 0)
        ? [...rule.destinations].sort((a, b) => (a.priority || 1) - (b.priority || 1))
        : [{ priority: 1, type: 'haproxy', target: 'Not configured', port: rule.port }];

    const copyPortSvg = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;

    // Build concise destination path pills
    const pathsHtml = sortedDests.map((dest, idx) => {
        const prio = dest.priority || (idx + 1);
        const isActive = prio === activePriority;
        const isPrimary = prio === 1;
        const isFailover = isActive && !isPrimary;
        const stat = destStats[`prio_${prio}`] || {};
        const isHealthy = (stat.status === 'healthy');
        const isDown = (stat.status === 'failed' || stat.status === 'down' || (stat.packet_loss !== undefined && parseInt(stat.packet_loss) >= 100));

        let pillClass = 'rule-list-path-pill';
        if (isActive) pillClass += (isFailover ? ' is-failover' : ' is-active');
        if (isDown) pillClass += ' is-down';

        let latText = '';
        if (stat.latency_ms !== null && stat.latency_ms !== undefined && stat.latency_ms > 0) {
            latText = ` · ${stat.latency_ms}ms`;
        }

        const rawTarget = String(dest.target || '');
        const targetDisplay = rawTarget.includes(':') ? `[${escapeHtml(rawTarget)}]` : escapeHtml(rawTarget);

        let dotColor = '#6EE7B7';
        if (isDown) dotColor = '#FB7185';
        else if (!isHealthy) dotColor = '#FBBF6B';

        return `
            <div class="${pillClass}" title="Priority #${prio}: ${escapeHtml(String(dest.type || 'haproxy').toUpperCase())} ${targetDisplay}:${escapeHtml(dest.port || rule.port)}${latText}">
                <span style="width:7px; height:7px; border-radius:50%; background:${dotColor}; display:inline-block;"></span>
                <span style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">#${prio}</span>
                <span class="font-mono" style="color:var(--text-secondary); font-size:0.75rem;">${targetDisplay}:${escapeHtml(dest.port || rule.port)}</span>
                ${latText ? `<span class="font-mono" style="color:var(--accent-mint); font-size:0.72rem;">${latText}</span>` : ''}
                ${isActive ? `<span style="font-size:0.68rem; font-weight:700; color:${isFailover ? 'var(--accent-amber)' : 'var(--accent-mint)'}; text-transform:uppercase;">${isFailover ? 'FAILOVER' : 'ACTIVE'}</span>` : ''}
            </div>
        `;
    }).join("");

    const activeDest = sortedDests.find(d => (d.priority || 1) === activePriority) || sortedDests[0];
    const testTarget = String(activeDest ? activeDest.target : '');
    const testPort = activeDest ? (activeDest.port || rule.port) : rule.port;
    const testType = activeDest ? (activeDest.type || 'haproxy') : 'haproxy';

    return `
        <div class="rule-list-row" id="rule-card-${encodedId}">
            <div class="rule-list-left">
                <span class="rule-list-port">:${escapeHtml(rule.port)}</span>
                <button class="btn-copy" onclick="copyText(decodeURIComponent('${encodeURIComponent(rule.port)}'))" title="Copy Port">${copyPortSvg}</button>
                <span class="proto-pill">${escapeHtml(formatProtoBadge(rule.protocol))}</span>
                ${rule.category ? `<span class="rule-category-pill" title="Category: ${escapeHtml(rule.category)}"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>${escapeHtml(rule.category)}</span>` : ''}
                ${rState.switch_pending_seconds > 0 ? `<span class="badge-pending-switch" style="font-size:0.68rem; padding:2px 6px;" title="Switching to P${rState.candidate_priority || ''} in ${rState.switch_pending_seconds}s">Switch in ${rState.switch_pending_seconds}s</span>` : ''}
                ${rState.hold_remaining > 0 ? `<span class="badge-cooldown" style="font-size:0.68rem; padding:2px 6px;" title="Min Hold 10m">Hold ${rState.hold_remaining}s</span>` : (rState.cooldown_remaining > 0 ? `<span class="badge-cooldown" style="font-size:0.68rem; padding:2px 6px;">Cooldown ${rState.cooldown_remaining}s</span>` : '')}
                ${rState.is_flapping ? `<span class="badge-flapping" style="font-size:0.68rem; padding:2px 6px;">Flap</span>` : ''}
            </div>

            <div class="rule-list-mid">
                <div class="rule-list-paths">
                    ${pathsHtml}
                </div>
            </div>

            <div class="rule-list-right">
                <button type="button" class="btn-path-test" style="height:32px; padding:0 10px;" onclick="runLivePacketLossTest(decodeURIComponent('${encodedId}'), decodeURIComponent('${encodeURIComponent(testTarget)}'), ${testPort}, '${testType}', this)" title="Test live latency & packet loss">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    <span>Test</span>
                </button>
                <button class="btn btn-secondary btn-sm btn-rule-copy" onclick="copyRuleJson(decodeURIComponent('${encodedId}'))" title="Copy Port Configuration (JSON)">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                </button>
                <button class="btn btn-secondary btn-sm" onclick="editRule(decodeURIComponent('${encodedId}'))" title="Edit Rule">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                </button>
                <button class="btn btn-secondary btn-sm" onclick="deleteRule(decodeURIComponent('${encodedId}'))" title="Delete Rule">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </div>
        </div>
    `;
}

// Render Rule Cards/Rows with Filtering, Search, Sorting, and Categorization Dividers
function renderRules(rules, runtime) {
    if (draggedPathInfo !== null) {
        return; // Don't interrupt user during drag & drop priority reordering
    }

    if (!rules || rules.length === 0) {
        lastRenderedRulesFingerprint = "__empty__";
        rulesContainer.className = "rules-container";
        rulesContainer.innerHTML = `
            <div style="text-align:center;padding:48px 20px;color:var(--text-secondary);border:1px dashed var(--border-color);border-radius:14px;width:100%;grid-column:1/-1;">
                <p style="font-size:1.1rem;margin-bottom:8px;">No port forwarding rules configured yet.</p>
                <p style="font-size:0.85rem;color:var(--text-muted);">Click "Add Port Rule" above to specify your ports and priority uplinks.</p>
            </div>
        `;
        return;
    }

    const rulesState = (runtime && runtime.rules_state) ? runtime.rules_state : {};

    // Filter rules
    const filtered = rules.filter(rule => {
        const ruleId = String(rule.id || `rule-${rule.port}`).toLowerCase();
        const portStr = String(rule.port || "");
        const protoStr = String(rule.protocol || "both").toLowerCase();
        const protoSearchStr = protoStr === "both" ? "tcp udp both tcp+udp" : protoStr;
        const catStr = String(rule.category || "").toLowerCase();

        // 1. Search Query Check across ports, IDs, categories, and all destinations
        if (searchQuery) {
            const matchesBasic = 
                portStr.includes(searchQuery) ||
                ruleId.includes(searchQuery) ||
                protoSearchStr.includes(searchQuery) ||
                catStr.includes(searchQuery);
            const matchesDest = (rule.destinations || []).some(d =>
                String(d.target || "").toLowerCase().includes(searchQuery) ||
                String(d.comment || "").toLowerCase().includes(searchQuery) ||
                String(d.type || "").toLowerCase().includes(searchQuery)
            );
            if (!matchesBasic && !matchesDest) return false;
        }

        // 2. Active Tab Filter Check
        const rState = rulesState[String(rule.id || `rule-${rule.port}`)] || {};
        const destStats = rState.dest_stats || {};
        const activePriority = rule.active_priority || 1;
        const activeStat = destStats[`prio_${activePriority}`] || {};
        const activeHealthy = (activeStat.status === 'healthy');

        if (activeFilter === "p1") {
            return activePriority === 1 && activeHealthy;
        } else if (activeFilter === "p2") {
            return activePriority > 1;
        } else if (activeFilter === "down") {
            return !activeHealthy;
        }

        return true;
    });

    if (filtered.length === 0) {
        lastRenderedRulesFingerprint = `__nofilter__${activeFilter}__${searchQuery}__v:${currentViewMode}__srt:${currentSort}`;
        rulesContainer.className = "rules-container";
        rulesContainer.innerHTML = `
            <div style="text-align:center;padding:40px 20px;color:var(--text-secondary);border:1px dashed var(--border-color);border-radius:14px;width:100%;grid-column:1/-1;">
                <p style="font-size:1rem;margin-bottom:6px;">No rules matching your search or active filter.</p>
                <p style="font-size:0.8rem;color:var(--text-muted);">Try clearing the search input or switching filter tabs.</p>
            </div>
        `;
        return;
    }

    // Smart Fingerprint Check: If rules, sort, view mode, and stats haven't changed, skip DOM recreation
    const currentFingerprint = computeRulesFingerprint(filtered, rulesState);
    if (currentFingerprint === lastRenderedRulesFingerprint) {
        return;
    }
    lastRenderedRulesFingerprint = currentFingerprint;

    // Apply Sort Order
    const sorted = sortRulesList(filtered, currentSort, rulesState);

    // Check if any rule in the active set has a non-empty category
    const hasAnyCategory = sorted.some(r => Boolean((r.category || "").trim()));

    if (!hasAnyCategory) {
        // Default layout: No categories assigned. Render directly without divider headers!
        const itemsHtml = sorted.map(rule => currentViewMode === "list" ? renderRuleListRow(rule, rulesState) : renderRuleCard(rule, rulesState)).join("");
        rulesContainer.className = currentViewMode === "list" ? "rules-list-container" : "rules-container";
        rulesContainer.innerHTML = itemsHtml;
    } else {
        // Categorized layout: Group by category and render with visual divider lines!
        const groups = new Map();
        sorted.forEach(r => {
            const cat = (r.category || "").trim();
            const key = cat ? cat : "__uncategorized__";
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(r);
        });

        const sortedKeys = Array.from(groups.keys()).sort((a, b) => {
            if (a === "__uncategorized__") return 1;
            if (b === "__uncategorized__") return -1;
            return a.localeCompare(b);
        });

        rulesContainer.className = ""; // Container wraps category sections
        rulesContainer.innerHTML = sortedKeys.map(catKey => {
            const groupRules = groups.get(catKey);
            const isUncat = catKey === "__uncategorized__";
            const catTitle = isUncat ? "General / Uncategorized" : escapeHtml(catKey);
            const itemsHtml = groupRules.map(r => currentViewMode === "list" ? renderRuleListRow(r, rulesState) : renderRuleCard(r, rulesState)).join("");

            return `
                <div class="rule-category-section">
                    <div class="rule-category-header">
                        <div class="rule-category-title-group">
                            <span class="rule-category-icon">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                                </svg>
                            </span>
                            <span class="rule-category-name">${catTitle}</span>
                            <span class="rule-category-count">${groupRules.length} Port${groupRules.length === 1 ? '' : 's'}</span>
                        </div>
                        <div class="rule-category-line"></div>
                        <button type="button" class="btn-category-copy" onclick="copyCategoryJson(decodeURIComponent('${safeInlineArg(catKey)}'))" title="Copy all ports in category '${catTitle}' as JSON">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                            </svg>
                            <span>Copy Category JSON</span>
                        </button>
                    </div>
                    <div class="${currentViewMode === 'list' ? 'rules-list-container' : 'rules-container'}">
                        ${itemsHtml}
                    </div>
                </div>
            `;
        }).join("");
    }
}

// ── Drag & Drop Priority Reordering Handlers (Rules List) ──
let draggedPathInfo = null;

function handlePathDragStart(e, ruleId, index) {
    if (e.target.closest("button, .btn-copy, .btn-path-test, input, select, a")) {
        e.preventDefault();
        return;
    }
    draggedPathInfo = { ruleId, index };
    e.dataTransfer.effectAllowed = "move";
    try {
        e.dataTransfer.setData("text/plain", JSON.stringify({ ruleId, index }));
    } catch (_) {}
    const box = e.currentTarget;
    setTimeout(() => {
        if (box) box.classList.add("is-dragging");
    }, 0);
}

function handlePathDragOver(e, ruleId, index) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (!draggedPathInfo) return;
    if (draggedPathInfo.ruleId === ruleId && draggedPathInfo.index !== index) {
        const box = e.currentTarget;
        if (box && !box.classList.contains("drag-over")) {
            box.classList.add("drag-over");
        }
    }
}

function handlePathDragLeave(e) {
    const box = e.currentTarget;
    if (box && !box.contains(e.relatedTarget)) {
        box.classList.remove("drag-over");
    }
}

function handlePathDragEnd(e) {
    document.querySelectorAll(".path-box").forEach(el => {
        el.classList.remove("is-dragging");
        el.classList.remove("drag-over");
    });
    draggedPathInfo = null;
}

async function handlePathDrop(e, ruleId, toIndex) {
    e.preventDefault();
    e.stopPropagation();
    document.querySelectorAll(".path-box").forEach(el => {
        el.classList.remove("is-dragging");
        el.classList.remove("drag-over");
    });

    if (!draggedPathInfo) return;
    const fromRuleId = draggedPathInfo.ruleId;
    const fromIndex = draggedPathInfo.index;
    draggedPathInfo = null;

    if (fromRuleId !== ruleId || fromIndex === toIndex) return;

    const rule = currentRules.find(r => String(r.id || `rule-${r.port}`) === ruleId);
    if (!rule || !rule.destinations) return;

    const dests = [...rule.destinations].sort((a, b) => (a.priority || 1) - (b.priority || 1));
    if (fromIndex < 0 || toIndex < 0 || fromIndex >= dests.length || toIndex >= dests.length) return;

    const moved = dests.splice(fromIndex, 1)[0];
    dests.splice(toIndex, 0, moved);
    dests.forEach((d, i) => d.priority = i + 1);
    rule.destinations = dests;

    // Optimistic UI update
    renderRules(currentRules, lastRuntime);

    try {
        const res = await fetch(`${API_BASE}/rule`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(rule)
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Reordered: #${fromIndex + 1} ➔ #${toIndex + 1}`, "success");
            if (data.sync_errors && data.sync_errors.length > 0) {
                showSyncErrorAlert(data.sync_errors);
            }
        } else {
            showToast(data.error || "Failed to save reordered priority", "error");
        }
    } catch (err) {
        showToast("Network error reordering priority", "error");
    } finally {
        fetchStatus();
    }
}

// ── Server Sync Error Modal Diagnostics & Retry ──
const syncErrorModal = document.getElementById("syncErrorModal");
const syncErrorList = document.getElementById("syncErrorList");
const btnDismissSyncError = document.getElementById("btnDismissSyncError");
const btnRetrySyncModal = document.getElementById("btnRetrySyncModal");

function showSyncErrorAlert(errors) {
    if (!errors || errors.length === 0 || !syncErrorModal || !syncErrorList) return;
    syncErrorList.innerHTML = errors.map(err => `<div>• ${escapeHtml(err)}</div>`).join("");
    syncErrorModal.classList.add("show");
}

function closeSyncErrorModal() {
    if (syncErrorModal) syncErrorModal.classList.remove("show");
}

if (btnDismissSyncError) btnDismissSyncError.addEventListener("click", closeSyncErrorModal);

if (btnRetrySyncModal) {
    btnRetrySyncModal.addEventListener("click", async () => {
        btnRetrySyncModal.disabled = true;
        btnRetrySyncModal.innerHTML = '<span class="btn-spinner"></span> <span>Retrying Sync...</span>';
        try {
            const res = await fetch(`${API_BASE}/sync`, { method: "POST" });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.ok) {
                showToast("Server rules synchronized successfully!", "success");
                closeSyncErrorModal();
                fetchStatus();
            } else {
                if (data.sync_errors && data.sync_errors.length > 0) {
                    syncErrorList.innerHTML = data.sync_errors.map(err => `<div>• ${escapeHtml(err)}</div>`).join("");
                }
                showToast("Server sync retry failed. Check service status.", "error");
            }
        } catch (err) {
            showToast("Connection error while retrying sync", "error");
        } finally {
            btnRetrySyncModal.disabled = false;
            btnRetrySyncModal.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                <span>Retry Server Sync</span>
            `;
        }
    });
}

// Pending override tracker to protect optimistic UI updates against polling races
const pendingOverrides = new Map();

// Override change handler (Auto Failover vs Manual Test Priority)
async function handleOverrideChange(ruleId, val) {
    const prioVal = parseInt(val);

    // Track pending override with timestamp
    pendingOverrides.set(ruleId, {
        force_override: prioVal,
        active_priority: prioVal > 0 ? prioVal : undefined,
        timestamp: Date.now()
    });

    // Optimistic UI update so button doesn't remain stuck
    const rule = currentRules.find(x => x.id === ruleId);
    if (rule) {
        rule.force_override = prioVal;
        if (prioVal > 0) {
            rule.active_priority = prioVal;
        } else {
            // Auto Failover: choose lowest healthy priority from cached state, or 1
            const rState = (lastRuntime.rules_state || {})[ruleId] || {};
            const destStats = rState.dest_stats || {};
            let best = 1;
            const sorted = [...(rule.destinations || [])].sort((a, b) => (a.priority || 1) - (b.priority || 1));
            for (const d of sorted) {
                const p = d.priority || 1;
                if (destStats[`prio_${p}`] && destStats[`prio_${p}`].status === 'healthy') {
                    best = p;
                    break;
                }
            }
            rule.active_priority = best;
            const pending = pendingOverrides.get(ruleId);
            if (pending) pending.active_priority = best;
        }
        renderRules(currentRules, lastRuntime);
    }

    try {
        const res = await fetch(`${API_BASE}/override`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rule_id: ruleId, force_override: prioVal })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            if (prioVal === 0) {
                showToast("Auto failover enabled", "success");
            } else {
                showToast(`Forced #${prioVal} enabled`, "info");
            }
            if (data.sync_errors && data.sync_errors.length > 0) {
                showSyncErrorAlert(data.sync_errors);
            }
        } else {
            showToast(data.error || "Failed to update forwarding mode", "error");
            pendingOverrides.delete(ruleId);
        }
    } catch (err) {
        showToast("Failed to update forwarding mode", "error");
        pendingOverrides.delete(ruleId);
    } finally {
        await fetchStatus();
    }
}

// Emergency Batch Override Action
batchSelect.addEventListener("change", async () => {
    pendingOverrides.clear();
    const val = batchSelect.value;
    if (val === "") return;
    const modeLabels = {
        "0": "Restore All to Auto Failover",
        "1": "Force All to #1 (Primary)",
        "2": "Force All to #2 (Backup)"
    };
    const confirmed = await askConfirm(
        "Apply Emergency Batch Action?",
        `Are you sure you want to execute '${modeLabels[val]}' across ALL forwarding rules?`
    );
    if (!confirmed) {
        batchSelect.value = "";
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/override/batch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ force_override: parseInt(val) })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Applied ${modeLabels[val]} to ${data.count} rule(s)`);
            if (data.sync_errors && data.sync_errors.length > 0) {
                showSyncErrorAlert(data.sync_errors);
            }
            fetchStatus();
        } else {
            showToast(data.error || "Batch action failed", "error");
        }
    } catch (e) {
        showToast("Connection error during batch action", "error");
    }
    batchSelect.value = "";
});

// Search and Filter Listeners with 120ms Debounce
let searchDebounceTimer = null;
searchInput.addEventListener("input", () => {
    searchQuery = searchInput.value.trim().toLowerCase();
    btnClearSearch.style.display = searchQuery ? "block" : "none";
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        renderRules(currentRules, lastRuntime);
    }, 120);
});

btnClearSearch.addEventListener("click", () => {
    clearTimeout(searchDebounceTimer);
    searchInput.value = "";
    searchQuery = "";
    btnClearSearch.style.display = "none";
    renderRules(currentRules, lastRuntime);
});

filterTabs.forEach(tab => {
    tab.addEventListener("click", () => {
        filterTabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeFilter = tab.getAttribute("data-filter") || "all";
        renderRules(currentRules, lastRuntime);
    });
});

// View Mode Toggle (Cards vs Compact List)
if (btnViewCards && btnViewList) {
    function setViewMode(mode) {
        currentViewMode = mode;
        try { localStorage.setItem("xfwd_rules_view", mode); } catch (_) {}
        if (mode === "list") {
            btnViewList.classList.add("active");
            btnViewCards.classList.remove("active");
        } else {
            btnViewCards.classList.add("active");
            btnViewList.classList.remove("active");
        }
        lastRenderedRulesFingerprint = "";
        renderRules(currentRules, lastRuntime);
    }

    btnViewCards.addEventListener("click", () => setViewMode("cards"));
    btnViewList.addEventListener("click", () => setViewMode("list"));

    // Set initial button active state based on persisted preference
    if (currentViewMode === "list") {
        btnViewList.classList.add("active");
        btnViewCards.classList.remove("active");
    } else {
        btnViewCards.classList.add("active");
        btnViewList.classList.remove("active");
    }
}

// Rules Sorting
if (selectSortRules) {
    selectSortRules.value = currentSort;
    selectSortRules.addEventListener("change", () => {
        currentSort = selectSortRules.value;
        try { localStorage.setItem("xfwd_rules_sort", currentSort); } catch (_) {}
        lastRenderedRulesFingerprint = "";
        renderRules(currentRules, lastRuntime);
    });
}

// Manual Refresh with Rotation Animation
btnManualRefresh.addEventListener("click", () => {
    refreshIcon.classList.add("spinning");
    fetchStatus().finally(() => {
        setTimeout(() => refreshIcon.classList.remove("spinning"), 600);
    });
});

// ── Dynamic Multi-Priority Destination Management ──
let currentModalDestinations = [];

function getPrioTagClass(prio) {
    if (prio === 1) return "prio-tag-1";
    if (prio === 2) return "prio-tag-2";
    if (prio === 3) return "prio-tag-3";
    if (prio === 4) return "prio-tag-4";
    if (prio === 5) return "prio-tag-5";
    return "prio-tag-n";
}

function getPrioSubtitle(prio) {
    if (prio === 1) return "Standard primary path";
    if (prio === 2) return "1st failover standby path";
    if (prio === 3) return "2nd failover standby path";
    return `Priority ${prio} failover standby path`;
}

function moveDestinationRow(index, direction) {
    syncDestinationsFromDom();
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= currentModalDestinations.length) return;
    const temp = currentModalDestinations[index];
    currentModalDestinations[index] = currentModalDestinations[targetIndex];
    currentModalDestinations[targetIndex] = temp;
    currentModalDestinations.forEach((d, i) => d.priority = i + 1);
    renderDestinationsList();
}

// ── Drag & Drop Priority Reordering Handlers (Modal) ──
let draggedModalPrioIndex = null;

function handleModalPrioDragStart(e, index) {
    if (e.target.closest("input, select, textarea, button, .btn-prio-move, .btn-remove-prio")) {
        e.preventDefault();
        return;
    }
    syncDestinationsFromDom();
    draggedModalPrioIndex = index;
    e.dataTransfer.effectAllowed = "move";
    try {
        e.dataTransfer.setData("text/plain", String(index));
    } catch (_) {}
    const box = e.currentTarget;
    setTimeout(() => {
        if (box) box.classList.add("is-dragging");
    }, 0);
}

function handleModalPrioDragOver(e, index) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (draggedModalPrioIndex === null || draggedModalPrioIndex === index) return;
    const box = e.currentTarget;
    if (box && !box.classList.contains("drag-over")) {
        box.classList.add("drag-over");
    }
}

function handleModalPrioDragLeave(e) {
    const box = e.currentTarget;
    if (box && !box.contains(e.relatedTarget)) {
        box.classList.remove("drag-over");
    }
}

function handleModalPrioDragEnd(e) {
    document.querySelectorAll(".priority-box").forEach(el => {
        el.classList.remove("is-dragging");
        el.classList.remove("drag-over");
    });
    draggedModalPrioIndex = null;
}

function handleModalPrioDrop(e, toIndex) {
    e.preventDefault();
    e.stopPropagation();
    document.querySelectorAll(".priority-box").forEach(el => {
        el.classList.remove("is-dragging");
        el.classList.remove("drag-over");
    });
    if (draggedModalPrioIndex === null || draggedModalPrioIndex === toIndex) return;
    syncDestinationsFromDom();
    const fromIndex = draggedModalPrioIndex;
    draggedModalPrioIndex = null;
    if (fromIndex < 0 || fromIndex >= currentModalDestinations.length || toIndex < 0 || toIndex >= currentModalDestinations.length) return;
    const moved = currentModalDestinations.splice(fromIndex, 1)[0];
    currentModalDestinations.splice(toIndex, 0, moved);
    currentModalDestinations.forEach((d, i) => d.priority = i + 1);
    renderDestinationsList();
}

function renderDestinationRow(dest, index, totalCount) {
    const prio = index + 1;
    const isPrimary = prio === 1;
    const type = dest.type || (isPrimary ? "haproxy" : "nftables");
    const target = dest.target || "";
    const port = dest.port !== undefined && dest.port !== null ? dest.port : "";
    const comment = dest.comment || "";
    const canRemove = totalCount > 1;

    const div = document.createElement("div");
    div.className = `priority-box priority-${prio}`;
    div.dataset.index = index;
    div.draggable = true;
    div.ondragstart = (e) => handleModalPrioDragStart(e, index);
    div.ondragover = (e) => handleModalPrioDragOver(e, index);
    div.ondragleave = (e) => handleModalPrioDragLeave(e);
    div.ondrop = (e) => handleModalPrioDrop(e, index);
    div.ondragend = (e) => handleModalPrioDragEnd(e);

    const targetPlaceholder = type === "haproxy"
        ? "2001:4ba0:cafe:84e::1 (IPv6 only)"
        : (type === "nftables" ? "10.88.1.2 (IPv4) or 2001:db8::2 (IPv6)" : "1.2.3.4 or 2001:db8::1");

    div.innerHTML = `
        <div class="priority-header">
            <div class="prio-title-group">
                <span class="drag-handle" title="Drag to reorder priority">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/></svg>
                </span>
                <span class="prio-tag ${getPrioTagClass(prio)}">#${prio}</span>
                <span class="prio-sub">${isPrimary ? "Primary Path" : "Backup Path"}</span>
            </div>
            <div class="prio-header-actions">
                <button type="button" class="btn-prio-move" title="Move Priority Up" ${index === 0 ? "disabled" : ""} onclick="moveDestinationRow(${index}, -1)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>
                </button>
                <button type="button" class="btn-prio-move" title="Move Priority Down" ${index === totalCount - 1 ? "disabled" : ""} onclick="moveDestinationRow(${index}, 1)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                ${canRemove ? `
                <button type="button" class="btn-remove-prio" title="Remove this priority path" onclick="removeDestinationRow(${index})">
                    &times;
                </button>` : ""}
            </div>
        </div>
        <div class="dest-form-row">
            <div class="form-group dest-col-type">
                <label>Engine Type</label>
                <select class="form-control dest-type" onchange="handleDestTypeChange(this)">
                    <option value="haproxy" ${type === "haproxy" ? "selected" : ""}>HAProxy (IPv6)</option>
                    <option value="nginx" ${type === "nginx" ? "selected" : ""}>Nginx (Stream)</option>
                    <option value="nftables" ${type === "nftables" ? "selected" : ""}>NFTables (Kernel)</option>
                </select>
            </div>
            <div class="form-group dest-col-target">
                <label>Destination Target IP / Host</label>
                <input type="text" class="form-control dest-target" placeholder="${targetPlaceholder}" value="${escapeHtml(target)}" required>
            </div>
            <div class="form-group dest-col-port">
                <label>Target Port</label>
                <input type="number" class="form-control dest-port" placeholder="Default" min="1" max="65535" value="${escapeHtml(port)}">
            </div>
        </div>
        <div class="form-group" style="margin-bottom:10px;">
            <label>Comment / Label</label>
            <input type="text" class="form-control dest-comment" placeholder="e.g. ${isPrimary ? 'Foreign Server 1 - Primary IPv6' : 'Backup Tunnel Node ' + prio}" value="${escapeHtml(comment)}">
        </div>
        <div class="dest-extra-row">
            <label class="dest-toggle-label" title="Enable only if remote destination (e.g. Xray/V2Ray with acceptProxyProtocol) is configured to receive PROXY Protocol headers.">
                <input type="checkbox" class="dest-proxy-proto" ${dest.proxy_protocol ? "checked" : ""}>
                <span>Send PROXY Protocol v2 (Advanced)</span>
            </label>
            <div class="dest-test-group">
                <button type="button" class="btn btn-secondary btn-xs btn-test-dest" onclick="testModalDestination(${index})">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    <span>Test Target</span>
                </button>
                <span class="test-dest-result" id="testDestResult_${index}"></span>
            </div>
        </div>
    `;
    return div;
}

function handleDestTypeChange(selectEl) {
    const row = selectEl.closest(".priority-box");
    if (!row) return;
    const targetInput = row.querySelector(".dest-target");
    if (!targetInput) return;
    const val = selectEl.value;
    if (val === "haproxy") {
        targetInput.placeholder = "2001:4ba0:cafe:84e::1 (IPv6 only)";
    } else if (val === "nftables") {
        targetInput.placeholder = "10.88.1.2 (IPv4) or 2001:db8::2 (IPv6)";
    } else {
        targetInput.placeholder = "1.2.3.4 or 2001:db8::1";
    }
}

function syncDestinationsFromDom() {
    const container = document.getElementById("destinationsContainer");
    if (!container) return;
    const boxes = container.querySelectorAll(".priority-box");
    const updated = [];
    boxes.forEach((box, idx) => {
        const typeEl = box.querySelector(".dest-type");
        const targetEl = box.querySelector(".dest-target");
        const portEl = box.querySelector(".dest-port");
        const commentEl = box.querySelector(".dest-comment");
        const protoEl = box.querySelector(".dest-proxy-proto");
        updated.push({
            priority: idx + 1,
            type: typeEl ? typeEl.value : (idx === 0 ? "haproxy" : "nftables"),
            target: targetEl ? targetEl.value : "",
            port: portEl ? portEl.value : "",
            proxy_protocol: protoEl ? protoEl.checked : false,
            comment: commentEl ? commentEl.value : ""
        });
    });
    if (updated.length > 0) {
        currentModalDestinations = updated;
    }
}

async function testModalDestination(index) {
    syncDestinationsFromDom();
    const dest = currentModalDestinations[index];
    if (!dest) return;
    const target = (dest.target || "").trim().replace(/^\[|\]$/g, '');
    const listenPort = document.getElementById("formPort") ? document.getElementById("formPort").value.trim() : "";
    const port = dest.port || listenPort;
    const resEl = document.getElementById(`testDestResult_${index}`);

    if (!target) {
        showToast("Please enter a destination target IP or host", "warn");
        if (resEl) { resEl.innerHTML = '<span class="text-amber">Enter target IP</span>'; }
        return;
    }
    if ((dest.type || "haproxy") === "haproxy" && !target.includes(':')) {
        showToast("HAProxy destination target must be a valid IPv6 address", "warn");
        if (resEl) { resEl.innerHTML = '<span class="text-amber">IPv6 required for HAProxy</span>'; }
        return;
    }
    if (!port) {
        showToast("Please specify a port to test", "warn");
        if (resEl) { resEl.innerHTML = '<span class="text-amber">Enter port</span>'; }
        return;
    }

    if (resEl) {
        resEl.innerHTML = '<span class="btn-spinner" style="width:11px;height:11px;display:inline-block;vertical-align:middle;"></span> <span class="text-muted" style="font-size:0.75rem;">Probing...</span>';
    }

    try {
        const res = await fetch(`${API_BASE}/test-target`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                target: target,
                port: parseInt(port),
                type: dest.type || "haproxy",
                protocol: document.getElementById("formProto") ? document.getElementById("formProto").value : "both",
                packets: 4
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            const loss = data.packet_loss !== undefined ? data.packet_loss : (data.healthy ? 0 : 100);
            if (data.healthy) {
                const latStr = (data.latency_ms !== null && data.latency_ms !== undefined && data.latency_ms > 0) ? ` (${data.latency_ms}ms · ${loss}% loss)` : ` (${loss}% loss)`;
                if (resEl) resEl.innerHTML = `<span class="badge-probe text-emerald" style="display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;">✓ Reachable${latStr}</span>`;
                showToast(`Destination [${target}]:${port} reachable${latStr}`);
            } else {
                const reason = data.reason ? `: ${data.reason}` : "";
                if (resEl) resEl.innerHTML = `<span class="badge-fail text-rose" style="display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;" title="${escapeHtml(data.reason || '')}">✗ Unreachable (100% loss${escapeHtml(reason)})</span>`;
                showToast(`Destination [${target}]:${port} unreachable${reason}`, "error");
            }
        } else {
            const err = data.error || "Probe test failed";
            if (resEl) resEl.innerHTML = `<span class="badge-fail text-rose" style="font-size:0.75rem;">✗ ${escapeHtml(err)}</span>`;
            showToast(err, "error");
        }
    } catch (e) {
        if (resEl) resEl.innerHTML = '<span class="badge-fail text-rose" style="font-size:0.75rem;">✗ Network error</span>';
        showToast("Network error contacting server", "error");
    }
}

function renderDestinationsList() {
    const container = document.getElementById("destinationsContainer");
    if (!container) return;
    container.innerHTML = "";
    if (!currentModalDestinations || currentModalDestinations.length === 0) {
        currentModalDestinations = [
            { priority: 1, type: "haproxy", target: "", port: "", comment: "Primary Direct IPv6" },
            { priority: 2, type: "nftables", target: "", port: "", comment: "Backup Tunnel" }
        ];
    }
    currentModalDestinations.forEach((dest, idx) => {
        container.appendChild(renderDestinationRow(dest, idx, currentModalDestinations.length));
    });
}

function addDestinationRow() {
    syncDestinationsFromDom();
    const nextPrio = currentModalDestinations.length + 1;
    const listenPort = document.getElementById("formPort").value.trim();
    currentModalDestinations.push({
        priority: nextPrio,
        type: nextPrio % 2 === 0 ? "nftables" : "haproxy",
        target: "",
        port: listenPort || "",
        comment: `Backup Path #${nextPrio}`
    });
    renderDestinationsList();
}

function removeDestinationRow(index) {
    syncDestinationsFromDom();
    if (currentModalDestinations.length <= 1) {
        showToast("At least one priority destination is required", "error");
        return;
    }
    currentModalDestinations.splice(index, 1);
    renderDestinationsList();
}

const btnAddDestination = document.getElementById("btnAddDestination");
if (btnAddDestination) {
    btnAddDestination.addEventListener("click", addDestinationRow);
}

// Port Auto-Fill in Modal Form
const formPortInput = document.getElementById("formPort");
formPortInput.addEventListener("input", () => {
    const val = formPortInput.value.trim();
    const container = document.getElementById("destinationsContainer");
    if (container) {
        const portInputs = container.querySelectorAll(".dest-port");
        portInputs.forEach(input => {
            if (!input.value || input.value === previousPortVal) {
                input.value = val;
            }
        });
    }
    previousPortVal = val;
});

// Modal open/close
btnOpenAddModal.addEventListener("click", () => {
    modalTitle.innerText = "Add New Port Forwarding Rule";
    ruleForm.reset();
    previousPortVal = "";
    document.getElementById("editRuleId").value = "";
    document.getElementById("formProto").value = "both";
    if (formCategory) formCategory.value = "";
    updateCategoryDatalist(currentRules);
    currentModalDestinations = [
        { priority: 1, type: "haproxy", target: "", port: "", comment: "Primary Direct IPv6" },
        { priority: 2, type: "nftables", target: "", port: "", comment: "Backup Tunnel" }
    ];
    renderDestinationsList();
    ruleModal.classList.add("show");
});

function closeModal() {
    ruleModal.classList.remove("show");
}
btnCloseModal.addEventListener("click", closeModal);
btnCancelModal.addEventListener("click", closeModal);

// Edit Rule
function editRule(ruleId) {
    const r = currentRules.find(x => x.id === ruleId);
    if (!r) return;

    modalTitle.innerText = `Edit Port Rule :${r.port}`;
    document.getElementById("editRuleId").value = r.id;
    document.getElementById("formPort").value = r.port;
    previousPortVal = String(r.port);
    document.getElementById("formProto").value = r.protocol || "both";
    if (formCategory) formCategory.value = r.category || "";
    updateCategoryDatalist(currentRules);

    if (r.destinations && r.destinations.length > 0) {
        currentModalDestinations = JSON.parse(JSON.stringify(r.destinations)).sort((a, b) => (a.priority || 1) - (b.priority || 1));
    } else {
        currentModalDestinations = [
            { priority: 1, type: "haproxy", target: "", port: r.port, comment: "Primary Uplink" },
            { priority: 2, type: "nftables", target: "", port: r.port, comment: "Backup Tunnel" }
        ];
    }
    renderDestinationsList();
    ruleModal.classList.add("show");
}

// Delete Rule with Custom Glass Confirm Modal & Optimistic UI
async function deleteRule(ruleId) {
    const confirmed = await askConfirm(
        "Delete Port Forwarding Rule?",
        `Are you sure you want to delete forwarding rule '${ruleId}'? Routing on this port will stop immediately.`
    );
    if (!confirmed) return;

    // Optimistic UI Update: Animate out card instantly
    const cardEl = document.getElementById(`rule-card-${encodeURIComponent(ruleId)}`) || document.getElementById(`rule-card-${ruleId}`);
    if (cardEl) {
        cardEl.classList.add("is-deleting");
    }

    const previousRules = [...currentRules];
    currentRules = currentRules.filter(r => String(r.id || `rule-${r.port}`) !== ruleId);
    renderStats(currentRules, lastRuntime);

    // After animation finishes, clean up DOM node if still present
    const cleanupTimer = setTimeout(() => {
        if (cardEl && cardEl.parentNode) {
            cardEl.remove();
        }
    }, 280);

    try {
        const res = await fetch(`${API_BASE}/rule/${encodeURIComponent(ruleId)}`, { method: "DELETE" });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Rule '${ruleId}' removed`);
            if (data.sync_errors && data.sync_errors.length > 0) {
                showSyncErrorAlert(data.sync_errors);
            }
        } else {
            // Rollback on server failure
            clearTimeout(cleanupTimer);
            currentRules = previousRules;
            lastRenderedRulesFingerprint = "";
            renderRules(currentRules, lastRuntime);
            renderStats(currentRules, lastRuntime);
            showToast(data.error || "Error deleting rule", "error");
        }
    } catch (err) {
        clearTimeout(cleanupTimer);
        currentRules = previousRules;
        lastRenderedRulesFingerprint = "";
        renderRules(currentRules, lastRuntime);
        renderStats(currentRules, lastRuntime);
        showToast("Error deleting rule", "error");
    }
}

// Save Rule Form
ruleForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const port = parseInt(document.getElementById("formPort").value);
    const proto = document.getElementById("formProto").value;
    const ruleId = document.getElementById("editRuleId").value || `rule-${port}`;
    const category = (formCategory ? formCategory.value : "").trim();
    const existingRule = currentRules.find(x => x.id === ruleId);
    const createdAt = existingRule && existingRule.created_at ? existingRule.created_at : Date.now() / 1000;

    syncDestinationsFromDom();

    if (!currentModalDestinations || currentModalDestinations.length === 0) {
        showToast("At least one destination path is required", "error");
        return;
    }

    // Validate all destinations
    for (let i = 0; i < currentModalDestinations.length; i++) {
        const d = currentModalDestinations[i];
        if (!d.target || !d.target.trim()) {
            showToast(`Target IP/Host for #${i + 1} is required`, "error");
            return;
        }
        const dtype = d.type || (i === 0 ? "haproxy" : "nftables");
        const cleanTarget = d.target.trim().replace(/^\[|\]$/g, '');
        if (dtype === "haproxy" && !cleanTarget.includes(':')) {
            showToast(`HAProxy destination for #${i + 1} must be a valid IPv6 address`, "error");
            return;
        }
    }

    const payload = {
        id: ruleId,
        port: port,
        protocol: proto,
        category: category,
        created_at: createdAt,
        active_priority: 1,
        force_override: 0,
        destinations: currentModalDestinations.map((d, idx) => ({
            priority: idx + 1,
            type: d.type || (idx === 0 ? "haproxy" : "nftables"),
            target: d.target.trim().replace(/^\[|\]$/g, ''),
            port: d.port ? parseInt(d.port) : port,
            proxy_protocol: Boolean(d.proxy_protocol),
            comment: (d.comment || "").trim()
        }))
    };

    const btnSaveRule = document.getElementById("btnSaveRule");
    const originalSaveText = btnSaveRule ? btnSaveRule.innerText : "Save & Apply Changes";
    if (btnSaveRule) {
        btnSaveRule.disabled = true;
        btnSaveRule.innerHTML = '<span class="btn-spinner"></span> <span>Applying...</span>';
    }

    try {
        const res = await fetch(`${API_BASE}/rule`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast("Rule saved and applied successfully");
            closeModal();
            if (data.sync_errors && data.sync_errors.length > 0) {
                showSyncErrorAlert(data.sync_errors);
            }
            fetchStatus();
        } else {
            showToast(data.error || "Failed to save rule", "error");
        }
    } catch (err) {
        showToast("Error communicating with server", "error");
    } finally {
        if (btnSaveRule) {
            btnSaveRule.disabled = false;
            btnSaveRule.innerHTML = originalSaveText;
        }
    }
});

// ── Theme Manager (Light & Dark Mode) ──
function initTheme() {
    const saved = localStorage.getItem("xfwd_theme") || "dark";
    applyTheme(saved);
}

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
        localStorage.setItem("xfwd_theme", theme);
    } catch (e) {}
    const label = document.getElementById("themeToggleLabel");
    if (label) {
        label.innerText = (theme === "light") ? "Dark Mode" : "Light Mode";
    }
    const loginLabel = document.getElementById("loginThemeName");
    if (loginLabel) {
        loginLabel.innerText = (theme === "light") ? "Dark Mode" : "Light Mode";
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = (current === "light") ? "dark" : "light";
    applyTheme(next);
    showToast(`Switched to ${next === "light" ? "Light" : "Dark"} theme`);
}

const btnThemeToggle = document.getElementById("btnThemeToggle");
if (btnThemeToggle) btnThemeToggle.addEventListener("click", toggleTheme);

const btnHeaderThemeToggle = document.getElementById("btnHeaderThemeToggle");
if (btnHeaderThemeToggle) btnHeaderThemeToggle.addEventListener("click", toggleTheme);

const btnLoginThemeToggle = document.getElementById("btnLoginThemeToggle");
if (btnLoginThemeToggle) btnLoginThemeToggle.addEventListener("click", toggleTheme);


// ── Panel Navigation & Section Switcher ──
const SECTIONS = ["rules", "overview", "services", "security", "logs"];

function switchSection(sectionId) {
    if (!SECTIONS.includes(sectionId)) sectionId = "rules";

    // Update active nav item
    document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
        if (item.getAttribute("data-section") === sectionId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    // Update visible section
    SECTIONS.forEach(s => {
        const el = document.getElementById(`section${s.charAt(0).toUpperCase() + s.slice(1)}`);
        if (el) {
            el.style.display = (s === sectionId) ? "block" : "none";
            if (s === sectionId) el.classList.add("active");
            else el.classList.remove("active");
        }
    });

    // Update breadcrumb
    const breadcrumb = document.getElementById("breadcrumbSection");
    if (breadcrumb) {
        const titles = {
            rules: "Port Matrix",
            overview: "Overview & Health",
            services: "Relay Services",
            security: "Security & Access",
            logs: "Logs & Probes"
        };
        breadcrumb.innerText = titles[sectionId] || "Dashboard";
    }

    // Sync URL hash
    if (window.location.hash !== `#${sectionId}`) {
        history.replaceState(null, "", `#${sectionId}`);
    }

    if (sectionId === "overview" && typeof loadNetworkQualityMetrics === "function") {
        loadNetworkQualityMetrics();
    }
    if (sectionId === "security" && typeof fetchSystemVersionInfo === "function") {
        fetchSystemVersionInfo(false);
    }

    closeMobileSidebar();
}

// Mobile sidebar drawer
const sidebar = document.getElementById("sidebar");
const sidebarBackdrop = document.getElementById("sidebarBackdrop");
const btnToggleSidebar = document.getElementById("btnToggleSidebar");
const btnCloseSidebar = document.getElementById("btnCloseSidebar");

function openMobileSidebar() {
    if (sidebar) sidebar.classList.add("open");
    if (sidebarBackdrop) sidebarBackdrop.classList.add("show");
}

function closeMobileSidebar() {
    if (sidebar) sidebar.classList.remove("open");
    if (sidebarBackdrop) sidebarBackdrop.classList.remove("show");
}

if (btnToggleSidebar) btnToggleSidebar.addEventListener("click", openMobileSidebar);
if (btnCloseSidebar) btnCloseSidebar.addEventListener("click", closeMobileSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener("click", closeMobileSidebar);

// Nav items click handler
document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
    item.addEventListener("click", () => {
        const sec = item.getAttribute("data-section");
        if (sec) switchSection(sec);
        if (window.innerWidth <= 1024) {
            closeMobileSidebar();
        }
    });
});

window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace(/^#/, "");
    if (hash && SECTIONS.includes(hash)) {
        switchSection(hash);
    }
});

// Sidebar quick actions & logout
const btnSidebarLogout = document.getElementById("btnSidebarLogout");
if (btnSidebarLogout) {
    btnSidebarLogout.addEventListener("click", () => {
        if (btnLogout) btnLogout.click();
    });
}



// ── Relay Services Scanner & Importer ──
const btnScanHaproxy = document.getElementById("btnScanHaproxy");
if (btnScanHaproxy) {
    btnScanHaproxy.addEventListener("click", async () => {
        btnScanHaproxy.disabled = true;
        btnScanHaproxy.innerHTML = '<span class="btn-spinner"></span> <span>Scanning...</span>';
        const resultEl = document.getElementById("serviceDiscoveryResult");
        try {
            const res = await fetch(`${API_BASE}/import/discover`);
            if (res.ok) {
                const data = await res.json();
                if (data.available && data.count > 0) {
                    const portsStr = data.ports.map(p => `:${p}`).join(", ");
                    const srcCounts = [];
                    if (data.sources) {
                        if (data.sources.haproxy > 0) srcCounts.push(`${data.sources.haproxy} HAProxy`);
                        if (data.sources.nftables > 0) srcCounts.push(`${data.sources.nftables} NFTables`);
                    }
                    const srcLabel = srcCounts.length > 0 ? ` [${srcCounts.join(" + ")}]` : "";
                    resultEl.innerHTML = `
                        <div style="color:var(--accent-emerald); font-weight:600; margin-bottom:8px;">
                            Discovered ${data.count} existing relay rule(s) (${portsStr})${srcLabel}
                        </div>
                        <button class="btn btn-primary btn-sm" id="btnServiceImport">Import All Discovered Rules</button>
                    `;
                    const sImport = document.getElementById("btnServiceImport");
                    if (sImport) {
                        sImport.addEventListener("click", () => {
                            if (btnImportHaproxy) btnImportHaproxy.click();
                        });
                    }
                } else {
                    resultEl.innerHTML = `<span style="color:var(--accent-emerald);">All existing HAProxy and NFTables forwarding rules on this server are already managed by XForwarder.</span>`;
                }
            } else {
                resultEl.innerText = "Failed to scan server.";
            }
        } catch (e) {
            resultEl.innerText = "Error scanning server.";
        } finally {
            btnScanHaproxy.disabled = false;
            btnScanHaproxy.innerHTML = "Scan Server";
        }
    });
}

// ── Inline Security Credentials Form ──
const inlineSecurityForm = document.getElementById("inlineSecurityForm");
if (inlineSecurityForm) {
    inlineSecurityForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const currentPwd = document.getElementById("secInlineCurrentPwd").value;
        const newUser = document.getElementById("secInlineNewUser").value.trim();
        const newPwd = document.getElementById("secInlineNewPwd").value;
        const confirmPwd = document.getElementById("secInlineConfirmPwd").value;
        const errorEl = document.getElementById("secInlineError");
        const submitBtn = document.getElementById("btnSaveSecurityInline");

        errorEl.style.display = "none";

        if (newPwd && newPwd.length < 8) {
            errorEl.innerText = "New password must be at least 8 characters long";
            errorEl.style.display = "block";
            return;
        }

        if (newPwd && newPwd !== confirmPwd) {
            errorEl.innerText = "New passwords do not match";
            errorEl.style.display = "block";
            return;
        }

        if (!newUser && !newPwd) {
            errorEl.innerText = "Please specify a new username or new password to update";
            errorEl.style.display = "block";
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="btn-spinner"></span> <span>Updating...</span>';

        try {
            const res = await fetch(`${API_BASE}/security/credentials`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    current_password: currentPwd,
                    new_username: newUser || undefined,
                    new_password: newPwd || undefined
                })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.ok) {
                showToast("Credentials updated successfully! Please sign in again.");
                setTimeout(() => {
                    showLogin();
                    inlineSecurityForm.reset();
                }, 1200);
            } else {
                errorEl.innerText = data.error || "Failed to update credentials";
                errorEl.style.display = "block";
            }
        } catch (err) {
            errorEl.innerText = "Network error communicating with server";
            errorEl.style.display = "block";
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "Update Credentials";
        }
    });
}

// ── Configuration Export & Import Handlers ──
async function handleExportConfig() {
    try {
        const res = await fetch(`${API_BASE}/config/export`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.error || "Failed to export configuration", "error");
            return;
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        const disposition = res.headers.get("content-disposition");
        let filename = `xforwarder-backup-${new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14)}.json`;
        if (disposition && disposition.includes("filename=")) {
            const match = disposition.match(/filename=["']?([^"';]+)["']?/);
            if (match && match[1]) filename = match[1];
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast(`Configuration backup downloaded: ${filename}`, "success");
    } catch (e) {
        showToast("Error downloading configuration backup", "error");
    }
}

const btnExportConfig = document.getElementById("btnExportConfig");
if (btnExportConfig) btnExportConfig.addEventListener("click", handleExportConfig);

const btnExportConfigSec = document.getElementById("btnExportConfigSec");
if (btnExportConfigSec) btnExportConfigSec.addEventListener("click", handleExportConfig);

// Modal and import elements
const importConfigModal = document.getElementById("importConfigModal");
const btnOpenImportModal = document.getElementById("btnOpenImportModal");
const btnOpenImportModalSec = document.getElementById("btnOpenImportModalSec");
const btnCloseImportModal = document.getElementById("btnCloseImportModal");
const btnCancelImportModal = document.getElementById("btnCancelImportModal");
const importConfigForm = document.getElementById("importConfigForm");
const importDropzone = document.getElementById("importDropzone");
const importFileInput = document.getElementById("importFileInput");
const importPreviewBox = document.getElementById("importPreviewBox");
const importPreviewBadge = document.getElementById("importPreviewBadge");
const importPreviewFilename = document.getElementById("importPreviewFilename");
const importPreviewDetails = document.getElementById("importPreviewDetails");
const btnTogglePasteJson = document.getElementById("btnTogglePasteJson");
const pasteJsonContainer = document.getElementById("pasteJsonContainer");
const importJsonTextarea = document.getElementById("importJsonTextarea");
const btnPasteFromClipboard = document.getElementById("btnPasteFromClipboard");
const btnFormatJson = document.getElementById("btnFormatJson");
const btnClearJsonText = document.getElementById("btnClearJsonText");
const importError = document.getElementById("importError");
const btnConfirmImport = document.getElementById("btnConfirmImport");

let currentImportConfig = null;

function openImportModal() {
    if (!importConfigModal) return;
    currentImportConfig = null;
    if (importConfigForm) importConfigForm.reset();
    if (importFileInput) importFileInput.value = "";
    if (importJsonTextarea) importJsonTextarea.value = "";
    if (pasteJsonContainer) pasteJsonContainer.style.display = "none";
    if (importPreviewBox) importPreviewBox.style.display = "none";
    if (importError) {
        importError.innerText = "";
        importError.style.display = "none";
    }
    if (btnConfirmImport) btnConfirmImport.disabled = true;
    importConfigModal.classList.add("show");
}

function closeImportModal() {
    if (importConfigModal) importConfigModal.classList.remove("show");
}

if (btnOpenImportModal) btnOpenImportModal.addEventListener("click", openImportModal);
if (btnOpenImportModalSec) btnOpenImportModalSec.addEventListener("click", openImportModal);
if (btnCloseImportModal) btnCloseImportModal.addEventListener("click", closeImportModal);
if (btnCancelImportModal) btnCancelImportModal.addEventListener("click", closeImportModal);

if (btnTogglePasteJson) {
    btnTogglePasteJson.addEventListener("click", () => {
        if (!pasteJsonContainer) return;
        const isHidden = pasteJsonContainer.style.display === "none";
        pasteJsonContainer.style.display = isHidden ? "block" : "none";
        if (isHidden && importJsonTextarea) {
            setTimeout(() => importJsonTextarea.focus(), 50);
        }
    });
}

if (btnPasteFromClipboard && importJsonTextarea) {
    btnPasteFromClipboard.addEventListener("click", async () => {
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                const text = await navigator.clipboard.readText();
                if (text && text.trim()) {
                    importJsonTextarea.value = text;
                    parseAndValidateImportJson(text, "Clipboard Content");
                    showToast("JSON pasted from clipboard!", "success");
                } else {
                    showToast("Clipboard is empty", "warning");
                }
            } else {
                showToast("Press Ctrl+V to paste into the box", "info");
                importJsonTextarea.focus();
            }
        } catch (_) {
            showToast("Press Ctrl+V to paste into the box", "info");
            importJsonTextarea.focus();
        }
    });
}

if (btnFormatJson && importJsonTextarea) {
    btnFormatJson.addEventListener("click", () => {
        const val = (importJsonTextarea.value || "").trim();
        if (!val) return;
        try {
            const obj = JSON.parse(val);
            importJsonTextarea.value = JSON.stringify(obj, null, 2);
            showToast("JSON formatted!", "success");
        } catch (e) {
            showToast("Cannot format invalid JSON: " + e.message, "error");
        }
    });
}

if (btnClearJsonText && importJsonTextarea) {
    btnClearJsonText.addEventListener("click", () => {
        importJsonTextarea.value = "";
        parseAndValidateImportJson("", "");
    });
}

function parseAndValidateImportJson(rawText, sourceName) {
    if (!rawText || !rawText.trim()) {
        if (importPreviewBox) importPreviewBox.style.display = "none";
        if (btnConfirmImport) btnConfirmImport.disabled = true;
        return;
    }
    try {
        let parsed = JSON.parse(rawText);
        if (Array.isArray(parsed)) {
            parsed = { rules: parsed };
        } else if (parsed && typeof parsed === "object" && !parsed.rules && parsed.port) {
            parsed = { rules: [parsed] };
        } else if (!parsed || typeof parsed !== "object") {
            throw new Error("Configuration must be a valid JSON object or rules array");
        }

        const rules = Array.isArray(parsed.rules) ? parsed.rules : [];
        if (rules.length === 0) {
            throw new Error("No forwarding rules found in configuration payload");
        }

        const ports = [];
        for (const r of rules) {
            if (r && r.port) {
                const p = parseInt(r.port, 10);
                if (p > 0 && p <= 65535) ports.push(p);
            }
        }

        currentImportConfig = parsed;
        if (importError) {
            importError.innerText = "";
            importError.style.display = "none";
        }

        if (importPreviewBox) {
            importPreviewBox.style.display = "block";
            if (importPreviewBadge) {
                importPreviewBadge.className = "preview-badge";
                importPreviewBadge.innerText = `${rules.length} Rule(s) Ready`;
            }
            if (importPreviewFilename) importPreviewFilename.innerText = sourceName || "config.json";
            if (importPreviewDetails) {
                const portsDisplay = ports.length > 0
                    ? `<code>:${ports.slice(0, 12).join("</code>, <code>:")}${ports.length > 12 ? '... (+' + (ports.length - 12) + ' more)' : ''}</code>`
                    : "No ports";
                importPreviewDetails.innerHTML = `
                    <div><strong>Detected Rules:</strong> ${rules.length} port mapping(s)</div>
                    <div style="margin-top: 4px;"><strong>Target Ports:</strong> ${portsDisplay}</div>
                    ${parsed.wan_interface ? `<div style="margin-top: 4px;"><strong>WAN Interface:</strong> <code>${escapeHtml(parsed.wan_interface)}</code></div>` : ""}
                `;
            }
        }
        if (btnConfirmImport) btnConfirmImport.disabled = false;

    } catch (e) {
        currentImportConfig = null;
        if (importPreviewBox) importPreviewBox.style.display = "none";
        if (importError) {
            importError.innerText = `Invalid JSON: ${e.message}`;
            importError.style.display = "block";
        }
        if (btnConfirmImport) btnConfirmImport.disabled = true;
    }
}

if (importDropzone && importFileInput) {
    importDropzone.addEventListener("click", () => importFileInput.click());

    importDropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        importDropzone.classList.add("dragover");
    });

    ["dragleave", "dragend"].forEach(type => {
        importDropzone.addEventListener(type, () => importDropzone.classList.remove("dragover"));
    });

    importDropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        importDropzone.classList.remove("dragover");
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            const reader = new FileReader();
            reader.onload = (event) => parseAndValidateImportJson(event.target.result, file.name);
            reader.readAsText(file);
        }
    });

    importFileInput.addEventListener("change", function() {
        if (this.files && this.files.length > 0) {
            const file = this.files[0];
            const reader = new FileReader();
            reader.onload = (event) => parseAndValidateImportJson(event.target.result, file.name);
            reader.readAsText(file);
        }
    });
}

if (importJsonTextarea) {
    importJsonTextarea.addEventListener("input", function() {
        parseAndValidateImportJson(this.value, "Pasted JSON Content");
    });
}

if (importConfigForm) {
    importConfigForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!currentImportConfig) {
            if (importError) {
                importError.innerText = "Please select or paste a valid configuration file";
                importError.style.display = "block";
            }
            return;
        }

        const modeRadio = document.querySelector('input[name="importMode"]:checked');
        const mode = modeRadio ? modeRadio.value : "merge";

        if (btnConfirmImport) {
            btnConfirmImport.disabled = true;
            btnConfirmImport.innerHTML = '<span class="btn-spinner"></span> <span>Applying...</span>';
        }
        if (importError) importError.style.display = "none";

        try {
            const res = await fetch(`${API_BASE}/config/import`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    mode: mode,
                    config: currentImportConfig
                })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.ok) {
                showToast(`Successfully imported ${data.imported_count} rule(s) (${data.mode} mode)! Pre-restore backup saved.`);
                closeImportModal();
                fetchStatus();
            } else {
                if (importError) {
                    importError.innerText = data.error || "Failed to import configuration";
                    importError.style.display = "block";
                }
            }
        } catch (err) {
            if (importError) {
                importError.innerText = "Network error communicating with server";
                importError.style.display = "block";
            }
        } finally {
            if (btnConfirmImport) {
                btnConfirmImport.disabled = false;
                btnConfirmImport.innerHTML = `
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                    <span>Import & Apply</span>
                `;
            }
        }
    });
}


// ── Real-time Failover & Probe Logs Stream ──
let logFeedActive = true;
const logConsole = document.getElementById("logConsole");
const logSearchInput = document.getElementById("logSearchInput");
const btnClearLogs = document.getElementById("btnClearLogs");
const btnToggleLogFeed = document.getElementById("btnToggleLogFeed");
const logFeedText = document.getElementById("logFeedText");

function addLogEntry(type, message) {
    if (!logConsole || !logFeedActive) return;

    const timeStr = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.className = `log-entry log-entry-${type}`;

    let badgeClass = "badge-info";
    let badgeText = "INFO";
    if (type === "probe") { badgeClass = "badge-probe"; badgeText = "PROBE"; }
    else if (type === "fail") { badgeClass = "badge-fail"; badgeText = "FAILOVER"; }
    else if (type === "warn") { badgeClass = "badge-warn"; badgeText = "WARN"; }

    entry.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        <span class="log-badge ${badgeClass}">${badgeText}</span>
        <span class="log-msg">${escapeHtml(message)}</span>
    `;

    logConsole.prepend(entry);

    while (logConsole.children.length > 150) {
        logConsole.removeChild(logConsole.lastChild);
    }
}

function appendLogEntry(type, message) {
    addLogEntry(type, message);
}


if (btnClearLogs) {
    btnClearLogs.addEventListener("click", () => {
        if (logConsole) {
            logConsole.innerHTML = `
                <div class="log-entry log-entry-info">
                    <span class="log-time">[System]</span>
                    <span class="log-badge badge-info">INFO</span>
                    <span class="log-msg">Logs cleared. Monitoring continues.</span>
                </div>
            `;
        }
    });
}

if (btnToggleLogFeed) {
    btnToggleLogFeed.addEventListener("click", () => {
        logFeedActive = !logFeedActive;
        if (logFeedText) {
            logFeedText.innerText = logFeedActive ? "Live Feed Active" : "Feed Paused";
        }
        btnToggleLogFeed.className = `btn btn-sm ${logFeedActive ? "btn-primary" : "btn-secondary"}`;
    });
}

if (logSearchInput) {
    logSearchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!logConsole) return;
        const entries = logConsole.querySelectorAll(".log-entry");
        entries.forEach(entry => {
            const text = entry.innerText.toLowerCase();
            entry.style.display = (!query || text.includes(query)) ? "flex" : "none";
        });
    });
}

// ── Live On-Demand Packet Loss Test Handler (Rule Cards) ──
async function runLivePacketLossTest(encodedRuleId, rawTarget, port, destType, btnEl) {
    const cleanTarget = (rawTarget || "").trim().replace(/^\[|\]$/g, '');
    if (!cleanTarget) {
        showToast("Invalid destination target host or IP", "warn");
        return;
    }
    const originalHtml = btnEl ? btnEl.innerHTML : "";
    if (btnEl) {
        btnEl.classList.add("is-testing");
        btnEl.disabled = true;
        btnEl.innerHTML = `<span class="btn-spinner" style="width:10px;height:10px;display:inline-block;vertical-align:middle;"></span> <span>Testing 50 Probes (~10s)...</span>`;
    }

    try {
        const res = await fetch(`${API_BASE}/test-loss`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                target: cleanTarget,
                port: parseInt(port || 443)
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            const loss = data.packet_loss !== undefined ? data.packet_loss : (data.healthy ? 0 : 100);
            const lat = data.latency_ms !== null && data.latency_ms !== undefined ? `${data.latency_ms}ms` : "";
            const pkts = `${data.packets_received || 0}/${data.packets_sent || 50} pkts`;
            if (data.healthy && loss === 0) {
                showToast(`✓ [${cleanTarget}] 50 probes: ${lat} · 0% loss (${pkts})`, "info");
                if (btnEl) {
                    btnEl.classList.remove("is-testing");
                    btnEl.classList.add("is-success");
                    btnEl.innerHTML = `<span>✓ ${lat || '0% loss'} (50 pkts)</span>`;
                }
                addLogEntry("probe", `[Loss Test 50-Probe] [${cleanTarget}] Clean — Latency: ${lat}, 0% loss (${pkts})`);
            } else if (data.healthy && loss > 0) {
                showToast(`⚠ [${cleanTarget}] 50 probes: ${lat} · ${loss}% loss (${pkts})`, "warn");
                if (btnEl) {
                    btnEl.classList.remove("is-testing");
                    btnEl.classList.add("is-fail");
                    btnEl.innerHTML = `<span>⚠ ${lat} · ${loss}% loss</span>`;
                }
                addLogEntry("warn", `[Loss Test 50-Probe] [${cleanTarget}] Degraded — Latency: ${lat}, ${loss}% loss (${pkts})`);
            } else {
                const reason = data.error || data.reason ? ` (${data.error || data.reason})` : "";
                showToast(`✗ [${cleanTarget}] Unreachable · 100% loss${reason}`, "error");
                if (btnEl) {
                    btnEl.classList.remove("is-testing");
                    btnEl.classList.add("is-fail");
                    btnEl.innerHTML = `<span>✗ 100% loss</span>`;
                }
                addLogEntry("fail", `[Loss Test 50-Probe] [${cleanTarget}] Unreachable — 100% loss${reason}`);
            }
            if (typeof loadNetworkQualityMetrics === 'function') {
                loadNetworkQualityMetrics();
            }
        } else {
            showToast(data.error || "Packet loss test failed", "error");
            if (btnEl) {
                btnEl.classList.remove("is-testing");
                btnEl.innerHTML = originalHtml;
            }
        }
    } catch (err) {
        console.error("runLivePacketLossTest error:", err);
        showToast("Network error executing packet loss test", "error");
        if (btnEl) {
            btnEl.classList.remove("is-testing");
            btnEl.innerHTML = originalHtml;
        }
    } finally {
        if (btnEl) btnEl.disabled = false;
        setTimeout(() => {
            if (btnEl) {
                btnEl.classList.remove("is-success", "is-fail", "is-testing");
                btnEl.innerHTML = originalHtml;
            }
        }, 5500);
    }
}

// ── Instant Live Packet Loss Diagnostic Tool (Logs Section) ──
function initDiagPacketLossTool() {
    const btnRun = document.getElementById("btnRunDiagTest");
    const targetInput = document.getElementById("diagTargetInput");
    const portInput = document.getElementById("diagPortInput");
    const packetsSelect = document.getElementById("diagPacketsSelect");
    const protoSelect = document.getElementById("diagProtoSelect");
    const resultBox = document.getElementById("diagResultContainer");

    if (!btnRun || !targetInput) return;

    btnRun.addEventListener("click", async () => {
        const target = targetInput.value.trim().replace(/^\[|\]$/g, '');
        const port = parseInt(portInput.value || "443");
        const packets = parseInt(packetsSelect.value || "50");
        const proto = protoSelect.value || "both";

        if (!target) {
            showToast("Please enter target IP or hostname to test", "warn");
            targetInput.focus();
            return;
        }

        const originalBtnHtml = btnRun.innerHTML;
        btnRun.disabled = true;
        const isStandard50 = (packets === 50);
        btnRun.innerHTML = isStandard50
            ? `<span class="btn-spinner" style="width:12px;height:12px;display:inline-block;vertical-align:middle;"></span> <span>Testing 50 Probes (~10s)...</span>`
            : `<span class="btn-spinner" style="width:12px;height:12px;display:inline-block;vertical-align:middle;"></span> <span>Sending ${packets} Probes...</span>`;

        if (resultBox) {
            resultBox.style.display = "block";
            resultBox.innerHTML = `<span class="text-muted" style="font-size:0.82rem;"><span class="btn-spinner" style="width:11px;height:11px;display:inline-block;vertical-align:middle;"></span> Measuring 50-probe ping & latency to [${escapeHtml(target)}] with 0.2s interval...</span>`;
        }

        try {
            const endpoint = isStandard50 ? `${API_BASE}/test-loss` : `${API_BASE}/test-target`;
            const payload = isStandard50
                ? { target: target, port: port }
                : { target: target, port: port, type: "haproxy", protocol: proto, packets: packets };

            const res = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.ok) {
                const loss = data.packet_loss !== undefined ? data.packet_loss : (data.healthy ? 0 : 100);
                const lat = data.latency_ms !== null && data.latency_ms !== undefined ? `${data.latency_ms} ms` : "N/A";
                const sent = data.packets_sent || packets;
                const rec = data.packets_received !== undefined ? data.packets_received : (data.healthy ? packets : 0);
                const isHealthy = data.healthy;
                const lossClass = loss === 0 ? "text-emerald" : (loss <= 20 ? "text-amber" : "text-rose");
                const statusBadge = isHealthy ? `<span class="latency-pill latency-good">HEALTHY</span>` : `<span class="latency-pill latency-bad">UNREACHABLE</span>`;

                resultBox.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            ${statusBadge}
                            <span class="font-mono" style="font-size:0.9rem; font-weight:700;">[${escapeHtml(target)}]:${port}</span>
                        </div>
                        <span style="font-size:0.75rem; color:var(--text-muted);">${new Date().toLocaleTimeString()}</span>
                    </div>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <div class="loss-stat-pill">
                            <span style="color:var(--text-muted);">Packet Loss:</span>
                            <span class="${lossClass}" style="font-weight:700;">${loss}%</span>
                        </div>
                        <div class="loss-stat-pill">
                            <span style="color:var(--text-muted);">Round-Trip Latency:</span>
                            <span class="text-cyan font-mono" style="font-weight:700;">${lat}</span>
                        </div>
                        <div class="loss-stat-pill">
                            <span style="color:var(--text-muted);">Packets:</span>
                            <span class="font-mono">${rec} / ${sent} received</span>
                        </div>
                    </div>
                    ${data.reason || data.error ? `<div style="margin-top:8px; font-size:0.75rem; color:var(--accent-rose);">${escapeHtml(data.reason || data.error)}</div>` : ''}
                `;

                if (isHealthy) {
                    showToast(`✓ [${target}] — ${lat}, ${loss}% loss (${rec}/${sent})`, loss === 0 ? "info" : "warn");
                    addLogEntry("probe", `[Diagnostic Test] [${target}] — Latency: ${lat}, Loss: ${loss}%, Received: ${rec}/${sent}`);
                } else {
                    showToast(`✗ [${target}] — 100% packet loss`, "error");
                    addLogEntry("fail", `[Diagnostic Test] [${target}] — Unreachable (100% loss) ${data.reason || data.error || ''}`);
                }
                if (typeof loadNetworkQualityMetrics === 'function') {
                    loadNetworkQualityMetrics();
                }
            } else {
                resultBox.innerHTML = `<span class="text-rose" style="font-size:0.82rem;">✗ Test failed: ${escapeHtml(data.error || 'Server error')}</span>`;
                showToast(data.error || "Diagnostic test failed", "error");
            }
        } catch (e) {
            resultBox.innerHTML = `<span class="text-rose" style="font-size:0.82rem;">✗ Network error contacting server</span>`;
            showToast("Network error contacting server", "error");
        } finally {
            btnRun.disabled = false;
            btnRun.innerHTML = originalBtnHtml;
        }
    });
}

// ── Network Quality & Disruption Timeline Subsystem ──
let currentMetricsRange = "24h";
let currentMetricsTarget = "all";
let isMetricsLoading = false;

function initNetworkQualityMonitor() {
    const targetSelect = document.getElementById("metricsTargetSelect");
    const rangeTabs = document.querySelectorAll(".btn-range-tab");
    const btnTrigger = document.getElementById("btnTriggerMetricsRound");

    if (targetSelect) {
        targetSelect.addEventListener("change", (e) => {
            currentMetricsTarget = e.target.value;
            loadNetworkQualityMetrics();
        });
    }

    if (rangeTabs) {
        rangeTabs.forEach(tab => {
            tab.addEventListener("click", () => {
                rangeTabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
                currentMetricsRange = tab.getAttribute("data-range") || "24h";
                const label = document.getElementById("timelineRangeLabel");
                if (label) {
                    const map = { "24h": "Past 24 Hours", "7d": "Past 7 Days", "30d": "Past 30 Days" };
                    label.innerText = map[currentMetricsRange] || "Custom Range";
                }
                loadNetworkQualityMetrics();
            });
        });
    }

    if (btnTrigger) {
        btnTrigger.addEventListener("click", async () => {
            const originalHtml = btnTrigger.innerHTML;
            btnTrigger.disabled = true;
            btnTrigger.innerHTML = `<span class="btn-spinner" style="width:10px;height:10px;display:inline-block;vertical-align:middle;"></span> <span>Running...</span>`;
            showToast("Executing 50-probe test round across unique targets...", "info");
            try {
                const res = await fetch(`${API_BASE}/metrics/trigger-round`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" }
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data.ok) {
                    showToast(`Round complete! Tested ${data.count || 0} unique target(s).`, "info");
                    loadNetworkQualityMetrics();
                } else {
                    showToast(data.error || "Failed to trigger round", "error");
                }
            } catch (err) {
                showToast("Network error triggering test round", "error");
            } finally {
                btnTrigger.disabled = false;
                btnTrigger.innerHTML = originalHtml;
            }
        });
    }

    loadNetworkQualityMetrics();
    setInterval(loadNetworkQualityMetrics, 60000);
}

async function loadNetworkQualityMetrics() {
    if (isMetricsLoading) return;
    isMetricsLoading = true;

    try {
        const query = `?target=${encodeURIComponent(currentMetricsTarget)}&range=${currentMetricsRange}`;
        const res = await fetch(`${API_BASE}/metrics/loss-history${query}`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.ok) return;

        // 1. Populate Target Dropdown
        const targetSelect = document.getElementById("metricsTargetSelect");
        if (targetSelect && data.targets) {
            const prevVal = targetSelect.value || currentMetricsTarget;
            let optionsHtml = '<option value="all">All Tracked Targets</option>';
            data.targets.forEach(t => {
                const sel = (t === prevVal) ? 'selected' : '';
                optionsHtml += `<option value="${escapeHtml(t)}" ${sel}>${escapeHtml(t)}</option>`;
            });
            targetSelect.innerHTML = optionsHtml;
        }

        // 2. Render KPIs
        const sum = data.summary || {};
        const qEl = document.getElementById("metricKpiQuality");
        const probEl = document.getElementById("metricKpiProbes");
        const latEl = document.getElementById("metricKpiLatency");
        const lossEl = document.getElementById("metricKpiLoss");
        const peakEl = document.getElementById("metricKpiPeak");
        const disEl = document.getElementById("metricKpiDisruptions");
        const disSubEl = document.getElementById("metricKpiDisruptionSub");

        if (qEl) {
            const q = sum.quality_pct !== undefined ? sum.quality_pct : 100;
            qEl.innerText = `${q}%`;
            qEl.className = "kpi-value font-mono " + (q >= 98 ? "text-emerald" : (q >= 85 ? "text-amber" : "text-rose"));
        }
        if (probEl) probEl.innerText = `${sum.total_probes || 0} probes analyzed`;
        if (latEl) latEl.innerText = `${sum.avg_latency_ms || 0} ms`;
        if (lossEl) lossEl.innerText = `${sum.avg_loss_pct || 0}%`;
        if (peakEl) peakEl.innerText = `Peak: ${sum.peak_loss_pct || 0}%`;
        if (disEl) {
            const dCount = sum.disruption_count || 0;
            disEl.innerText = dCount;
            disEl.className = "kpi-value font-mono " + (dCount === 0 ? "text-emerald" : (dCount <= 3 ? "text-amber" : "text-rose"));
        }
        if (disSubEl) {
            disSubEl.innerText = `${sum.disrupted_probes || 0} disrupted event(s)`;
        }

        // Top Stats Grid Card Sync
        const statQ = document.getElementById("statNetworkQuality");
        const statLossSub = document.getElementById("statLossSubtext");
        const statIcon = document.getElementById("statLossIcon");
        if (statQ) {
            const q = sum.quality_pct !== undefined ? sum.quality_pct : 100;
            statQ.innerText = `${q}%`;
            statQ.className = "stat-number font-mono " + (q >= 98 ? "text-emerald" : (q >= 85 ? "text-amber" : "text-rose"));
        }
        if (statLossSub) {
            statLossSub.innerText = `${sum.avg_loss_pct || 0}% Loss · ${sum.disruption_count || 0} Disruption(s)`;
        }
        if (statIcon) {
            statIcon.className = "stat-icon " + ((sum.disruption_count || 0) === 0 ? "icon-emerald" : ((sum.disruption_count || 0) <= 3 ? "icon-amber" : "icon-rose"));
        }

        // 3. Render Timeline Bar
        renderTimelineBar(data.timeline || [], currentMetricsRange);

        // 4. Render Disruption Incidents Table
        renderDisruptionsTable(data.recent_disruptions || []);
    } catch (err) {
        console.warn("Failed to load network quality metrics:", err);
    } finally {
        isMetricsLoading = false;
    }
}

function renderTimelineBar(timeline, range) {
    const bar = document.getElementById("metricsTimelineBar");
    if (!bar) return;

    if (!timeline || timeline.length === 0) {
        bar.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;width:100%;font-size:0.75rem;color:var(--text-muted);">No probe samples recorded yet. Next 15m round will populate timeline.</div>';
        return;
    }

    let slotsHtml = "";
    timeline.forEach(slot => {
        let slotClass = "slot-clean";
        if (slot.is_disrupted || slot.peak_loss_pct > 20) {
            slotClass = "slot-disrupted";
        } else if (slot.peak_loss_pct > 0) {
            slotClass = "slot-degraded";
        }

        const tooltip = `${slot.time_str} · Avg Loss: ${slot.avg_loss_pct}% (Peak: ${slot.peak_loss_pct}%) · Latency: ${slot.avg_latency_ms !== null ? slot.avg_latency_ms + 'ms' : 'Timeout'} (${slot.probe_count} probes)`;
        slotsHtml += `<div class="timeline-slot ${slotClass}" title="${escapeHtml(tooltip)}"></div>`;
    });

    bar.innerHTML = slotsHtml;

    // Update ticks
    const ticks = document.getElementById("timelineTicks");
    if (ticks) {
        if (range === "7d") {
            ticks.innerHTML = "<span>7 days ago</span><span>5 days ago</span><span>3 days ago</span><span>1 day ago</span><span>Now</span>";
        } else if (range === "30d") {
            ticks.innerHTML = "<span>30 days ago</span><span>22 days ago</span><span>15 days ago</span><span>7 days ago</span><span>Now</span>";
        } else {
            ticks.innerHTML = "<span>24h ago</span><span>18h ago</span><span>12h ago</span><span>6h ago</span><span>Now</span>";
        }
    }
}

function renderDisruptionsTable(disruptions) {
    const tbody = document.getElementById("disruptionsTableBody");
    if (!tbody) return;

    if (!disruptions || disruptions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-emerald" style="padding:18px; font-weight:600;">
                    ✓ All network targets operating with 0% packet loss in this period. No disruptions detected.
                </td>
            </tr>
        `;
        return;
    }

    let rowsHtml = "";
    disruptions.forEach(d => {
        const loss = d.packet_loss !== undefined ? d.packet_loss : 100;
        const lossBadge = loss >= 50
            ? `<span class="disruption-badge-alert font-mono">${loss}% LOSS</span>`
            : `<span class="disruption-badge-warn font-mono">${loss}% LOSS</span>`;
        const latStr = (d.latency_ms !== null && d.latency_ms !== undefined) ? `${d.latency_ms} ms` : `<span class="text-rose font-mono">Timeout</span>`;
        const statusBadge = loss >= 50
            ? `<span class="latency-pill latency-bad">DISRUPTED</span>`
            : `<span class="latency-pill latency-warn">DEGRADED</span>`;

        rowsHtml += `
            <tr>
                <td class="font-mono text-muted" style="white-space:nowrap;">${escapeHtml(d.time_str || '')}</td>
                <td>
                    <span class="font-mono font-bold">[${escapeHtml(d.target)}]</span>
                    <button class="btn-copy" onclick="copyText('${escapeHtml(d.target)}')" title="Copy IP" style="margin-left:4px;">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                </td>
                <td>${lossBadge}</td>
                <td><span class="text-cyan font-mono">${latStr}</span></td>
                <td class="font-mono text-muted">${d.packets_received || 0}/${d.packets_sent || 50}</td>
                <td>${statusBadge}</td>
            </tr>
        `;
    });

    tbody.innerHTML = rowsHtml;
}

// ── System Updates & Core Upgrade Manager ──
let updatePollTimer = null;
let updatePollingActive = false;
let updateReconnectTries = 0;

function initSystemUpdateManager() {
    const btnCheckUpdates = document.getElementById("btnCheckUpdates");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const iconCheckUpdates = document.getElementById("iconCheckUpdates");

    // Initially disable trigger button until check confirms an update is available
    if (btnTriggerUpdate) {
        btnTriggerUpdate.disabled = true;
        btnTriggerUpdate.title = "Click 'Check for Updates' to scan GitHub for new releases";
    }

    if (btnCheckUpdates) {
        btnCheckUpdates.addEventListener("click", async () => {
            if (iconCheckUpdates) iconCheckUpdates.classList.add("spinning");
            btnCheckUpdates.disabled = true;
            try {
                const info = await fetchSystemVersionInfo(true);
                if (info && info.update_available) {
                    showToast(`New release available: #${info.remote_commit || 'update'}`, "info");
                } else if (info && info.check_error) {
                    const errStr = String(info.check_error);
                    if (errStr.includes("403") || errStr.toLowerCase().includes("rate limit")) {
                        showToast("GitHub API rate-limited. Click 'Force Update' below to update directly via Git.", "warn");
                    } else {
                        showToast(`Update check failed: ${info.check_error}`, "error");
                    }
                } else {
                    showToast("XForwarder is up to date!", "success");
                }
            } catch (err) {
                showToast("Could not check for updates: " + err.message, "error");
            } finally {
                if (iconCheckUpdates) iconCheckUpdates.classList.remove("spinning");
                btnCheckUpdates.disabled = false;
            }
        });
    }

    if (btnTriggerUpdate) {
        btnTriggerUpdate.addEventListener("click", () => {
            if (btnTriggerUpdate.disabled) return;
            openSystemUpdateModal();
        });
    }

    if (btnCloseUpdateModal) {
        btnCloseUpdateModal.addEventListener("click", () => {
            closeSystemUpdateModal();
        });
    }

    if (btnCancelUpdateModal) {
        btnCancelUpdateModal.addEventListener("click", () => {
            closeSystemUpdateModal();
        });
    }

    if (btnConfirmStartUpdate) {
        btnConfirmStartUpdate.addEventListener("click", () => {
            startSystemUpdateProcedure();
        });
    }

    // Trigger non-forced initial version check
    fetchSystemVersionInfo(false);
}

async function fetchSystemVersionInfo(force = false) {
    const valInstalledVersion = document.getElementById("valInstalledVersion");
    const valLocalCommit = document.getElementById("valLocalCommit");
    const valRemoteCommit = document.getElementById("valRemoteCommit");
    const valLastChecked = document.getElementById("valLastChecked");
    const badgeUpdateStatus = document.getElementById("badgeUpdateStatus");
    const updateStatusNotice = document.getElementById("updateStatusNotice");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");
    const btnTriggerUpdateText = document.getElementById("btnTriggerUpdateText");

    try {
        const res = await fetch(`${API_BASE}/system/version${force ? "?check=1" : ""}`, {
            headers: { "Accept": "application/json" }
        });
        if (!res.ok) return null;
        const data = await res.json();

        if (valInstalledVersion && data.current_version) {
            valInstalledVersion.textContent = `v${data.current_version}`;
        }
        const brandVersionBadge = document.getElementById("brandVersionBadge");
        if (brandVersionBadge && data.current_version) {
            brandVersionBadge.textContent = `v${data.current_version}`;
        }
        if (valLocalCommit) {
            if (data.current_commit) {
                const dateStr = data.current_date ? ` (${data.current_date})` : "";
                valLocalCommit.textContent = `#${data.current_commit}${dateStr}`;
            } else {
                valLocalCommit.textContent = "Release package";
            }
        }
        if (valRemoteCommit) {
            if (data.remote_commit) {
                const msg = data.remote_commit_msg ? ` - ${data.remote_commit_msg.substring(0, 32)}` : "";
                valRemoteCommit.textContent = `#${data.remote_commit}${msg}`;
                valRemoteCommit.title = data.remote_commit_msg || `#${data.remote_commit}`;
            } else if (data.check_error) {
                const errStr = String(data.check_error);
                const isRateLimit = errStr.toLowerCase().includes("rate limit") || errStr.includes("403");
                valRemoteCommit.textContent = isRateLimit ? "Rate Limited (GitHub API)" : "Check Failed";
                valRemoteCommit.title = data.check_error;
            } else {
                valRemoteCommit.textContent = "Up to date";
                valRemoteCommit.title = "Running latest commit";
            }
        }
        if (valLastChecked) {
            valLastChecked.textContent = data.checked_at
                ? new Date(data.checked_at * 1000).toLocaleTimeString()
                : "Just now";
        }

        if (data.update_available) {
            if (badgeUpdateStatus) {
                badgeUpdateStatus.className = "stat-badge badge-amber";
                badgeUpdateStatus.textContent = "UPDATE AVAILABLE";
            }
            if (updateStatusNotice) {
                updateStatusNotice.style.display = "block";
                updateStatusNotice.className = "update-notice notice-amber";
                const commitLabel = data.remote_commit ? `#${escapeHtml(data.remote_commit)}` : "Latest Release";
                const msgLabel = data.remote_commit_msg ? ` &mdash; <em>${escapeHtml(data.remote_commit_msg)}</em>` : "";
                updateStatusNotice.innerHTML = `<strong>Update Available:</strong> A newer release (<code class="font-mono">${commitLabel}</code>${msgLabel}) is available on GitHub. Click <strong>Update to Latest</strong> below to upgrade.`;
            }
            if (btnTriggerUpdate) {
                btnTriggerUpdate.disabled = false;
                btnTriggerUpdate.classList.add("pulse-glow");
                btnTriggerUpdate.title = "Click to apply software update";
            }
            if (btnTriggerUpdateText) {
                btnTriggerUpdateText.textContent = data.remote_commit ? `Update to #${data.remote_commit}` : "Update to Latest";
            }
        } else if (data.check_error) {
            if (badgeUpdateStatus) {
                badgeUpdateStatus.className = "stat-badge badge-warn";
                badgeUpdateStatus.textContent = "CHECK FAILED";
            }
            if (updateStatusNotice) {
                updateStatusNotice.style.display = "block";
                updateStatusNotice.className = "update-notice notice-rose";
                const errStr = String(data.check_error);
                const isRateLimit = errStr.toLowerCase().includes("rate limit") || errStr.includes("403");
                const errDetail = isRateLimit
                    ? "GitHub API rate limit exceeded for this IP. Please wait a few minutes before checking again, or update directly via CLI."
                    : `Could not connect to GitHub API (${escapeHtml(data.check_error)}). Please check internet connectivity on the server.`;
                updateStatusNotice.innerHTML = `<strong>Check Failed:</strong> ${errDetail}`;
            }
            if (btnTriggerUpdate) {
                btnTriggerUpdate.disabled = false;
                btnTriggerUpdate.classList.remove("pulse-glow");
                btnTriggerUpdate.title = "Click to run update procedure anyway";
            }
            if (btnTriggerUpdateText) btnTriggerUpdateText.textContent = "Force Update";
        } else {
            if (badgeUpdateStatus) {
                badgeUpdateStatus.className = "stat-badge badge-active";
                badgeUpdateStatus.textContent = "UP TO DATE";
            }
            if (updateStatusNotice) {
                updateStatusNotice.style.display = "block";
                updateStatusNotice.className = "update-notice notice-emerald";
                const verLabel = `v${escapeHtml(data.current_version || "1.3.1")}`;
                const commitLabel = data.current_commit ? ` (#${escapeHtml(data.current_commit)})` : "";
                updateStatusNotice.innerHTML = `<strong>System Up to Date:</strong> Running latest version <strong>${verLabel}</strong>${commitLabel}. No updates needed.`;
            }
            if (btnTriggerUpdate) {
                btnTriggerUpdate.disabled = true;
                btnTriggerUpdate.classList.remove("pulse-glow");
                btnTriggerUpdate.title = "No update available - system is already running the latest release";
            }
            if (btnTriggerUpdateText) btnTriggerUpdateText.textContent = "Up to Date";
        }

        return data;
    } catch (e) {
        console.warn("Failed to fetch system version info", e);
        return null;
    }
}

function openSystemUpdateModal() {
    const updateModal = document.getElementById("updateModal");
    const updateConfirmView = document.getElementById("updateConfirmView");
    const updateProgressView = document.getElementById("updateProgressView");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");

    if (updateConfirmView) updateConfirmView.style.display = "block";
    if (updateProgressView) updateProgressView.style.display = "none";
    if (btnCancelUpdateModal) {
        btnCancelUpdateModal.style.display = "inline-flex";
        btnCancelUpdateModal.textContent = "Cancel";
        btnCancelUpdateModal.disabled = false;
        btnCancelUpdateModal.onclick = () => closeSystemUpdateModal();
    }
    if (btnConfirmStartUpdate) {
        btnConfirmStartUpdate.style.display = "inline-flex";
        btnConfirmStartUpdate.disabled = false;
    }
    if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;

    if (updateModal) updateModal.classList.add("show");
}

function closeSystemUpdateModal() {
    const updateModal = document.getElementById("updateModal");
    if (updatePollingActive) return;
    if (updateModal) updateModal.classList.remove("show");
}

async function startSystemUpdateProcedure() {
    const updateConfirmView = document.getElementById("updateConfirmView");
    const updateProgressView = document.getElementById("updateProgressView");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");
    const updateStatusBanner = document.getElementById("updateStatusBanner");
    const updateStatusText = document.getElementById("updateStatusText");
    const updateSpinner = document.getElementById("updateSpinner");
    const updateConsole = document.getElementById("updateConsole");

    if (updateConfirmView) updateConfirmView.style.display = "none";
    if (updateProgressView) updateProgressView.style.display = "block";
    if (btnConfirmStartUpdate) btnConfirmStartUpdate.style.display = "none";
    if (btnCancelUpdateModal) btnCancelUpdateModal.disabled = true;
    if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = true;

    if (updateStatusBanner) {
        updateStatusBanner.style.background = "rgba(56, 189, 248, 0.12)";
        updateStatusBanner.style.border = "1px solid rgba(56, 189, 248, 0.3)";
        updateStatusBanner.style.color = "var(--accent-cyan)";
    }
    if (updateSpinner) updateSpinner.style.display = "block";
    if (updateStatusText) updateStatusText.textContent = "Triggering update procedure on server...";
    if (updateConsole) {
        updateConsole.innerHTML = '<div class="log-entry"><span class="log-time">[INIT]</span><span class="log-msg text-cyan">Connecting to host daemon...</span></div>';
    }

    updatePollingActive = true;
    updateReconnectTries = 0;

    try {
        const res = await fetch(`${API_BASE}/system/update`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({})
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok && res.status !== 409) {
            throw new Error(data.error || "Server returned " + res.status);
        }
    } catch (err) {
        if (updateConsole) {
            updateConsole.innerHTML += `<div class="log-entry"><span class="log-time text-rose">[ERROR]</span><span class="log-msg text-rose">${escapeHtml(err.message)}</span></div>`;
        }
        if (updateStatusText) updateStatusText.textContent = "Failed to initiate update: " + err.message;
        if (btnCancelUpdateModal) {
            btnCancelUpdateModal.disabled = false;
            btnCancelUpdateModal.textContent = "Close";
        }
        if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;
        updatePollingActive = false;
        return;
    }

    pollUpdateProgress();
}

function pollUpdateProgress() {
    if (updatePollTimer) clearTimeout(updatePollTimer);

    const updateStatusBanner = document.getElementById("updateStatusBanner");
    const updateStatusText = document.getElementById("updateStatusText");
    const updateSpinner = document.getElementById("updateSpinner");
    const updateConsole = document.getElementById("updateConsole");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");

    updatePollTimer = setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/system/update/status`, {
                headers: { "Accept": "application/json" }
            });

            if (!res.ok) {
                if (res.status === 401) {
                    // Daemon restarted or session refreshed; trigger dashboard reload
                    if (updateConsole) {
                        updateConsole.innerHTML += `<div class="log-entry"><span class="log-time text-emerald">[DONE]</span><span class="log-msg text-emerald font-bold">Services restarted with updated code! Reloading dashboard...</span></div>`;
                        updateConsole.scrollTop = updateConsole.scrollHeight;
                    }
                    if (updateStatusText) {
                        updateStatusText.innerHTML = "<strong>Update Complete!</strong> Reloading dashboard in 1.2s...";
                    }
                    setTimeout(() => window.location.reload(), 1200);
                    return;
                }
                throw new Error("Status HTTP " + res.status);
            }
            const data = await res.json();
            updateReconnectTries = 0;

            if (data.log && updateConsole) {
                const lines = data.log.split("\n");
                let logHtml = "";
                lines.forEach(l => {
                    if (!l.trim()) return;
                    let cls = "text-secondary";
                    if (l.includes("[OK]")) cls = "text-emerald font-bold";
                    else if (l.includes("[ERROR]") || l.includes("Failed")) cls = "text-rose font-bold";
                    else if (l.includes("[WARN]")) cls = "text-amber";
                    else if (l.includes("[INFO]")) cls = "text-cyan";
                    logHtml += `<div class="log-entry"><span class="log-msg ${cls}">${escapeHtml(l)}</span></div>`;
                });
                updateConsole.innerHTML = logHtml || '<div class="log-entry"><span class="log-msg text-muted">Running update...</span></div>';
                updateConsole.scrollTop = updateConsole.scrollHeight;
            }

            if (data.status === "completed") {
                if (updateStatusBanner) {
                    updateStatusBanner.style.background = "rgba(16, 185, 129, 0.16)";
                    updateStatusBanner.style.border = "1px solid rgba(16, 185, 129, 0.35)";
                    updateStatusBanner.style.color = "var(--accent-mint)";
                }
                if (updateSpinner) updateSpinner.style.display = "none";
                if (updateStatusText) {
                    updateStatusText.innerHTML = "<strong>Update Completed Successfully!</strong> Refreshing dashboard in 1.5s...";
                }
                if (btnCancelUpdateModal) {
                    btnCancelUpdateModal.disabled = false;
                    btnCancelUpdateModal.textContent = "Reload Now";
                    btnCancelUpdateModal.onclick = () => window.location.reload();
                }
                if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;
                updatePollingActive = false;

                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                return;
            } else if (data.status === "failed") {
                if (updateStatusBanner) {
                    updateStatusBanner.style.background = "rgba(244, 63, 94, 0.16)";
                    updateStatusBanner.style.border = "1px solid rgba(244, 63, 94, 0.35)";
                    updateStatusBanner.style.color = "var(--accent-rose)";
                }
                if (updateSpinner) updateSpinner.style.display = "none";
                if (updateStatusText) {
                    updateStatusText.textContent = "Update encountered an error. Check logs above.";
                }
                if (btnCancelUpdateModal) {
                    btnCancelUpdateModal.disabled = false;
                    btnCancelUpdateModal.textContent = "Close";
                }
                if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;
                updatePollingActive = false;
                return;
            } else {
                if (updateStatusText) {
                    updateStatusText.textContent = "Applying update and restarting services...";
                }
                pollUpdateProgress();
            }
        } catch (err) {
            updateReconnectTries++;
            if (updateStatusBanner) {
                updateStatusBanner.style.background = "rgba(167, 139, 250, 0.16)";
                updateStatusBanner.style.border = "1px solid rgba(167, 139, 250, 0.35)";
                updateStatusBanner.style.color = "var(--accent-violet)";
            }
            if (updateStatusText) {
                updateStatusText.textContent = `Services reloading with new update... Waiting for web panel to resume (Attempt ${updateReconnectTries})...`;
            }
            if (updateConsole && updateReconnectTries <= 2) {
                updateConsole.innerHTML += `<div class="log-entry"><span class="log-time text-violet">[RELOAD]</span><span class="log-msg text-violet">Web daemon reloading with new code...</span></div>`;
                updateConsole.scrollTop = updateConsole.scrollHeight;
            }

            // Actively probe if web server has resumed
            if (updateReconnectTries >= 2) {
                try {
                    const pingCheck = await fetch(`${API_BASE}/services/status`, { cache: "no-store" }).catch(() => null);
                    if (pingCheck && (pingCheck.ok || pingCheck.status === 401)) {
                        if (updateConsole) {
                            updateConsole.innerHTML += `<div class="log-entry"><span class="log-time text-emerald">[DONE]</span><span class="log-msg text-emerald font-bold">Web panel successfully resumed! Refreshing...</span></div>`;
                            updateConsole.scrollTop = updateConsole.scrollHeight;
                        }
                        if (updateStatusText) {
                            updateStatusText.innerHTML = "<strong>Update Complete!</strong> Dashboard reconnected. Refreshing in 1s...";
                        }
                        setTimeout(() => window.location.reload(), 1200);
                        return;
                    }
                } catch (e) {}
            }

            if (updateReconnectTries > 35) {
                if (updateStatusText) {
                    updateStatusText.textContent = "Update completed. Please refresh the browser manually.";
                }
                if (btnCancelUpdateModal) {
                    btnCancelUpdateModal.disabled = false;
                    btnCancelUpdateModal.textContent = "Reload Page";
                    btnCancelUpdateModal.onclick = () => window.location.reload();
                }
                updatePollingActive = false;
                return;
            }
            pollUpdateProgress();
        }
    }, 1200);
}

// ── Relay Services Restart & Reload Controls ──
async function handleServiceRestart(service) {
    const serviceNames = {
        all: "All Relay Services & Daemons",
        engine: "XForwarder Core Failover Engine",
        haproxy: "HAProxy Relay Service",
        nginx: "Nginx Stream Proxy",
        nftables: "NFTables Table 'xfwd_orchestrator'"
    };
    const friendlyName = serviceNames[service] || service;
    const isFullRestart = service === "all" || service === "web";
    const warnMsg = isFullRestart
        ? `Are you sure you want to restart ${friendlyName}? The web dashboard will temporarily disconnect and reconnect automatically in ~2 seconds.`
        : `Are you sure you want to reload/restart ${friendlyName}? Active client connections will be preserved.`;

    const confirmed = await askConfirm(`Restart ${friendlyName}?`, warnMsg);
    if (!confirmed) return;

    showToast(`Restarting ${friendlyName}...`, "info");

    try {
        const res = await fetch(`${API_BASE}/services/restart`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ service })
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
            throw new Error(data.error || `HTTP ${res.status}`);
        }

        if (data.reconnecting) {
            showToast(data.message || "Services restarting...", "info");
            pollDashboardReconnection();
        } else {
            showToast(data.message || `${friendlyName} reloaded successfully!`, "success");
            fetchStatus();
        }
    } catch (err) {
        showToast(`Failed to restart ${friendlyName}: ${err.message}`, "error");
    }
}

function pollDashboardReconnection() {
    let tries = 0;
    const interval = setInterval(async () => {
        tries++;
        try {
            const res = await fetch(`${API_BASE}/services/status`);
            if (res.ok) {
                clearInterval(interval);
                showToast("Dashboard reconnected successfully!", "success");
                setTimeout(() => window.location.reload(), 1000);
            }
        } catch (e) {
            if (tries > 25) {
                clearInterval(interval);
                showToast("Please refresh the page manually", "warn");
            }
        }
    }, 1200);
}

function initServiceRestartControls() {
    const btnRestartAllServices = document.getElementById("btnRestartAllServices");
    const btnRestartCoreEngine = document.getElementById("btnRestartCoreEngine");
    const btnReloadHaproxy = document.getElementById("btnReloadHaproxy");
    const btnResyncNftables = document.getElementById("btnResyncNftables");
    const btnReloadNginx = document.getElementById("btnReloadNginx");

    if (btnRestartAllServices) {
        btnRestartAllServices.addEventListener("click", () => handleServiceRestart("all"));
    }
    if (btnRestartCoreEngine) {
        btnRestartCoreEngine.addEventListener("click", () => handleServiceRestart("engine"));
    }
    if (btnReloadHaproxy) {
        btnReloadHaproxy.addEventListener("click", () => handleServiceRestart("haproxy"));
    }
    if (btnResyncNftables) {
        btnResyncNftables.addEventListener("click", () => handleServiceRestart("nftables"));
    }
    if (btnReloadNginx) {
        btnReloadNginx.addEventListener("click", () => handleServiceRestart("nginx"));
    }
}

// Initialize on page load
initTheme();
initDiagPacketLossTool();
initNetworkQualityMonitor();
initSystemUpdateManager();
initServiceRestartControls();
checkAuth();

