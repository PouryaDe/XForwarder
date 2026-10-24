// ============================================================================
// XForwarder Web UI - Traffic & Bandwidth Subsystem (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { formatBytes, showToast, escapeHtml, askConfirm } from "./utils.js";
import { currentRules, lastRuntime, lastTrafficData } from "./state.js";

let currentTrafficEntity = "all:all";
let currentTrafficPeriod = "24h";
let trafficModalLoading = false;

export function populateTrafficEntitySelect(selectedType, selectedId) {
    const portOptgroup = document.getElementById("trafficPortOptgroup");
    const typeOptgroup = document.getElementById("trafficTypeOptgroup");
    const tunnelOptgroup = document.getElementById("trafficTunnelOptgroup");
    const entitySelect = document.getElementById("trafficEntitySelect");
    if (!entitySelect) return;

    if (portOptgroup) {
        if (currentRules && currentRules.length > 0) {
            portOptgroup.innerHTML = currentRules
                .slice()
                .sort((a, b) => (Number(a.port) || 0) - (Number(b.port) || 0))
                .map(r => {
                    const cat = r.category ? ` [${r.category}]` : "";
                    return `<option value="port:${r.port}">Port :${escapeHtml(r.port)}${escapeHtml(cat)}</option>`;
                })
                .join("");
        } else {
            portOptgroup.innerHTML = `<option disabled>No forwarded ports</option>`;
        }
    }

    if (typeOptgroup) {
        typeOptgroup.innerHTML = `
            <option value="method:haproxy">Direct IPv6 Relay (HAProxy)</option>
            <option value="method:nftables">Kernel Tunnel DNAT (NFTables)</option>
            <option value="tunnel_type:gre">GRE Tunnels (gre*)</option>
            <option value="tunnel_type:ipip">IPIP Tunnels (ipip*)</option>
            <option value="tunnel_type:wireguard">WireGuard / AWG (awg*)</option>
        `;
    }

    if (tunnelOptgroup) {
        const tunnels = (lastRuntime && lastRuntime.tunnel_interfaces) || (lastTrafficData && lastTrafficData.tunnels ? Object.keys(lastTrafficData.tunnels).map(name => ({ name })) : []);
        const tunnelNames = Array.from(new Set(tunnels.map(t => (typeof t === 'string' ? t : t.name)).filter(Boolean)));
        if (tunnelNames.length > 0) {
            tunnelOptgroup.innerHTML = tunnelNames
                .sort()
                .map(name => `<option value="tunnel:${escapeHtml(name)}">Tunnel Interface: ${escapeHtml(name)}</option>`)
                .join("");
        } else {
            tunnelOptgroup.innerHTML = `<option disabled>No active tunnel devices</option>`;
        }
    }

    const targetVal = `${selectedType}:${selectedId}`;
    if (Array.from(entitySelect.options).some(o => o.value === targetVal)) {
        entitySelect.value = targetVal;
    } else {
        entitySelect.value = "all:all";
    }
}

export function openTrafficModal(entityType = "all", entityId = "all") {
    const modal = document.getElementById("trafficModal");
    if (!modal) return;

    currentTrafficEntity = `${entityType}:${entityId}`;
    populateTrafficEntitySelect(entityType, entityId);

    const pills = document.querySelectorAll("#trafficPeriodPills .period-pill");
    pills.forEach(p => {
        if (p.getAttribute("data-period") === currentTrafficPeriod) {
            p.classList.add("active");
        } else {
            p.classList.remove("active");
        }
    });

    modal.classList.add("show");
    loadTrafficModalData();
}

export function closeTrafficModal() {
    const modal = document.getElementById("trafficModal");
    if (modal) modal.classList.remove("show");
}

export function handleTrafficEntityChange() {
    const entitySelect = document.getElementById("trafficEntitySelect");
    if (!entitySelect) return;
    currentTrafficEntity = entitySelect.value || "all:all";
    loadTrafficModalData();
}

export function handleTrafficPeriodChange(period) {
    currentTrafficPeriod = period;
    const pills = document.querySelectorAll("#trafficPeriodPills .period-pill");
    pills.forEach(p => {
        if (p.getAttribute("data-period") === period) {
            p.classList.add("active");
        } else {
            p.classList.remove("active");
        }
    });
    loadTrafficModalData();
}

export function renderTrafficBreakdown(summary, entityType, entityId) {
    const section = document.getElementById("trafficBreakdownSection");
    const grid = document.getElementById("trafficBreakdownGrid");
    const titleEl = document.getElementById("trafficBreakdownTitle");
    const subEl = document.getElementById("trafficBreakdownSubtitle");
    if (!section || !grid) return;

    let items = [];
    if (entityType === "port" && summary.path_breakdown && summary.path_breakdown.length > 0) {
        if (titleEl) titleEl.textContent = `Port :${entityId} Relay Paths Breakdown`;
        if (subEl) subEl.textContent = "Traffic divided by active forwarding path";
        items = summary.path_breakdown;
    } else if (summary.type_breakdown && summary.type_breakdown.length > 0) {
        if (titleEl) titleEl.textContent = "Forwarding Methods & Tunnel Types Breakdown";
        if (subEl) subEl.textContent = "Distribution across Direct IPv6 and tunnel protocols";
        items = summary.type_breakdown;
    }

    if (!items || items.length === 0) {
        section.style.display = "none";
        return;
    }

    section.style.display = "flex";

    const colors = [
        "var(--accent-mint)",
        "var(--accent-cyan)",
        "var(--accent-violet)",
        "var(--accent-amber)",
        "var(--accent-rose)",
        "var(--accent-blue)"
    ];

    grid.innerHTML = items.map((it, idx) => {
        const color = colors[idx % colors.length];
        const pct = Math.min(100, Math.max(0, it.percentage || 0));
        const total = it.total_bytes || 0;
        const tx = it.tx_bytes || 0;
        const rx = it.rx_bytes || 0;

        return `
            <div class="breakdown-card">
                <div class="breakdown-card-top">
                    <span class="breakdown-name" title="${escapeHtml(it.label)}">${escapeHtml(it.label)}</span>
                    <span class="breakdown-pct-chip" style="color:${color}; background:${color}1f;">${pct}%</span>
                </div>
                <div class="breakdown-bar-track">
                    <div class="breakdown-bar-fill" style="width:${pct}%; background:${color};"></div>
                </div>
                <div class="breakdown-meta-row">
                    <span style="font-weight:700; color:var(--text-primary);">${formatBytes(total)}</span>
                    <span>↑ ${formatBytes(tx)} · ↓ ${formatBytes(rx)}</span>
                </div>
            </div>
        `;
    }).join("");
}

export function renderTrafficBarsChart(rows) {
    const container = document.getElementById("trafficBarsContainer");
    if (!container) return;

    if (!rows || rows.length === 0) {
        container.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;color:var(--text-muted);font-size:0.8rem;">
                No traffic recorded during this period yet.
            </div>
        `;
        return;
    }

    const maxVal = Math.max(...rows.map(r => r.total_bytes || 0), 1);

    container.innerHTML = rows.map(r => {
        const total = r.total_bytes || 0;
        const tx = r.tx_bytes || 0;
        const rx = r.rx_bytes || 0;

        const stackHeightPct = total > 0 ? Math.min(100, Math.max(4, Math.round((total / maxVal) * 100))) : 2;
        const txPct = total > 0 ? Math.round((tx / total) * 100) : 50;
        const rxPct = 100 - txPct;

        let label = r.period || r.label || "";
        if (currentTrafficPeriod === "24h" && label.includes(" ")) {
            label = label.split(" ")[1] || label;
        } else if ((currentTrafficPeriod === "7d" || currentTrafficPeriod === "30d") && label.includes("-")) {
            const parts = label.split("-");
            if (parts.length === 3) label = `${parts[1]}/${parts[2]}`;
        }

        const fullTime = r.period || r.label || "";

        return `
            <div class="traffic-bar-col">
                <div class="traffic-tooltip">
                    <strong>${escapeHtml(fullTime)}</strong>
                    <div style="margin-top:4px;">Total: <b>${formatBytes(total)}</b></div>
                    <div style="color:var(--accent-mint);">Upload (TX): ${formatBytes(tx)}</div>
                    <div style="color:var(--accent-cyan);">Download (RX): ${formatBytes(rx)}</div>
                </div>
                <div class="traffic-bar-stack" style="height:${stackHeightPct}%;">
                    <div class="traffic-bar-segment segment-tx" style="height:${txPct}%;"></div>
                    <div class="traffic-bar-segment segment-rx" style="height:${rxPct}%;"></div>
                </div>
                <span class="traffic-bar-label">${escapeHtml(label)}</span>
            </div>
        `;
    }).join("");
}

export function renderTrafficTable(rows) {
    const tableBody = document.getElementById("trafficTableBody");
    if (!tableBody) return;

    if (!rows || rows.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No records found for this period.</td></tr>`;
        return;
    }

    const totalSum = rows.reduce((acc, r) => acc + (r.total_bytes || 0), 0) || 1;
    const reversed = rows.slice().reverse();

    tableBody.innerHTML = reversed.map(r => {
        const total = r.total_bytes || 0;
        const tx = r.tx_bytes || 0;
        const rx = r.rx_bytes || 0;
        const sharePct = Math.min(100, Math.round((total / totalSum) * 100));
        const timeLabel = r.period || r.label || "";

        return `
            <tr>
                <td style="color:var(--text-primary); font-weight:600;">${escapeHtml(timeLabel)}</td>
                <td><span class="text-cyan font-mono">↓ ${formatBytes(rx)}</span></td>
                <td><span class="text-mint font-mono">↑ ${formatBytes(tx)}</span></td>
                <td><span class="text-violet font-mono" style="font-weight:700;">${formatBytes(total)}</span></td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="flex:1; height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                            <div style="width:${sharePct}%; height:100%; background:var(--accent-mint);"></div>
                        </div>
                        <span style="font-size:0.7rem; color:var(--text-muted);">${sharePct}%</span>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

export async function loadTrafficModalData() {
    if (trafficModalLoading) return;
    trafficModalLoading = true;

    const [entityType, entityId] = currentTrafficEntity.split(":");
    const titleEl = document.getElementById("trafficModalTitle");
    const subEl = document.getElementById("trafficModalSubtitle");
    const tableBody = document.getElementById("trafficTableBody");
    const recordsCountEl = document.getElementById("trafficRecordsCount");

    if (titleEl) {
        if (entityType === "all") {
            titleEl.textContent = "Global Traffic & Bandwidth Analytics";
            if (subEl) subEl.textContent = "Aggregated usage across all forwarded ports and kernel tunnels";
        } else if (entityType === "port") {
            titleEl.textContent = `Port :${entityId} Bandwidth Analytics`;
            if (subEl) subEl.textContent = `Traffic accounting for forwarded port ${entityId} (HAProxy / NFTables / Nginx)`;
        } else if (entityType === "method") {
            const methodLabel = entityId === "haproxy" ? "Direct IPv6 (HAProxy Relay)" : "Kernel Tunnel DNAT (NFTables)";
            titleEl.textContent = `${methodLabel} Analytics`;
            if (subEl) subEl.textContent = `Aggregated bandwidth forwarded via ${methodLabel}`;
        } else if (entityType === "tunnel_type") {
            const tLabel = entityId.toUpperCase();
            titleEl.textContent = `${tLabel} Tunnels Bandwidth Analytics`;
            if (subEl) subEl.textContent = `Aggregated bandwidth for all ${tLabel} virtual interfaces`;
        } else if (entityType === "tunnel") {
            titleEl.textContent = `Tunnel Interface ${entityId} Analytics`;
            if (subEl) subEl.textContent = `Kernel device accounting for virtual interface ${entityId}`;
        }
    }

    try {
        const url = `${API_BASE}/traffic/summary?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}&period=${encodeURIComponent(currentTrafficPeriod)}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to load traffic metrics");
        const data = await res.json();

        const summary = data.summary || {};
        const rows = data.rows || [];

        const rxEl = document.getElementById("trafficStatRx");
        const txEl = document.getElementById("trafficStatTx");
        const totalEl = document.getElementById("trafficStatTotal");
        const peakEl = document.getElementById("trafficStatPeak");

        if (rxEl) rxEl.textContent = formatBytes(summary.total_rx_bytes || 0);
        if (txEl) txEl.textContent = formatBytes(summary.total_tx_bytes || 0);
        if (totalEl) totalEl.textContent = formatBytes(summary.total_bytes || 0);
        if (peakEl) peakEl.textContent = formatBytes(summary.peak_hour_bytes || 0);

        renderTrafficBarsChart(rows);
        renderTrafficTable(rows);
        renderTrafficBreakdown(summary, entityType, entityId);

        if (recordsCountEl) {
            recordsCountEl.textContent = `${rows.length} time slice(s)`;
        }
    } catch (err) {
        showToast("Error loading traffic data: " + err.message, "error");
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-rose">Failed to load analytics: ${escapeHtml(err.message)}</td></tr>`;
        }
    } finally {
        trafficModalLoading = false;
    }
}

export async function triggerTrafficResetFromModal(fetchStatusCallback) {
    const [entityType, entityId] = currentTrafficEntity.split(":");
    const targetLabel = entityType === "all" ? "ALL ports and tunnels" : (entityType === "port" ? `Port :${entityId}` : `Tunnel ${entityId}`);

    const confirmed = await askConfirm(
        `Reset Billing Cycle?`,
        `Reset current billing cycle counter for ${targetLabel}? Current usage will reset to 0, and historical hourly records will remain intact.`
    );
    if (!confirmed) return;

    try {
        const res = await fetch(`${API_BASE}/traffic/reset`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                entity_type: entityType,
                entity_id: entityId,
                wipe_history: false
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Billing cycle reset successfully for ${targetLabel}!`, "success");
            loadTrafficModalData();
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        } else {
            showToast(data.error || "Failed to reset traffic cycle", "error");
        }
    } catch (err) {
        showToast("Error resetting traffic: " + err.message, "error");
    }
}

export async function triggerWipeHistoryFromModal(fetchStatusCallback) {
    const [entityType, entityId] = currentTrafficEntity.split(":");
    const targetLabel = entityType === "all" ? "ALL ports and tunnels" : (entityType === "port" ? `Port :${entityId}` : `Tunnel ${entityId}`);

    const confirmed = await askConfirm(
        `Wipe All Traffic History?`,
        `DANGER: Permanently wipe ALL recorded historical traffic data for ${targetLabel}? This cannot be undone.`
    );
    if (!confirmed) return;

    try {
        const res = await fetch(`${API_BASE}/traffic/reset`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                entity_type: entityType,
                entity_id: entityId,
                wipe_history: true
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Traffic history permanently wiped for ${targetLabel}!`, "info");
            loadTrafficModalData();
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        } else {
            showToast(data.error || "Failed to wipe traffic history", "error");
        }
    } catch (err) {
        showToast("Error wiping traffic: " + err.message, "error");
    }
}

export async function promptResetTraffic(entityType, entityId, fetchStatusCallback) {
    const targetLabel = entityType === "port" ? `Port :${entityId}` : `Tunnel ${entityId}`;
    const confirmed = await askConfirm(
        `Reset Traffic for ${targetLabel}?`,
        `Reset the current billing cycle counter for ${targetLabel} to 0? Historical hourly analytics will be preserved.`
    );
    if (!confirmed) return;

    try {
        const res = await fetch(`${API_BASE}/traffic/reset`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                entity_type: entityType,
                entity_id: entityId,
                wipe_history: false
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            showToast(`Billing cycle reset for ${targetLabel}!`, "success");
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        } else {
            showToast(data.error || "Failed to reset traffic", "error");
        }
    } catch (err) {
        showToast("Error resetting traffic: " + err.message, "error");
    }
}

export function initTrafficAnalytics() {
    const btnOpen = document.getElementById("btnOpenTrafficModal");
    if (btnOpen) {
        btnOpen.addEventListener("click", () => openTrafficModal("all", "all"));
    }

    const btnClose = document.getElementById("btnCloseTrafficModal");
    if (btnClose) {
        btnClose.addEventListener("click", closeTrafficModal);
    }

    const btnCloseFooter = document.getElementById("btnCloseTrafficModalFooter");
    if (btnCloseFooter) {
        btnCloseFooter.addEventListener("click", closeTrafficModal);
    }

    const modal = document.getElementById("trafficModal");
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                closeTrafficModal();
            }
        });
    }

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal && modal.classList.contains("show")) {
            closeTrafficModal();
        }
    });

    const entitySelect = document.getElementById("trafficEntitySelect");
    if (entitySelect) {
        entitySelect.addEventListener("change", handleTrafficEntityChange);
    }

    const pills = document.querySelectorAll("#trafficPeriodPills .period-pill");
    pills.forEach(p => {
        p.addEventListener("click", () => {
            const period = p.getAttribute("data-period");
            if (period) handleTrafficPeriodChange(period);
        });
    });

    const btnResetCycle = document.getElementById("btnTrafficResetCycle");
    if (btnResetCycle) {
        btnResetCycle.addEventListener("click", () => triggerTrafficResetFromModal());
    }

    const btnWipeHistory = document.getElementById("btnTrafficWipeHistory");
    if (btnWipeHistory) {
        btnWipeHistory.addEventListener("click", () => triggerWipeHistoryFromModal());
    }
}
