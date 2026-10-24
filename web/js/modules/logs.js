// ============================================================================
// XForwarder Web UI - Logs Module (Native ES Module)
// ============================================================================

import { escapeHtml } from "./utils.js";

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
    const btnToggleLogFeed = document.getElementById("btnToggleLogFeed");
    const logFeedText = document.getElementById("logFeedText");
    const logSearchInput = document.getElementById("logSearchInput");
    const logConsole = document.getElementById("logConsole");

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
