// ============================================================================
// XForwarder Web UI - Logs Module (Native ES Module)
// ============================================================================

import { escapeHtml, showToast } from "./utils.js";

let logFeedActive = true;

export function addLogEntry(type, message) {
    const logConsole = document.getElementById("logConsole");
    if (!logConsole || !logFeedActive) return;

    const timeStr = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.className = `log-entry log-entry-${type}`;

    let badgeClass = "badge-info";
    let badgeText = "INFO";
    if (type === "probe") { badgeClass = "badge-probe"; badgeText = "PROBE"; }
    else if (type === "fail") { badgeClass = "badge-fail"; badgeText = "FAILOVER"; }
    else if (type === "warn") { badgeClass = "badge-warn"; badgeText = "WARN"; }

    entry.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        <span class="log-badge ${badgeClass}">${badgeText}</span>
        <span class="log-msg">${escapeHtml(message)}</span>
    `;

    logConsole.prepend(entry);

    while (logConsole.children.length > 150) {
        logConsole.removeChild(logConsole.lastChild);
    }
}

export function appendLogEntry(type, message) {
    addLogEntry(type, message);
}

export function initLogs() {
    const btnClearLogs = document.getElementById("btnClearLogs");
    const btnCopyConsoleLogs = document.getElementById("btnCopyConsoleLogs");
    const btnToggleLogFeed = document.getElementById("btnToggleLogFeed");
    const logFeedText = document.getElementById("logFeedText");
    const logSearchInput = document.getElementById("logSearchInput");
    const logConsole = document.getElementById("logConsole");

    if (btnCopyConsoleLogs) {
        btnCopyConsoleLogs.addEventListener("click", () => {
            if (!logConsole) return;
            const entries = logConsole.querySelectorAll(".log-entry");
            if (entries.length === 0) {
                showToast("No console logs to copy", "warn");
                return;
            }
            const lines = [
                `=== XForwarder Real-time Failover & Probe Logs ===`,
                `Exported at: ${new Date().toLocaleString()}`,
                `Total entries: ${entries.length}`,
                ""
            ];
            entries.forEach(entry => {
                lines.push(entry.innerText.replace(/\s+/g, " ").trim());
            });
            const fullText = lines.join("\n");
            const doToast = () => showToast(`Copied ${entries.length} log entries to clipboard!`);

            if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
                navigator.clipboard.writeText(fullText).then(doToast).catch(() => {
                    fallbackCopyLogs(fullText, doToast);
                });
            } else {
                fallbackCopyLogs(fullText, doToast);
            }
        });
    }

    if (btnClearLogs) {
        btnClearLogs.addEventListener("click", () => {
            if (logConsole) {
                logConsole.innerHTML = `
                    <div class="log-entry log-entry-info">
                        <span class="log-time">[System]</span>
                        <span class="log-badge badge-info">INFO</span>
                        <span class="log-msg">Logs cleared. Monitoring continues.</span>
                    </div>
                `;
            }
        });
    }

    if (btnToggleLogFeed) {
        btnToggleLogFeed.addEventListener("click", () => {
            logFeedActive = !logFeedActive;
            if (logFeedText) {
                logFeedText.innerText = logFeedActive ? "Live Feed Active" : "Feed Paused";
            }
            btnToggleLogFeed.className = `btn btn-sm ${logFeedActive ? "btn-primary" : "btn-secondary"}`;
        });
    }

    if (logSearchInput) {
        logSearchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!logConsole) return;
            const entries = logConsole.querySelectorAll(".log-entry");
            entries.forEach(entry => {
                const text = entry.innerText.toLowerCase();
                entry.style.display = (!query || text.includes(query)) ? "flex" : "none";
            });
        });
    }
}

function fallbackCopyLogs(text, onSuccess) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
        document.execCommand("copy");
        if (typeof onSuccess === "function") onSuccess();
    } catch (_) {
        showToast("Unable to copy logs to clipboard", "error");
    }
    document.body.removeChild(ta);
}
