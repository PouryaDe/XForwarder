// ============================================================================
// XForwarder Web UI - Port Forwarding Rules Renderer & Organizer (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { escapeHtml, safeInlineArg, formatLatencyBadge, formatLoss50Badge, formatLoss50Inline, formatConciseReason, formatProtoBadge, formatBytes, showToast, askConfirm } from "./utils.js";
import { currentRules, lastRuntime, lastTrafficData, lastLatestLoss } from "./state.js";

let currentViewMode = localStorage.getItem("xfwd_rules_view") || "cards";
let currentSort = localStorage.getItem("xfwd_rules_sort") || "port_asc";
let activeFilter = "all";
let searchQuery = "";
let draggedPathInfo = null;
let lastRenderedRulesFingerprint = null;
const pendingOverrides = new Map();

function getPrioTagClass(prio) {
    if (prio === 1) return "prio-tag-1";
    if (prio === 2) return "prio-tag-2";
    if (prio === 3) return "prio-tag-3";
    return "prio-tag-other";
}

export function sortRulesList(rulesList, sortMode, rulesState) {
    if (!Array.isArray(rulesList)) return [];
    const copy = [...rulesList];

    copy.sort((a, b) => {
        const portA = parseInt(a.port, 10) || 0;
        const portB = parseInt(b.port, 10) || 0;

        if (sortMode === "port_desc") return portB - portA;
        if (sortMode === "port_asc") return portA - portB;

        if (sortMode === "created_desc") {
            const timeA = parseFloat(a.created_at) || 0;
            const timeB = parseFloat(b.created_at) || 0;
            return timeB - timeA;
        }
        if (sortMode === "created_asc") {
            const timeA = parseFloat(a.created_at) || 0;
            const timeB = parseFloat(b.created_at) || 0;
            return timeA - timeB;
        }

        if (sortMode === "category") {
            const catA = String(a.category || "").trim().toLowerCase();
            const catB = String(b.category || "").trim().toLowerCase();
            if (!catA && catB) return 1;
            if (catA && !catB) return -1;
            if (catA !== catB) return catA.localeCompare(catB);
            return portA - portB;
        }

        if (sortMode === "health") {
            const rStateA = rulesState ? (rulesState[String(a.id || `rule-${a.port}`)] || {}) : {};
            const rStateB = rulesState ? (rulesState[String(b.id || `rule-${b.port}`)] || {}) : {};
            const statA = (rStateA.dest_stats && rStateA.dest_stats[`prio_${a.active_priority || 1}`]) || {};
            const statB = (rStateB.dest_stats && rStateB.dest_stats[`prio_${b.active_priority || 1}`]) || {};

            const isDownA = statA.status === 'failed' || statA.status === 'down';
            const isDownB = statB.status === 'failed' || statB.status === 'down';
            if (isDownA && !isDownB) return -1;
            if (!isDownA && isDownB) return 1;
            return portA - portB;
        }

        return portA - portB;
    });
    return copy;
}

export function updateCategoryDatalist(rules) {
    const datalist = document.getElementById("categoryDatalist");
    if (!datalist || !Array.isArray(rules)) return;
    const categories = new Set();
    rules.forEach(r => {
        if (r && r.category && String(r.category).trim()) {
            categories.add(String(r.category).trim());
        }
    });

    datalist.innerHTML = Array.from(categories)
        .sort((a, b) => a.localeCompare(b))
        .map(cat => `<option value="${escapeHtml(cat)}"></option>`)
        .join("");
}

export function computeRulesFingerprint(filteredRules, rulesState) {
    const parts = [
        `v:${currentViewMode}`,
        `s:${currentSort}`,
        `f:${activeFilter}`,
        `q:${searchQuery}`,
        `len:${filteredRules.length}`
    ];
    filteredRules.forEach(r => {
        const id = String(r.id || `rule-${r.port}`);
        const st = rulesState[id] || {};
        const activePrio = r.active_priority || 1;
        const ds = (st.dest_stats && st.dest_stats[`prio_${activePrio}`]) || {};
        const destSummary = (r.destinations || []).map(d => `${d.priority}:${d.target}:${d.port}`).join('|');
        parts.push(`${id}:${r.port}:${activePrio}:${r.force_override || 0}:${r.category || ''}:${ds.status || ''}:${ds.latency_ms || ''}:${destSummary}`);
    });
    return parts.join(';');
}

export function handlePathDragStart(e, ruleId, index) {
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

export function handlePathDragOver(e, ruleId, index) {
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

export function handlePathDragLeave(e) {
    const box = e.currentTarget;
    if (box && !box.contains(e.relatedTarget)) {
        box.classList.remove("drag-over");
    }
}

export function handlePathDragEnd(e) {
    document.querySelectorAll(".path-box").forEach(el => {
        el.classList.remove("is-dragging");
        el.classList.remove("drag-over");
    });
    draggedPathInfo = null;
}

export async function handlePathDrop(e, ruleId, toIndex) {
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

    const rule = (currentRules || []).find(r => String(r.id || `rule-${r.port}`) === ruleId);
    if (!rule || !rule.destinations) return;

    const dests = [...rule.destinations].sort((a, b) => (a.priority || 1) - (b.priority || 1));
    if (fromIndex < 0 || toIndex < 0 || fromIndex >= dests.length || toIndex >= dests.length) return;

    const moved = dests.splice(fromIndex, 1)[0];
    dests.splice(toIndex, 0, moved);
    dests.forEach((d, i) => d.priority = i + 1);
    rule.destinations = dests;

    renderRules(currentRules, lastRuntime);

    try {
        const res = await fetch(`${API_BASE}/rule`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(rule)
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Reordered: #${fromIndex + 1} -> #${toIndex + 1}`, "success");
        } else {
            showToast(data.error || "Failed to save reordered priority", "error");
        }
    } catch (_) {
        showToast("Network error reordering priority", "error");
    }
}

export function renderRuleCard(rule, rulesState) {
    const ruleId = String(rule.id || `rule-${rule.port}`);
    const encodedId = encodeURIComponent(ruleId);
    const rState = (rulesState && rulesState[ruleId]) ? rulesState[ruleId] : {};
    const destStats = rState.dest_stats || {};
    const activePriority = rule.active_priority || 1;
    const forceOverride = rule.force_override || 0;

    const sortedDests = (rule.destinations && rule.destinations.length > 0)
        ? [...rule.destinations].sort((a, b) => (a.priority || 1) - (b.priority || 1))
        : [{ priority: 1, type: 'haproxy', target: 'Not configured', port: rule.port }];

    const copyPortSvg = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;

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

    const pathsHtml = sortedDests.map((dest, destIndex) => {
        const prio = dest.priority || (destIndex + 1);
        const isPrimary = prio === 1;
        const isActive = prio === activePriority;
        const isFailover = isActive && !isPrimary;
        const isEnabled = dest.enabled !== undefined ? Boolean(dest.enabled) : true;

        const stat = destStats[`prio_${prio}`] || {};
        const isHealthy = (stat.status === 'healthy');
        const isDown = (stat.status === 'failed' || stat.status === 'down' || (stat.packet_loss !== undefined && parseInt(stat.packet_loss) >= 100));

        let statusLabel = 'STANDBY';
        let statusClass = 'status-standby';
        if (!isEnabled) {
            statusLabel = 'OFF';
            statusClass = 'status-disabled';
        } else if (isHealthy) {
            statusLabel = 'HEALTHY';
            statusClass = 'status-healthy';
        } else if (isDown) {
            statusLabel = 'DOWN';
            statusClass = 'status-failed';
        } else if (stat.status) {
            statusLabel = String(stat.status).toUpperCase();
        }

        const rawTarget = String(dest.target || '');
        const cleanTarget = rawTarget.toLowerCase().replace(/^\[|\]$/g, "");
        const lossInfo = (stat && stat.loss_50) || (lastLatestLoss && lastLatestLoss[cleanTarget]) || null;
        const loss50Badge = formatLoss50Badge(lossInfo, stat.packet_loss);
        const targetDisplay = rawTarget.includes(':') ? `[${escapeHtml(rawTarget)}]` : escapeHtml(rawTarget);
        const latencyBadge = formatLatencyBadge(stat);
        const tagClass = getPrioTagClass(prio);

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
        if (!isEnabled) {
            pathBoxClasses.push('is-disabled');
        } else if (isActive) {
            pathBoxClasses.push(isFailover ? 'is-failover' : 'is-active');
        }
        if (isDown && isEnabled) {
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
                        ${dest.is_relay ? `<span class="badge-relay-pill" title="Mid Server: The engine anchors on Priority 1 and only fails over here on outage, packet loss, or latency > 150ms.">Mid Server</span>` : ''}
                        <span class="path-status ${statusClass}">
                            <span class="status-indicator"></span>
                            ${statusLabel}
                        </span>
                    </div>
                    <div class="path-header-right">
                        <button type="button" 
                                class="btn-dest-toggle ${isEnabled ? 'is-enabled' : 'is-disabled'}" 
                                onclick="toggleDestinationEnabled(event, decodeURIComponent('${encodedId}'), ${prio})"
                                title="${isEnabled ? 'Priority #' + prio + ' is ON (Click to turn OFF)' : 'Priority #' + prio + ' is OFF (Click to turn ON)'}"
                                aria-label="Toggle Priority #${prio}">
                            <span class="dest-toggle-slider"></span>
                        </button>
                    </div>
                </div>
                <div class="path-dest">
                    <span>${escapeHtml(String(dest.type || 'haproxy').toUpperCase())}: ${targetDisplay}:${escapeHtml(dest.port || rule.port)}</span>
                    <button class="btn-copy" onclick="copyText(decodeURIComponent('${encodeURIComponent(rawTarget)}'))" title="Copy Destination IP">${copyPortSvg}</button>
                </div>
                <div class="path-meta">
                    <span>${metaText}</span>
                    <div class="path-meta-badges">
                        ${latencyBadge}
                        ${loss50Badge}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    const portKey = String(rule.port || "");
    const pTraffic = (lastTrafficData && lastTrafficData.ports) ? lastTrafficData.ports[portKey] : null;
    const trafficPillHtml = pTraffic ? `
        <span class="traffic-pill-badge" onclick="openTrafficModal('port', '${escapeHtml(portKey)}')" title="Billing Cycle Traffic: ↑ ${formatBytes(pTraffic.cycle_tx)} · ↓ ${formatBytes(pTraffic.cycle_rx)} (Click for details & reset)">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
            <span>${formatBytes(pTraffic.cycle_total)}</span>
        </span>
    ` : '';

    return `
        <div class="rule-card" id="rule-card-${encodedId}">
            <div class="rule-top">
                <div class="port-badge">
                    <span class="port-num">:${escapeHtml(rule.port)}</span>
                    <button class="btn-copy" onclick="copyText(decodeURIComponent('${encodeURIComponent(rule.port)}'))" title="Copy Port Number">${copyPortSvg}</button>
                    ${trafficPillHtml}
                    ${rState.switch_pending_seconds > 0 ? `<span class="badge-pending-switch" title="Candidate P${rState.candidate_priority || ''} sustained quality advantage. Switching after streak confirmation."><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>Switch in ${rState.switch_pending_seconds}s</span>` : ''}
                    ${rState.hold_remaining > 0 ? `<span class="badge-cooldown" title="Route held stable to prevent disruption (Min Hold: 10m)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>Hold ${rState.hold_remaining}s</span>` : (rState.cooldown_remaining > 0 ? `<span class="badge-cooldown" title="Post-Critical Cooldown active"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>Cooldown ${rState.cooldown_remaining}s</span>` : '')}
                    ${rState.is_flapping ? `<span class="badge-flapping" title="Repeated route flapping detected. Cooldown extended."><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>Flap Guard</span>` : ''}
                </div>
                <div class="rule-actions">
                    <button class="btn btn-secondary btn-sm" onclick="openTrafficModal('port', '${escapeHtml(portKey)}')" title="Traffic & Bandwidth Analytics">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                    </button>
                    <button class="btn btn-secondary btn-sm btn-rule-copy" onclick="copyRuleJson(decodeURIComponent('${encodedId}'))" title="Copy Port Configuration (JSON)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="openEditRuleModal(decodeURIComponent('${encodedId}'))" title="Edit Rule">
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

export function renderRuleListRow(rule, rulesState) {
    const ruleId = String(rule.id || `rule-${rule.port}`);
    const encodedId = encodeURIComponent(ruleId);
    const rState = (rulesState && rulesState[ruleId]) ? rulesState[ruleId] : {};
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

        const isEnabled = dest.enabled !== undefined ? Boolean(dest.enabled) : true;
        let pillClass = 'rule-list-path-pill';
        if (!isEnabled) pillClass += ' is-disabled';
        else if (isActive) pillClass += (isFailover ? ' is-failover' : ' is-active');
        if (isDown && isEnabled) pillClass += ' is-down';

        let latText = '';
        if (stat.latency_ms !== null && stat.latency_ms !== undefined && stat.latency_ms > 0) {
            latText = ` · ${stat.latency_ms}ms`;
        }

        const rawTarget = String(dest.target || '');
        const cleanTarget = rawTarget.toLowerCase().replace(/^\[|\]$/g, "");
        const lossInfo = (stat && stat.loss_50) || (lastLatestLoss && lastLatestLoss[cleanTarget]) || null;
        const loss50Inline = formatLoss50Inline(lossInfo, stat.packet_loss);
        const targetDisplay = rawTarget.includes(':') ? `[${escapeHtml(rawTarget)}]` : escapeHtml(rawTarget);

        let dotColor = '#6EE7B7';
        if (!isEnabled) dotColor = 'var(--text-muted)';
        else if (isDown) dotColor = '#FB7185';
        else if (!isHealthy) dotColor = '#FBBF6B';

        return `
            <div class="${pillClass}" title="Priority #${prio}: ${escapeHtml(String(dest.type || 'haproxy').toUpperCase())} ${targetDisplay}:${escapeHtml(dest.port || rule.port)}${latText}">
                <span style="width:7px; height:7px; border-radius:50%; background:${dotColor}; display:inline-block;"></span>
                <span style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">#${prio}</span>
                ${dest.is_relay ? `<span class="badge-relay-pill" style="font-size:0.62rem; padding:1px 4px;" title="Mid Server">Mid Server</span>` : ''}
                <span class="font-mono" style="color:var(--text-secondary); font-size:0.75rem;">${targetDisplay}:${escapeHtml(dest.port || rule.port)}</span>
                ${latText && isEnabled ? `<span class="font-mono" style="color:var(--accent-mint); font-size:0.72rem;">${latText}</span>` : ''}
                ${isEnabled ? loss50Inline : ''}
                ${isActive && isEnabled ? `<span style="font-size:0.68rem; font-weight:700; color:${isFailover ? 'var(--accent-amber)' : 'var(--accent-mint)'}; text-transform:uppercase;">${isFailover ? 'FAILOVER' : 'ACTIVE'}</span>` : ''}
                <button type="button" 
                        class="btn-list-dest-toggle ${isEnabled ? 'is-enabled' : 'is-disabled'}" 
                        onclick="toggleDestinationEnabled(event, decodeURIComponent('${encodedId}'), ${prio})"
                        title="${isEnabled ? 'Priority #' + prio + ' is ON (Click to turn OFF)' : 'Priority #' + prio + ' is OFF (Click to turn ON)'}"
                        aria-label="Toggle Priority #${prio}">
                    <span class="dest-toggle-slider"></span>
                </button>
            </div>
        `;
    }).join("");

    const portKey = String(rule.port || "");
    const pTraffic = (lastTrafficData && lastTrafficData.ports) ? lastTrafficData.ports[portKey] : null;
    const trafficPillHtml = pTraffic ? `
        <span class="traffic-pill-badge" onclick="openTrafficModal('port', '${escapeHtml(portKey)}')" title="Billing Cycle Traffic: ↑ ${formatBytes(pTraffic.cycle_tx)} · ↓ ${formatBytes(pTraffic.cycle_rx)} (Click for details & reset)">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
            <span>${formatBytes(pTraffic.cycle_total)}</span>
        </span>
    ` : '';

    return `
        <div class="rule-list-row" id="rule-card-${encodedId}">
            <div class="rule-list-left">
                <span class="rule-list-port">:${escapeHtml(rule.port)}</span>
                <button class="btn-copy" onclick="copyText(decodeURIComponent('${encodeURIComponent(rule.port)}'))" title="Copy Port">${copyPortSvg}</button>
                ${trafficPillHtml}
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
                <button class="btn btn-secondary btn-sm" onclick="openTrafficModal('port', '${escapeHtml(portKey)}')" title="Traffic & Bandwidth Analytics">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                </button>
                <button class="btn btn-secondary btn-sm btn-rule-copy" onclick="copyRuleJson(decodeURIComponent('${encodedId}'))" title="Copy Port Configuration (JSON)">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                </button>
                <button class="btn btn-secondary btn-sm" onclick="openEditRuleModal(decodeURIComponent('${encodedId}'))" title="Edit Rule">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                </button>
                <button class="btn btn-secondary btn-sm" onclick="deleteRule(decodeURIComponent('${encodedId}'))" title="Delete Rule">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </div>
        </div>
    `;
}

export function renderRules(rules, runtime) {
    const rulesContainer = document.getElementById("rulesContainer");
    if (!rulesContainer) return;

    if (draggedPathInfo !== null) {
        return;
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

    const filtered = rules.filter(rule => {
        const ruleId = String(rule.id || `rule-${rule.port}`).toLowerCase();
        const portStr = String(rule.port || "");
        const protoStr = String(rule.protocol || "both").toLowerCase();
        const protoSearchStr = protoStr === "both" ? "tcp udp both tcp+udp" : protoStr;
        const catStr = String(rule.category || "").toLowerCase();

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

    const sorted = sortRulesList(filtered, currentSort, rulesState);
    const hasAnyCategory = sorted.some(r => Boolean((r.category || "").trim()));

    if (!hasAnyCategory) {
        const itemsHtml = sorted.map(rule => currentViewMode === "list" ? renderRuleListRow(rule, rulesState) : renderRuleCard(rule, rulesState)).join("");
        rulesContainer.className = currentViewMode === "list" ? "rules-list-container" : "rules-container";
        rulesContainer.innerHTML = itemsHtml;
    } else {
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

        rulesContainer.className = "";
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
                        <button type="button" class="btn-category-copy" onclick="copyCategoryJson(decodeURIComponent('${encodeURIComponent(catKey)}'))" title="Copy all ports in category '${catTitle}' as JSON">
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

export async function handleOverrideChange(ruleId, val, fetchStatusCallback) {
    const prioVal = parseInt(val, 10);
    pendingOverrides.set(ruleId, {
        force_override: prioVal,
        active_priority: prioVal > 0 ? prioVal : undefined,
        timestamp: Date.now()
    });

    const rule = (currentRules || []).find(x => String(x.id || `rule-${x.port}`) === ruleId);
    if (rule) {
        rule.force_override = prioVal;
        if (prioVal > 0) {
            rule.active_priority = prioVal;
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
            showToast(prioVal > 0 ? `Manually forced Priority #${prioVal}` : "Restored to Automatic Failover");
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        } else {
            showToast(data.error || "Failed to update override mode", "error");
        }
    } catch (_) {
        showToast("Network error updating override mode", "error");
    }
}

export async function toggleDestinationEnabled(event, ruleId, prio, fetchStatusCallback) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    const rule = (currentRules || []).find(r => String(r.id || `rule-${r.port}`) === ruleId);
    if (!rule || !Array.isArray(rule.destinations)) return;

    const dest = rule.destinations.find(d => (d.priority || 1) === prio);
    if (!dest) return;

    const currentEnabled = dest.enabled !== undefined ? Boolean(dest.enabled) : true;
    const newEnabled = !currentEnabled;

    // Optimistic UI update
    dest.enabled = newEnabled;
    if (!newEnabled && rule.active_priority === prio) {
        const nextEnabled = rule.destinations.find(d => (d.priority || 1) !== prio && (d.enabled !== false));
        if (nextEnabled) {
            rule.active_priority = nextEnabled.priority || 1;
        }
    }
    renderRules(currentRules, lastRuntime);

    try {
        const res = await fetch(`${API_BASE}/rule/toggle-destination`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                rule_id: ruleId,
                priority: prio,
                enabled: newEnabled
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Priority #${prio} turned ${newEnabled ? "ON" : "OFF"}`);
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        } else {
            // Revert on failure
            dest.enabled = currentEnabled;
            renderRules(currentRules, lastRuntime);
            showToast(data.error || "Failed to update priority status", "error");
        }
    } catch (_) {
        dest.enabled = currentEnabled;
        renderRules(currentRules, lastRuntime);
        showToast("Network error updating priority status", "error");
    }
}

export async function deleteRule(ruleId, fetchStatusCallback) {
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
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        } else {
            showToast(data.error || "Failed to delete rule", "error");
        }
    } catch (_) {
        showToast("Error deleting rule", "error");
    }
}

export function initRulesViewControls(fetchStatusCallback) {
    const btnViewCards = document.getElementById("btnViewCards");
    const btnViewList = document.getElementById("btnViewList");
    const selectSort = document.getElementById("selectSortRules");
    const searchInput = document.getElementById("searchInput") || document.getElementById("searchRulesInput");
    const btnClearSearch = document.getElementById("btnClearSearch");

    if (btnViewCards && btnViewList) {
        if (currentViewMode === "list") {
            btnViewList.classList.add("active");
            btnViewCards.classList.remove("active");
        } else {
            btnViewCards.classList.add("active");
            btnViewList.classList.remove("active");
        }

        btnViewCards.addEventListener("click", () => {
            currentViewMode = "cards";
            localStorage.setItem("xfwd_rules_view", "cards");
            btnViewCards.classList.add("active");
            btnViewList.classList.remove("active");
            renderRules(currentRules, lastRuntime);
        });

        btnViewList.addEventListener("click", () => {
            currentViewMode = "list";
            localStorage.setItem("xfwd_rules_view", "list");
            btnViewList.classList.add("active");
            btnViewCards.classList.remove("active");
            renderRules(currentRules, lastRuntime);
        });
    }

    if (selectSort) {
        selectSort.value = currentSort;
        selectSort.addEventListener("change", (e) => {
            currentSort = e.target.value;
            localStorage.setItem("xfwd_rules_sort", currentSort);
            renderRules(currentRules, lastRuntime);
        });
    }

    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            if (btnClearSearch) btnClearSearch.style.display = searchQuery ? "block" : "none";
            renderRules(currentRules, lastRuntime);
        });
    }

    if (btnClearSearch && searchInput) {
        btnClearSearch.addEventListener("click", () => {
            searchInput.value = "";
            searchQuery = "";
            btnClearSearch.style.display = "none";
            renderRules(currentRules, lastRuntime);
        });
    }

    const filterTabs = document.querySelectorAll(".filter-tab");
    filterTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            filterTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            activeFilter = tab.getAttribute("data-filter") || "all";
            renderRules(currentRules, lastRuntime);
        });
    });
}
