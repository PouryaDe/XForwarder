/**
 * XForwarder - Formatting, Sanitization & Toast Notification Utilities
 */

import { t } from "./i18n.js";

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

export function encodeInlineParam(val) {
    return encodeURIComponent(String(val ?? "")).replace(/'/g, "%27");
}

export function getRuleId(rule) {
    if (!rule) return "";
    if (rule.id && String(rule.id).trim()) return String(rule.id).trim();
    if (Array.isArray(rule.excluded_ports) && rule.excluded_ports.length > 0) {
        return `rule-excl-${rule.excluded_ports.slice(0, 5).join("-")}`;
    }
    const spec = rule.port_range || rule.port;
    return (spec !== undefined && spec !== null && String(spec).trim()) ? `rule-${spec}` : "";
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
        } else if (loss >= 5 || fbLoss >= 5) {
            cls = "loss-warn";
        }

        let tooltip = `15m Test: ${loss}% loss (${recv}/${sent} pkts) · Tested ${escapeHtml(agoStr)}`;
        let displayLoss = `${loss}% loss`;

        if (fbLoss > 0 && loss === 0) {
            if (fbLoss < 5) {
                tooltip += ` · Active rolling probe: ${fbLoss}% transient drop (Stable)`;
                displayLoss = `${loss}% loss`;
            } else {
                tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
                displayLoss = `${fbLoss}% probe loss`;
            }
        } else if (fbLoss > 0) {
            tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
        }

        return `<span class="loss50-pill ${cls}" title="${escapeHtml(tooltip)}"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg><span>${escapeHtml(displayLoss)}</span></span>`;
    }
    if (fallbackLoss !== null && fallbackLoss !== undefined && !isNaN(fallbackLoss)) {
        const loss = Math.round(Number(fallbackLoss));
        let cls = "loss-good";
        if (loss >= 30) cls = "loss-bad";
        else if (loss >= 5) cls = "loss-warn";
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
        else if (loss >= 5 || fbLoss >= 5) color = "var(--accent-amber)";

        let tooltip = `15m Test: ${loss}% loss (${recv}/${sent} pkts) · Tested ${escapeHtml(agoStr)}`;
        let displayText = `· ${loss}% loss`;

        if (fbLoss > 0 && loss === 0) {
            if (fbLoss < 5) {
                tooltip += ` · Active rolling probe: ${fbLoss}% transient drop (Stable)`;
                displayText = `· ${loss}% loss`;
            } else {
                tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
                displayText = `· ${fbLoss}% probe loss`;
            }
        } else if (fbLoss > 0) {
            tooltip += ` · Active rolling probe: ${fbLoss}% loss`;
        }

        return `<span class="loss50-pill-inline font-mono" style="color:${color};" title="${escapeHtml(tooltip)}">${escapeHtml(displayText)}</span>`;
    }
    if (fallbackLoss !== null && fallbackLoss !== undefined && !isNaN(fallbackLoss)) {
        const loss = Math.round(Number(fallbackLoss));
        let color = "var(--accent-mint)";
        if (loss >= 30) color = "var(--accent-rose)";
        else if (loss >= 5) color = "var(--accent-amber)";
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

const CHECKMARK_COPY_SVG = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

function triggerCopyFeedback(triggerEl) {
    if (!triggerEl || typeof triggerEl.classList === "undefined") return;
    if (!triggerEl.dataset.origSvg) {
        triggerEl.dataset.origSvg = triggerEl.innerHTML;
    }
    triggerEl.innerHTML = CHECKMARK_COPY_SVG;
    triggerEl.classList.add("is-copied");
    if (triggerEl._copyTimer) clearTimeout(triggerEl._copyTimer);
    triggerEl._copyTimer = setTimeout(() => {
        if (triggerEl.dataset.origSvg) {
            triggerEl.innerHTML = triggerEl.dataset.origSvg;
            delete triggerEl.dataset.origSvg;
        }
        triggerEl.classList.remove("is-copied");
        triggerEl._copyTimer = null;
    }, 1100);
}

export function copyText(text, triggerEl = null) {
    if (!text) return;
    const onSuccess = () => {
        triggerCopyFeedback(triggerEl);
        showToast(`Copied to clipboard: ${text}`);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(onSuccess).catch(() => fallbackCopy(text, triggerEl));
    } else {
        fallbackCopy(text, triggerEl);
    }
}

function fallbackCopy(text, triggerEl = null) {
    const el = document.createElement("textarea");
    el.value = text;
    document.body.appendChild(el);
    el.select();
    try {
        document.execCommand("copy");
        triggerCopyFeedback(triggerEl);
        showToast(`Copied to clipboard: ${text}`);
    } catch (_) {}
    document.body.removeChild(el);
}

let confirmResolve = null;

const CONFIRM_ICON_DANGER_SVG = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
const CONFIRM_ICON_PRIMARY_SVG = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`;

/**
 * Displays a styled confirmation modal and returns a Promise resolving to true/false.
 * Dynamically configures button labels, button variants ('primary' vs 'danger'),
 * and modal icons based on the action context.
 *
 * @param {string} title - The modal dialog title.
 * @param {string} message - The explanatory message describing consequences.
 * @param {Object|string} [options={}] - Options object ({ confirmText, cancelText, variant }) or confirmText string.
 * @returns {Promise<boolean>} Resolves to true if confirmed, false if cancelled or dismissed.
 */
export function askConfirm(title, message, options = {}) {
    const titleEl = document.getElementById("confirmTitle");
    const msgEl = document.getElementById("confirmMessage");
    const modalEl = document.getElementById("confirmModal");
    const btnConfirm = document.getElementById("btnProceedConfirm") || document.getElementById("btnConfirmAction");
    const btnCancel = document.getElementById("btnCancelConfirm");
    const btnAlt = document.getElementById("btnAltConfirm");
    const iconEl = modalEl ? modalEl.querySelector(".confirm-icon") : null;

    if (btnAlt) btnAlt.style.display = "none";

    if (titleEl) titleEl.innerText = title;
    if (msgEl) msgEl.innerText = message;

    const opts = typeof options === "string" ? { confirmText: options } : (options || {});
    const titleLower = String(title || "").toLowerCase();

    let confirmText = opts.confirmText;
    let variant = opts.variant;

    if (!confirmText) {
        if (titleLower.includes("restart") || titleLower.includes("راه‌اندازی")) {
            confirmText = t("confirm.restart_btn", {}, "Restart Service");
        } else if (titleLower.includes("reload") || titleLower.includes("بارگذاری")) {
            confirmText = t("confirm.reload_btn", {}, "Reload Service");
        } else if (titleLower.includes("sync") || titleLower.includes("همگام")) {
            confirmText = t("confirm.sync_btn", {}, "Sync Table");
        } else if (titleLower.includes("reset") || titleLower.includes("ریست")) {
            confirmText = t("confirm.reset_btn", {}, "Reset Counter");
        } else if (titleLower.includes("wipe") || titleLower.includes("حذف کامل")) {
            confirmText = t("confirm.wipe_btn", {}, "Wipe History");
        } else if (titleLower.includes("delete") || titleLower.includes("حذف")) {
            confirmText = t("confirm.delete_btn", {}, "Delete Rule");
        } else {
            confirmText = t("confirm.confirm_btn", {}, "Confirm");
        }
    }

    if (!variant) {
        const isDestructive = titleLower.includes("delete") || titleLower.includes("wipe") || titleLower.includes("حذف");
        variant = isDestructive ? "danger" : "primary";
    }

    if (btnConfirm) {
        btnConfirm.textContent = confirmText;
        btnConfirm.removeAttribute("data-i18n");
        btnConfirm.classList.remove("btn-danger", "btn-primary");
        btnConfirm.classList.add(variant === "primary" ? "btn-primary" : "btn-danger");
    }

    if (btnCancel) {
        btnCancel.textContent = opts.cancelText || t("confirm.cancel", {}, "Cancel");
    }

    if (iconEl) {
        iconEl.classList.toggle("confirm-icon-primary", variant === "primary");
        iconEl.innerHTML = variant === "primary" ? CONFIRM_ICON_PRIMARY_SVG : CONFIRM_ICON_DANGER_SVG;
    }

    if (modalEl) modalEl.classList.add("show");

    // Clean up any previously pending confirmation dialog before creating a new one
    if (confirmResolve) {
        confirmResolve(false);
        confirmResolve = null;
    }

    return new Promise((resolve) => {
        confirmResolve = resolve;
    });
}

/**
 * Displays a two-choice confirmation modal (e.g. bidirectional sync direction).
 * Returns Promise<'primary' | 'alt' | null>.
 */
export function askChoice(title, message, primaryText, altText) {
    const modalEl = document.getElementById("confirmModal");
    const titleEl = document.getElementById("confirmTitle");
    const msgEl = document.getElementById("confirmMessage");
    const btnCancel = document.getElementById("btnCancelConfirm");
    const btnAlt = document.getElementById("btnAltConfirm");
    const btnConfirm = document.getElementById("btnProceedConfirm") || document.getElementById("btnConfirmAction");
    const iconEl = modalEl ? modalEl.querySelector(".confirm-icon") : null;

    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;

    if (btnConfirm) {
        btnConfirm.textContent = primaryText;
        btnConfirm.removeAttribute("data-i18n");
        btnConfirm.classList.remove("btn-danger");
        btnConfirm.classList.add("btn-primary");
    }
    if (btnAlt) {
        btnAlt.textContent = altText;
        btnAlt.style.display = "inline-flex";
    }
    if (btnCancel) {
        btnCancel.textContent = t("confirm.cancel", {}, "Cancel");
    }
    if (iconEl) {
        iconEl.classList.add("confirm-icon-primary");
        iconEl.innerHTML = CONFIRM_ICON_PRIMARY_SVG;
    }

    if (confirmResolve) {
        confirmResolve(null);
        confirmResolve = null;
    }
    if (modalEl) modalEl.classList.add("show");

    return new Promise((resolve) => {
        confirmResolve = resolve;
    });
}

if (typeof document !== "undefined") {
    const bindConfirmModalEvents = () => {
        const btnCancel = document.getElementById("btnCancelConfirm");
        const btnAlt = document.getElementById("btnAltConfirm");
        const btnConfirm = document.getElementById("btnProceedConfirm") || document.getElementById("btnConfirmAction");
        const modalEl = document.getElementById("confirmModal");

        const resetConfirmState = () => {
            if (btnAlt) btnAlt.style.display = "none";
            if (btnConfirm) {
                btnConfirm.setAttribute("data-i18n", "confirm.confirm_btn");
            }
        };

        const closeWithCancel = () => {
            if (modalEl) modalEl.classList.remove("show");
            resetConfirmState();
            if (confirmResolve) {
                confirmResolve(false);
                confirmResolve = null;
            }
        };

        if (btnCancel) {
            btnCancel.onclick = () => {
                const isChoice = btnAlt && btnAlt.style.display !== "none";
                if (modalEl) modalEl.classList.remove("show");
                resetConfirmState();
                if (confirmResolve) {
                    confirmResolve(isChoice ? null : false);
                    confirmResolve = null;
                }
            };
        }

        if (btnAlt) {
            btnAlt.onclick = () => {
                if (modalEl) modalEl.classList.remove("show");
                resetConfirmState();
                if (confirmResolve) {
                    confirmResolve("alt");
                    confirmResolve = null;
                }
            };
        }

        if (btnConfirm) {
            btnConfirm.onclick = () => {
                if (modalEl) modalEl.classList.remove("show");
                resetConfirmState();
                if (confirmResolve) {
                    confirmResolve(btnAlt && btnAlt.style.display !== "none" ? "primary" : true);
                    confirmResolve = null;
                }
            };
        }

        if (modalEl) {
            modalEl.addEventListener("click", (e) => {
                if (e.target === modalEl) {
                    closeWithCancel();
                }
            });
        }

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && modalEl && modalEl.classList.contains("show")) {
                closeWithCancel();
            }
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindConfirmModalEvents);
    } else {
        bindConfirmModalEvents();
    }
}

