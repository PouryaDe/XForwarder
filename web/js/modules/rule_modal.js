// ============================================================================
// XForwarder Web UI - Rule Modal & Destination Editor Subsystem (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { escapeHtml, showToast } from "./utils.js";
import { currentRules, lastNetwork, setLastNetwork } from "./state.js";
import { updateCategoryDatalist } from "./rules.js";
import { t } from "./i18n.js";

let currentModalDestinations = [];
let draggedModalPrioIndex = null;
let currentEditingRuleId = null;

/**
 * Parses comma/space separated excluded ports or small sub-ranges (e.g. "22, 443, 1001").
 * Returns sorted array of unique ints, [] if empty, or null if invalid.
 */
function parseExcludedPortsInput(rawVal) {
    if (rawVal === null || rawVal === undefined) return [];
    let s = String(rawVal).trim();
    if (!s) return [];
    if (s.startsWith("!=")) s = s.slice(2).trim();
    s = s.replace(/^\{|\}$/g, "").trim();
    if (!s) return [];

    const set = new Set();
    for (const tok of s.split(/[\s,]+/)) {
        if (!tok) continue;
        const rm = /^(\d{1,5})-(\d{1,5})$/.exec(tok);
        if (rm) {
            const sp = parseInt(rm[1], 10);
            const ep = parseInt(rm[2], 10);
            if (isNaN(sp) || isNaN(ep) || sp < 1 || ep > 65535 || sp > ep || (ep - sp) > 1000) return null;
            for (let p = sp; p <= ep; p++) set.add(p);
        } else if (/^\d{1,5}$/.test(tok)) {
            const p = parseInt(tok, 10);
            if (isNaN(p) || p < 1 || p > 65535) return null;
            set.add(p);
        } else {
            return null;
        }
    }
    return Array.from(set).sort((a, b) => a - b);
}

/**
 * Parses a single port ("443"), range ("10000-20000"), or wildcard exclusion ("!= 22, 443, 1001").
 * Returns { start, end, rangeStr, excludedPorts? }.
 */
function parsePortSpec(rawVal) {
    if (rawVal === null || rawVal === undefined) return null;
    const s = String(rawVal).trim();
    if (!s) return null;
    if (s.startsWith("!=")) {
        const excl = parseExcludedPortsInput(s);
        if (!excl || excl.length === 0) return null;
        return { start: 1, end: 65535, rangeStr: "1-65535", excludedPorts: excl };
    }
    const rangeMatch = /^(\d{1,5})\s*-\s*(\d{1,5})$/.exec(s);
    if (rangeMatch) {
        const sp = parseInt(rangeMatch[1], 10);
        const ep = parseInt(rangeMatch[2], 10);
        if (isNaN(sp) || isNaN(ep) || sp < 1 || ep > 65535 || sp > ep) return null;
        if (sp === ep) return { start: sp, end: sp, rangeStr: null };
        return { start: sp, end: ep, rangeStr: `${sp}-${ep}` };
    }
    if (!/^\d{1,5}$/.test(s)) return null;
    const p = parseInt(s, 10);
    if (isNaN(p) || p < 1 || p > 65535) return null;
    return { start: p, end: p, rangeStr: null };
}

function getCurrentInboundSpec() {
    const portInput = document.getElementById("formPort");
    const exclInput = document.getElementById("formExcludedPorts");
    const parsedPort = portInput ? parsePortSpec(portInput.value) : null;
    const rawExcl = exclInput ? exclInput.value.trim() : "";
    if (parsedPort && parsedPort.excludedPorts) return parsedPort;
    if (rawExcl) {
        const excl = parseExcludedPortsInput(rawExcl);
        if (parsedPort && parsedPort.rangeStr) {
            return { ...parsedPort, excludedPorts: excl || [] };
        }
        return { start: 1, end: 65535, rangeStr: "1-65535", excludedPorts: excl || [] };
    }
    return parsedPort;
}

function refreshRangeConstraintUI() {
    const inbound = getCurrentInboundSpec();
    const isRange = Boolean(inbound && inbound.rangeStr);
    const hintEl = document.getElementById("portRangeHint");
    if (hintEl) {
        hintEl.style.display = isRange ? "inline-flex" : "none";
    }

    const boxes = document.querySelectorAll("#destinationsContainer .priority-box");
    boxes.forEach((box) => {
        const selectEl = box.querySelector(".dest-type");
        const portEl = box.querySelector(".dest-port");
        if (selectEl) {
            const prev = selectEl.value || "nftables";
            const optionsHtml = isRange
                ? `<option value="nftables" selected>NFTables (Kernel)</option>`
                : `
                    <option value="haproxy" ${prev === "haproxy" ? "selected" : ""}>HAProxy (IPv6)</option>
                    <option value="nginx" ${prev === "nginx" ? "selected" : ""}>Nginx (Stream)</option>
                    <option value="nftables" ${prev === "nftables" ? "selected" : ""}>NFTables (Kernel)</option>
                `;
            selectEl.innerHTML = optionsHtml;
            if (isRange) selectEl.value = "nftables";
            handleDestTypeChange(selectEl);
        }
        if (portEl) {
            portEl.placeholder = isRange
                ? (t("modal.dest_port_range_placeholder", {}, "Same range or single port"))
                : "Default";
        }
    });
}

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
    if (title) title.innerText = t("modal.rule_title_add");
    updateCategoryDatalist(currentRules);

    const ruleIdInput = document.getElementById("editRuleId") || document.getElementById("ruleId");
    if (ruleIdInput) ruleIdInput.value = "";

    const activePriorityInput = document.getElementById("activePriority");
    if (activePriorityInput) activePriorityInput.value = "1";

    const forceOverrideInput = document.getElementById("forceOverride");
    if (forceOverrideInput) forceOverrideInput.value = "0";

    const ruleCreatedAtInput = document.getElementById("ruleCreatedAt");
    if (ruleCreatedAtInput) ruleCreatedAtInput.value = "";

    setExcludedTags([]);

    currentModalDestinations = [
        { priority: 1, type: "haproxy", target: "", port: "", comment: "", proxy_protocol: false, is_relay: false, enabled: true },
        { priority: 2, type: "nftables", target: "", port: "", comment: "", proxy_protocol: false, is_relay: true, enabled: true }
    ];

    renderDestinationsList();
    refreshRangeConstraintUI();
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

    const displayPort = (Array.isArray(rule.excluded_ports) && rule.excluded_ports.length > 0)
        ? `!= ${rule.excluded_ports.join(", ")}`
        : (rule.port_range || rule.port);
    if (form) form.reset();
    if (title) title.innerText = `${t("modal.rule_title_configure")} :${displayPort}`;
    updateCategoryDatalist(currentRules);

    const ruleIdInput = document.getElementById("editRuleId") || document.getElementById("ruleId");
    if (ruleIdInput) ruleIdInput.value = rule.id || `rule-${rule.port_range || rule.port}`;

    const portInput = document.getElementById("formPort");
    if (portInput) portInput.value = rule.port_range || rule.port || "1-65535";

    setExcludedTags(Array.isArray(rule.excluded_ports) ? rule.excluded_ports : []);

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
        type: rule.port_range ? "nftables" : (d.type || "haproxy"),
        target: d.target || "",
        port: d.port_range ? d.port_range : (d.port !== undefined && d.port !== null ? d.port : ""),
        port_range: d.port_range || null,
        tunnel_iface: d.tunnel_iface || "",
        comment: d.comment || "",
        proxy_protocol: Boolean(d.proxy_protocol),
        is_relay: Boolean(d.is_relay),
        enabled: d.enabled !== undefined ? Boolean(d.enabled) : true
    }));

    if (currentModalDestinations.length === 0) {
        currentModalDestinations.push({
            priority: 1,
            type: rule.port_range ? "nftables" : "haproxy",
            target: "",
            port: "",
            comment: "",
            proxy_protocol: false,
            is_relay: false,
            enabled: true
        });
    }

    renderDestinationsList();
    refreshRangeConstraintUI();
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
    if (!lastNetwork) {
        ensureNetworkInterfacesLoaded();
    }
}

let networkFetchPromise = null;
function ensureNetworkInterfacesLoaded() {
    if (networkFetchPromise) return;
    networkFetchPromise = fetch(`${API_BASE}/network`)
        .then(r => (r.ok ? r.json() : null))
        .then(net => {
            if (net && typeof net === "object") {
                setLastNetwork(net);
                document.querySelectorAll("#destinationsContainer .dest-iface-group").forEach(grp => {
                    const hidden = grp.querySelector(".dest-tunnel-iface");
                    const wrap = grp.querySelector(".iface-tags-wrap");
                    const prevVal = (hidden && hidden.value) || "";
                    if (wrap) wrap.innerHTML = buildTunnelIfaceTagsHtml(prevVal);
                });
            }
        })
        .catch(() => {})
        .finally(() => { networkFetchPromise = null; });
}

function getAvailableServerInterfaces() {
    const entries = [];
    const seen = new Set();
    const net = lastNetwork || {};

    (Array.isArray(net.tunnel_interfaces) ? net.tunnel_interfaces : []).forEach(tObj => {
        const name = String((tObj && tObj.name) || "").trim();
        if (!name || seen.has(name)) return;
        seen.add(name);
        const ipPart = tObj.ip && tObj.ip !== "No IP assigned" ? tObj.ip : "";
        const statePart = String(tObj.state || "UP").toUpperCase();
        entries.push({
            name,
            ip: ipPart,
            up: statePart === "UP",
            label: `${name} (${tObj.type || "Tunnel"}${ipPart ? ` · ${ipPart}` : ""} · ${statePart})`
        });
    });

    (Array.isArray(net.server_ips) ? net.server_ips : []).forEach(sObj => {
        const name = String((sObj && sObj.interface) || "").trim();
        if (!name || seen.has(name)) return;
        seen.add(name);
        const ipPart = sObj.ip || "";
        entries.push({
            name,
            ip: ipPart,
            up: true,
            label: `${name} (WAN${ipPart ? ` · ${ipPart}` : ""})`
        });
    });

    const primaryName = String(net.primary_interface || "").trim();
    if (primaryName && !seen.has(primaryName)) {
        seen.add(primaryName);
        entries.push({ name: primaryName, ip: "", up: true, label: `${primaryName} (Primary WAN)` });
    }
    return entries;
}

function buildTunnelIfaceTagsHtml(selectedVal = "") {
    const cur = String(selectedVal || "").trim();
    const autoLabel = escapeHtml(t("modal.tunnel_iface_auto_tag", {}, "Auto"));
    let html = `<button type="button" class="iface-tag-chip ${!cur ? "is-selected" : ""}" data-iface="">${autoLabel}</button>`;
    const list = getAvailableServerInterfaces();
    let foundSelected = !cur;
    list.forEach(item => {
        const isSel = Boolean(cur && cur === item.name);
        if (isSel) foundSelected = true;
        html += `<button type="button" class="iface-tag-chip ${isSel ? "is-selected" : ""}" data-iface="${escapeHtml(item.name)}" title="${escapeHtml(item.label)}"><span class="iface-dot ${item.up ? "is-up" : "is-down"}"></span><span>${escapeHtml(item.name)}</span>${item.ip ? `<small>${escapeHtml(item.ip)}</small>` : ""}</button>`;
    });
    if (cur && !foundSelected) {
        html += `<button type="button" class="iface-tag-chip is-selected" data-iface="${escapeHtml(cur)}" title="Saved interface"><span class="iface-dot is-up"></span><span>${escapeHtml(cur)}</span><small>saved</small></button>`;
    }
    return html;
}

let currentExcludedTags = [];

function renderExcludedTagChips() {
    const chipsEl = document.getElementById("exclTagChips");
    const hiddenEl = document.getElementById("formExcludedPorts");
    if (hiddenEl) {
        hiddenEl.value = currentExcludedTags.join(", ");
    }
    if (!chipsEl) return;
    chipsEl.innerHTML = currentExcludedTags.map(p => (
        `<span class="xfwd-tag-chip" data-port="${escapeHtml(p)}"><span>${escapeHtml(p)}</span><button type="button" class="xfwd-tag-remove" data-remove-port="${escapeHtml(p)}" aria-label="Remove ${escapeHtml(p)}">&times;</button></span>`
    )).join("");
}

function setExcludedTags(portsArr) {
    const parsed = parseExcludedPortsInput(Array.isArray(portsArr) ? portsArr.join(",") : String(portsArr || ""));
    currentExcludedTags = parsed || [];
    const inlineEl = document.getElementById("exclTagText");
    if (inlineEl) inlineEl.value = "";
    renderExcludedTagChips();
}

function addExcludedTokens(rawText, triggerRangeFill = true) {
    const tokens = String(rawText || "").split(/[\s,]+/).filter(Boolean);
    if (tokens.length === 0) return true;
    const next = new Set(currentExcludedTags);
    for (const tok of tokens) {
        const parsed = parseExcludedPortsInput(tok);
        if (parsed === null || parsed.length === 0) {
            showToast(`Invalid port token '${tok}'`, "warn");
            return false;
        }
        parsed.forEach(p => next.add(p));
    }
    currentExcludedTags = Array.from(next).sort((a, b) => a - b);
    renderExcludedTagChips();
    if (triggerRangeFill && currentExcludedTags.length > 0) {
        const formPortInput = document.getElementById("formPort");
        if (formPortInput) {
            const cur = parsePortSpec(formPortInput.value);
            if (!cur || !cur.rangeStr || cur.excludedPorts) {
                formPortInput.value = "1-65535";
            }
        }
        refreshRangeConstraintUI();
        if (!currentEditingRuleId) {
            document.querySelectorAll("#destinationsContainer .dest-port").forEach(input => {
                if (!input.value) input.value = "1-65535";
            });
        }
    }
    return true;
}

export function renderDestinationRow(dest, index, totalCount) {
    const prio = index + 1;
    const isPrimary = prio === 1;
    const inboundSpec = getCurrentInboundSpec();
    const isRangeRule = Boolean(inboundSpec && inboundSpec.rangeStr);
    const type = isRangeRule ? "nftables" : (dest.type || (isPrimary ? "haproxy" : "nftables"));
    const target = dest.target || "";
    const port = dest.port_range || (dest.port !== undefined && dest.port !== null ? dest.port : "");
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
                <span class="drag-handle" title="${escapeHtml(t('modal.drag_hint'))}">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/></svg>
                </span>
                <span class="prio-tag ${getPrioTagClass(prio)}">#${prio}</span>
                <span class="prio-sub">${isPrimary ? escapeHtml(t("modal.primary_path")) : escapeHtml(t("modal.backup_path"))}</span>
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
                <label>${escapeHtml(t("modal.dest_type"))}</label>
                <select class="form-control dest-type" onchange="handleDestTypeChange(this)">
                    ${isRangeRule
                        ? `<option value="nftables" selected>NFTables (Kernel)</option>`
                        : `<option value="haproxy" ${type === "haproxy" ? "selected" : ""}>HAProxy (IPv6)</option>
                           <option value="nginx" ${type === "nginx" ? "selected" : ""}>Nginx (Stream)</option>
                           <option value="nftables" ${type === "nftables" ? "selected" : ""}>NFTables (Kernel)</option>`}
                </select>
            </div>
            <div class="form-group dest-col-target">
                <label>${escapeHtml(t("modal.dest_target"))}</label>
                <input type="text" class="form-control dest-target" placeholder="${targetPlaceholder}" value="${escapeHtml(target)}" required>
            </div>
            <div class="form-group dest-col-port">
                <label>${escapeHtml(t("modal.dest_port"))}</label>
                <input type="text" inputmode="numeric" class="form-control dest-port" placeholder="${isRangeRule ? escapeHtml(t("modal.dest_port_range_placeholder", {}, "Same range or single port")) : "Default"}" value="${escapeHtml(port)}">
            </div>
        </div>
        <div class="form-group dest-iface-group" style="margin-bottom:10px; display:${type === "nftables" ? "block" : "none"};">
            <label>${escapeHtml(t("modal.tunnel_iface", {}, "Tunnel / Outbound Interface (Optional · NFTables)"))}</label>
            <input type="hidden" class="dest-tunnel-iface" value="${escapeHtml(dest.tunnel_iface || "")}">
            <div class="iface-tags-wrap">${buildTunnelIfaceTagsHtml(dest.tunnel_iface || "")}</div>
        </div>
        <div class="form-group" style="margin-bottom:10px;">
            <label>${escapeHtml(t("modal.comment_label"))}</label>
            <input type="text" class="form-control dest-comment" placeholder="e.g. ${isPrimary ? 'Foreign Server 1 - Primary IPv6' : 'Backup Tunnel Node ' + prio}" value="${escapeHtml(comment)}">
        </div>
        <div class="dest-extra-row" style="flex-wrap: wrap; gap: 10px;">
            <label class="dest-toggle-label" title="Enable only if remote destination (e.g. Xray/V2Ray with acceptProxyProtocol) is configured to receive PROXY Protocol headers.">
                <input type="checkbox" class="dest-proxy-proto" ${dest.proxy_protocol ? "checked" : ""}>
                <span>${escapeHtml(t("modal.send_proxy_v2"))}</span>
            </label>
            <label class="dest-toggle-label" title="Mid Server: Ping to this node is a partial hop. The engine strictly anchors on Priority 1 unless Priority 1 fails, has packet loss, or exceeds 150ms.">
                <input type="checkbox" class="dest-is-relay" ${dest.is_relay ? "checked" : ""}>
                <span>${escapeHtml(t("modal.mid_server"))}</span>
            </label>
            <div class="dest-test-group">
                <button type="button" class="btn-test-dest" id="btnTestDest_${index}" onclick="testModalDestination(${index})">
                    <span class="test-pulse-ring"></span>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    <span>${escapeHtml(t("modal.test_target"))}</span>
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
    const ifaceGroup = row.querySelector(".dest-iface-group");
    const val = selectEl.value;
    if (ifaceGroup) {
        ifaceGroup.style.display = val === "nftables" ? "block" : "none";
    }
    if (!targetInput) return;
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
        const ifaceEl = box.querySelector(".dest-tunnel-iface");
        const commentEl = box.querySelector(".dest-comment");
        const proxyProtoEl = box.querySelector(".dest-proxy-proto");
        const relayEl = box.querySelector(".dest-is-relay");
        const enabledEl = box.querySelector(".dest-enabled-check");

        const rawDPort = portEl ? portEl.value.trim() : "";
        const parsedDPort = rawDPort ? parsePortSpec(rawDPort) : null;
        const dType = typeEl ? typeEl.value : "haproxy";
        const rawIface = ifaceEl ? ifaceEl.value.trim() : "";
        const destObj = {
            priority: i + 1,
            type: dType,
            target: targetEl ? targetEl.value.trim() : "",
            port: parsedDPort ? parsedDPort.start : null,
            comment: commentEl ? commentEl.value.trim() : "",
            proxy_protocol: proxyProtoEl ? proxyProtoEl.checked : false,
            is_relay: relayEl ? relayEl.checked : false,
            enabled: enabledEl ? enabledEl.checked : true
        };
        if (dType === "nftables" && rawIface) {
            destObj.tunnel_iface = rawIface;
        }
        if (parsedDPort && parsedDPort.rangeStr) {
            destObj.port_range = parsedDPort.rangeStr;
        } else if (rawDPort) {
            destObj._invalidPortInput = rawDPort;
        }
        updated.push(destObj);
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
    if (e.target.closest("input, select, textarea, button, .btn-prio-move, .btn-remove-prio, .iface-tag-chip")) {
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
    const listenRaw = document.getElementById("formPort") ? document.getElementById("formPort").value.trim() : "";
    const portParsed = parsePortSpec(dest.port_range || dest.port || listenRaw);
    const port = portParsed ? portParsed.start : null;
    const resEl = document.getElementById(`testDestResult_${index}`);
    const btnEl = document.getElementById(`btnTestDest_${index}`);
    const setResultPill = (kind, htmlText, titleText = "") => {
        if (!resEl) return;
        const titleAttr = titleText ? ` title="${escapeHtml(titleText)}"` : "";
        resEl.innerHTML = `<span class="test-pill is-${kind}"${titleAttr}><span class="test-pill-dot"></span><span>${htmlText}</span></span>`;
    };

    if (!target) {
        showToast("Please enter a destination target IP or host", "warn");
        setResultPill("warn", escapeHtml(t("status.enter_target", {}, "Enter target IP")));
        return;
    }
    if ((dest.type || "haproxy") === "haproxy" && !target.includes(':')) {
        showToast("HAProxy destination target must be a valid IPv6 address", "warn");
        setResultPill("warn", escapeHtml(t("status.ipv6_required", {}, "IPv6 required")));
        return;
    }
    if (!port) {
        showToast("Please specify a port to test", "warn");
        setResultPill("warn", escapeHtml(t("status.enter_port", {}, "Enter port")));
        return;
    }

    if (btnEl) {
        btnEl.disabled = true;
        btnEl.classList.add("is-probing");
    }
    setResultPill("probing", escapeHtml(t("status.probing", {}, "Probing...")));

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
                const latStr = (data.latency_ms !== null && data.latency_ms !== undefined && data.latency_ms > 0) ? ` · ${data.latency_ms}ms · ${loss}%` : ` · ${loss}% loss`;
                setResultPill("ok", `${escapeHtml(t("status.reachable", {}, "Reachable"))}${latStr}`);
                showToast(`Destination [${target}]:${port} reachable${latStr}`);
            } else {
                const reason = data.reason ? `: ${data.reason}` : "";
                setResultPill("fail", `${escapeHtml(t("status.unreachable", {}, "Unreachable"))} (${loss}%)`, data.reason || "");
                showToast(`Destination [${target}]:${port} failed health probe${reason}`, "error");
            }
        } else {
            const errMsg = data.error || "Connection test failed";
            setResultPill("fail", escapeHtml(errMsg));
            showToast(`Target test error: ${errMsg}`, "error");
        }
    } catch (err) {
        setResultPill("fail", escapeHtml(t("status.network_error", {}, "Network Error")));
        showToast("Error executing target probe: " + err.message, "error");
    } finally {
        if (btnEl) {
            btnEl.disabled = false;
            btnEl.classList.remove("is-probing");
        }
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
            const inboundSpec = getCurrentInboundSpec();
            const isRange = Boolean(inboundSpec && inboundSpec.rangeStr);
            const defaultPort = inboundSpec ? (inboundSpec.rangeStr || inboundSpec.start) : "";
            const nextPrio = currentModalDestinations.length + 1;
            const nextType = isRange ? "nftables" : (nextPrio === 1 ? "haproxy" : "nftables");
            const newDest = {
                priority: nextPrio,
                type: nextType,
                target: "",
                port: defaultPort,
                comment: "",
                proxy_protocol: false,
                is_relay: nextPrio > 1,
                enabled: true
            };
            if (isRange) newDest.port_range = inboundSpec.rangeStr;
            currentModalDestinations.push(newDest);
            renderDestinationsList();
        });
    }

    const formPortInput = document.getElementById("formPort");
    const formExclInput = document.getElementById("formExcludedPorts");
    const exclTagBox = document.getElementById("exclTagInputBox");
    const exclTagText = document.getElementById("exclTagText");
    const exclTagChips = document.getElementById("exclTagChips");
    const destContainer = document.getElementById("destinationsContainer");

    if (destContainer) {
        destContainer.addEventListener("click", (ev) => {
            const chip = ev.target.closest(".iface-tag-chip");
            if (!chip) return;
            const grp = chip.closest(".dest-iface-group");
            if (!grp) return;
            const hidden = grp.querySelector(".dest-tunnel-iface");
            if (hidden) hidden.value = chip.dataset.iface || "";
            grp.querySelectorAll(".iface-tag-chip").forEach(c => c.classList.remove("is-selected"));
            chip.classList.add("is-selected");
        });
    }

    if (exclTagBox && exclTagText) {
        exclTagBox.addEventListener("click", () => exclTagText.focus());
        exclTagText.addEventListener("keydown", (ev) => {
            if (ev.key === " " || ev.key === "," || ev.key === "Enter") {
                ev.preventDefault();
                const val = exclTagText.value.trim();
                if (val && addExcludedTokens(val, true)) {
                    exclTagText.value = "";
                }
            } else if (ev.key === "Backspace" && !exclTagText.value && currentExcludedTags.length > 0) {
                currentExcludedTags.pop();
                renderExcludedTagChips();
                refreshRangeConstraintUI();
            }
        });
        exclTagText.addEventListener("input", () => {
            if (/[\s,]/.test(exclTagText.value)) {
                const raw = exclTagText.value;
                const endsWithDelim = /[\s,]$/.test(raw);
                const parts = raw.split(/[\s,]+/);
                const tail = endsWithDelim ? "" : (parts.pop() || "");
                const toCommit = parts.filter(Boolean).join(" ");
                if (toCommit && addExcludedTokens(toCommit, true)) {
                    exclTagText.value = tail;
                }
            }
        });
        exclTagText.addEventListener("blur", () => {
            const val = exclTagText.value.trim();
            if (val && addExcludedTokens(val, true)) {
                exclTagText.value = "";
            }
        });
    }
    if (exclTagChips) {
        exclTagChips.addEventListener("click", (ev) => {
            const rmBtn = ev.target.closest(".xfwd-tag-remove");
            if (!rmBtn) return;
            const pRem = parseInt(rmBtn.dataset.removePort || "0", 10);
            currentExcludedTags = currentExcludedTags.filter(p => p !== pRem);
            renderExcludedTagChips();
            refreshRangeConstraintUI();
        });
    }

    if (formPortInput) {
        formPortInput.addEventListener("input", () => {
            const parsed = parsePortSpec(formPortInput.value);
            if (parsed && parsed.excludedPorts) {
                setExcludedTags(parsed.excludedPorts);
            }
            refreshRangeConstraintUI();
            if (!currentEditingRuleId && parsed) {
                const fillVal = parsed.rangeStr || parsed.start;
                const portInputs = document.querySelectorAll("#destinationsContainer .dest-port");
                portInputs.forEach(input => {
                    if (!input.value) {
                        input.value = fillVal;
                    }
                });
            }
        });
    }

    const catInput = document.getElementById("formCategory");
    if (catInput) {
        const triggerPicker = () => {
            if (catInput.hasAttribute("list") && !catInput.value && typeof catInput.showPicker === "function") {
                try { catInput.showPicker(); } catch (_) {}
            }
        };
        catInput.addEventListener("focus", triggerPicker);
        catInput.addEventListener("click", triggerPicker);
    }

    if (ruleForm) {
        ruleForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (exclTagText && exclTagText.value.trim()) {
                if (!addExcludedTokens(exclTagText.value.trim(), true)) return;
                exclTagText.value = "";
            }
            syncDestinationsFromDom();

            const rawPortVal = (document.getElementById("formPort")?.value || "").trim();
            const rawExclVal = (document.getElementById("formExcludedPorts")?.value || "").trim();
            let inbound = parsePortSpec(rawPortVal);
            let excludedPorts = inbound && inbound.excludedPorts ? inbound.excludedPorts : [];

            if (rawExclVal) {
                const parsedExcl = parseExcludedPortsInput(rawExclVal);
                if (parsedExcl === null) {
                    showToast("Invalid excluded ports list. Use comma-separated ports like 22, 443, 1001", "error");
                    return;
                }
                excludedPorts = parsedExcl;
                if (!inbound && !rawPortVal) {
                    inbound = { start: 1, end: 65535, rangeStr: "1-65535" };
                }
            }

            if (!inbound) {
                showToast("Please enter a valid port (1 - 65535), range (10000-20000), or != excluded ports", "error");
                return;
            }
            if (excludedPorts.length > 0 && !inbound.rangeStr) {
                showToast("Excluded ports (!=) require an inbound port range such as 1-65535", "error");
                return;
            }
            const inboundLabel = excludedPorts.length > 0
                ? `!=${excludedPorts.slice(0, 4).join(",")}`
                : (inbound.rangeStr || String(inbound.start));

            if (currentModalDestinations.length === 0) {
                showToast("At least one forwarding destination path is required", "error");
                return;
            }

            const sanitizedDests = [];
            for (let i = 0; i < currentModalDestinations.length; i++) {
                const d = currentModalDestinations[i];
                if (!d.target || !d.target.trim()) {
                    showToast(`Please enter target IP for Priority #${i + 1}`, "error");
                    return;
                }
                if (d._invalidPortInput) {
                    showToast(`Priority #${i + 1} has an invalid target port '${d._invalidPortInput}'`, "error");
                    return;
                }
                if (inbound.rangeStr) {
                    if (d.type !== "nftables") {
                        showToast(`Port range ${inbound.rangeStr} is supported only on NFTables (Priority #${i + 1})`, "error");
                        return;
                    }
                    if (d.port_range && d.port_range !== inbound.rangeStr) {
                        showToast(`NFTables outbound range on Priority #${i + 1} must match ${inbound.rangeStr} or be a single port`, "error");
                        return;
                    }
                } else if (d.port_range) {
                    showToast(`Destination port range '${d.port_range}' requires a matching inbound NFTables range`, "error");
                    return;
                }
                const cleanDest = { ...d };
                delete cleanDest._invalidPortInput;
                sanitizedDests.push(cleanDest);
            }

            const ruleIdInput = document.getElementById("editRuleId") || document.getElementById("ruleId");
            const nameInput = document.getElementById("formName");
            const protoInput = document.getElementById("formProto");
            const catInput = document.getElementById("formCategory");
            const activePriorityInput = document.getElementById("activePriority");
            const forceOverrideInput = document.getElementById("forceOverride");
            const ruleCreatedAtInput = document.getElementById("ruleCreatedAt");

            const rulePayload = {
                id: (ruleIdInput && ruleIdInput.value) ? ruleIdInput.value : `rule-${inboundLabel}`,
                name: (nameInput && nameInput.value ? nameInput.value.trim() : "") || `Port ${inboundLabel}`,
                port: inbound.start,
                protocol: (protoInput && protoInput.value) ? protoInput.value : "both",
                category: (catInput && catInput.value ? catInput.value.trim() : ""),
                active_priority: parseInt((activePriorityInput && activePriorityInput.value) || "1", 10),
                force_override: parseInt((forceOverrideInput && forceOverrideInput.value) || "0", 10),
                destinations: sanitizedDests
            };
            if (inbound.rangeStr) {
                rulePayload.port_range = inbound.rangeStr;
            }
            if (excludedPorts.length > 0) {
                rulePayload.excluded_ports = excludedPorts;
                if (!rulePayload.name || rulePayload.name === `Port ${inboundLabel}`) {
                    rulePayload.name = `All != ${excludedPorts.join(", ")}`;
                }
            }

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
                    if (data.sync_ok === false && Array.isArray(data.sync_errors) && data.sync_errors.length > 0) {
                        showToast(`Rule saved, but firewall/proxy sync reported: ${data.sync_errors[0]}`, "warning");
                    } else {
                        showToast(`Port :${inboundLabel} rule saved successfully!`, "success");
                    }
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
