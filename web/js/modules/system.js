// ============================================================================
// XForwarder Web UI - System Updates & Services Management (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { showToast, escapeHtml, askConfirm, askChoice } from "./utils.js";
import { t } from "./i18n.js";

let updatePollTimer = null;
let updatePollingActive = false;
let updateReconnectTries = 0;
let updateTransportsLoaded = false;

function getSelectedUpdateTransportPayload() {
    const mode = document.getElementById("selUpdateTransportMode")?.value || "auto";
    const tunnel_iface = (document.getElementById("selUpdateTunnelIface")?.value || "").trim();
    const proxy_url = (document.getElementById("inpUpdateProxyUrl")?.value || "").trim();
    const mirror_url = (document.getElementById("inpUpdateMirrorUrl")?.value || "").trim();
    return { transport_mode: mode, tunnel_iface, proxy_url, mirror_url };
}

function syncUpdateTransportVisibility() {
    const mode = document.getElementById("selUpdateTransportMode")?.value || "auto";
    const wrapIface = document.getElementById("wrapUpdateIface");
    const wrapProxy = document.getElementById("wrapUpdateProxy");
    const wrapMirror = document.getElementById("wrapUpdateMirror");
    const wrapAuto = document.getElementById("wrapUpdateAutoInfo");
    if (wrapIface) wrapIface.style.display = mode === "iface" ? "flex" : "none";
    if (wrapProxy) wrapProxy.style.display = mode === "proxy" ? "flex" : "none";
    if (wrapMirror) wrapMirror.style.display = mode === "mirror" ? "flex" : "none";
    if (wrapAuto) wrapAuto.style.display = (mode === "auto" || mode === "direct") ? "flex" : "none";
}

function validateUpdateTransportClient(payload) {
    if (payload.transport_mode === "iface" && !payload.tunnel_iface) {
        return "Please select an active server tunnel interface first.";
    }
    if (payload.transport_mode === "proxy" && !payload.proxy_url) {
        return "Please enter a SOCKS5 or HTTP proxy URL (e.g. socks5h://127.0.0.1:10808).";
    }
    if (payload.transport_mode === "mirror" && !payload.mirror_url) {
        return "Please enter a GitHub mirror URL (e.g. https://ghproxy.net/).";
    }
    return null;
}

export async function fetchUpdateTransports(showFeedback = false, preserveInputs = false) {
    const selMode = document.getElementById("selUpdateTransportMode");
    const selIface = document.getElementById("selUpdateTunnelIface");
    const inpProxy = document.getElementById("inpUpdateProxyUrl");
    const inpMirror = document.getElementById("inpUpdateMirrorUrl");
    const proxyChipsWrap = document.getElementById("updateProxyChipsWrap");
    const proxyChips = document.getElementById("updateProxyChips");
    const valCounts = document.getElementById("valDetectedTransportCounts");

    try {
        const res = await fetch(`${API_BASE}/system/update/transports`, {
            headers: { "Accept": "application/json" }
        });
        if (!res.ok) return null;
        const data = await res.json();
        updateTransportsLoaded = true;

        const tunnels = Array.isArray(data.tunnels) ? data.tunnels : [];
        const proxies = Array.isArray(data.local_proxies) ? data.local_proxies : [];
        const cfg = data.config || {};

        if (!preserveInputs) {
            if (selMode && cfg.transport_mode) selMode.value = cfg.transport_mode;
            if (inpProxy && typeof cfg.proxy_url === "string") inpProxy.value = cfg.proxy_url;
            if (inpMirror && typeof cfg.mirror_url === "string") inpMirror.value = cfg.mirror_url;
        }

        if (selIface) {
            const currentVal = preserveInputs ? selIface.value : (cfg.tunnel_iface || "");
            selIface.innerHTML = "";
            if (tunnels.length === 0) {
                const opt = document.createElement("option");
                opt.value = "";
                opt.textContent = t("updates.iface_empty", {}, "No active tunnel interfaces detected");
                selIface.appendChild(opt);
            } else {
                tunnels.forEach((tun) => {
                    const opt = document.createElement("option");
                    opt.value = tun.name || "";
                    const latText = (tun.latency_ms !== null && tun.latency_ms !== undefined) ? ` · ${tun.latency_ms}ms` : "";
                    const stateText = tun.state === "UP" ? "UP" : "DOWN";
                    opt.textContent = `${tun.name} · ${tun.type || "Tunnel"} (${stateText}${latText})`;
                    selIface.appendChild(opt);
                });
                if (currentVal && Array.from(selIface.options).some((o) => o.value === currentVal)) {
                    selIface.value = currentVal;
                } else {
                    const firstUsable = tunnels.find((tun) => tun.usable);
                    if (firstUsable) selIface.value = firstUsable.name;
                }
            }
        }

        if (proxyChipsWrap && proxyChips) {
            proxyChips.innerHTML = "";
            if (proxies.length > 0) {
                proxyChipsWrap.style.display = "block";
                proxies.forEach((prx) => {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "update-proxy-chip";
                    btn.textContent = `${String(prx.proto || "proxy").toUpperCase()} :${prx.port}`;
                    btn.title = prx.url;
                    btn.addEventListener("click", () => {
                        if (inpProxy) inpProxy.value = prx.url;
                        if (selMode) {
                            selMode.value = "proxy";
                            syncUpdateTransportVisibility();
                        }
                    });
                    proxyChips.appendChild(btn);
                });
            } else {
                proxyChipsWrap.style.display = "none";
            }
        }

        if (valCounts) {
            const upTunnels = tunnels.filter((tun) => tun.usable).length;
            valCounts.textContent = t(
                "updates.detected_summary",
                { tunnels: upTunnels, proxies: proxies.length },
                `${upTunnels} UP tunnel(s) · ${proxies.length} local proxy(s) ready`
            );
        }

        syncUpdateTransportVisibility();
        if (showFeedback) {
            const upTunnels = tunnels.filter((tun) => tun.usable).length;
            showToast(
                t(
                    "updates.detected_summary",
                    { tunnels: upTunnels, proxies: proxies.length },
                    `${upTunnels} UP tunnel(s) · ${proxies.length} local proxy(s) ready`
                ),
                "info"
            );
        }
        return data;
    } catch (_) {
        return null;
    }
}

export function initSystemUpdateManager() {
    const btnCheckUpdates = document.getElementById("btnCheckUpdates");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const iconCheckUpdates = document.getElementById("iconCheckUpdates");
    const selUpdateTransportMode = document.getElementById("selUpdateTransportMode");
    const btnScanUpdateTunnels = document.getElementById("btnScanUpdateTunnels");
    const btnSaveUpdateTransport = document.getElementById("btnSaveUpdateTransport");

    if (selUpdateTransportMode) {
        selUpdateTransportMode.addEventListener("change", syncUpdateTransportVisibility);
        syncUpdateTransportVisibility();
    }

    if (btnScanUpdateTunnels) {
        btnScanUpdateTunnels.addEventListener("click", async () => {
            btnScanUpdateTunnels.disabled = true;
            await fetchUpdateTransports(true, true);
            btnScanUpdateTunnels.disabled = false;
        });
    }

    if (btnSaveUpdateTransport) {
        btnSaveUpdateTransport.addEventListener("click", async () => {
            const payload = getSelectedUpdateTransportPayload();
            const valErr = validateUpdateTransportClient(payload);
            if (valErr) {
                showToast(valErr, "error");
                return;
            }
            btnSaveUpdateTransport.disabled = true;
            try {
                const res = await fetch(`${API_BASE}/system/update/transports`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Accept": "application/json" },
                    body: JSON.stringify({ ...payload, test: true })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data.error || `HTTP ${res.status}`);
                }
                if (data.version_status) {
                    renderVersionStatusData(data.version_status);
                    if (data.version_status.check_error) {
                        showToast(`Saved, but GitHub check failed: ${data.version_status.check_error}`, "warn");
                    } else {
                        const viaLabel = data.version_status.used_transport?.label || payload.transport_mode;
                        showToast(`Update route verified cleanly (${viaLabel})`, "success");
                    }
                } else {
                    showToast("Update connection settings saved", "success");
                }
            } catch (err) {
                showToast("Failed to save update transport: " + err.message, "error");
            } finally {
                btnSaveUpdateTransport.disabled = false;
            }
        });
    }

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
        btnTriggerUpdate.addEventListener("click", async () => {
            if (btnTriggerUpdate.disabled || updatePollingActive) return;
            const confirmed = await askConfirm(
                t("update_modal.title", {}, "XForwarder System Update"),
                t("update_modal.ready_sub", {}, "Pull latest release from GitHub, execute schema migrations, and reload daemons?"),
                t("update_modal.start_btn", {}, "Start Update Now")
            );
            if (confirmed) {
                startSystemUpdateProcedure();
            }
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
}

function renderVersionStatusData(data) {
    const valInstalledVersion = document.getElementById("valInstalledVersion");
    const valLocalCommit = document.getElementById("valLocalCommit");
    const valRemoteCommit = document.getElementById("valRemoteCommit");
    const valLastChecked = document.getElementById("valLastChecked");
    const badgeUpdateStatus = document.getElementById("badgeUpdateStatus");
    const updateStatusNotice = document.getElementById("updateStatusNotice");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");
    const btnTriggerUpdateText = document.getElementById("btnTriggerUpdateText");
    const badgeTransportSummary = document.getElementById("badgeUpdateTransportSummary");

    if (valInstalledVersion && data.current_version) {
        valInstalledVersion.textContent = `v${data.current_version}`;
    }
    const brandVersionBadge = document.getElementById("brandVersionBadge");
    if (brandVersionBadge && data.current_version) {
        brandVersionBadge.textContent = `v${data.current_version}`;
    }
    if (badgeTransportSummary) {
        const used = data.used_transport;
        if (used && used.label) {
            badgeTransportSummary.textContent = t("updates.via_prefix", { label: used.label }, `Route: ${used.label}`);
            badgeTransportSummary.className = "stat-badge badge-good ltr-mono";
        } else if (data.transport_config && data.transport_config.transport_mode) {
            const tm = data.transport_config.transport_mode;
            badgeTransportSummary.textContent = tm === "auto"
                ? t("updates.transport_auto_short", {}, "Auto Discovery")
                : String(tm).toUpperCase();
            badgeTransportSummary.className = "stat-badge badge-neutral ltr-mono";
        }
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

    const navUpdateDot = document.getElementById("navUpdateDot");
    if (navUpdateDot) {
        navUpdateDot.style.display = data.update_available ? "inline-block" : "none";
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
            updateStatusNotice.innerHTML = `<strong>Could Not Reach GitHub:</strong> ${errText}. Select an active server tunnel or local proxy below and click <strong>Save &amp; Test</strong>.`;
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
}

export async function fetchSystemVersionInfo(force = false) {
    try {
        if (!updateTransportsLoaded) {
            fetchUpdateTransports(false, false);
        }
        const res = await fetch(`${API_BASE}/system/version${force ? "?check=1" : ""}`, {
            headers: { "Accept": "application/json" }
        });
        if (!res.ok) return null;
        const data = await res.json();
        renderVersionStatusData(data);
        return data;
    } catch (_) {
        return null;
    }
}

export function openSystemUpdateModal() {
    const updateModal = document.getElementById("updateModal");
    const updateConfirmView = document.getElementById("updateConfirmView");
    const btnCancelUpdateModal = document.getElementById("btnCancelUpdateModal");
    const btnConfirmStartUpdate = document.getElementById("btnConfirmStartUpdate");
    const btnCloseUpdateModal = document.getElementById("btnCloseUpdateModal");

    if (updateConfirmView) updateConfirmView.style.display = "block";
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
    if (updateModal) updateModal.classList.remove("show");
}

function setInlineUpdateVisualState(state) {
    const banner = document.getElementById("updateStatusBanner");
    const bar = document.getElementById("updateProgressBar");
    const spinner = document.getElementById("updateSpinner");
    const stateClasses = ["is-running", "is-reloading", "is-success", "is-error"];
    [banner, bar].forEach((el) => {
        if (!el) return;
        el.classList.remove(...stateClasses);
        el.classList.add(`is-${state}`);
    });
    if (spinner) {
        spinner.style.display = (state === "running" || state === "reloading") ? "block" : "none";
    }
}

function renderUpdateConsoleErrors(rawLog, fallbackMessage = "") {
    const updateConsole = document.getElementById("updateConsole");
    if (!updateConsole) return;
    let logHtml = "";
    if (rawLog) {
        rawLog.split("\n").forEach((l) => {
            if (!l.trim()) return;
            let cls = "text-secondary";
            if (l.includes("[OK]")) cls = "text-emerald font-bold";
            else if (l.includes("[ERROR]") || l.includes("Failed") || l.toLowerCase().includes("fatal")) cls = "text-rose font-bold";
            else if (l.includes("[WARN]")) cls = "text-amber";
            else if (l.includes("[INFO]")) cls = "text-cyan";
            logHtml += `<div class="log-entry"><span class="log-msg ${cls}">${escapeHtml(l)}</span></div>`;
        });
    }
    if (!logHtml && fallbackMessage) {
        logHtml = `<div class="log-entry"><span class="log-time text-rose">[ERROR]</span><span class="log-msg text-rose">${escapeHtml(fallbackMessage)}</span></div>`;
    }
    updateConsole.innerHTML = logHtml;
    updateConsole.style.display = "block";
    updateConsole.scrollTop = updateConsole.scrollHeight;
}

export async function startSystemUpdateProcedure() {
    const updateModal = document.getElementById("updateModal");
    const updateProgressView = document.getElementById("updateProgressView");
    const btnCheckUpdates = document.getElementById("btnCheckUpdates");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");
    const updateStatusText = document.getElementById("updateStatusText");
    const updateConsole = document.getElementById("updateConsole");

    const transportPayload = getSelectedUpdateTransportPayload();
    const valErr = validateUpdateTransportClient(transportPayload);
    if (valErr) {
        showToast(valErr, "error");
        return;
    }

    if (updateModal) updateModal.classList.remove("show");
    if (btnCheckUpdates) btnCheckUpdates.disabled = true;
    if (btnTriggerUpdate) btnTriggerUpdate.disabled = true;

    if (updateProgressView) {
        updateProgressView.style.display = "block";
        updateProgressView.classList.remove("is-open");
        requestAnimationFrame(() => updateProgressView.classList.add("is-open"));
    }
    if (updateConsole) {
        updateConsole.style.display = "none";
        updateConsole.innerHTML = "";
    }
    setInlineUpdateVisualState("running");
    if (updateStatusText) updateStatusText.textContent = "Initiating system update...";

    updatePollingActive = true;
    updateReconnectTries = 0;

    try {
        const res = await fetch(`${API_BASE}/system/update`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(transportPayload)
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok && res.status !== 409) {
            throw new Error(data.error || "Server returned " + res.status);
        }
    } catch (err) {
        setInlineUpdateVisualState("error");
        if (updateStatusText) updateStatusText.textContent = "Failed to initiate update: " + err.message;
        renderUpdateConsoleErrors("", err.message);
        if (btnCheckUpdates) btnCheckUpdates.disabled = false;
        if (btnTriggerUpdate) btnTriggerUpdate.disabled = false;
        updatePollingActive = false;
        return;
    }

    pollUpdateProgress();
}

export function pollUpdateProgress() {
    if (updatePollTimer) clearTimeout(updatePollTimer);

    const updateStatusText = document.getElementById("updateStatusText");
    const btnCheckUpdates = document.getElementById("btnCheckUpdates");
    const btnTriggerUpdate = document.getElementById("btnTriggerUpdate");

    updatePollTimer = setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/system/update/status`, {
                headers: { "Accept": "application/json" }
            });

            if (!res.ok) {
                if (res.status === 401) {
                    setInlineUpdateVisualState("success");
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

            if (data.status === "completed") {
                setInlineUpdateVisualState("success");
                if (updateStatusText) {
                    updateStatusText.innerHTML = "<strong>Update Completed Successfully!</strong> Refreshing dashboard in 1.5s...";
                }
                updatePollingActive = false;
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                return;
            } else if (data.status === "failed") {
                setInlineUpdateVisualState("error");
                if (updateStatusText) {
                    updateStatusText.textContent = "Update failed. Exact error log shown below:";
                }
                renderUpdateConsoleErrors(data.log || "", "Update job exited with failure status.");
                if (btnCheckUpdates) btnCheckUpdates.disabled = false;
                if (btnTriggerUpdate) btnTriggerUpdate.disabled = false;
                updatePollingActive = false;
                return;
            } else {
                setInlineUpdateVisualState("running");
                const lines = (data.log || "").split("\n").map((l) => l.trim()).filter(Boolean);
                const lastLine = lines.length ? lines[lines.length - 1].replace(/^\[[^\]]+\]\s*/, "") : "";
                if (updateStatusText) {
                    updateStatusText.textContent = lastLine || "Applying update and restarting services...";
                }
                pollUpdateProgress();
            }
        } catch (_) {
            updateReconnectTries++;
            setInlineUpdateVisualState("reloading");
            if (updateStatusText) {
                updateStatusText.textContent = `Reloading services with new update... Reconnecting (${updateReconnectTries})...`;
            }

            if (updateReconnectTries > 30) {
                setInlineUpdateVisualState("error");
                if (updateStatusText) {
                    updateStatusText.textContent = "Server reconnection timeout. Please refresh your browser.";
                }
                renderUpdateConsoleErrors("", "Timed out waiting for web service to resume after update.");
                if (btnCheckUpdates) btnCheckUpdates.disabled = false;
                if (btnTriggerUpdate) btnTriggerUpdate.disabled = false;
                updatePollingActive = false;
                return;
            }
            pollUpdateProgress();
        }
    }, 1200);
}

/**
 * Binds UI event listeners to all relay service reload and restart buttons.
 *
 * @param {Function} [fetchStatusCallback] - Optional callback to refresh dashboard telemetry.
 */
export function initServiceRestartControls(fetchStatusCallback) {
    const btnRestartAllServices = document.getElementById("btnRestartAllServices");
    const btnRestartCoreEngine = document.getElementById("btnRestartCoreEngine");
    const btnReloadHaproxy = document.getElementById("btnReloadHaproxy");
    const btnRestartHaproxy = document.getElementById("btnRestartHaproxy");
    const btnResyncNftables = document.getElementById("btnResyncNftables");
    const btnRestartNftables = document.getElementById("btnRestartNftables");
    const btnSyncNginx = document.getElementById("btnSyncNginx");
    const btnReloadNginx = document.getElementById("btnReloadNginx");
    const btnRestartNginx = document.getElementById("btnRestartNginx");

    if (btnRestartAllServices) {
        btnRestartAllServices.addEventListener("click", () => handleServiceRestart("all", fetchStatusCallback));
    }
    if (btnRestartCoreEngine) {
        btnRestartCoreEngine.addEventListener("click", () => handleServiceRestart("engine", fetchStatusCallback));
    }
    if (btnReloadHaproxy) {
        btnReloadHaproxy.addEventListener("click", () => handleServiceRestart("haproxy", fetchStatusCallback));
    }
    if (btnRestartHaproxy) {
        btnRestartHaproxy.addEventListener("click", () => handleServiceRestart("haproxy_restart", fetchStatusCallback));
    }
    if (btnResyncNftables) {
        btnResyncNftables.addEventListener("click", () => handleServiceRestart("nftables", fetchStatusCallback));
    }
    if (btnRestartNftables) {
        btnRestartNftables.addEventListener("click", () => handleServiceRestart("nftables_restart", fetchStatusCallback));
    }
    if (btnSyncNginx) {
        btnSyncNginx.addEventListener("click", () => handleNginxSyncChoice(fetchStatusCallback));
    }
    if (btnReloadNginx) {
        btnReloadNginx.addEventListener("click", () => handleServiceRestart("nginx", fetchStatusCallback));
    }
    if (btnRestartNginx) {
        btnRestartNginx.addEventListener("click", () => handleServiceRestart("nginx_restart", fetchStatusCallback));
    }
}

/**
 * Prompts the user to choose bidirectional Nginx sync mode:
 * - Primary: Apply XForwarder rules onto Nginx (`nginx_sync`)
 * - Alt: Sync XForwarder priorities from actual Nginx stream config (`nginx_pull`)
 */
export async function handleNginxSyncChoice(fetchStatusCallback) {
    const choice = await askChoice(
        t("services.nginx_sync_mode_title", {}, "Choose Nginx Sync Direction"),
        t("services.nginx_sync_mode_msg", {}, "Choose whether to apply XForwarder settings to Nginx config, or update XForwarder's Nginx priorities from the actual Nginx configuration on the server (if Nginx is empty, Nginx priorities in Ports will be removed)."),
        t("services.nginx_sync_push_btn", {}, "XForwarder → Nginx"),
        t("services.nginx_sync_pull_btn", {}, "Nginx → XForwarder")
    );
    if (!choice) return;
    const svcAction = choice === "alt" ? "nginx_pull" : "nginx_sync";
    await dispatchServiceAction(svcAction, t("services.name_nginx", {}, "Nginx Stream Proxy"), false, fetchStatusCallback);
}

/**
 * Orchestrates user confirmation, API dispatch, and toast notifications for service lifecycle actions.
 *
 * @param {string} service - Service identifier (e.g., 'all', 'engine', 'haproxy', 'haproxy_restart', etc.).
 * @param {Function} [fetchStatusCallback] - Optional callback to refresh status after action completes.
 */
export async function handleServiceRestart(service, fetchStatusCallback) {
    const serviceNames = {
        all: t("services.name_all", {}, "All Relay Services & Daemons"),
        engine: t("services.name_engine", {}, "XForwarder Core Failover Engine"),
        haproxy: t("services.name_haproxy", {}, "HAProxy Relay Service"),
        haproxy_restart: t("services.name_haproxy", {}, "HAProxy Relay Service"),
        nginx: t("services.name_nginx", {}, "Nginx Stream Proxy"),
        nginx_sync: t("services.name_nginx", {}, "Nginx Stream Proxy"),
        nginx_pull: t("services.name_nginx", {}, "Nginx Stream Proxy"),
        nginx_restart: t("services.name_nginx", {}, "Nginx Stream Proxy"),
        nftables: t("services.name_nftables", {}, "NFTables Table 'xfwd_orchestrator'"),
        nftables_restart: t("services.name_nftables", {}, "NFTables Table 'xfwd_orchestrator'")
    };
    const friendlyName = serviceNames[service] || service;
    const isFullRestart = service === "all" || service === "web";
    const isExplicitRestart = isFullRestart || service === "engine" || String(service).endsWith("_restart");
    const isSyncOnly = service === "nftables" || service === "nginx_sync" || service === "nginx_pull";

    let modalTitle;
    let warnMsg;
    let confirmBtnText;

    if (isFullRestart) {
        modalTitle = t("confirm.restart_svc_title", { service: friendlyName }, `Restart ${friendlyName}?`);
        warnMsg = t("confirm.restart_all_msg", { service: friendlyName }, `Are you sure you want to restart ${friendlyName}? The web dashboard will temporarily disconnect and reconnect automatically in ~2 seconds.`);
        confirmBtnText = t("confirm.restart_btn", {}, "Restart Service");
    } else if (isExplicitRestart) {
        modalTitle = t("confirm.restart_svc_title", { service: friendlyName }, `Restart ${friendlyName}?`);
        warnMsg = t("confirm.restart_svc_msg", { service: friendlyName }, `Are you sure you want to restart ${friendlyName}? Configuration will be re-synchronized and the service will restart cleanly.`);
        confirmBtnText = t("confirm.restart_btn", {}, "Restart Service");
    } else if (isSyncOnly) {
        modalTitle = t("confirm.sync_svc_title", { service: friendlyName }, `Synchronize ${friendlyName}?`);
        warnMsg = t("confirm.reload_svc_msg", { service: friendlyName }, `Are you sure you want to reload/restart ${friendlyName}? Active client connections will be preserved.`);
        confirmBtnText = t("confirm.sync_btn", {}, "Sync Table");
    } else {
        modalTitle = t("confirm.reload_svc_title", { service: friendlyName }, `Reload ${friendlyName}?`);
        warnMsg = t("confirm.reload_svc_msg", { service: friendlyName }, `Are you sure you want to reload/restart ${friendlyName}? Active client connections will be preserved.`);
        confirmBtnText = t("confirm.reload_btn", {}, "Reload Service");
    }

    const confirmed = await askConfirm(modalTitle, warnMsg, {
        confirmText: confirmBtnText,
        variant: "primary"
    });
    if (!confirmed) return;

    await dispatchServiceAction(service, friendlyName, isExplicitRestart, fetchStatusCallback);
}

async function dispatchServiceAction(service, friendlyName, isExplicitRestart, fetchStatusCallback) {
    showToast(t("services.restarting_toast", { service: friendlyName }, `Restarting ${friendlyName}...`), "info");

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
            const defaultDoneMsg = isExplicitRestart
                ? t("services.restarted_toast", { service: friendlyName }, `${friendlyName} restarted successfully!`)
                : t("services.reloaded_toast", { service: friendlyName }, `${friendlyName} reloaded successfully!`);
            showToast(data.message || defaultDoneMsg, "success");
            if (typeof fetchStatusCallback === "function") fetchStatusCallback();
        }
    } catch (err) {
        showToast(t("services.restart_failed_toast", { service: friendlyName, error: err.message }, `Failed to restart ${friendlyName}: ${err.message}`), "error");
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

/**
 * Renders live kernel tuning telemetry and conflict alerts inside #cardKernelOptimizer.
 */
function renderKernelOptimizerState(data) {
    const badge = document.getElementById("badgeKernelOptStatus");
    const profEl = document.getElementById("kernelOptProfile");
    const tcpEl = document.getElementById("kernelOptTcp");
    const rpEl = document.getElementById("kernelOptRpFilter");
    const ctEl = document.getElementById("kernelOptConntrack");
    const conflictsEl = document.getElementById("kernelOptConflicts");
    const resetRow = document.querySelector(".kernel-opt-reset-row");
    if (!data || typeof data !== "object") return;

    const prof = data.profile || {};
    const live = data.live || {};
    const conflicts = Array.isArray(data.conflicts) ? data.conflicts : [];

    if (profEl) {
        profEl.textContent = prof.mem_mb ? `${prof.mem_mb} MB · ${prof.cpu_cores || 1} vCPU` : "--";
    }
    if (tcpEl) {
        tcpEl.textContent = `${live.congestion_control || "?"} · ${live.default_qdisc || "?"}`;
    }
    if (rpEl) {
        const rpAll = live.rp_filter_all;
        rpEl.textContent = (rpAll === 0) ? "0 (ESP/DSR Safe)" : (rpAll !== null && rpAll !== undefined ? `${rpAll} (Non-zero)` : "--");
        rpEl.style.color = (rpAll === 0) ? "var(--accent-emerald, #10b981)" : (rpAll > 0 ? "#f59e0b" : "");
    }
    if (ctEl) {
        const ctMaxStr = live.conntrack_max ? Number(live.conntrack_max).toLocaleString() : "--";
        ctEl.textContent = live.conntrack_loaded ? `Loaded · max ${ctMaxStr}` : "Not loaded";
    }

    if (badge) {
        if (conflicts.length > 0) {
            badge.className = "stat-badge badge-amber";
            badge.textContent = "CONFLICT";
        } else if (data.optimal) {
            badge.className = "stat-badge badge-good";
            badge.textContent = "OPTIMIZED";
        } else if (data.tuned) {
            badge.className = "stat-badge badge-active";
            badge.textContent = "TUNED";
        } else {
            badge.className = "stat-badge badge-warn";
            badge.textContent = "DEFAULT";
        }
    }

    if (conflictsEl) {
        if (conflicts.length > 0) {
            const hdr = escapeHtml(t("services.kernel_opt_conflict_hdr", {}, "Conflicts / legacy kernel settings detected:"));
            const items = conflicts.map(c => `<li>${escapeHtml(String(c.message || c.code || ""))}</li>`).join("");
            conflictsEl.innerHTML = `<strong>${hdr}</strong><ul>${items}</ul>`;
            conflictsEl.style.display = "block";
        } else {
            conflictsEl.style.display = "none";
            conflictsEl.innerHTML = "";
        }
    }
    if (resetRow) {
        resetRow.classList.toggle("has-warning", conflicts.length > 0);
    }
}

export async function refreshKernelOptimizerStatus() {
    if (!document.getElementById("cardKernelOptimizer")) return;
    try {
        const res = await fetch(`${API_BASE}/system/optimize`, { headers: { "Accept": "application/json" } });
        if (!res.ok) return;
        const data = await res.json();
        renderKernelOptimizerState(data);
    } catch (_) {}
}

export function initKernelOptimizer(fetchStatusCallback) {
    const btnRefresh = document.getElementById("btnRefreshKernelOpt");
    const btnApply = document.getElementById("btnApplyKernelOpt");
    const chkReset = document.getElementById("chkKernelOptReset");
    const resultEl = document.getElementById("kernelOptResult");

    if (btnRefresh) {
        btnRefresh.addEventListener("click", async () => {
            btnRefresh.disabled = true;
            await refreshKernelOptimizerStatus();
            btnRefresh.disabled = false;
        });
    }

    if (btnApply) {
        btnApply.addEventListener("click", async () => {
            const resetExisting = Boolean(chkReset && chkReset.checked);
            const title = t("services.kernel_opt_confirm_title", {}, "Apply Kernel & Network Optimization?");
            const msg = resetExisting
                ? t("services.kernel_opt_confirm_reset_msg", {}, "Creates a backup, clears previous /etc/sysctl.conf and conflicting files, deduplicates /etc/modules, and applies clean ESP/DSR-safe optimization.")
                : t("services.kernel_opt_confirm_msg", {}, "Applies adaptive BBR, fq qdisc, conntrack scaling, MTU probing, and rp_filter=0 cleanly.");
            const confirmed = await askConfirm(title, msg, {
                confirmText: t("services.kernel_opt_apply", {}, "Optimize Now"),
                variant: resetExisting ? "warn" : "primary"
            });
            if (!confirmed) return;

            btnApply.disabled = true;
            const labelSpan = btnApply.querySelector("span");
            const prevLabel = labelSpan ? labelSpan.textContent : "";
            if (labelSpan) labelSpan.textContent = t("services.kernel_opt_applying", {}, "Optimizing...");

            try {
                const res = await fetch(`${API_BASE}/system/optimize`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Accept": "application/json" },
                    body: JSON.stringify({ reset_existing: resetExisting })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok || !data.ok) {
                    throw new Error(data.error || `HTTP ${res.status}`);
                }
                if (data.status) renderKernelOptimizerState(data.status);
                if (chkReset) chkReset.checked = false;
                if (resultEl) {
                    const bakDir = data.reset && data.reset.backup_dir ? ` · Backup: <code class="font-mono">${escapeHtml(data.reset.backup_dir)}</code>` : "";
                    resultEl.innerHTML = `<strong>OK:</strong> ${escapeHtml(data.message || "Kernel optimization applied")}${bakDir}`;
                    resultEl.style.display = "block";
                }
                showToast(data.message || "Kernel optimization applied!", "success");
                if (typeof fetchStatusCallback === "function") fetchStatusCallback();
            } catch (err) {
                showToast(`Optimization failed: ${err.message}`, "error");
            } finally {
                btnApply.disabled = false;
                if (labelSpan && prevLabel) labelSpan.textContent = prevLabel;
            }
        });
    }
}

let spoofStatusPollTimer = null;

function renderSpoofTestState(data) {
    if (!data || typeof data !== "object") return;
    const local = data.local || {};
    const listener = data.listener || {};
    const badge = document.getElementById("badgeSpoofLocalReady");
    const pillsEl = document.getElementById("spoofLocalPills");
    const btnToggle = document.getElementById("btnSpoofListenToggle");
    const statusBox = document.getElementById("spoofListenStatusBox");
    const cliCode = document.getElementById("spoofListenCliCmd");

    if (badge) {
        if (local.raw_socket_ok) {
            badge.className = "stat-badge badge-good";
            badge.textContent = "READY";
        } else {
            badge.className = "stat-badge badge-rose";
            badge.textContent = "RESTRICTED";
        }
    }

    if (pillsEl) {
        const rawCls = local.raw_socket_ok ? "is-ok" : "is-bad";
        const fwdCls = local.ip_forward === true ? "is-ok" : "is-bad";
        const rpCls = local.rp_filter_all === 0 ? "is-ok" : "";
        pillsEl.innerHTML = `
            <span class="spoof-pill font-mono ${rawCls}">RAW_HDRINCL: ${local.raw_socket_ok ? "OK" : "FAIL"}</span>
            <span class="spoof-pill font-mono ${fwdCls}">ip_forward: ${local.ip_forward === true ? "1" : (local.ip_forward === false ? "0" : "?")}</span>
            <span class="spoof-pill font-mono ${rpCls}">rp_filter: ${local.rp_filter_all !== null && local.rp_filter_all !== undefined ? local.rp_filter_all : "?"}</span>
            <span class="spoof-pill font-mono">WAN: ${escapeHtml(local.wan_ip || "--")}</span>
        `;
    }

    const listenPort = listener.port || document.getElementById("inpSpoofListenPort")?.value || 55199;
    const wanIpHint = local.wan_ip || "<PEER_IP>";
    if (cliCode) {
        cliCode.textContent = `curl -fsSL https://raw.githubusercontent.com/PouryaDe/XForwarder/main/scripts/test-dsr-spoof.sh | bash -s -- --outside ${wanIpHint} --port ${listenPort}`;
    }

    if (btnToggle) {
        const sp = btnToggle.querySelector("span");
        if (listener.active) {
            btnToggle.className = "btn btn-danger";
            if (sp) sp.textContent = t("network.spoof_listen_stop", {}, "Stop Listener");
        } else {
            btnToggle.className = "btn btn-secondary";
            if (sp) sp.textContent = t("network.spoof_listen_start", {}, "Start Listener");
        }
        btnToggle.dataset.active = listener.active ? "1" : "0";
    }

    if (statusBox) {
        if (listener.active) {
            statusBox.style.display = "block";
            statusBox.textContent = `LISTENING on UDP :${listener.port} · ${listener.remaining_seconds}s left · Ctrl: ${listener.total_ctrl || 0} · Spoof: ${listener.total_spoof || 0}`;
            if (!spoofStatusPollTimer) {
                spoofStatusPollTimer = setInterval(refreshSpoofTesterStatus, 3000);
            }
        } else {
            statusBox.style.display = "none";
            if (spoofStatusPollTimer) {
                clearInterval(spoofStatusPollTimer);
                spoofStatusPollTimer = null;
            }
        }
    }
}

export async function refreshSpoofTesterStatus() {
    if (!document.getElementById("cardDsrSpoofTester")) return;
    try {
        const res = await fetch(`${API_BASE}/system/spoof-test/status`, { headers: { "Accept": "application/json" } });
        if (!res.ok) return;
        const data = await res.json();
        renderSpoofTestState(data);
    } catch (_) {}
}

export function initDsrSpoofTester() {
    const btnRefresh = document.getElementById("btnRefreshSpoofStatus");
    const btnToggle = document.getElementById("btnSpoofListenToggle");
    const btnCopyCli = document.getElementById("btnCopySpoofCli");
    const btnRun = document.getElementById("btnRunSpoofTest");
    const inpListenPort = document.getElementById("inpSpoofListenPort");

    if (btnRefresh) {
        btnRefresh.addEventListener("click", async () => {
            btnRefresh.disabled = true;
            await refreshSpoofTesterStatus();
            btnRefresh.disabled = false;
        });
    }

    if (btnCopyCli) {
        btnCopyCli.addEventListener("click", async () => {
            const cmdText = document.getElementById("spoofListenCliCmd")?.textContent || "";
            if (!cmdText) return;
            try {
                await navigator.clipboard.writeText(cmdText);
                showToast("CLI command copied!", "success");
            } catch (_) {
                showToast("Select and copy the CLI command manually.", "warn");
            }
        });
    }

    if (btnToggle) {
        btnToggle.addEventListener("click", async () => {
            const isActive = btnToggle.dataset.active === "1";
            const port = parseInt(inpListenPort?.value || "55199", 10) || 55199;
            btnToggle.disabled = true;
            try {
                const res = await fetch(`${API_BASE}/system/spoof-test/listen`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Accept": "application/json" },
                    body: JSON.stringify(isActive ? { action: "stop" } : { action: "start", port, timeout: 180 })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
                showToast(data.message || "Listener updated.", "success");
                await refreshSpoofTesterStatus();
            } catch (err) {
                showToast(`Listener error: ${err.message}`, "error");
            } finally {
                btnToggle.disabled = false;
            }
        });
    }

    if (btnRun) {
        btnRun.addEventListener("click", async () => {
            const peerIp = (document.getElementById("inpSpoofPeerIp")?.value || "").trim();
            const spoofIp = (document.getElementById("inpSpoofSrcIp")?.value || "").trim();
            const port = parseInt(document.getElementById("inpSpoofRunPort")?.value || "55199", 10) || 55199;
            const resBox = document.getElementById("spoofTestResultBox");
            if (!peerIp) {
                showToast("Enter Peer Listener IP (e.g. your Iran server IP) first.", "error");
                return;
            }
            btnRun.disabled = true;
            const sp = btnRun.querySelector("span");
            const prevTxt = sp ? sp.textContent : "";
            if (sp) sp.textContent = t("network.spoof_running", {}, "Testing...");
            try {
                const res = await fetch(`${API_BASE}/system/spoof-test/run`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Accept": "application/json" },
                    body: JSON.stringify({ peer_ip: peerIp, spoof_ip: spoofIp, port, count: 5 })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
                if (resBox) {
                    const cls = data.verdict === "supported"
                        ? "is-supported"
                        : (data.verdict === "blocked" || data.verdict === "local_failed" ? "is-blocked" : "is-warn");
                    resBox.className = `spoof-result-box ${cls}`;
                    resBox.innerHTML = `
                        <div><strong>${escapeHtml(data.message || "")}</strong></div>
                        <div class="font-mono" style="margin-top:4px;font-size:0.74rem;">
                            Real (${escapeHtml(data.wan_ip || "--")}): ${data.ctrl_delivered}/${data.count} &middot;
                            Spoofed (${escapeHtml(data.spoof_ip || "--")}): ${data.spoof_delivered}/${data.count}
                        </div>
                    `;
                    resBox.style.display = "block";
                }
                showToast(data.verdict === "supported" ? "Spoof / DSR Supported!" : (data.verdict === "blocked" ? "Spoof Blocked by Datacenter (uRPF)" : data.message), data.verdict === "supported" ? "success" : "warn");
            } catch (err) {
                showToast(`Spoof test failed: ${err.message}`, "error");
            } finally {
                btnRun.disabled = false;
                if (sp && prevTxt) sp.textContent = prevTxt;
            }
        });
    }
}
