// ============================================================================
// XForwarder Web UI - Network Quality & Latency Diagnostic Subsystem
// ============================================================================

import { API_BASE } from "./api.js";
import { showToast, escapeHtml } from "./utils.js";
import { addLogEntry } from "./logs.js";

export async function runLivePacketLossTest(encodedRuleId, rawTarget, port, destType, btnEl) {
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
                showToast(`[${cleanTarget}] 50 probes: ${lat} · 0% loss (${pkts})`, "info");
                if (btnEl) {
                    btnEl.classList.remove("is-testing");
                    btnEl.classList.add("is-success");
                    btnEl.innerHTML = `<span>${lat || '0% loss'} (50 pkts)</span>`;
                }
                addLogEntry("probe", `[Loss Test 50-Probe] [${cleanTarget}] Clean -> Latency: ${lat}, 0% loss (${pkts})`);
            } else if (data.healthy && loss > 0) {
                showToast(`[${cleanTarget}] 50 probes: ${lat} · ${loss}% loss (${pkts})`, "warn");
                if (btnEl) {
                    btnEl.classList.remove("is-testing");
                    btnEl.classList.add("is-fail");
                    btnEl.innerHTML = `<span>${lat} · ${loss}% loss</span>`;
                }
                addLogEntry("warn", `[Loss Test 50-Probe] [${cleanTarget}] Degraded -> Latency: ${lat}, ${loss}% loss (${pkts})`);
            } else {
                const reason = data.error || data.reason ? ` (${data.error || data.reason})` : "";
                showToast(`[${cleanTarget}] Unreachable · 100% loss${reason}`, "error");
                if (btnEl) {
                    btnEl.classList.remove("is-testing");
                    btnEl.classList.add("is-fail");
                    btnEl.innerHTML = `<span>100% loss</span>`;
                }
                addLogEntry("fail", `[Loss Test 50-Probe] [${cleanTarget}] Unreachable -> 100% packet loss${reason}`);
            }
        } else {
            showToast(data.error || "Failed to execute packet loss test", "error");
            if (btnEl) {
                btnEl.classList.remove("is-testing");
                btnEl.classList.add("is-fail");
                btnEl.innerHTML = `<span>Test Error</span>`;
            }
        }
    } catch (err) {
        showToast("Error measuring packet loss: " + err.message, "error");
        if (btnEl) {
            btnEl.classList.remove("is-testing");
            btnEl.innerHTML = originalHtml;
            btnEl.disabled = false;
        }
    } finally {
        if (btnEl) {
            setTimeout(() => {
                btnEl.classList.remove("is-testing", "is-success", "is-fail");
                btnEl.innerHTML = originalHtml;
                btnEl.disabled = false;
            }, 6000);
        }
    }
}

export function initDiagPacketLossTool() {
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
                const jitter = data.jitter_ms !== undefined && data.jitter_ms !== null ? ` | Jitter: ${data.jitter_ms} ms` : "";

                let statusBadge = `<span class="badge-good">CLEAN (0% Loss)</span>`;
                if (loss >= 100 || !data.healthy) {
                    statusBadge = `<span class="badge-bad">OUTAGE (100% Loss)</span>`;
                } else if (loss > 20) {
                    statusBadge = `<span class="badge-bad">CRITICAL (${loss}% Loss)</span>`;
                } else if (loss > 0) {
                    statusBadge = `<span class="badge-warn">DEGRADED (${loss}% Loss)</span>`;
                }

                if (resultBox) {
                    resultBox.innerHTML = `
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                            <strong>Probe Result for [${escapeHtml(target)}]:</strong>
                            ${statusBadge}
                        </div>
                        <div style="font-family:var(--font-mono);font-size:0.82rem;line-height:1.5;">
                            <div>Latency: <b class="text-mint">${lat}</b>${jitter}</div>
                            <div>Packets: <b>${rec}/${sent} received</b> (${loss}% packet loss)</div>
                            ${data.diagnostic_detail ? `<div class="text-muted" style="margin-top:4px;">${escapeHtml(data.diagnostic_detail)}</div>` : ""}
                        </div>
                    `;
                }
            } else {
                if (resultBox) {
                    resultBox.innerHTML = `<span class="text-rose font-mono">Test failed: ${escapeHtml(data.error || "Unknown error")}</span>`;
                }
            }
        } catch (err) {
            if (resultBox) {
                resultBox.innerHTML = `<span class="text-rose font-mono">Network error: ${escapeHtml(err.message)}</span>`;
            }
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

export function initNetworkQualityMonitor() {
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
                    showToast(`Round complete! ${data.tested_count || 0} unique target(s) analyzed.`, "success");
                    await loadNetworkQualityMetrics();
                } else {
                    showToast(data.error || "Failed to trigger round", "error");
                }
            } catch (err) {
                showToast("Network error running round: " + err.message, "error");
            } finally {
                btnTrigger.disabled = false;
                btnTrigger.innerHTML = originalHtml;
            }
        });
    }
}

export async function loadNetworkQualityMetrics() {
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

export function renderTimelineBar(timeline, range) {
    const bar = document.getElementById("metricsTimelineBar");
    if (!bar) return;

    if (!timeline || timeline.length === 0) {
        bar.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;width:100%;font-size:0.75rem;color:var(--text-muted);padding:10px 0;">No probe samples recorded yet. Next 15m round will populate timeline.</div>';
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

        const tooltip = `${slot.time_str || ''} · Avg Loss: ${slot.avg_loss_pct || 0}% (Peak: ${slot.peak_loss_pct || 0}%) · Latency: ${slot.avg_latency_ms !== null && slot.avg_latency_ms !== undefined ? slot.avg_latency_ms + 'ms' : 'Timeout'} (${slot.probe_count || 0} probes)`;
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

export function renderDisruptionsTable(disruptions) {
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
