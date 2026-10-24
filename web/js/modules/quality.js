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
