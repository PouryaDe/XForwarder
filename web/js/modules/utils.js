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

export function formatEngineVersion(ver) {
    if (!ver) return "";
    return `v${ver}`;
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

export function formatLatencyBadge(latencyMs, packetLoss = 0) {
    const ms = Number(latencyMs);
    const loss = Number(packetLoss) || 0;
    if (ms <= 0 && loss >= 100) {
        return `<span class="badge badge-down">Down (100% loss)</span>`;
    }
    if (loss > 0 || ms > 150) {
        return `<span class="badge badge-amber">${ms > 0 ? ms + 'ms' : '0ms'} (${loss}% loss)</span>`;
    }
    if (ms > 250) {
        return `<span class="badge badge-amber">${ms}ms</span>`;
    }
    return `<span class="badge badge-ok">${ms > 0 ? ms + 'ms' : '<1ms'}</span>`;
}

export function formatConciseReason(reason) {
    if (!reason) return "";
    const r = String(reason).trim();
    if (r.includes("100% loss") || r.includes("Unreachable")) return "Unreachable";
    if (r.includes("timed out")) return "Timeout";
    if (r.includes("Connection refused")) return "Conn Refused";
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
    document.addEventListener("DOMContentLoaded", () => {
        const btnCancel = document.getElementById("btnCancelConfirm");
        const btnConfirm = document.getElementById("btnConfirmAction");
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
    });
}

