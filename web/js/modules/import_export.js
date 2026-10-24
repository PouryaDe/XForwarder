// ============================================================================
// XForwarder Web UI - Import & Export Module (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { showToast, escapeHtml, copyJsonToClipboard } from "./utils.js";
import { currentRules } from "./state.js";

let currentImportConfig = null;

export function getSanitizedRuleForExport(rule) {
    if (!rule) return null;
    const clean = {
        name: rule.name || `Port ${rule.port}`,
        port: parseInt(rule.port, 10),
        protocol: rule.protocol || "both"
    };
    if (rule.category && String(rule.category).trim()) {
        clean.category = String(rule.category).trim();
    }
    if (rule.comment && String(rule.comment).trim()) {
        clean.comment = String(rule.comment).trim();
    }
    if (rule.force_override !== undefined && rule.force_override !== 0) {
        clean.force_override = rule.force_override;
    }
    if (rule.active_priority !== undefined) {
        clean.active_priority = rule.active_priority;
    }

    if (Array.isArray(rule.destinations)) {
        clean.destinations = rule.destinations.map(d => {
            const destPort = parseInt(d.port || rule.port, 10);
            const cd = {
                priority: d.priority || 1,
                type: d.type || "haproxy",
                target: String(d.target || "").trim(),
                port: (destPort > 0 && destPort <= 65535) ? destPort : parseInt(rule.port, 10)
            };
            if (d.proxy_protocol) cd.proxy_protocol = true;
            if (d.is_tunnel) cd.is_tunnel = true;
            if (d.tunnel_iface) cd.tunnel_iface = d.tunnel_iface;
            return cd;
        });
    }
    return clean;
}

export function copyRuleJson(ruleId) {
    if (!Array.isArray(currentRules)) return;
    const rule = currentRules.find(r => String(r.id || `rule-${r.port}`) === String(ruleId));
    if (!rule) {
        showToast("Port rule not found", "error");
        return;
    }
    const cleanRule = getSanitizedRuleForExport(rule);
    const exportPayload = {
        rules: [cleanRule]
    };
    const jsonStr = JSON.stringify(exportPayload, null, 2);
    copyJsonToClipboard(jsonStr, `Port :${rule.port} configuration JSON copied! Ready to import.`);
}

export function copyCategoryJson(catKey) {
    if (!Array.isArray(currentRules)) return;
    const isUncat = (catKey === "__uncategorized__");
    const categoryRules = currentRules.filter(r => {
        const cat = (r.category || "").trim();
        return isUncat ? !cat : cat === catKey;
    });

    if (categoryRules.length === 0) {
        showToast("No rules found in this category", "warning");
        return;
    }

    const cleanRules = categoryRules.map(getSanitizedRuleForExport);
    const exportPayload = {
        rules: cleanRules
    };
    const jsonStr = JSON.stringify(exportPayload, null, 2);
    const catName = isUncat ? "General / Uncategorized" : catKey;
    copyJsonToClipboard(jsonStr, `Category "${catName}" (${categoryRules.length} ports) JSON copied! Ready to import.`);
}

export async function checkImportableRules() {
    try {
        const res = await fetch(`${API_BASE}/import/discover`);
        if (!res.ok) return;
        const data = await res.json();
        const banner = document.getElementById("importBanner");
        if (!banner) return;
        if (data.available && data.count > 0) {
            const portsStr = data.ports.map(p => `:${p}`).join(", ");
            const bannerText = document.getElementById("importBannerText");
            if (bannerText) {
                const srcCounts = [];
                if (data.sources) {
                    if (data.sources.haproxy > 0) srcCounts.push(`${data.sources.haproxy} HAProxy`);
                    if (data.sources.nftables > 0) srcCounts.push(`${data.sources.nftables} NFTables`);
                }
                const srcLabel = srcCounts.length > 0 ? ` (${srcCounts.join(" + ")})` : "";
                bannerText.innerText = `Discovered ${data.count} existing forwarding port(s) on this server (${portsStr})${srcLabel}. Import them to manage failover in the dashboard.`;
            }
            banner.style.display = "flex";
        } else {
            banner.style.display = "none";
        }
    } catch (_) {}
}

export async function handleExportConfig() {
    try {
        const res = await fetch(`${API_BASE}/config/export`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.error || "Failed to export configuration", "error");
            return;
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        const disposition = res.headers.get("content-disposition");
        let filename = `xforwarder-backup-${new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14)}.json`;
        if (disposition && disposition.includes("filename=")) {
            const match = disposition.match(/filename=["']?([^"';]+)["']?/);
            if (match && match[1]) filename = match[1];
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast(`Configuration backup downloaded: ${filename}`, "success");
    } catch (_) {
        showToast("Error downloading configuration backup", "error");
    }
}

export function openImportModal() {
    const importConfigModal = document.getElementById("importConfigModal");
    const importConfigForm = document.getElementById("importConfigForm");
    const importFileInput = document.getElementById("importFileInput");
    const importJsonTextarea = document.getElementById("importJsonTextarea");
    const pasteJsonContainer = document.getElementById("pasteJsonContainer");
    const importPreviewBox = document.getElementById("importPreviewBox");
    const importError = document.getElementById("importError");
    const btnConfirmImport = document.getElementById("btnConfirmImport");

    if (!importConfigModal) return;
    currentImportConfig = null;
    if (importConfigForm) importConfigForm.reset();
    if (importFileInput) importFileInput.value = "";
    if (importJsonTextarea) importJsonTextarea.value = "";
    if (pasteJsonContainer) pasteJsonContainer.style.display = "none";
    if (importPreviewBox) importPreviewBox.style.display = "none";
    if (importError) {
        importError.innerText = "";
        importError.style.display = "none";
    }
    if (btnConfirmImport) btnConfirmImport.disabled = true;
    importConfigModal.classList.add("show");
}

export function closeImportModal() {
    const importConfigModal = document.getElementById("importConfigModal");
    if (importConfigModal) importConfigModal.classList.remove("show");
}

export function parseAndValidateImportJson(rawText, sourceName) {
    const importPreviewBox = document.getElementById("importPreviewBox");
    const importPreviewBadge = document.getElementById("importPreviewBadge");
    const importPreviewFilename = document.getElementById("importPreviewFilename");
    const importPreviewDetails = document.getElementById("importPreviewDetails");
    const importError = document.getElementById("importError");
    const btnConfirmImport = document.getElementById("btnConfirmImport");

    if (!rawText || !rawText.trim()) {
        if (importPreviewBox) importPreviewBox.style.display = "none";
        if (btnConfirmImport) btnConfirmImport.disabled = true;
        return;
    }
    try {
        let parsed = JSON.parse(rawText);
        if (Array.isArray(parsed)) {
            parsed = { rules: parsed };
        } else if (parsed && typeof parsed === "object" && !parsed.rules && parsed.port) {
            parsed = { rules: [parsed] };
        } else if (!parsed || typeof parsed !== "object") {
            throw new Error("Configuration must be a valid JSON object or rules array");
        }

        const rules = Array.isArray(parsed.rules) ? parsed.rules : [];
        if (rules.length === 0) {
            throw new Error("No forwarding rules found in configuration payload");
        }

        const ports = [];
        for (const r of rules) {
            if (r && r.port) {
                const p = parseInt(r.port, 10);
                if (p > 0 && p <= 65535) ports.push(p);
            }
        }

        currentImportConfig = parsed;
        if (importError) {
            importError.innerText = "";
            importError.style.display = "none";
        }

        if (importPreviewBox) {
            importPreviewBox.style.display = "block";
            if (importPreviewBadge) {
                importPreviewBadge.className = "preview-badge";
                importPreviewBadge.innerText = `${rules.length} Rule(s) Ready`;
            }
            if (importPreviewFilename) importPreviewFilename.innerText = sourceName || "config.json";
            if (importPreviewDetails) {
                const portsDisplay = ports.length > 0
                    ? `<code>:${ports.slice(0, 12).join("</code>, <code>:")}${ports.length > 12 ? '... (+' + (ports.length - 12) + ' more)' : ''}</code>`
                    : "No ports";
                importPreviewDetails.innerHTML = `
                    <div><strong>Detected Rules:</strong> ${rules.length} port mapping(s)</div>
                    <div style="margin-top: 4px;"><strong>Target Ports:</strong> ${portsDisplay}</div>
                    ${parsed.wan_interface ? `<div style="margin-top: 4px;"><strong>WAN Interface:</strong> <code>${escapeHtml(parsed.wan_interface)}</code></div>` : ""}
                `;
            }
        }
        if (btnConfirmImport) btnConfirmImport.disabled = false;

    } catch (e) {
        currentImportConfig = null;
        if (importPreviewBox) importPreviewBox.style.display = "none";
        if (importError) {
            importError.innerText = `Invalid JSON: ${e.message}`;
            importError.style.display = "block";
        }
        if (btnConfirmImport) btnConfirmImport.disabled = true;
    }
}

export function initImportExport(fetchStatusCallback) {
    const btnExportConfig = document.getElementById("btnExportConfig");
    if (btnExportConfig) btnExportConfig.addEventListener("click", handleExportConfig);

    const btnExportConfigSec = document.getElementById("btnExportConfigSec");
    if (btnExportConfigSec) btnExportConfigSec.addEventListener("click", handleExportConfig);

    const btnOpenImportModal = document.getElementById("btnOpenImportModal");
    const btnOpenImportModalSec = document.getElementById("btnOpenImportModalSec");
    const btnCloseImportModal = document.getElementById("btnCloseImportModal");
    const btnCancelImportModal = document.getElementById("btnCancelImportModal");

    if (btnOpenImportModal) btnOpenImportModal.addEventListener("click", openImportModal);
    if (btnOpenImportModalSec) btnOpenImportModalSec.addEventListener("click", openImportModal);
    if (btnCloseImportModal) btnCloseImportModal.addEventListener("click", closeImportModal);
    if (btnCancelImportModal) btnCancelImportModal.addEventListener("click", closeImportModal);

    const btnTogglePasteJson = document.getElementById("btnTogglePasteJson");
    const pasteJsonContainer = document.getElementById("pasteJsonContainer");
    const importJsonTextarea = document.getElementById("importJsonTextarea");
    const btnPasteFromClipboard = document.getElementById("btnPasteFromClipboard");
    const btnFormatJson = document.getElementById("btnFormatJson");
    const btnClearJsonText = document.getElementById("btnClearJsonText");

    if (btnTogglePasteJson) {
        btnTogglePasteJson.addEventListener("click", () => {
            if (!pasteJsonContainer) return;
            const isHidden = pasteJsonContainer.style.display === "none";
            pasteJsonContainer.style.display = isHidden ? "block" : "none";
            if (isHidden && importJsonTextarea) {
                setTimeout(() => importJsonTextarea.focus(), 50);
            }
        });
    }

    if (btnPasteFromClipboard && importJsonTextarea) {
        btnPasteFromClipboard.addEventListener("click", async () => {
            try {
                if (navigator.clipboard && navigator.clipboard.readText) {
                    const text = await navigator.clipboard.readText();
                    if (text && text.trim()) {
                        importJsonTextarea.value = text;
                        parseAndValidateImportJson(text, "Clipboard Content");
                        showToast("JSON pasted from clipboard!", "success");
                    } else {
                        showToast("Clipboard is empty", "warning");
                    }
                } else {
                    showToast("Press Ctrl+V to paste into the box", "info");
                    importJsonTextarea.focus();
                }
            } catch (_) {
                showToast("Press Ctrl+V to paste into the box", "info");
                importJsonTextarea.focus();
            }
        });
    }

    if (btnFormatJson && importJsonTextarea) {
        btnFormatJson.addEventListener("click", () => {
            const val = (importJsonTextarea.value || "").trim();
            if (!val) return;
            try {
                const obj = JSON.parse(val);
                importJsonTextarea.value = JSON.stringify(obj, null, 2);
                showToast("JSON formatted!", "success");
            } catch (e) {
                showToast("Cannot format invalid JSON: " + e.message, "error");
            }
        });
    }

    if (btnClearJsonText && importJsonTextarea) {
        btnClearJsonText.addEventListener("click", () => {
            importJsonTextarea.value = "";
            parseAndValidateImportJson("", "");
        });
    }

    const importDropzone = document.getElementById("importDropzone");
    const importFileInput = document.getElementById("importFileInput");

    if (importDropzone && importFileInput) {
        importDropzone.addEventListener("click", () => importFileInput.click());

        importDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            importDropzone.classList.add("dragover");
        });

        ["dragleave", "dragend"].forEach(type => {
            importDropzone.addEventListener(type, () => importDropzone.classList.remove("dragover"));
        });

        importDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            importDropzone.classList.remove("dragover");
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                const reader = new FileReader();
                reader.onload = (event) => parseAndValidateImportJson(event.target.result, file.name);
                reader.readAsText(file);
            }
        });

        importFileInput.addEventListener("change", function() {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                const reader = new FileReader();
                reader.onload = (event) => parseAndValidateImportJson(event.target.result, file.name);
                reader.readAsText(file);
            }
        });
    }

    if (importJsonTextarea) {
        importJsonTextarea.addEventListener("input", function() {
            parseAndValidateImportJson(this.value, "Pasted JSON Content");
        });
    }

    const importConfigForm = document.getElementById("importConfigForm");
    const importError = document.getElementById("importError");
    const btnConfirmImport = document.getElementById("btnConfirmImport");

    if (importConfigForm) {
        importConfigForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!currentImportConfig) {
                if (importError) {
                    importError.innerText = "Please select or paste a valid configuration file";
                    importError.style.display = "block";
                }
                return;
            }

            const modeRadio = document.querySelector('input[name="importMode"]:checked');
            const mode = modeRadio ? modeRadio.value : "merge";

            if (btnConfirmImport) {
                btnConfirmImport.disabled = true;
                btnConfirmImport.innerHTML = '<span class="btn-spinner"></span> <span>Applying...</span>';
            }
            if (importError) importError.style.display = "none";

            try {
                const res = await fetch(`${API_BASE}/config/import`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        mode: mode,
                        config: currentImportConfig
                    })
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data.ok) {
                    showToast(`Successfully imported ${data.imported_count} rule(s) (${data.mode} mode)! Pre-restore backup saved.`);
                    closeImportModal();
                    if (typeof fetchStatusCallback === "function") fetchStatusCallback();
                } else {
                    if (importError) {
                        importError.innerText = data.error || "Failed to import configuration";
                        importError.style.display = "block";
                    }
                }
            } catch (_) {
                if (importError) {
                    importError.innerText = "Network error communicating with server";
                    importError.style.display = "block";
                }
            } finally {
                if (btnConfirmImport) {
                    btnConfirmImport.disabled = false;
                    btnConfirmImport.innerHTML = `
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                        <span>Import & Apply</span>
                    `;
                }
            }
        });
    }

    const btnImportHaproxy = document.getElementById("btnImportHaproxy");
    if (btnImportHaproxy) {
        btnImportHaproxy.addEventListener("click", async () => {
            btnImportHaproxy.disabled = true;
            btnImportHaproxy.innerHTML = '<span class="btn-spinner"></span> <span>Importing...</span>';
            try {
                const res = await fetch(`${API_BASE}/import/all`, { method: "POST" });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data.ok) {
                    showToast(`Successfully imported ${data.imported_count} relay port rules!`);
                    const banner = document.getElementById("importBanner");
                    if (banner) banner.style.display = "none";
                    if (typeof fetchStatusCallback === "function") fetchStatusCallback();
                } else {
                    showToast(data.error || "Failed to import rules", "error");
                }
            } catch (_) {
                showToast("Error communicating with server", "error");
            } finally {
                btnImportHaproxy.disabled = false;
                btnImportHaproxy.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                    <span>Import All Rules</span>
                `;
            }
        });
    }
}
