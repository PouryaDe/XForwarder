// ============================================================================
// XForwarder Web UI - Traffic & Bandwidth Subsystem (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { formatBytes, showToast, escapeHtml, askConfirm } from "./utils.js";
import { currentRules, lastRuntime, lastTrafficData } from "./state.js";
import { t } from "./i18n.js";

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
    const totalBars = rows.length;

    container.innerHTML = rows.map((r, idx) => {
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
        const isPeak = total === maxVal && total > 0;

        let posClass = "pos-center";
        if (idx < 3) posClass = "pos-left";
        else if (idx >= totalBars - 3) posClass = "pos-right";

        return `
            <div class="traffic-bar-col ${posClass}">
                <div class="traffic-tooltip">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:3px; margin-bottom:2px;">
                        <strong style="color:var(--text-primary); font-size:0.75rem;">${escapeHtml(fullTime)}</strong>
                        ${isPeak ? `<span style="font-size:0.6rem; font-weight:800; background:rgba(251,191,36,0.18); color:var(--accent-amber); border:1px solid rgba(251,191,36,0.4); padding:1px 4px; border-radius:4px;">PEAK</span>` : ""}
                    </div>
                    <div style="font-weight:700; color:#fff;">Total: <span style="color:var(--accent-cyan); font-weight:800;">${formatBytes(total)}</span></div>
                    <div style="display:flex; flex-direction:column; gap:2px; font-size:0.68rem; margin-top:2px;">
                        <span style="color:var(--accent-mint); display:inline-flex; align-items:center; gap:4px;"><span style="width:6px;height:6px;border-radius:1px;background:var(--accent-mint);display:inline-block;"></span>↑ TX: <b>${formatBytes(tx)}</b> (${txPct}%)</span>
                        <span style="color:var(--accent-cyan); display:inline-flex; align-items:center; gap:4px;"><span style="width:6px;height:6px;border-radius:1px;background:var(--accent-cyan);display:inline-block;"></span>↓ RX: <b>${formatBytes(rx)}</b> (${rxPct}%)</span>
                    </div>
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
    const barsContainer = document.getElementById("trafficBarsContainer");

    // Immediate loading feedback for user
    if (tableBody) {
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted"><span class="btn-spinner" style="width:14px;height:14px;display:inline-block;vertical-align:middle;margin-right:8px;"></span> Loading traffic records...</td></tr>`;
    }
    if (barsContainer) {
        barsContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;width:100%;color:var(--text-muted);font-size:0.85rem;"><span class="btn-spinner" style="width:14px;height:14px;display:inline-block;vertical-align:middle;margin-right:8px;"></span> Loading timeline chart...</div>`;
    }
    if (recordsCountEl) {
        recordsCountEl.textContent = "Loading...";
    }

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
        const [sumRes, tsRes] = await Promise.all([
            fetch(`${API_BASE}/traffic/summary?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}&period=${encodeURIComponent(currentTrafficPeriod)}`),
            fetch(`${API_BASE}/traffic/timeseries?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}&period=${encodeURIComponent(currentTrafficPeriod)}`)
        ]);

        const sumJson = sumRes.ok ? await sumRes.json().catch(() => ({})) : {};
        const tsJson = tsRes.ok ? await tsRes.json().catch(() => ({})) : {};

        const summary = (sumJson && sumJson.data) ? sumJson.data : (sumJson || {});
        const rows = (tsJson && Array.isArray(tsJson.data)) ? tsJson.data : (Array.isArray(tsJson) ? tsJson : []);

        const rxEl = document.getElementById("kpiTotalRx") || document.getElementById("trafficStatRx");
        const txEl = document.getElementById("kpiTotalTx") || document.getElementById("trafficStatTx");
        const totalEl = document.getElementById("kpiTotalBytes") || document.getElementById("trafficStatTotal");
        const peakEl = document.getElementById("trafficStatPeak");
        const cycleTotalEl = document.getElementById("kpiCycleTotal");
        const cycleMetaEl = document.getElementById("kpiCycleMeta");

        const totalRx = summary.total_rx_bytes !== undefined ? summary.total_rx_bytes : (summary.total_rx !== undefined ? summary.total_rx : (summary.rx_bytes || 0));
        const totalTx = summary.total_tx_bytes !== undefined ? summary.total_tx_bytes : (summary.total_tx !== undefined ? summary.total_tx : (summary.tx_bytes || 0));
        const totalBytes = summary.total_bytes || 0;

        if (rxEl) rxEl.textContent = formatBytes(totalRx);
        if (txEl) txEl.textContent = formatBytes(totalTx);
        if (totalEl) totalEl.textContent = formatBytes(totalBytes);
        if (peakEl) peakEl.textContent = formatBytes(summary.peak_hour_bytes || 0);

        const cycleBytes = summary.cycle_bytes !== undefined ? summary.cycle_bytes : (summary.cycle_total !== undefined ? summary.cycle_total : 0);
        if (cycleTotalEl) cycleTotalEl.textContent = formatBytes(cycleBytes);
        if (cycleMetaEl) {
            if (summary.reset_timestamp) {
                const dt = new Date(summary.reset_timestamp * 1000);
                cycleMetaEl.textContent = `Reset: ${dt.toLocaleDateString()} ${dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            } else {
                cycleMetaEl.textContent = "Active since service install";
            }
        }

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
        if (barsContainer) {
            barsContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;width:100%;color:var(--text-rose);font-size:0.82rem;">Failed to load timeline: ${escapeHtml(err.message)}</div>`;
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

    // Overview 24h Daily Traffic Range Tabs & Refresh
    const btnOv24h = document.getElementById("btnOvTraffic24h");
    if (btnOv24h && !btnOv24h._xfwdBound) {
        btnOv24h._xfwdBound = true;
        btnOv24h.addEventListener("click", () => loadOverviewTrafficChart("24h"));
    }
    const btnOv7d = document.getElementById("btnOvTraffic7d");
    if (btnOv7d && !btnOv7d._xfwdBound) {
        btnOv7d._xfwdBound = true;
        btnOv7d.addEventListener("click", () => loadOverviewTrafficChart("7d"));
    }
    const btnRefreshOv = document.getElementById("btnRefreshOvTraffic");
    if (btnRefreshOv && !btnRefreshOv._xfwdBound) {
        btnRefreshOv._xfwdBound = true;
        btnRefreshOv.addEventListener("click", async () => {
            btnRefreshOv.classList.add("spinning");
            await loadOverviewTrafficChart();
            setTimeout(() => btnRefreshOv.classList.remove("spinning"), 400);
        });
    }
}

// ── Overview Page Daily Traffic Chart & KPIs ──
let currentOverviewPeriod = "24h";
let overviewTrafficLoading = false;

export async function loadOverviewTrafficChart(period = currentOverviewPeriod) {
    if (typeof period !== "string" || (period !== "24h" && period !== "7d")) {
        period = (currentOverviewPeriod === "7d") ? "7d" : "24h";
    }
    if (overviewTrafficLoading) return;
    overviewTrafficLoading = true;
    currentOverviewPeriod = period;

    const barsContainer = document.getElementById("ovTrafficBarsContainer");
    const kpiTotal = document.getElementById("ovTrafficCardTotal");
    const kpiRx = document.getElementById("ovTrafficCardRx");
    const kpiTx = document.getElementById("ovTrafficCardTx");
    const kpiPeak = document.getElementById("ovTrafficCardPeak");
    const kpiPeakTime = document.getElementById("ovTrafficCardPeakTime");
    const rangeBadge = document.getElementById("ovTrafficRangeBadge");
    const chartTitle = document.getElementById("ovTrafficChartRangeTitle");

    if (rangeBadge) rangeBadge.textContent = period === "24h" ? "Past 24 Hours" : "Past 7 Days";
    if (chartTitle) chartTitle.textContent = period === "24h" ? "Past 24 Hours" : "Past 7 Days";

    // Range tabs active state
    const btn24h = document.getElementById("btnOvTraffic24h");
    const btn7d = document.getElementById("btnOvTraffic7d");
    if (btn24h) btn24h.classList.toggle("active", period === "24h");
    if (btn7d) btn7d.classList.toggle("active", period === "7d");

    const ticks = document.getElementById("ovTrafficTimelineTicks");
    if (ticks) {
        if (period === "24h") {
            ticks.innerHTML = `<span>24h ago</span><span>18h ago</span><span>12h ago</span><span>6h ago</span><span>Now</span>`;
        } else {
            ticks.innerHTML = `<span>7d ago</span><span>5d ago</span><span>3d ago</span><span>1d ago</span><span>Today</span>`;
        }
    }

    try {
        const [sumRes, tsRes] = await Promise.all([
            fetch(`${API_BASE}/traffic/summary?entity_type=all&entity_id=all&period=${encodeURIComponent(period)}`),
            fetch(`${API_BASE}/traffic/timeseries?entity_type=all&entity_id=all&period=${encodeURIComponent(period)}`)
        ]);

        const sumJson = sumRes.ok ? await sumRes.json().catch(() => ({})) : {};
        const tsJson = tsRes.ok ? await tsRes.json().catch(() => ({})) : {};

        const summary = (sumJson && sumJson.data) ? sumJson.data : (sumJson || {});
        const rows = (tsJson && Array.isArray(tsJson.data)) ? tsJson.data : (Array.isArray(tsJson) ? tsJson : []);

        const totalRx = summary.total_rx_bytes !== undefined ? summary.total_rx_bytes : (summary.total_rx !== undefined ? summary.total_rx : (summary.rx_bytes || 0));
        const totalTx = summary.total_tx_bytes !== undefined ? summary.total_tx_bytes : (summary.total_tx !== undefined ? summary.total_tx : (summary.tx_bytes || 0));
        const totalBytes = summary.total_bytes || 0;

        if (kpiTotal) kpiTotal.textContent = formatBytes(totalBytes);
        if (kpiRx) kpiRx.textContent = `↓ ${formatBytes(totalRx)}`;
        if (kpiTx) kpiTx.textContent = `↑ ${formatBytes(totalTx)}`;

        // Peak computation
        if (rows.length > 0) {
            let maxRow = rows[0];
            rows.forEach(r => {
                if ((r.total_bytes || 0) > (maxRow.total_bytes || 0)) maxRow = r;
            });
            const pVal = maxRow.total_bytes || 0;
            let pLabel = maxRow.period || maxRow.label || "";
            if (pLabel.includes(" ")) pLabel = pLabel.split(" ")[1] || pLabel;
            if (kpiPeak) kpiPeak.textContent = pVal > 0 ? `${formatBytes(pVal)}/${period === "24h" ? "h" : "d"}` : "0 B";
            if (kpiPeakTime) kpiPeakTime.textContent = pVal > 0 ? `Peak window at ${pLabel}` : "No peak usage recorded";
        } else {
            if (kpiPeak) kpiPeak.textContent = "0 B";
            if (kpiPeakTime) kpiPeakTime.textContent = "No data recorded";
        }

        renderOverviewTrafficBars(rows, period);
        renderOverviewMethods(summary);
    } catch (err) {
        console.warn("Error loading overview traffic:", err);
        if (barsContainer) {
            barsContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;width:100%;color:var(--text-muted);font-size:0.8rem;">Traffic data unavailable (${escapeHtml(err.message)})</div>`;
        }
    } finally {
        overviewTrafficLoading = false;
    }
}

export function renderOverviewTrafficBars(rows, period) {
    const container = document.getElementById("ovTrafficBarsContainer");
    if (!container) return;

    if (!rows || rows.length === 0) {
        container.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;color:var(--text-muted);font-size:0.8rem;gap:8px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <span>No traffic recorded during this period yet. Data automatically aggregates every ~30s.</span>
            </div>
        `;
        return;
    }

    const maxVal = Math.max(...rows.map(r => r.total_bytes || 0), 1);
    const midVal = maxVal / 2;

    const gridHtml = `
        <div class="ov-traffic-grid" aria-hidden="true">
            <div class="ov-grid-line line-peak"><span class="ov-grid-val">${maxVal > 1 ? formatBytes(maxVal) : "Peak"}</span></div>
            <div class="ov-grid-line line-mid"><span class="ov-grid-val">${maxVal > 1 ? formatBytes(midVal) : ""}</span></div>
            <div class="ov-grid-line line-zero"><span class="ov-grid-val">0 B</span></div>
        </div>
    `;

    const totalBars = rows.length;

    const barsHtml = rows.map((r, idx) => {
        const total = r.total_bytes || 0;
        const tx = r.tx_bytes || 0;
        const rx = r.rx_bytes || 0;

        const stackHeightPct = total > 0 ? Math.min(100, Math.max(6, Math.round((total / maxVal) * 100))) : 2;
        const txPct = total > 0 ? Math.round((tx / total) * 100) : 0;
        const rxPct = total > 0 ? (100 - txPct) : 0;

        let label = r.period || r.label || "";
        if (period === "24h" && label.includes(" ")) {
            label = label.split(" ")[1] || label;
        } else if (label.includes("-")) {
            const parts = label.split("-");
            if (parts.length === 3) label = `${parts[1]}/${parts[2]}`;
        }

        const fullTime = r.period || r.label || "";
        const isPeak = total === maxVal && total > 0;

        // Smart position alignment to keep tooltip cleanly within viewport bounds
        let posClass = "pos-center";
        if (idx < 3) posClass = "pos-left";
        else if (idx >= totalBars - 3) posClass = "pos-right";

        return `
            <div class="traffic-bar-col ${posClass}">
                <div class="traffic-tooltip">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:3px; margin-bottom:2px;">
                        <strong style="color:var(--text-primary); font-size:0.75rem;">${escapeHtml(fullTime)}</strong>
                        ${isPeak ? `<span style="font-size:0.6rem; font-weight:800; background:rgba(251,191,36,0.18); color:var(--accent-amber); border:1px solid rgba(251,191,36,0.4); padding:1px 4px; border-radius:4px;">PEAK</span>` : ""}
                    </div>
                    <div style="font-weight:700; color:#fff;">Total: <span style="color:var(--accent-cyan); font-weight:800;">${formatBytes(total)}</span></div>
                    <div style="display:flex; flex-direction:column; gap:2px; font-size:0.68rem; margin-top:2px;">
                        <span style="color:var(--accent-mint); display:inline-flex; align-items:center; gap:4px;"><span style="width:6px;height:6px;border-radius:1px;background:var(--accent-mint);display:inline-block;"></span>↑ TX: <b>${formatBytes(tx)}</b> (${txPct}%)</span>
                        <span style="color:var(--accent-cyan); display:inline-flex; align-items:center; gap:4px;"><span style="width:6px;height:6px;border-radius:1px;background:var(--accent-cyan);display:inline-block;"></span>↓ RX: <b>${formatBytes(rx)}</b> (${rxPct}%)</span>
                    </div>
                </div>
                <div class="traffic-bar-stack" style="height:${stackHeightPct}%;">
                    <div class="traffic-bar-segment segment-tx" style="height:${txPct}%;"></div>
                    <div class="traffic-bar-segment segment-rx" style="height:${rxPct}%;"></div>
                </div>
                <span class="traffic-bar-label">${escapeHtml(label)}</span>
            </div>
        `;
    }).join("");

    container.innerHTML = gridHtml + barsHtml;
}

export function renderOverviewMethods(summary) {
    const section = document.getElementById("ovTrafficMethodSection");
    const track = document.getElementById("ovMethodTrack");
    const legend = document.getElementById("ovMethodLegend");
    if (!section || !track || !legend) return;

    const items = summary && summary.type_breakdown ? summary.type_breakdown : [];
    if (!items || items.length === 0) {
        section.style.display = "none";
        return;
    }

    section.style.display = "block";
    const colors = [
        "var(--accent-mint)",
        "var(--accent-cyan)",
        "var(--accent-violet)",
        "var(--accent-amber)"
    ];

    track.innerHTML = items.map((it, idx) => {
        const color = colors[idx % colors.length];
        const pct = Math.min(100, Math.max(0, it.percentage || 0));
        return `<div style="width:${pct}%; height:100%; background:${color};" title="${escapeHtml(it.label)}: ${pct}% (${formatBytes(it.total_bytes || 0)})"></div>`;
    }).join("");

    legend.innerHTML = items.map((it, idx) => {
        const color = colors[idx % colors.length];
        const pct = it.percentage || 0;
        return `
            <span style="display:inline-flex; align-items:center; gap:6px;">
                <span style="width:8px; height:8px; border-radius:2px; background:${color};"></span>
                <span style="color:var(--text-secondary); font-weight:600;">${escapeHtml(it.label)}:</span>
                <span class="font-mono text-cyan" style="font-weight:700;">${formatBytes(it.total_bytes || 0)}</span>
                <span style="color:var(--text-muted); font-size:0.7rem;">(${pct}%)</span>
            </span>
        `;
    }).join("");
}
