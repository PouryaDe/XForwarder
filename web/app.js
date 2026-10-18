// XForwarder - Web Panel Logic (English Only)

// Dynamically compute base API prefix (supports custom security secret paths)
const basePath = window.location.pathname.replace(/\/+$/, "");
const API_BASE = basePath ? `${basePath}/api` : "/api";

let currentRules = [];
let pollTimer = null;

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
        const runtime = data.runtime || {};
        currentRules = cfg.rules || [];

        renderStats(currentRules, runtime);
        renderRules(currentRules, runtime);
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

    rules.forEach(r => {
        const activePrio = r.active_priority || 1;
        const dest = (r.destinations || []).find(d => d.priority === activePrio) || (r.destinations || [])[0];
        if (dest) {
            if (dest.type === "haproxy") haproxyCount++;
            if (dest.type === "nginx") nginxCount++;
            if (dest.type === "nftables") nftablesCount++;
        }
    });

    statActiveHaproxy.innerText = nginxCount > 0 ? `${haproxyCount + nginxCount} (HA:${haproxyCount} / Ngx:${nginxCount})` : haproxyCount;
    statActiveNftables.innerText = nftablesCount;

    if (runtime.active_services) {
        engineStatusBadge.innerText = "SYNCED";
        engineStatusBadge.className = "stat-badge badge-active";
    }
}

// Render Rule Cards
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

    rulesContainer.innerHTML = rules.map(rule => {
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

        return `
            <div class="rule-card">
                <div class="rule-top">
                    <div class="port-badge">
                        <span class="port-num">:${escapeHtml(rule.port)}</span>
                        <span class="proto-pill">${escapeHtml(String(rule.protocol || 'both').toUpperCase())}</span>
                    </div>
                    <div class="rule-actions">
                        <select class="form-control" style="width:auto;padding:4px 10px;font-size:0.8rem;" onchange="handleOverrideChange(decodeURIComponent('${encodedId}'), this.value)">
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
                        <div class="path-dest">${escapeHtml(String(d1.type || 'haproxy').toUpperCase())}: ${d1TargetDisplay}:${escapeHtml(d1.port || rule.port)}</div>
                        <div class="path-meta">
                            <span>${escapeHtml(d1.comment || 'Primary uplink')}</span>
                            <span>Latency: ${d1Stat.latency_ms ? escapeHtml(d1Stat.latency_ms) + ' ms' : '--'}</span>
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
                        <div class="path-dest">${escapeHtml(String(d2.type || 'nftables').toUpperCase())}: ${d2TargetDisplay}:${escapeHtml(d2.port || rule.port)}</div>
                        <div class="path-meta">
                            <span>${escapeHtml(d2.comment || 'Backup tunnel')}</span>
                            <span>Latency: ${d2Stat.latency_ms ? escapeHtml(d2Stat.latency_ms) + ' ms' : '--'}</span>
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

// Modal open/close
btnOpenAddModal.addEventListener("click", () => {
    modalTitle.innerText = "Add New Port Forwarding Rule";
    ruleForm.reset();
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

// Delete Rule
async function deleteRule(ruleId) {
    if (!confirm(`Are you sure you want to delete rule '${ruleId}'?`)) return;
    try {
        const res = await fetch(`${API_BASE}/rule/${encodeURIComponent(ruleId)}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Rule removed");
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
