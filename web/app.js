// XForwarder - Web Panel Logic (English Only)

// Dynamically compute base API prefix (supports custom security secret paths)
const basePath = window.location.pathname.replace(/\/+$/, "");
const API_BASE = basePath ? `${basePath}/api` : "/api";

let currentRules = [];
let lastRuntime = {};
let pollTimer = null;
let searchQuery = "";
let activeFilter = "all";
let previousPortVal = "";
let confirmResolve = null;

// DOM Elements
const loginScreen = document.getElementById("loginScreen");
const dashboardScreen = document.getElementById("dashboardScreen");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const currentUsernameEl = document.getElementById("currentUsername");
const btnLogout = document.getElementById("btnLogout");

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

// Header System Resource Elements
const ramText = document.getElementById("ramText");
const cpuText = document.getElementById("cpuText");
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

// Latency Badge Formatter (suppress when 0ms or not healthy)
function formatLatencyBadge(stat) {
    if (!stat || stat.status !== 'healthy' || stat.latency_ms === undefined || stat.latency_ms === null) {
        return '';
    }
    const ms = parseFloat(stat.latency_ms);
    if (isNaN(ms) || ms <= 0) {
        return '';
    }
    let cls = "latency-good";
    if (ms > 150) cls = "latency-bad";
    else if (ms > 70) cls = "latency-medium";
    return `<span class="latency-pill ${cls}"><span class="latency-dot"></span>${ms} ms</span>`;
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
    loginScreen.style.display = "flex";
    dashboardScreen.style.display = "none";
}

function showDashboard(username) {
    loginScreen.style.display = "none";
    dashboardScreen.style.display = "flex";
    if (username) {
        currentUsernameEl.innerText = username;
        const sidebarUsername = document.getElementById("sidebarUsername");
        if (sidebarUsername) sidebarUsername.innerText = username;
    }
    const hash = window.location.hash.replace(/^#/, "");
    if (hash && typeof switchSection === "function") {
        switchSection(hash);
    }
    fetchStatus();
    checkImportableRules();
    if (!pollTimer) {
        pollTimer = setInterval(fetchStatus, 3000);
    }
}

// ── Pre-existing HAProxy Rules Discovery & 1-Click Import ──
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
                bannerText.innerText = `Discovered ${data.count} existing HAProxy forwarding port(s) on this server (${portsStr}). Import them to manage failover in the dashboard.`;
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
            const res = await fetch(`${API_BASE}/import/haproxy`, { method: "POST" });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.ok) {
                showToast(`Successfully imported ${data.imported_count} HAProxy port rules!`);
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
btnOpenSecurityModal.addEventListener("click", () => {
    securityForm.reset();
    securityError.style.display = "none";
    pwdStrengthContainer.style.display = "none";
    secNewUser.value = currentUsernameEl.innerText || "";
    securityModal.classList.add("show");
});

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
                currentUsernameEl.innerText = data.username;
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

    statActiveHaproxy.innerText = nginxCount > 0 ? `${haproxyCount + nginxCount} (HA:${haproxyCount} / Ngx:${nginxCount})` : haproxyCount;
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

// Render Host System Metrics (RAM & CPU)
function renderSystemStats(sys) {
    if (!sys) return;
    if (sys.ram_total_mb > 0) {
        ramText.innerHTML = `<span class="ram-full">RAM: ${sys.ram_used_mb}MB / ${sys.ram_total_mb}MB (${sys.ram_percent}%)</span><span class="ram-short">RAM: ${sys.ram_percent}%</span>`;
        const ovRamText = document.getElementById("ovRamText");
        const ovRamBar = document.getElementById("ovRamBar");
        if (ovRamText) ovRamText.innerText = `${sys.ram_used_mb} / ${sys.ram_total_mb} MB (${sys.ram_percent}%)`;
        if (ovRamBar) ovRamBar.style.width = `${Math.min(100, Math.max(0, sys.ram_percent))}%`;
    }
    if (sys.cpu_percent !== undefined) {
        cpuText.innerText = `CPU: ${sys.cpu_percent}%`;
        const ovCpuText = document.getElementById("ovCpuText");
        const ovCpuBar = document.getElementById("ovCpuBar");
        if (ovCpuText) ovCpuText.innerText = `${sys.cpu_percent}%`;
        if (ovCpuBar) ovCpuBar.style.width = `${Math.min(100, Math.max(0, sys.cpu_percent))}%`;
    }
}

// Helper to format clean, semver-focused engine versions (e.g. 2.4.30-0ubuntu0.22.04.2 -> v2.4.30)
function formatEngineVersion(rawVer) {
    if (!rawVer) return "";
    const str = String(rawVer).trim();
    const base = str.split("-")[0].trim().replace(/^v/i, "");
    return base ? `v${base}` : str;
}

// Helper to format user-friendly protocol badges ('both' -> 'TCP+UDP')
function formatProtoBadge(proto) {
    const p = String(proto || "both").toLowerCase().trim();
    if (p === "both") return "TCP+UDP";
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
            valNft.className = "svc-pill-val text-emerald";
            valNft.title = nft.version || "";
        } else {
            dotNft.className = "svc-pill-dot dot-amber";
            valNft.innerText = "Inactive";
            valNft.className = "svc-pill-val text-amber";
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
            valHa.className = "svc-pill-val text-emerald";
            valHa.title = ha.version || "";
        } else {
            dotHa.className = "svc-pill-dot dot-amber";
            valHa.innerText = haVerShort ? `Standby (${haVerShort})` : "Standby";
            valHa.className = "svc-pill-val text-amber";
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
            valNgx.className = "svc-pill-val text-emerald";
            valNgx.title = ngx.version || "";
        } else {
            dotNgx.className = "svc-pill-dot dot-amber";
            valNgx.innerText = ngxVerShort ? `Standby (${ngxVerShort})` : "Standby";
            valNgx.className = "svc-pill-val text-amber";
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
        svcNftablesKernel.innerText = nft.active ? (nft.table_active ? "Active (table ip xfwd_orchestrator)" : "Active (Kernel ready)") : "Inactive";
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

    // Sidebar badge
    const navServicesBadge = document.getElementById("navServicesBadge");
    if (navServicesBadge) {
        if (missing.length === 0) {
            navServicesBadge.innerText = "SYNCED";
            navServicesBadge.className = "nav-badge nav-badge-ok";
        } else {
            navServicesBadge.innerText = `${3 - missing.length}/3`;
            navServicesBadge.className = "nav-badge";
        }
    }
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

// Render Rule Cards with Filtering and Search
function renderRules(rules, runtime) {
    if (!rules || rules.length === 0) {
        rulesContainer.innerHTML = `
            <div style="text-align:center;padding:48px 20px;color:var(--text-secondary);border:1px dashed var(--border-color);border-radius:14px;">
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

        // 1. Search Query Check across all destinations
        if (searchQuery) {
            const matchesBasic = 
                portStr.includes(searchQuery) ||
                ruleId.includes(searchQuery) ||
                protoSearchStr.includes(searchQuery);
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
        rulesContainer.innerHTML = `
            <div style="text-align:center;padding:40px 20px;color:var(--text-secondary);border:1px dashed var(--border-color);border-radius:14px;">
                <p style="font-size:1rem;margin-bottom:6px;">No rules matching your search or active filter.</p>
                <p style="font-size:0.8rem;color:var(--text-muted);">Try clearing the search input or switching filter tabs.</p>
            </div>
        `;
        return;
    }

    rulesContainer.innerHTML = filtered.map(rule => {
        const ruleId = String(rule.id || `rule-${rule.port}`);
        const encodedId = encodeURIComponent(ruleId);
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
            const isDown = (stat.status === 'failed' || stat.status === 'down');

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
                        <span>Forced (Reset)</span>
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

            return `
                <div class="path-box ${isActive ? (isFailover ? 'is-failover' : 'is-active') : ''}"
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
            <div class="rule-card">
                <div class="rule-top">
                    <div class="port-badge">
                        <span class="port-num">:${escapeHtml(rule.port)}</span>
                        <button class="btn-copy" onclick="copyText(decodeURIComponent('${encodeURIComponent(rule.port)}'))" title="Copy Port Number">${copyPortSvg}</button>
                        <span class="proto-pill">${escapeHtml(formatProtoBadge(rule.protocol))}</span>
                    </div>
                    <div class="rule-actions">
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
    }).join("");
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

// Override change handler (Auto Failover vs Manual Test Priority)
async function handleOverrideChange(ruleId, val) {
    const prioVal = parseInt(val);

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
        }
    } catch (err) {
        showToast("Failed to update forwarding mode", "error");
    } finally {
        fetchStatus();
    }
}

// Emergency Batch Override Action
batchSelect.addEventListener("change", async () => {
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

// Search and Filter Listeners
searchInput.addEventListener("input", () => {
    searchQuery = searchInput.value.trim().toLowerCase();
    btnClearSearch.style.display = searchQuery ? "block" : "none";
    renderRules(currentRules, lastRuntime);
});

btnClearSearch.addEventListener("click", () => {
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
        <div class="form-row">
            <div class="form-group flex-1">
                <label>Engine Type</label>
                <select class="form-control dest-type">
                    <option value="haproxy" ${type === "haproxy" ? "selected" : ""}>HAProxy (Direct Zero-Tunnel IPv6)</option>
                    <option value="nginx" ${type === "nginx" ? "selected" : ""}>Nginx (Stream TCP/UDP Proxy)</option>
                    <option value="nftables" ${type === "nftables" ? "selected" : ""}>NFTables (Kernel Tunnel DNAT)</option>
                </select>
            </div>
            <div class="form-group flex-2">
                <label>Destination Target IP / Host</label>
                <input type="text" class="form-control dest-target" placeholder="${isPrimary ? '2001:4ba0:cafe:84e::1' : '10.88.1.2'}" value="${escapeHtml(target)}" required>
            </div>
            <div class="form-group flex-1">
                <label>Target Port</label>
                <input type="number" class="form-control dest-port" placeholder="Same as listen" min="1" max="65535" value="${escapeHtml(port)}">
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
                protocol: document.getElementById("formProtocol") ? document.getElementById("formProtocol").value : "both"
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            if (data.healthy) {
                const latStr = (data.latency_ms !== null && data.latency_ms !== undefined && data.latency_ms > 0) ? ` (${data.latency_ms}ms)` : "";
                if (resEl) resEl.innerHTML = `<span class="badge-probe text-emerald" style="display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;">✓ Reachable${latStr}</span>`;
                showToast(`Destination [${target}]:${port} is reachable${latStr}`);
            } else {
                const reason = data.reason ? `: ${data.reason}` : "";
                if (resEl) resEl.innerHTML = `<span class="badge-fail text-rose" style="display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;" title="${escapeHtml(data.reason || '')}">✗ Unreachable${escapeHtml(reason)}</span>`;
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

// Delete Rule with Custom Glass Confirm Modal
async function deleteRule(ruleId) {
    const confirmed = await askConfirm(
        "Delete Port Forwarding Rule?",
        `Are you sure you want to delete forwarding rule '${ruleId}'? Routing on this port will stop immediately.`
    );
    if (!confirmed) return;

    try {
        const res = await fetch(`${API_BASE}/rule/${encodeURIComponent(ruleId)}`, { method: "DELETE" });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Rule '${ruleId}' removed`);
            if (data.sync_errors && data.sync_errors.length > 0) {
                showSyncErrorAlert(data.sync_errors);
            }
            fetchStatus();
        } else {
            showToast(data.error || "Error deleting rule", "error");
        }
    } catch (err) {
        showToast("Error deleting rule", "error");
    }
}

// Save Rule Form
ruleForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const port = parseInt(document.getElementById("formPort").value);
    const proto = document.getElementById("formProto").value;
    const ruleId = document.getElementById("editRuleId").value || `rule-${port}`;

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
    }

    const payload = {
        id: ruleId,
        port: port,
        protocol: proto,
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

// Overview quick action shortcuts
const btnOvAddRule = document.getElementById("btnOvAddRule");
if (btnOvAddRule) {
    btnOvAddRule.addEventListener("click", () => {
        switchSection("rules");
        if (btnOpenAddModal) btnOpenAddModal.click();
    });
}

const btnOvGotoServices = document.getElementById("btnOvGotoServices");
if (btnOvGotoServices) {
    btnOvGotoServices.addEventListener("click", () => switchSection("services"));
}

const btnOvGotoSecurity = document.getElementById("btnOvGotoSecurity");
if (btnOvGotoSecurity) {
    btnOvGotoSecurity.addEventListener("click", () => switchSection("security"));
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
                    resultEl.innerHTML = `
                        <div style="color:var(--accent-emerald); font-weight:600; margin-bottom:8px;">
                            Discovered ${data.count} existing HAProxy forwarding rule(s) (${portsStr})
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
                    resultEl.innerHTML = `<span style="color:var(--accent-emerald);">All existing HAProxy forwarding rules on this server are already managed by XForwarder.</span>`;
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

// Initialize on page load
initTheme();
checkAuth();
