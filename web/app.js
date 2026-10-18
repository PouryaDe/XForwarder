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
    loginScreen.style.display = "flex";
    dashboardScreen.style.display = "none";
}

function showDashboard(username) {
    loginScreen.style.display = "none";
    dashboardScreen.style.display = "block";
    if (username) currentUsernameEl.innerText = username;
    fetchStatus();
    if (!pollTimer) {
        pollTimer = setInterval(fetchStatus, 3000);
    }
}

// Login Form Submit
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.style.display = "none";
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;

    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok && data.ok) {
            showDashboard(data.username);
            showToast(`Welcome back, ${data.username}!`);
        } else {
            loginError.innerText = data.error || "Invalid username or password";
            loginError.style.display = "block";
        }
    } catch (err) {
        loginError.innerText = "Connection error. Is the service running?";
        loginError.style.display = "block";
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
        const d1Stat = destStats['prio_1'] || {};
        const d1Healthy = (d1Stat.status === 'healthy');

        if (activePrio === 1 && d1Healthy) {
            p1ActiveCount++;
        } else if (activePrio === 2) {
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

        const d1 = (rule.destinations || []).find(d => d.priority === 1) || {};
        const d2 = (rule.destinations || []).find(d => d.priority === 2) || {};
        const d1Target = String(d1.target || "").toLowerCase();
        const d2Target = String(d2.target || "").toLowerCase();
        const d1Comment = String(d1.comment || "").toLowerCase();
        const d2Comment = String(d2.comment || "").toLowerCase();

        // 1. Search Query Check
        if (searchQuery) {
            const matchesSearch = 
                portStr.includes(searchQuery) ||
                ruleId.includes(searchQuery) ||
                protoStr.includes(searchQuery) ||
                d1Target.includes(searchQuery) ||
                d2Target.includes(searchQuery) ||
                d1Comment.includes(searchQuery) ||
                d2Comment.includes(searchQuery);
            if (!matchesSearch) return false;
        }

        // 2. Active Tab Filter Check
        const rState = rulesState[String(rule.id || `rule-${rule.port}`)] || {};
        const destStats = rState.dest_stats || {};
        const d1Stat = destStats['prio_1'] || {};
        const d1Healthy = (d1Stat.status === 'healthy');
        const activePriority = rule.active_priority || 1;

        if (activeFilter === "p1") {
            return activePriority === 1 && d1Healthy;
        } else if (activeFilter === "p2") {
            return activePriority === 2;
        } else if (activeFilter === "down") {
            return !d1Healthy && activePriority === 1;
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

        const d1 = (rule.destinations || []).find(d => d.priority === 1) || { type: 'haproxy', target: 'Not configured', port: rule.port };
        const d2 = (rule.destinations || []).find(d => d.priority === 2) || { type: 'nftables', target: 'Not configured', port: rule.port };

        const d1Stat = destStats['prio_1'] || {};
        const d2Stat = destStats['prio_2'] || {};

        const d1Healthy = (d1Stat.status === 'healthy');
        const d2Healthy = (d2Stat.status === 'healthy');

        const d1Target = String(d1.target || '');
        const d2Target = String(d2.target || '');
        const d1TargetDisplay = d1Target.includes(':') ? `[${escapeHtml(d1Target)}]` : escapeHtml(d1Target);
        const d2TargetDisplay = d2Target.includes(':') ? `[${escapeHtml(d2Target)}]` : escapeHtml(d2Target);

        const d1LatencyBadge = formatLatencyBadge(d1Stat);
        const d2LatencyBadge = formatLatencyBadge(d2Stat);

        const copyPortSvg = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;

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
                            <option value="0" ${forceOverride === 0 ? 'selected' : ''}>Mode: Auto Failover</option>
                            <option value="1" ${forceOverride === 1 ? 'selected' : ''}>Force: Priority 1</option>
                            <option value="2" ${forceOverride === 2 ? 'selected' : ''}>Force: Priority 2</option>
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
                    <!-- Priority 1 Path Box -->
                    <div class="path-box ${activePriority === 1 ? 'is-active' : ''}">
                        ${activePriority === 1 ? '<span class="active-ribbon">ACTIVE ROUTE</span>' : ''}
                        <div class="path-header">
                            <span class="path-tag path-tag-1">Priority 1 (Primary)</span>
                            <span class="path-status ${d1Healthy ? 'status-healthy' : 'status-failed'}">
                                <span class="status-indicator"></span>
                                ${d1Healthy ? 'HEALTHY' : 'DOWN / TIMEOUT'}
                            </span>
                        </div>
                        <div class="path-dest">
                            <span>${escapeHtml(String(d1.type || 'haproxy').toUpperCase())}: ${d1TargetDisplay}:${escapeHtml(d1.port || rule.port)}</span>
                            <button class="btn-copy" onclick="copyText('${escapeHtml(d1Target)}')" title="Copy Destination IP">${copyPortSvg}</button>
                        </div>
                        <div class="path-meta">
                            <span>${escapeHtml(d1.comment || 'Primary uplink')}</span>
                            ${d1LatencyBadge}
                        </div>
                    </div>

                    <!-- Priority 2 Path Box -->
                    <div class="path-box ${activePriority === 2 ? 'is-failover' : ''}">
                        ${activePriority === 2 ? '<span class="active-ribbon" style="background:var(--accent-amber);">FAILOVER ACTIVE</span>' : ''}
                        <div class="path-header">
                            <span class="path-tag path-tag-2">Priority 2 (Failover)</span>
                            <span class="path-status ${d2Healthy ? 'status-healthy' : 'status-standby'}">
                                <span class="status-indicator"></span>
                                ${d2Healthy ? 'HEALTHY' : 'STANDBY'}
                            </span>
                        </div>
                        <div class="path-dest">
                            <span>${escapeHtml(String(d2.type || 'nftables').toUpperCase())}: ${d2TargetDisplay}:${escapeHtml(d2.port || rule.port)}</span>
                            <button class="btn-copy" onclick="copyText('${escapeHtml(d2Target)}')" title="Copy Destination IP">${copyPortSvg}</button>
                        </div>
                        <div class="path-meta">
                            <span>${escapeHtml(d2.comment || 'Backup tunnel')}</span>
                            ${d2LatencyBadge}
                        </div>
                    </div>
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

// Port Auto-Fill in Modal Form
const formPortInput = document.getElementById("formPort");
formPortInput.addEventListener("input", () => {
    const val = formPortInput.value.trim();
    const p1Port = document.getElementById("p1Port");
    const p2Port = document.getElementById("p2Port");
    if (!p1Port.value || p1Port.value === previousPortVal) {
        p1Port.value = val;
    }
    if (!p2Port.value || p2Port.value === previousPortVal) {
        p2Port.value = val;
    }
    previousPortVal = val;
});

// Modal Preset Scenario Buttons
document.getElementById("presetHaproxyGre").addEventListener("click", () => {
    document.getElementById("p1Type").value = "haproxy";
    document.getElementById("p1Comment").value = "Primary Direct IPv6";
    document.getElementById("p2Type").value = "nftables";
    document.getElementById("p2Comment").value = "Backup GRE/FakeTCP Tunnel";
    showToast("Preset applied: HAProxy IPv6 + GRE/FakeTCP");
});

document.getElementById("presetNginxTunnel").addEventListener("click", () => {
    document.getElementById("p1Type").value = "nginx";
    document.getElementById("p1Comment").value = "Primary Nginx Stream Proxy";
    document.getElementById("p2Type").value = "nftables";
    document.getElementById("p2Comment").value = "Backup Layer 3 Tunnel";
    showToast("Preset applied: Nginx Proxy + Tunnel");
});

document.getElementById("presetDualHaproxy").addEventListener("click", () => {
    document.getElementById("p1Type").value = "haproxy";
    document.getElementById("p1Comment").value = "Foreign Exit Node 1";
    document.getElementById("p2Type").value = "haproxy";
    document.getElementById("p2Comment").value = "Foreign Exit Node 2";
    showToast("Preset applied: Dual Direct IPv6");
});

// Modal open/close
btnOpenAddModal.addEventListener("click", () => {
    modalTitle.innerText = "Add New Port Forwarding Rule";
    ruleForm.reset();
    previousPortVal = "";
    document.getElementById("editRuleId").value = "";
    document.getElementById("formProto").value = "both";
    document.getElementById("p1Type").value = "haproxy";
    document.getElementById("p2Type").value = "nftables";
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

    const d1 = (r.destinations || []).find(d => d.priority === 1) || {};
    const d2 = (r.destinations || []).find(d => d.priority === 2) || {};

    document.getElementById("p1Type").value = d1.type || "haproxy";
    document.getElementById("p1Target").value = d1.target || "";
    document.getElementById("p1Port").value = d1.port || r.port;
    document.getElementById("p1Comment").value = d1.comment || "";

    document.getElementById("p2Type").value = d2.type || "nftables";
    document.getElementById("p2Target").value = d2.target || "";
    document.getElementById("p2Port").value = d2.port || r.port;
    document.getElementById("p2Comment").value = d2.comment || "";

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

    const p1PortVal = document.getElementById("p1Port").value;
    const p2PortVal = document.getElementById("p2Port").value;

    const payload = {
        id: ruleId,
        port: port,
        protocol: proto,
        active_priority: 1,
        force_override: 0,
        destinations: [
            {
                priority: 1,
                type: document.getElementById("p1Type").value,
                target: document.getElementById("p1Target").value.trim(),
                port: p1PortVal ? parseInt(p1PortVal) : port,
                comment: document.getElementById("p1Comment").value.trim()
            },
            {
                priority: 2,
                type: document.getElementById("p2Type").value,
                target: document.getElementById("p2Target").value.trim(),
                port: p2PortVal ? parseInt(p2PortVal) : port,
                comment: document.getElementById("p2Comment").value.trim()
            }
        ]
    };

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
    }
});

// Initialize on page load
checkAuth();
