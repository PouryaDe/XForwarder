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

// Latency Badge Formatter
function formatLatencyBadge(stat) {
    if (!stat || stat.latency_ms === undefined || stat.latency_ms === null) {
        return '<span class="latency-pill latency-none">Latency: --</span>';
    }
    const ms = stat.latency_ms;
    let cls = "latency-good";
    if (ms > 150) cls = "latency-bad";
    else if (ms > 70) cls = "latency-medium";
    return `<span class="latency-pill ${cls}"><span class="latency-dot"></span>${ms} ms</span>`;
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
    dashboardScreen.style.display = "block";
    if (username) currentUsernameEl.innerText = username;
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
        renderRules(currentRules, lastRuntime);
    } catch (err) {
        console.warn("Polling error:", err);
    }
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

    if (runtime.active_services) {
        engineStatusBadge.innerText = "SYNCED";
        engineStatusBadge.className = "stat-badge badge-active";
    }
}

// Render Host System Metrics (RAM & CPU)
function renderSystemStats(sys) {
    if (!sys) return;
    if (sys.ram_total_mb > 0) {
        ramText.innerText = `RAM: ${sys.ram_used_mb}MB / ${sys.ram_total_mb}MB (${sys.ram_percent}%)`;
    }
    if (sys.cpu_percent !== undefined) {
        cpuText.innerText = `CPU: ${sys.cpu_percent}%`;
    }
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

        // 1. Search Query Check across all destinations
        if (searchQuery) {
            const matchesBasic = 
                portStr.includes(searchQuery) ||
                ruleId.includes(searchQuery) ||
                protoStr.includes(searchQuery);
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

        // Build dynamic override dropdown options
        const overrideOptions = [
            `<option value="0" ${forceOverride === 0 ? 'selected' : ''}>Mode: Auto Failover</option>`
        ];
        sortedDests.forEach(d => {
            const p = d.priority || 1;
            const t = escapeHtml(String(d.type || 'haproxy').toUpperCase());
            const lbl = p === 1 ? `Force: Priority 1 (Primary · ${t})` : `Force: Priority ${p} (Failover · ${t})`;
            overrideOptions.push(`<option value="${p}" ${forceOverride === p ? 'selected' : ''}>${lbl}</option>`);
        });

        // Build dynamic paths grid
        const pathsHtml = sortedDests.map(dest => {
            const prio = dest.priority || 1;
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
                statusLabel = 'DOWN / TIMEOUT';
                statusClass = 'status-failed';
            } else if (stat.status) {
                statusLabel = String(stat.status).toUpperCase();
            }

            const rawTarget = String(dest.target || '');
            const targetDisplay = rawTarget.includes(':') ? `[${escapeHtml(rawTarget)}]` : escapeHtml(rawTarget);
            const latencyBadge = formatLatencyBadge(stat);
            const tagClass = getPrioTagClass(prio);

            const ribbonHtml = isActive
                ? `<span class="active-ribbon" ${isFailover ? 'style="background:var(--accent-amber);"' : ''}>${isFailover ? `FAILOVER P${prio} ACTIVE` : 'ACTIVE ROUTE'}</span>`
                : '';

            return `
                <div class="path-box ${isActive ? (isFailover ? 'is-failover' : 'is-active') : ''}">
                    ${ribbonHtml}
                    <div class="path-header">
                        <span class="path-tag ${tagClass}">Priority ${prio} ${isPrimary ? '(Primary)' : '(Failover)'}</span>
                        <span class="path-status ${statusClass}">
                            <span class="status-indicator"></span>
                            ${statusLabel}
                        </span>
                    </div>
                    <div class="path-dest">
                        <span>${escapeHtml(String(dest.type || 'haproxy').toUpperCase())}: ${targetDisplay}:${escapeHtml(dest.port || rule.port)}</span>
                        <button class="btn-copy" onclick="copyText('${escapeHtml(rawTarget)}')" title="Copy Destination IP">${copyPortSvg}</button>
                    </div>
                    <div class="path-meta">
                        <span>${escapeHtml(dest.comment || (isPrimary ? 'Primary uplink' : `Failover path ${prio}`))}</span>
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
                        <button class="btn-copy" onclick="copyText('${escapeHtml(rule.port)}')" title="Copy Port Number">${copyPortSvg}</button>
                        <span class="proto-pill">${escapeHtml(String(rule.protocol || 'both').toUpperCase())}</span>
                    </div>
                    <div class="rule-actions">
                        <select class="form-control" style="width:auto;padding:6px 12px;font-size:0.8rem;" onchange="handleOverrideChange(decodeURIComponent('${encodedId}'), this.value)">
                            ${overrideOptions.join('')}
                        </select>
                        <button class="btn btn-secondary btn-sm" onclick="editRule(decodeURIComponent('${encodedId}'))" title="Edit Rule">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="deleteRule(decodeURIComponent('${encodedId}'))" title="Delete Rule">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                    </div>
                </div>

                <div class="paths-grid">
                    ${pathsHtml}
                </div>
            </div>
        `;
    }).join("");
}

// Override change handler
async function handleOverrideChange(ruleId, val) {
    try {
        const res = await fetch(`${API_BASE}/override`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rule_id: ruleId, force_override: parseInt(val) })
        });
        if (res.ok) {
            showToast("Routing mode updated successfully");
            fetchStatus();
        } else {
            const data = await res.json().catch(() => ({}));
            showToast(data.error || "Failed to update override", "error");
        }
    } catch (err) {
        showToast("Failed to update override", "error");
    }
}

// Emergency Batch Override Action
batchSelect.addEventListener("change", async () => {
    const val = batchSelect.value;
    if (val === "") return;
    const modeLabels = {
        "0": "Restore All to Auto Failover",
        "1": "Force All to Priority 1 (Primary)",
        "2": "Force All to Priority 2 (Backup Tunnel)"
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

    div.innerHTML = `
        <div class="priority-header">
            <div>
                <span class="prio-tag ${getPrioTagClass(prio)}">Priority ${prio} ${isPrimary ? "(Primary)" : "(Failover)"}</span>
                <span class="prio-sub">${getPrioSubtitle(prio)}</span>
            </div>
            ${canRemove ? `
            <button type="button" class="btn-remove-prio" title="Remove this priority path" onclick="removeDestinationRow(${index})">
                &times;
            </button>` : ""}
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
        <div class="form-group" style="margin-bottom:0;">
            <label>Comment / Label</label>
            <input type="text" class="form-control dest-comment" placeholder="e.g. ${isPrimary ? 'Foreign Server 1 - Primary IPv6' : 'Backup Tunnel Node ' + prio}" value="${escapeHtml(comment)}">
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
        updated.push({
            priority: idx + 1,
            type: typeEl ? typeEl.value : (idx === 0 ? "haproxy" : "nftables"),
            target: targetEl ? targetEl.value : "",
            port: portEl ? portEl.value : "",
            comment: commentEl ? commentEl.value : ""
        });
    });
    if (updated.length > 0) {
        currentModalDestinations = updated;
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
        comment: `Backup Priority ${nextPrio}`
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

// Modal Preset Scenario Buttons
document.getElementById("presetHaproxyGre").addEventListener("click", () => {
    const listenPort = document.getElementById("formPort").value.trim();
    currentModalDestinations = [
        { priority: 1, type: "haproxy", target: "", port: listenPort, comment: "Primary Direct IPv6" },
        { priority: 2, type: "nftables", target: "", port: listenPort, comment: "Backup GRE/FakeTCP Tunnel" }
    ];
    renderDestinationsList();
    showToast("Preset applied: HAProxy IPv6 + GRE/FakeTCP");
});

document.getElementById("presetNginxTunnel").addEventListener("click", () => {
    const listenPort = document.getElementById("formPort").value.trim();
    currentModalDestinations = [
        { priority: 1, type: "nginx", target: "", port: listenPort, comment: "Primary Nginx Stream Proxy" },
        { priority: 2, type: "nftables", target: "", port: listenPort, comment: "Backup Layer 3 Tunnel" }
    ];
    renderDestinationsList();
    showToast("Preset applied: Nginx Proxy + Tunnel");
});

document.getElementById("presetDualHaproxy").addEventListener("click", () => {
    const listenPort = document.getElementById("formPort").value.trim();
    currentModalDestinations = [
        { priority: 1, type: "haproxy", target: "", port: listenPort, comment: "Foreign Exit Node 1" },
        { priority: 2, type: "haproxy", target: "", port: listenPort, comment: "Foreign Exit Node 2" }
    ];
    renderDestinationsList();
    showToast("Preset applied: Dual Direct IPv6");
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
        if (res.ok) {
            showToast(`Rule '${ruleId}' removed`);
            fetchStatus();
        } else {
            const data = await res.json().catch(() => ({}));
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
            showToast(`Target IP/Host for Priority ${i + 1} is required`, "error");
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
            target: d.target.trim(),
            port: d.port ? parseInt(d.port) : port,
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
        if (res.ok) {
            showToast("Rule saved and applied successfully");
            closeModal();
            fetchStatus();
        } else {
            const errData = await res.json().catch(() => ({}));
            showToast(errData.error || "Failed to save rule", "error");
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

// Initialize on page load
checkAuth();
