// ============================================================================
// XForwarder Web UI - System Updates & Services Management (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { showToast, escapeHtml, askConfirm } from "./utils.js";

let updatePollTimer = null;
let updatePollingActive = false;
let updateReconnectTries = 0;

export function initSystemUpdateManager() {
    const btnCheckUpdates = document.getElementById("btnCheckUpdates");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const iconCheckUpdates = document.getElementById("iconCheckUpdates");

    if (btnTriggerUpdate) {
        btnTriggerUpdate.disabled = true;
        btnTriggerUpdate.title = "Click 'Check for Updates' to scan GitHub for new releases";
    }

    if (btnCheckUpdates) {
        btnCheckUpdates.addEventListener("click", async () => {
            if (iconCheckUpdates) iconCheckUpdates.classList.add("spinning");
            btnCheckUpdates.disabled = true;
            try {
                const info = await fetchSystemVersionInfo(true);
                if (info && info.update_available) {
                    showToast(`New release available: #${info.remote_commit || 'update'}`, "info");
                } else if (info && info.check_error) {
                    const errStr = String(info.check_error);
                    if (errStr.includes("403") || errStr.toLowerCase().includes("rate limit")) {
                        showToast("GitHub API rate-limited. Click 'Force Update' below to update directly via Git.", "warn");
                    } else {
                        showToast(`Update check failed: ${info.check_error}`, "error");
                    }
                } else {
                    showToast("XForwarder is up to date!", "success");
                }
            } catch (err) {
                showToast("Could not check for updates: " + err.message, "error");
            } finally {
                if (iconCheckUpdates) iconCheckUpdates.classList.remove("spinning");
                btnCheckUpdates.disabled = false;
            }
        });
    }

    if (btnTriggerUpdate) {
        btnTriggerUpdate.addEventListener("click", () => {
            if (btnTriggerUpdate.disabled) return;
            openSystemUpdateModal();
        });
    }

    if (btnCloseUpdateModal) {
        btnCloseUpdateModal.addEventListener("click", () => {
            closeSystemUpdateModal();
        });
    }

    if (btnCancelUpdateModal) {
        btnCancelUpdateModal.addEventListener("click", () => {
            closeSystemUpdateModal();
        });
    }

    if (btnConfirmStartUpdate) {
        btnConfirmStartUpdate.addEventListener("click", () => {
            startSystemUpdateProcedure();
        });
    }

    fetchSystemVersionInfo(false);
}

export async function fetchSystemVersionInfo(force = false) {
    const valInstalledVersion = document.getElementById("valInstalledVersion");
    const valLocalCommit = document.getElementById("valLocalCommit");
    const valRemoteCommit = document.getElementById("valRemoteCommit");
    const valLastChecked = document.getElementById("valLastChecked");
    const badgeUpdateStatus = document.getElementById("badgeUpdateStatus");
    const updateStatusNotice = document.getElementById("updateStatusNotice");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");
    const btnTriggerUpdateText = document.getElementById("btnTriggerUpdateText");

    try {
        const res = await fetch(`${API_BASE}/system/version${force ? "?check=1" : ""}`, {
            headers: { "Accept": "application/json" }
        });
        if (!res.ok) return null;
        const data = await res.json();

        if (valInstalledVersion && data.current_version) {
            valInstalledVersion.textContent = `v${data.current_version}`;
        }
        const brandVersionBadge = document.getElementById("brandVersionBadge");
        if (brandVersionBadge && data.current_version) {
            brandVersionBadge.textContent = `v${data.current_version}`;
        }
        if (valLocalCommit) {
            if (data.current_commit) {
                const dateStr = data.current_date ? ` (${data.current_date})` : "";
                valLocalCommit.textContent = `#${data.current_commit}${dateStr}`;
            } else {
                valLocalCommit.textContent = "Release package";
            }
        }
        if (valRemoteCommit) {
            if (data.remote_commit) {
                const msg = data.remote_commit_msg ? ` - ${data.remote_commit_msg.substring(0, 32)}` : "";
                valRemoteCommit.textContent = `#${data.remote_commit}${msg}`;
                valRemoteCommit.title = data.remote_commit_msg || `#${data.remote_commit}`;
            } else if (data.check_error) {
                const errStr = String(data.check_error);
                const isRateLimit = errStr.toLowerCase().includes("rate limit") || errStr.includes("403");
                valRemoteCommit.textContent = isRateLimit ? "Rate Limited (GitHub API)" : "Check Failed";
                valRemoteCommit.title = data.check_error;
            } else {
                valRemoteCommit.textContent = "Up to date";
                valRemoteCommit.title = "Running latest commit";
            }
        }
        if (valLastChecked) {
            valLastChecked.textContent = data.checked_at
                ? new Date(data.checked_at * 1000).toLocaleTimeString()
                : "Just now";
        }

        if (data.update_available) {
            if (badgeUpdateStatus) {
                badgeUpdateStatus.className = "stat-badge badge-amber";
                badgeUpdateStatus.textContent = "UPDATE AVAILABLE";
            }
            if (updateStatusNotice) {
                updateStatusNotice.style.display = "block";
                updateStatusNotice.className = "update-notice notice-amber";
                const commitLabel = data.remote_commit ? `#${escapeHtml(data.remote_commit)}` : "Latest Release";
                const msgLabel = data.remote_commit_msg ? ` &mdash; <em>${escapeHtml(data.remote_commit_msg)}</em>` : "";
                updateStatusNotice.innerHTML = `<strong>Update Available:</strong> A newer release (<code class="font-mono">${commitLabel}</code>${msgLabel}) is available on GitHub. Click <strong>Update to Latest</strong> below to upgrade.`;
            }
            if (btnTriggerUpdate) {
                btnTriggerUpdate.disabled = false;
                btnTriggerUpdate.classList.add("pulse-glow");
                btnTriggerUpdate.title = "Click to apply software update";
            }
            if (btnTriggerUpdateText) {
                btnTriggerUpdateText.textContent = data.remote_commit ? `Update to #${data.remote_commit}` : "Update to Latest";
            }
        } else if (data.check_error) {
            if (badgeUpdateStatus) {
                badgeUpdateStatus.className = "stat-badge badge-warn";
                badgeUpdateStatus.textContent = "CHECK FAILED";
            }
            if (updateStatusNotice) {
                updateStatusNotice.style.display = "block";
                updateStatusNotice.className = "update-notice notice-rose";
                const errText = escapeHtml(String(data.check_error));
                updateStatusNotice.innerHTML = `<strong>Could Not Reach GitHub:</strong> ${errText}. Updates will continue on the next scheduled interval.`;
            }
            if (btnTriggerUpdate) {
                btnTriggerUpdate.disabled = false;
                btnTriggerUpdate.classList.remove("pulse-glow");
                btnTriggerUpdate.title = "Force software update from GitHub repository";
            }
            if (btnTriggerUpdateText) {
                btnTriggerUpdateText.textContent = "Force Update";
            }
        } else {
            if (badgeUpdateStatus) {
                badgeUpdateStatus.className = "stat-badge badge-good";
                badgeUpdateStatus.textContent = "UP TO DATE";
            }
            if (updateStatusNotice) {
                updateStatusNotice.style.display = "none";
            }
            if (btnTriggerUpdate) {
                btnTriggerUpdate.disabled = false;
                btnTriggerUpdate.classList.remove("pulse-glow");
                btnTriggerUpdate.title = "Re-pull latest code from repository";
            }
            if (btnTriggerUpdateText) {
                btnTriggerUpdateText.textContent = "Reinstall / Update";
            }
        }
        return data;
    } catch (_) {
        return null;
    }
}

export function openSystemUpdateModal() {
    const updateModal = document.getElementById("updateModal");
    const updateConfirmView = document.getElementById("updateConfirmView");
    const updateProgressView = document.getElementById("updateProgressView");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");

    if (updateConfirmView) updateConfirmView.style.display = "block";
    if (updateProgressView) updateProgressView.style.display = "none";
    if (btnCancelUpdateModal) {
        btnCancelUpdateModal.style.display = "inline-flex";
        btnCancelUpdateModal.textContent = "Cancel";
        btnCancelUpdateModal.disabled = false;
        btnCancelUpdateModal.onclick = () => closeSystemUpdateModal();
    }
    if (btnConfirmStartUpdate) {
        btnConfirmStartUpdate.style.display = "inline-flex";
        btnConfirmStartUpdate.disabled = false;
    }
    if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;

    if (updateModal) updateModal.classList.add("show");
}

export function closeSystemUpdateModal() {
    const updateModal = document.getElementById("updateModal");
    if (updatePollingActive) return;
    if (updateModal) updateModal.classList.remove("show");
}

export async function startSystemUpdateProcedure() {
    const updateConfirmView = document.getElementById("updateConfirmView");
    const updateProgressView = document.getElementById("updateProgressView");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");
    const updateStatusBanner = document.getElementById("updateStatusBanner");
    const updateStatusText = document.getElementById("updateStatusText");
    const updateSpinner = document.getElementById("updateSpinner");
    const updateConsole = document.getElementById("updateConsole");

    if (updateConfirmView) updateConfirmView.style.display = "none";
    if (updateProgressView) updateProgressView.style.display = "block";
    if (btnConfirmStartUpdate) btnConfirmStartUpdate.style.display = "none";
    if (btnCancelUpdateModal) btnCancelUpdateModal.disabled = true;
    if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = true;

    if (updateStatusBanner) {
        updateStatusBanner.style.background = "rgba(56, 189, 248, 0.12)";
        updateStatusBanner.style.border = "1px solid rgba(56, 189, 248, 0.3)";
        updateStatusBanner.style.color = "var(--accent-cyan)";
    }
    if (updateSpinner) updateSpinner.style.display = "block";
    if (updateStatusText) updateStatusText.textContent = "Triggering update procedure on server...";
    if (updateConsole) {
        updateConsole.innerHTML = '<div class="log-entry"><span class="log-time">[INIT]</span><span class="log-msg text-cyan">Connecting to host daemon...</span></div>';
    }

    updatePollingActive = true;
    updateReconnectTries = 0;

    try {
        const res = await fetch(`${API_BASE}/system/update`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({})
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok && res.status !== 409) {
            throw new Error(data.error || "Server returned " + res.status);
        }
    } catch (err) {
        if (updateConsole) {
            updateConsole.innerHTML += `<div class="log-entry"><span class="log-time text-rose">[ERROR]</span><span class="log-msg text-rose">${escapeHtml(err.message)}</span></div>`;
        }
        if (updateStatusText) updateStatusText.textContent = "Failed to initiate update: " + err.message;
        if (btnCancelUpdateModal) {
            btnCancelUpdateModal.disabled = false;
            btnCancelUpdateModal.textContent = "Close";
        }
        if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;
        updatePollingActive = false;
        return;
    }

    pollUpdateProgress();
}

export function pollUpdateProgress() {
    if (updatePollTimer) clearTimeout(updatePollTimer);

    const updateStatusBanner = document.getElementById("updateStatusBanner");
    const updateStatusText = document.getElementById("updateStatusText");
    const updateSpinner = document.getElementById("updateSpinner");
    const updateConsole = document.getElementById("updateConsole");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");

    updatePollTimer = setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/system/update/status`, {
                headers: { "Accept": "application/json" }
            });

            if (!res.ok) {
                if (res.status === 401) {
                    if (updateConsole) {
                        updateConsole.innerHTML += `<div class="log-entry"><span class="log-time text-emerald">[DONE]</span><span class="log-msg text-emerald font-bold">Services restarted with updated code! Reloading dashboard...</span></div>`;
                        updateConsole.scrollTop = updateConsole.scrollHeight;
                    }
                    if (updateStatusText) {
                        updateStatusText.innerHTML = "<strong>Update Complete!</strong> Reloading dashboard in 1.2s...";
                    }
                    setTimeout(() => window.location.reload(), 1200);
                    return;
                }
                throw new Error("Status HTTP " + res.status);
            }
            const data = await res.json();
            updateReconnectTries = 0;

            if (data.log && updateConsole) {
                const lines = data.log.split("\n");
                let logHtml = "";
                lines.forEach(l => {
                    if (!l.trim()) return;
                    let cls = "text-secondary";
                    if (l.includes("[OK]")) cls = "text-emerald font-bold";
                    else if (l.includes("[ERROR]") || l.includes("Failed")) cls = "text-rose font-bold";
                    else if (l.includes("[WARN]")) cls = "text-amber";
                    else if (l.includes("[INFO]")) cls = "text-cyan";
                    logHtml += `<div class="log-entry"><span class="log-msg ${cls}">${escapeHtml(l)}</span></div>`;
                });
                updateConsole.innerHTML = logHtml || '<div class="log-entry"><span class="log-msg text-muted">Running update...</span></div>';
                updateConsole.scrollTop = updateConsole.scrollHeight;
            }

            if (data.status === "completed") {
                if (updateStatusBanner) {
                    updateStatusBanner.style.background = "rgba(16, 185, 129, 0.16)";
                    updateStatusBanner.style.border = "1px solid rgba(16, 185, 129, 0.35)";
                    updateStatusBanner.style.color = "var(--accent-mint)";
                }
                if (updateSpinner) updateSpinner.style.display = "none";
                if (updateStatusText) {
                    updateStatusText.innerHTML = "<strong>Update Completed Successfully!</strong> Refreshing dashboard in 1.5s...";
                }
                if (btnCancelUpdateModal) {
                    btnCancelUpdateModal.disabled = false;
                    btnCancelUpdateModal.textContent = "Reload Now";
                    btnCancelUpdateModal.onclick = () => window.location.reload();
                }
                if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;
                updatePollingActive = false;

                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                return;
            } else if (data.status === "failed") {
                if (updateStatusBanner) {
                    updateStatusBanner.style.background = "rgba(244, 63, 94, 0.16)";
                    updateStatusBanner.style.border = "1px solid rgba(244, 63, 94, 0.35)";
                    updateStatusBanner.style.color = "var(--accent-rose)";
                }
                if (updateSpinner) updateSpinner.style.display = "none";
                if (updateStatusText) {
                    updateStatusText.textContent = "Update encountered an error. Check logs above.";
                }
                if (btnCancelUpdateModal) {
                    btnCancelUpdateModal.disabled = false;
                    btnCancelUpdateModal.textContent = "Close";
                }
                if (btnCloseUpdateModal) btnCloseUpdateModal.disabled = false;
                updatePollingActive = false;
                return;
            } else {
                if (updateStatusText) {
                    updateStatusText.textContent = "Applying update and restarting services...";
                }
                pollUpdateProgress();
            }
        } catch (_) {
            updateReconnectTries++;
            if (updateStatusBanner) {
                updateStatusBanner.style.background = "rgba(167, 139, 250, 0.16)";
                updateStatusBanner.style.border = "1px solid rgba(167, 139, 250, 0.35)";
                updateStatusBanner.style.color = "var(--accent-violet)";
            }
            if (updateStatusText) {
                updateStatusText.textContent = `Services reloading with new update... Waiting for web panel to resume (Attempt ${updateReconnectTries})...`;
            }
            if (updateConsole && updateReconnectTries <= 2) {
                updateConsole.innerHTML += `<div class="log-entry"><span class="log-time text-violet">[RELOAD]</span><span class="log-msg text-violet">Web daemon reloading with new code...</span></div>`;
                updateConsole.scrollTop = updateConsole.scrollHeight;
            }

            if (updateReconnectTries > 30) {
                if (updateStatusText) {
                    updateStatusText.textContent = "Server reconnection timeout. Please refresh your browser.";
                }
                if (btnCancelUpdateModal) {
                    btnCancelUpdateModal.disabled = false;
                    btnCancelUpdateModal.textContent = "Reload Page";
                    btnCancelUpdateModal.onclick = () => window.location.reload();
                }
                updatePollingActive = false;
                return;
            }
            pollUpdateProgress();
        }
    }, 1200);
}

export function initServiceRestartControls(fetchStatusCallback) {
    const btnRestartAllServices = document.getElementById("btnRestartAllServices");
    const btnRestartCoreEngine = document.getElementById("btnRestartCoreEngine");
    const btnReloadHaproxy = document.getElementById("btnReloadHaproxy");
    const btnResyncNftables = document.getElementById("btnResyncNftables");
    const btnReloadNginx = document.getElementById("btnReloadNginx");

    if (btnRestartAllServices) {
        btnRestartAllServices.addEventListener("click", () => handleServiceRestart("all", fetchStatusCallback));
    }
    if (btnRestartCoreEngine) {
        btnRestartCoreEngine.addEventListener("click", () => handleServiceRestart("engine", fetchStatusCallback));
    }
    if (btnReloadHaproxy) {
        btnReloadHaproxy.addEventListener("click", () => handleServiceRestart("haproxy", fetchStatusCallback));
    }
    if (btnResyncNftables) {
        btnResyncNftables.addEventListener("click", () => handleServiceRestart("nftables", fetchStatusCallback));
    }
    if (btnReloadNginx) {
        btnReloadNginx.addEventListener("click", () => handleServiceRestart("nginx", fetchStatusCallback));
    }
}

export async function handleServiceRestart(service, fetchStatusCallback) {
    const serviceNames = {
        all: "All Relay Services & Daemons",
        engine: "XForwarder Core Failover Engine",
        haproxy: "HAProxy Relay Service",
        nginx: "Nginx Stream Proxy",
        nftables: "NFTables Table 'xfwd_orchestrator'"
    };
    const friendlyName = serviceNames[service] || service;
    const isFullRestart = service === "all" || service === "web";
    const warnMsg = isFullRestart
        ? `Are you sure you want to restart ${friendlyName}? The web dashboard will temporarily disconnect and reconnect automatically in ~2 seconds.`
        : `Are you sure you want to reload/restart ${friendlyName}? Active client connections will be preserved.`;

    const confirmed = await askConfirm(`Restart ${friendlyName}?`, warnMsg);
    if (!confirmed) return;

    showToast(`Restarting ${friendlyName}...`, "info");

    try {
        const res = await fetch(`${API_BASE}/services/restart`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ service })
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
            throw new Error(data.error || `HTTP ${res.status}`);
        }

        if (data.reconnecting) {
            showToast(data.message || "Services restarting...", "info");
            pollDashboardReconnection();
        } else {
            showToast(data.message || `${friendlyName} reloaded successfully!`, "success");
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        }
    } catch (err) {
        showToast(`Failed to restart ${friendlyName}: ${err.message}`, "error");
    }
}

export function pollDashboardReconnection() {
    let tries = 0;
    const interval = setInterval(async () => {
        tries++;
        try {
            const res = await fetch(`${API_BASE}/services/status`);
            if (res.ok) {
                clearInterval(interval);
                showToast("Dashboard reconnected successfully!", "success");
                setTimeout(() => window.location.reload(), 1000);
            }
        } catch (_) {
            if (tries > 25) {
                clearInterval(interval);
                showToast("Please refresh the page manually", "warn");
            }
        }
    }, 1500);
}
