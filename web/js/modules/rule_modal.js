// ============================================================================
// XForwarder Web UI - Rule Modal & Destination Editor Subsystem (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { escapeHtml, showToast } from "./utils.js";
import { currentRules } from "./state.js";

let currentModalDestinations = [];
let draggedModalPrioIndex = null;
let currentEditingRuleId = null;

function getPrioTagClass(prio) {
    if (prio === 1) return "prio-tag-1";
    if (prio === 2) return "prio-tag-2";
    if (prio === 3) return "prio-tag-3";
    return "prio-tag-other";
}

export function openAddRuleModal() {
    currentEditingRuleId = null;
    const modal = document.getElementById("ruleModal");
    const title = document.getElementById("modalTitle");
    const form = document.getElementById("ruleForm");
    if (!modal) return;

    if (form) form.reset();
    if (title) title.innerText = "Add Forwarding Port";

    const ruleIdInput = document.getElementById("editRuleId") || document.getElementById("ruleId");
    if (ruleIdInput) ruleIdInput.value = "";

    const activePriorityInput = document.getElementById("activePriority");
    if (activePriorityInput) activePriorityInput.value = "1";

    const forceOverrideInput = document.getElementById("forceOverride");
    if (forceOverrideInput) forceOverrideInput.value = "0";

    const ruleCreatedAtInput = document.getElementById("ruleCreatedAt");
    if (ruleCreatedAtInput) ruleCreatedAtInput.value = "";

    currentModalDestinations = [
        { priority: 1, type: "haproxy", target: "", port: "", comment: "", proxy_protocol: false, is_relay: false, enabled: true },
        { priority: 2, type: "nftables", target: "", port: "", comment: "", proxy_protocol: false, is_relay: true, enabled: true }
    ];

    renderDestinationsList();
    modal.classList.add("show");
    setTimeout(() => {
        const portInput = document.getElementById("formPort");
        if (portInput) portInput.focus();
    }, 50);
}

export function openEditRuleModal(ruleId) {
    currentEditingRuleId = String(ruleId);
    const rule = (currentRules || []).find(r => String(r.id || `rule-${r.port}`) === currentEditingRuleId);
    if (!rule) {
        showToast("Rule not found", "error");
        return;
    }

    const modal = document.getElementById("ruleModal");
    const title = document.getElementById("modalTitle");
    const form = document.getElementById("ruleForm");
    if (!modal) return;

    if (form) form.reset();
    if (title) title.innerText = `Edit Port :${rule.port}`;

    const ruleIdInput = document.getElementById("editRuleId") || document.getElementById("ruleId");
    if (ruleIdInput) ruleIdInput.value = rule.id || `rule-${rule.port}`;

    const portInput = document.getElementById("formPort");
    if (portInput) portInput.value = rule.port;

    const nameInput = document.getElementById("formName");
    if (nameInput) nameInput.value = rule.name || "";

    const protoInput = document.getElementById("formProto");
    if (protoInput) protoInput.value = rule.protocol || "both";

    const catInput = document.getElementById("formCategory");
    if (catInput) catInput.value = rule.category || "";

    const activePriorityInput = document.getElementById("activePriority");
    if (activePriorityInput) activePriorityInput.value = rule.active_priority || 1;

    const forceOverrideInput = document.getElementById("forceOverride");
    if (forceOverrideInput) forceOverrideInput.value = rule.force_override !== undefined ? rule.force_override : 0;

    const ruleCreatedAtInput = document.getElementById("ruleCreatedAt");
    if (ruleCreatedAtInput) ruleCreatedAtInput.value = rule.created_at !== undefined ? String(rule.created_at) : "";

    currentModalDestinations = (rule.destinations || []).map(d => ({
        priority: d.priority || 1,
        type: d.type || "haproxy",
        target: d.target || "",
        port: d.port !== undefined && d.port !== null ? d.port : "",
        comment: d.comment || "",
        proxy_protocol: Boolean(d.proxy_protocol),
        is_relay: Boolean(d.is_relay),
        enabled: d.enabled !== undefined ? Boolean(d.enabled) : true
    }));

    if (currentModalDestinations.length === 0) {
        currentModalDestinations.push({
            priority: 1,
            type: "haproxy",
            target: "",
            port: "",
            comment: "",
            proxy_protocol: false,
            is_relay: false,
            enabled: true
        });
    }

    renderDestinationsList();
    modal.classList.add("show");
}

export function closeRuleModal() {
    const modal = document.getElementById("ruleModal");
    if (modal) modal.classList.remove("show");
    currentEditingRuleId = null;
}

export function renderDestinationsList() {
    const container = document.getElementById("destinationsContainer");
    if (!container) return;
    container.innerHTML = "";
    currentModalDestinations.forEach((dest, idx) => {
        const row = renderDestinationRow(dest, idx, currentModalDestinations.length);
        container.appendChild(row);
    });
}

export function renderDestinationRow(dest, index, totalCount) {
    const prio = index + 1;
    const isPrimary = prio === 1;
    const type = dest.type || (isPrimary ? "haproxy" : "nftables");
    const target = dest.target || "";
    const port = dest.port !== undefined && dest.port !== null ? dest.port : "";
    const comment = dest.comment || "";
    const canRemove = totalCount > 1;

    const div = document.createElement("div");
    div.className = `priority-box priority-${prio}`;
    div.dataset.index = index;
    div.draggable = true;
    div.ondragstart = (e) => handleModalPrioDragStart(e, index);
    div.ondragover = (e) => handleModalPrioDragOver(e, index);
    div.ondragleave = (e) => handleModalPrioDragLeave(e);
    div.ondrop = (e) => handleModalPrioDrop(e, index);
    div.ondragend = (e) => handleModalPrioDragEnd(e);

    const targetPlaceholder = type === "haproxy"
        ? "2001:4ba0:cafe:84e::1 (IPv6 only)"
        : (type === "nftables" ? "10.88.1.2 (IPv4) or 2001:db8::2 (IPv6)" : "1.2.3.4 or 2001:db8::1");

    div.innerHTML = `
        <div class="priority-header">
            <div class="prio-title-group">
                <span class="drag-handle" title="Drag to reorder priority">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/></svg>
                </span>
                <span class="prio-tag ${getPrioTagClass(prio)}">#${prio}</span>
                <span class="prio-sub">${isPrimary ? "Primary Path" : "Backup Path"}</span>
            </div>
            <div class="prio-header-actions">
                <label class="dest-switch-control" title="Enable or disable this priority path">
                    <input type="checkbox" class="dest-enabled-check" ${dest.enabled !== false ? "checked" : ""}>
                    <span class="dest-switch-slider"></span>
                </label>
                <button type="button" class="btn-prio-move" title="Move Priority Up" ${index === 0 ? "disabled" : ""} onclick="moveDestinationRow(${index}, -1)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>
                </button>
                <button type="button" class="btn-prio-move" title="Move Priority Down" ${index === totalCount - 1 ? "disabled" : ""} onclick="moveDestinationRow(${index}, 1)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                ${canRemove ? `
                <button type="button" class="btn-remove-prio" title="Remove this priority path" onclick="removeDestinationRow(${index})">
                    &times;
                </button>` : ""}
            </div>
        </div>
        <div class="dest-form-row">
            <div class="form-group dest-col-type">
                <label>Engine Type</label>
                <select class="form-control dest-type" onchange="handleDestTypeChange(this)">
                    <option value="haproxy" ${type === "haproxy" ? "selected" : ""}>HAProxy (IPv6)</option>
                    <option value="nginx" ${type === "nginx" ? "selected" : ""}>Nginx (Stream)</option>
                    <option value="nftables" ${type === "nftables" ? "selected" : ""}>NFTables (Kernel)</option>
                </select>
            </div>
            <div class="form-group dest-col-target">
                <label>Destination Target IP / Host</label>
                <input type="text" class="form-control dest-target" placeholder="${targetPlaceholder}" value="${escapeHtml(target)}" required>
            </div>
            <div class="form-group dest-col-port">
                <label>Target Port</label>
                <input type="number" class="form-control dest-port" placeholder="Default" min="1" max="65535" value="${escapeHtml(port)}">
            </div>
        </div>
        <div class="form-group" style="margin-bottom:10px;">
            <label>Comment / Label</label>
            <input type="text" class="form-control dest-comment" placeholder="e.g. ${isPrimary ? 'Foreign Server 1 - Primary IPv6' : 'Backup Tunnel Node ' + prio}" value="${escapeHtml(comment)}">
        </div>
        <div class="dest-extra-row" style="flex-wrap: wrap; gap: 10px;">
            <label class="dest-toggle-label" title="Enable only if remote destination (e.g. Xray/V2Ray with acceptProxyProtocol) is configured to receive PROXY Protocol headers.">
                <input type="checkbox" class="dest-proxy-proto" ${dest.proxy_protocol ? "checked" : ""}>
                <span>Send PROXY Protocol v2 (Advanced)</span>
            </label>
            <label class="dest-toggle-label" title="Mid Server: Ping to this node is a partial hop. The engine strictly anchors on Priority 1 unless Priority 1 fails, has packet loss, or exceeds 150ms.">
                <input type="checkbox" class="dest-is-relay" ${dest.is_relay ? "checked" : ""}>
                <span>Mid Server</span>
            </label>
            <div class="dest-test-group">
                <button type="button" class="btn btn-secondary btn-xs btn-test-dest" onclick="testModalDestination(${index})">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    <span>Test Target</span>
                </button>
                <span class="test-dest-result" id="testDestResult_${index}"></span>
            </div>
        </div>
    `;

    const targetInput = div.querySelector(".dest-target");
    if (targetInput && prio > 1) {
        targetInput.addEventListener("input", () => {
            const val = targetInput.value.trim().toLowerCase();
            const relayCheck = div.querySelector(".dest-is-relay");
            if (relayCheck && (val.startsWith("10.") || val.startsWith("172.") || val.startsWith("192.168.") || val.startsWith("fc") || val.startsWith("fd"))) {
                relayCheck.checked = true;
            }
        });
    }

    return div;
}

export function handleDestTypeChange(selectEl) {
    const row = selectEl.closest(".priority-box");
    if (!row) return;
    const targetInput = row.querySelector(".dest-target");
    if (!targetInput) return;
    const val = selectEl.value;
    if (val === "haproxy") {
        targetInput.placeholder = "2001:4ba0:cafe:84e::1 (IPv6 only)";
    } else if (val === "nftables") {
        targetInput.placeholder = "10.88.1.2 (IPv4) or 2001:db8::2 (IPv6)";
    } else {
        targetInput.placeholder = "1.2.3.4 or 2001:db8::1";
    }
}

export function syncDestinationsFromDom() {
    const container = document.getElementById("destinationsContainer");
    if (!container) return;
    const boxes = container.querySelectorAll(".priority-box");
    const updated = [];
    boxes.forEach((box, i) => {
        const typeEl = box.querySelector(".dest-type");
        const targetEl = box.querySelector(".dest-target");
        const portEl = box.querySelector(".dest-port");
        const commentEl = box.querySelector(".dest-comment");
        const proxyProtoEl = box.querySelector(".dest-proxy-proto");
        const relayEl = box.querySelector(".dest-is-relay");
        const enabledEl = box.querySelector(".dest-enabled-check");

        updated.push({
            priority: i + 1,
            type: typeEl ? typeEl.value : "haproxy",
            target: targetEl ? targetEl.value.trim() : "",
            port: (portEl && portEl.value.trim()) ? parseInt(portEl.value.trim()) : null,
            comment: commentEl ? commentEl.value.trim() : "",
            proxy_protocol: proxyProtoEl ? proxyProtoEl.checked : false,
            is_relay: relayEl ? relayEl.checked : false,
            enabled: enabledEl ? enabledEl.checked : true
        });
    });
    currentModalDestinations = updated;
}

export function moveDestinationRow(index, delta) {
    syncDestinationsFromDom();
    const newIndex = index + delta;
    if (newIndex < 0 || newIndex >= currentModalDestinations.length) return;
    const moved = currentModalDestinations.splice(index, 1)[0];
    currentModalDestinations.splice(newIndex, 0, moved);
    currentModalDestinations.forEach((d, i) => d.priority = i + 1);
    renderDestinationsList();
}

export function removeDestinationRow(index) {
    syncDestinationsFromDom();
    if (currentModalDestinations.length <= 1) return;
    currentModalDestinations.splice(index, 1);
    currentModalDestinations.forEach((d, i) => d.priority = i + 1);
    renderDestinationsList();
}

export function handleModalPrioDragStart(e, index) {
    if (e.target.closest("input, select, textarea, button, .btn-prio-move, .btn-remove-prio")) {
        e.preventDefault();
        return;
    }
    syncDestinationsFromDom();
    draggedModalPrioIndex = index;
    e.dataTransfer.effectAllowed = "move";
    try {
        e.dataTransfer.setData("text/plain", String(index));
    } catch (_) {}
    const box = e.currentTarget;
    setTimeout(() => {
        if (box) box.classList.add("is-dragging");
    }, 0);
}

export function handleModalPrioDragOver(e, index) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (draggedModalPrioIndex === null || draggedModalPrioIndex === index) return;
    const box = e.currentTarget;
    if (box && !box.classList.contains("drag-over")) {
        box.classList.add("drag-over");
    }
}

export function handleModalPrioDragLeave(e) {
    const box = e.currentTarget;
    if (box && !box.contains(e.relatedTarget)) {
        box.classList.remove("drag-over");
    }
}

export function handleModalPrioDragEnd(e) {
    document.querySelectorAll(".priority-box").forEach(el => {
        el.classList.remove("is-dragging");
        el.classList.remove("drag-over");
    });
    draggedModalPrioIndex = null;
}

export function handleModalPrioDrop(e, toIndex) {
    e.preventDefault();
    e.stopPropagation();
    document.querySelectorAll(".priority-box").forEach(el => {
        el.classList.remove("is-dragging");
        el.classList.remove("drag-over");
    });
    if (draggedModalPrioIndex === null || draggedModalPrioIndex === toIndex) return;
    syncDestinationsFromDom();
    const fromIndex = draggedModalPrioIndex;
    draggedModalPrioIndex = null;
    if (fromIndex < 0 || fromIndex >= currentModalDestinations.length || toIndex < 0 || toIndex >= currentModalDestinations.length) return;
    const moved = currentModalDestinations.splice(fromIndex, 1)[0];
    currentModalDestinations.splice(toIndex, 0, moved);
    currentModalDestinations.forEach((d, i) => d.priority = i + 1);
    renderDestinationsList();
}

export async function testModalDestination(index) {
    syncDestinationsFromDom();
    const dest = currentModalDestinations[index];
    if (!dest) return;
    const target = (dest.target || "").trim().replace(/^\[|\]$/g, '');
    const listenPort = document.getElementById("formPort") ? document.getElementById("formPort").value.trim() : "";
    const port = dest.port || listenPort;
    const resEl = document.getElementById(`testDestResult_${index}`);

    if (!target) {
        showToast("Please enter a destination target IP or host", "warn");
        if (resEl) { resEl.innerHTML = '<span class="text-amber">Enter target IP</span>'; }
        return;
    }
    if ((dest.type || "haproxy") === "haproxy" && !target.includes(':')) {
        showToast("HAProxy destination target must be a valid IPv6 address", "warn");
        if (resEl) { resEl.innerHTML = '<span class="text-amber">IPv6 required for HAProxy</span>'; }
        return;
    }
    if (!port) {
        showToast("Please specify a port to test", "warn");
        if (resEl) { resEl.innerHTML = '<span class="text-amber">Enter port</span>'; }
        return;
    }

    if (resEl) {
        resEl.innerHTML = '<span class="btn-spinner" style="width:11px;height:11px;display:inline-block;vertical-align:middle;"></span> <span class="text-muted" style="font-size:0.75rem;">Probing...</span>';
    }

    try {
        const res = await fetch(`${API_BASE}/test-target`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                target: target,
                port: parseInt(port),
                type: dest.type || "haproxy",
                protocol: document.getElementById("formProto") ? document.getElementById("formProto").value : "both",
                packets: 10
            })
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
            const loss = data.packet_loss !== undefined ? data.packet_loss : (data.healthy ? 0 : 100);
            if (data.healthy) {
                const latStr = (data.latency_ms !== null && data.latency_ms !== undefined && data.latency_ms > 0) ? ` (${data.latency_ms}ms · ${loss}% loss)` : ` (${loss}% loss)`;
                if (resEl) resEl.innerHTML = `<span class="badge-probe text-emerald" style="display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;">Reachable${latStr}</span>`;
                showToast(`Destination [${target}]:${port} reachable${latStr}`);
            } else {
                const reason = data.reason ? `: ${data.reason}` : "";
                if (resEl) resEl.innerHTML = `<span class="badge-fail text-rose" style="display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;" title="${escapeHtml(data.reason || '')}">Unreachable (100% loss${escapeHtml(reason)})</span>`;
                showToast(`Destination [${target}]:${port} failed health probe${reason}`, "error");
            }
        } else {
            const errMsg = data.error || "Connection test failed";
            if (resEl) resEl.innerHTML = `<span class="badge-fail text-rose" style="font-size:0.75rem;">${escapeHtml(errMsg)}</span>`;
            showToast(`Target test error: ${errMsg}`, "error");
        }
    } catch (err) {
        if (resEl) resEl.innerHTML = `<span class="badge-fail text-rose" style="font-size:0.75rem;">Network Error</span>`;
        showToast("Error executing target probe: " + err.message, "error");
    }
}

export function initRuleModal(fetchStatusCallback) {
    const btnOpenAddModal = document.getElementById("btnOpenAddModal") || document.getElementById("btnOpenAddRuleModal");
    const btnCloseModal = document.getElementById("btnCloseModal") || document.getElementById("btnCloseRuleModal");
    const btnCancelModal = document.getElementById("btnCancelModal") || document.getElementById("btnCancelRuleModal");
    const btnAddDestination = document.getElementById("btnAddDestination");
    const ruleForm = document.getElementById("ruleForm");

    if (btnOpenAddModal) btnOpenAddModal.addEventListener("click", openAddRuleModal);
    if (btnCloseModal) btnCloseModal.addEventListener("click", closeRuleModal);
    if (btnCancelModal) btnCancelModal.addEventListener("click", closeRuleModal);

    if (btnAddDestination) {
        btnAddDestination.addEventListener("click", () => {
            syncDestinationsFromDom();
            const nextPrio = currentModalDestinations.length + 1;
            const nextType = nextPrio === 1 ? "haproxy" : "nftables";
            currentModalDestinations.push({
                priority: nextPrio,
                type: nextType,
                target: "",
                port: "",
                comment: "",
                proxy_protocol: false,
                is_relay: nextPrio > 1,
                enabled: true
            });
            renderDestinationsList();
        });
    }

    if (ruleForm) {
        ruleForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            syncDestinationsFromDom();

            const portVal = parseInt(document.getElementById("formPort").value, 10);
            if (isNaN(portVal) || portVal < 1 || portVal > 65535) {
                showToast("Please enter a valid port (1 - 65535)", "error");
                return;
            }

            if (currentModalDestinations.length === 0) {
                showToast("At least one forwarding destination path is required", "error");
                return;
            }

            for (let i = 0; i < currentModalDestinations.length; i++) {
                const d = currentModalDestinations[i];
                if (!d.target || !d.target.trim()) {
                    showToast(`Please enter target IP for Priority #${i + 1}`, "error");
                    return;
                }
            }

            const ruleIdInput = document.getElementById("editRuleId") || document.getElementById("ruleId");
            const nameInput = document.getElementById("formName");
            const protoInput = document.getElementById("formProto");
            const catInput = document.getElementById("formCategory");
            const activePriorityInput = document.getElementById("activePriority");
            const forceOverrideInput = document.getElementById("forceOverride");
            const ruleCreatedAtInput = document.getElementById("ruleCreatedAt");

            const rulePayload = {
                id: (ruleIdInput && ruleIdInput.value) ? ruleIdInput.value : `rule-${portVal}`,
                name: (nameInput && nameInput.value ? nameInput.value.trim() : "") || `Port ${portVal}`,
                port: portVal,
                protocol: (protoInput && protoInput.value) ? protoInput.value : "both",
                category: (catInput && catInput.value ? catInput.value.trim() : ""),
                active_priority: parseInt((activePriorityInput && activePriorityInput.value) || "1", 10),
                force_override: parseInt((forceOverrideInput && forceOverrideInput.value) || "0", 10),
                destinations: currentModalDestinations
            };

            const createdAtStr = ruleCreatedAtInput ? ruleCreatedAtInput.value : "";
            if (createdAtStr && !isNaN(parseFloat(createdAtStr))) {
                rulePayload.created_at = parseFloat(createdAtStr);
            }

            const btnSave = document.getElementById("btnSaveRule");
            if (btnSave) {
                btnSave.disabled = true;
                btnSave.innerHTML = '<span class="btn-spinner"></span> <span>Saving...</span>';
            }

            try {
                const res = await fetch(`${API_BASE}/rule`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(rulePayload)
                });
                const data = await res.json().catch(() => ({}));

                if (res.ok && data.ok) {
                    showToast(`Port :${portVal} rule saved successfully!`, "success");
                    closeRuleModal();
                    if (typeof fetchStatusCallback === "function") fetchStatusCallback();
                } else {
                    showToast(data.error || "Failed to save rule", "error");
                }
            } catch (err) {
                showToast("Network error saving rule: " + err.message, "error");
            } finally {
                if (btnSave) {
                    btnSave.disabled = false;
                    btnSave.innerHTML = '<span>Save Port Rule</span>';
                }
            }
        });
    }
}
