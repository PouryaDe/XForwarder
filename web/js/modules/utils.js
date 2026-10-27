/**
 * XForwarder - Formatting, Sanitization & Toast Notification Utilities
 */

export function formatBytes(bytes, decimals = 2) {
    if (bytes === undefined || bytes === null || isNaN(bytes)) return "0 B";
    const b = Number(bytes);
    if (b <= 0) return "0 B";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
    const i = Math.floor(Math.log(b) / Math.log(k));
    const idx = Math.min(i, sizes.length - 1);
    const val = parseFloat((b / Math.pow(k, idx)).toFixed(dm));
    return `${val} ${sizes[idx]}`;
}

export function formatTrafficMB(bytes) {
    if (bytes === undefined || bytes === null || isNaN(bytes)) return "0";
    const mb = Number(bytes) / (1024 * 1024);
    if (mb < 0.01 && mb > 0) return "<0.01";
    if (mb >= 1000) return (mb / 1024).toFixed(2) + " GB";
    return mb.toFixed(1) + " MB";
}

export function formatEngineVersion(rawVer) {
    if (!rawVer) return "";
    const str = String(rawVer).trim();
    const base = str.split("-")[0].trim().replace(/^v/i, "");
    return base ? `v${base}` : str;
}

export function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

export function safeInlineArg(str) {
    if (!str) return "''";
    const escaped = String(str)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, "&quot;")
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "\\r");
    return `'${escaped}'`;
}

/**
 * Formats the dedicated round-trip latency pill badge (.latency-pill) for card view.
 * Strictly displays ping latency (e.g. 100.1 ms or Down); never embeds packet loss.
 * @param {Object|number|string} statOrMs - Destination health stat object or latency ms number
 * @param {number} maybeLoss - Fallback loss percentage if statOrMs is a raw number
 * @returns {string} HTML markup for .latency-pill badge
 */
export function formatLatencyBadge(statOrMs, maybeLoss = 0) {
    if (!statOrMs && statOrMs !== 0) return '';
    let stat = statOrMs;
    if (typeof statOrMs !== 'object' || statOrMs === null) {
        const msNum = Number(statOrMs);
        const lossNum = Number(maybeLoss) || 0;
        stat = {
            latency_ms: isNaN(msNum) ? null : msNum,
            packet_loss: lossNum,
            status: (msNum <= 0 && lossNum >= 100) ? 'down' : ((lossNum > 0 || msNum > 150) ? 'degraded' : 'healthy')
        };
    }

    const isHealthy = (stat.status === 'healthy');
    const isDegraded = (stat.status === 'degraded');
    const isCritical = (stat.status === 'critical');
    const isFailed = (stat.status === 'failed' || stat.status === 'down');
    const loss = (stat.packet_loss !== undefined && stat.packet_loss !== null)
        ? parseInt(stat.packet_loss, 10)
        : (isHealthy ? 0 : 100);
    const ms = (stat.latency_ms !== undefined && stat.latency_ms !== null)
        ? parseFloat(stat.latency_ms)
        : NaN;
    const jitter = (stat.jitter_ms !== undefined && stat.jitter_ms !== null)
        ? parseFloat(stat.jitter_ms)
        : null;
    const score = (stat.composite_score !== undefined && stat.composite_score !== null)
        ? stat.composite_score
        : null;

    let tooltipParts = [];
    if (!isNaN(ms) && ms > 0) tooltipParts.push(`Avg Latency: ${ms} ms`);
    if (jitter !== null && !isNaN(jitter)) tooltipParts.push(`Jitter: ${jitter} ms`);
    if (stat.status) tooltipParts.push(`Status: ${stat.status}`);
    if (score !== null) tooltipParts.push(`Score: ${score}`);
    const tooltipText = tooltipParts.join(' · ');

    if (isFailed || isNaN(ms) || ms <= 0) {
        return `<span class="latency-pill latency-bad" title="${escapeHtml(tooltipText || 'Unreachable / Down')}"><span class="latency-dot"></span>Down</span>`;
    }

    let cls = "latency-good";
    if (isCritical || ms > 250) {
        cls = "latency-bad";
    } else if (isDegraded || ms > 150 || (jitter !== null && jitter > 30)) {
        cls = "latency-medium";
    }

    const label = `${ms} ms`;
    return `<span class="latency-pill ${cls}" title="${escapeHtml(tooltipText)}"><span class="latency-dot"></span>${label}</span>`;
}

/**
 * Formats a 15-minute 50-probe packet loss pill badge for card view with test age tooltip.
 * @param {Object|null} lossInfo - Latest packet loss record from SQLite
 * @param {number|null} fallbackLoss - Optional fallback loss from continuous 10-probe monitor
 * @returns {string} HTML markup for .loss50-pill badge
 */
export function formatLoss50Badge(lossInfo, fallbackLoss = null) {
    const fbLoss = (fallbackLoss !== null && fallbackLoss !== undefined && !isNaN(fallbackLoss)) ? Math.round(Number(fallbackLoss)) : 0;

    if (lossInfo && lossInfo.packet_loss !== undefined && lossInfo.packet_loss !== null) {
        const loss = Math.round(Number(lossInfo.packet_loss));
        const agoStr = lossInfo.tested_ago_str || "recently";
        const sent = lossInfo.packets_sent || 50;
        const recv = lossInfo.packets_received !== undefined ? lossInfo.packets_received : (sent - Math.round(sent * loss / 100));

        let cls = "loss-good";
        if (loss >= 30 || fbLoss >= 30) {
            cls = "loss-bad";
        } else if (loss > 0 || fbLoss > 0) {
            cls = "loss-warn";
        }

        let tooltip = `15m Test: ${loss}% loss (${recv}/${sent} pkts) · Tested ${escapeHtml(agoStr)}`;
        let displayLoss = `${loss}% loss`;

        if (fbLoss > 0 && loss === 0) {
            tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
            displayLoss = `${fbLoss}% probe loss`;
        } else if (fbLoss > 0) {
            tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
        }

        return `<span class="loss50-pill ${cls}" title="${escapeHtml(tooltip)}"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg><span>${escapeHtml(displayLoss)}</span></span>`;
    }
    if (fallbackLoss !== null && fallbackLoss !== undefined && !isNaN(fallbackLoss)) {
        const loss = Math.round(Number(fallbackLoss));
        let cls = "loss-good";
        if (loss >= 30) cls = "loss-bad";
        else if (loss > 0) cls = "loss-warn";
        const tooltip = `Engine Loss: ${loss}% (10-probe sliding window)`;
        return `<span class="loss50-pill ${cls}" title="${escapeHtml(tooltip)}"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg><span>${loss}% loss</span></span>`;
    }
    return "";
}

/**
 * Formats an inline 15-minute packet loss indicator for list view rows with test age tooltip.
 * @param {Object|null} lossInfo - Latest packet loss record from SQLite
 * @param {number|null} fallbackLoss - Optional fallback loss from continuous 10-probe monitor
 * @returns {string} HTML markup for .loss50-pill-inline
 */
export function formatLoss50Inline(lossInfo, fallbackLoss = null) {
    const fbLoss = (fallbackLoss !== null && fallbackLoss !== undefined && !isNaN(fallbackLoss)) ? Math.round(Number(fallbackLoss)) : 0;

    if (lossInfo && lossInfo.packet_loss !== undefined && lossInfo.packet_loss !== null) {
        const loss = Math.round(Number(lossInfo.packet_loss));
        const agoStr = lossInfo.tested_ago_str || "recently";
        const sent = lossInfo.packets_sent || 50;
        const recv = lossInfo.packets_received !== undefined ? lossInfo.packets_received : (sent - Math.round(sent * loss / 100));

        let color = "var(--accent-mint)";
        if (loss >= 30 || fbLoss >= 30) color = "var(--accent-rose)";
        else if (loss > 0 || fbLoss > 0) color = "var(--accent-amber)";

        let tooltip = `15m Test: ${loss}% loss (${recv}/${sent} pkts) · Tested ${escapeHtml(agoStr)}`;
        let displayText = `· ${loss}% loss`;

        if (fbLoss > 0 && loss === 0) {
            tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
            displayText = `· ${fbLoss}% probe loss`;
        } else if (fbLoss > 0) {
            tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
        }

        return `<span class="loss50-pill-inline font-mono" style="color:${color};" title="${escapeHtml(tooltip)}">${escapeHtml(displayText)}</span>`;
    }
    if (fallbackLoss !== null && fallbackLoss !== undefined && !isNaN(fallbackLoss)) {
        const loss = Math.round(Number(fallbackLoss));
        let color = "var(--accent-mint)";
        if (loss >= 30) color = "var(--accent-rose)";
        else if (loss > 0) color = "var(--accent-amber)";
        const tooltip = `Engine Loss: ${loss}% (10-probe sliding window)`;
        return `<span class="loss50-pill-inline font-mono" style="color:${color};" title="${escapeHtml(tooltip)}">· ${loss}% loss</span>`;
    }
    return "";
}

export function formatConciseReason(reason) {
    if (!reason) return "";
    const r = String(reason).trim();
    if (r.includes("100% loss") || r.includes("Unreachable") || r.includes("unresponsive")) return "Unreachable";
    if (r.includes("timed out")) return "Timeout";
    if (r.includes("Connection refused")) return "Conn Refused";
    if (r.includes("leaks to WAN") || r.includes("missing interface")) return "WAN Leak";
    if (r.includes("Critical packet loss")) {
        const m = r.match(/([\d.]+%)/);
        return m ? `Crit Loss ${m[1]}` : "Crit Loss";
    }
    if (r.includes("Active probe loss") || r.includes("probe loss")) {
        const m = r.match(/([\d.]+%)/);
        return m ? `Loss: ${m[1]}` : "Probe Loss";
    }
    if (r.includes("Sustained 5m packet loss")) {
        const m = r.match(/([\d.]+%)/);
        return m ? `5m Loss: ${m[1]}` : "5m Loss";
    }
    if (r.length > 25) return r.substring(0, 22) + "...";
    return r;
}

export function showToast(message, type = "info", duration = 3500) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    if (type === "success") {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
    } else if (type === "error") {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    }

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
        <button type="button" class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("toast-leaving");
        setTimeout(() => toast.remove(), 250);
    }, duration);
}

export async function copyJsonToClipboard(text, successMsg = "Copied to clipboard!") {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.left = "-999999px";
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            document.body.removeChild(ta);
        }
        showToast(successMsg, "success");
        return true;
    } catch (err) {
        showToast("Failed to copy to clipboard", "error");
        return false;
    }
}

export function formatProtoBadge(proto) {
    const p = String(proto || "both").toLowerCase().trim();
    if (p === "both" || p === "tcp+udp" || p === "tcp/udp") return "TCP + UDP";
    if (p === "tcp") return "TCP";
    if (p === "udp") return "UDP";
    return p.toUpperCase();
}

export function copyText(text) {
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
    try {
        document.execCommand("copy");
        showToast(`Copied to clipboard: ${text}`);
    } catch (_) {}
    document.body.removeChild(el);
}

let confirmResolve = null;

export function askConfirm(title, message) {
    const titleEl = document.getElementById("confirmTitle");
    const msgEl = document.getElementById("confirmMessage");
    const modalEl = document.getElementById("confirmModal");
    if (titleEl) titleEl.innerText = title;
    if (msgEl) msgEl.innerText = message;
    if (modalEl) modalEl.classList.add("show");

    return new Promise((resolve) => {
        confirmResolve = resolve;
    });
}

if (typeof document !== "undefined") {
    const bindConfirmModalEvents = () => {
        const btnCancel = document.getElementById("btnCancelConfirm");
        const btnConfirm = document.getElementById("btnProceedConfirm") || document.getElementById("btnConfirmAction");
        const modalEl = document.getElementById("confirmModal");

        if (btnCancel) {
            btnCancel.onclick = () => {
                if (modalEl) modalEl.classList.remove("show");
                if (confirmResolve) {
                    confirmResolve(false);
                    confirmResolve = null;
                }
            };
        }

        if (btnConfirm) {
            btnConfirm.onclick = () => {
                if (modalEl) modalEl.classList.remove("show");
                if (confirmResolve) {
                    confirmResolve(true);
                    confirmResolve = null;
                }
            };
        }
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindConfirmModalEvents);
    } else {
        bindConfirmModalEvents();
    }
}

