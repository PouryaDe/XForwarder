// ============================================================================
// XForwarder Web UI - Rule Modal & Destination Editor Subsystem (Native ES Module)
// ============================================================================

import { API_BASE } from "./api.js";
import { escapeHtml, showToast, getRuleId } from "./utils.js";
import { currentRules, lastNetwork, setLastNetwork } from "./state.js";
import { updateCategoryDatalist } from "./rules.js";
import { t } from "./i18n.js";

let currentModalDestinations = [];
let draggedModalPrioIndex = null;
let currentEditingRuleId = null;
let lastAutoInboundPort = "";

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

function isNftablesType(destType) {
    const s = String(destType || "").toLowerCase().trim();
    return s === "nftables" || s === "nftables_dsr" || s === "nftables_dsr_relay";
}

function isLbSupportedType(destType) {
    const s = String(destType || "").toLowerCase().trim();
    return s === "nftables" || s === "nginx";
}

const LB_MODES_NFT = ["ip_hash", "round_robin", "random"];
const LB_MODES_NGINX = ["ip_hash", "least_conn", "round_robin", "random"];
const LB_SPLIT_COLORS = [
    "var(--accent, #34e0a1)",
    "var(--accent-2, #46d6e6)",
    "#f59e0b",
    "#a78bfa",
    "#fb7185",
    "#38bdf8"
];

function getLbModeOptions(destType) {
    return String(destType || "").toLowerCase().trim() === "nginx" ? LB_MODES_NGINX : LB_MODES_NFT;
}

function normalizeLbModeForType(destType, mode) {
    const allowed = getLbModeOptions(destType);
    const clean = String(mode || "ip_hash").toLowerCase().trim();
    return allowed.includes(clean) ? clean : "ip_hash";
}

function buildLbModeOptionsHtml(destType, selectedMode) {
    const allowed = getLbModeOptions(destType);
    const sel = normalizeLbModeForType(destType, selectedMode);
    const labels = {
        ip_hash: t("modal.lb_algo_ip_hash", {}, "IP Hash (Sticky Session)"),
        least_conn: t("modal.lb_algo_least_conn", {}, "Least Connections"),
        round_robin: t("modal.lb_algo_round_robin", {}, "Round-Robin"),
        random: t("modal.lb_algo_random", {}, "Random")
    };
    return allowed.map(m => `<option value="${m}" ${sel === m ? "selected" : ""}>${escapeHtml(labels[m] || m)}</option>`).join("");
}

function getLbModeHintText(mode) {
    const clean = String(mode || "ip_hash").toLowerCase().trim();
    if (clean === "least_conn") return t("modal.lb_hint_least_conn", {}, "Routes each new connection to the backend with the fewest active connections (weighted).");
    if (clean === "round_robin") return t("modal.lb_hint_round_robin", {}, "Distributes each new connection sequentially across healthy backends according to their weights.");
    if (clean === "random") return t("modal.lb_hint_random", {}, "Randomly selects a healthy backend per new connection according to weights.");
    return t("modal.lb_hint_ip_hash", {}, "Sticky per client IP — recommended for VPN, Xray, Reality & WireGuard so active sessions never jump servers.");
}

function detectIpVersion(rawIp) {
    const s = String(rawIp || "").trim().replace(/^\[|\]$/g, "");
    if (!s) return 0;
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(s)) {
        const octs = s.split(".").map(Number);
        return octs.every(o => o >= 0 && o <= 255) ? 4 : 0;
    }
    if (s.includes(":")) return 6;
    return 0;
}

function refreshLbBoxState(box) {
    if (!box) return;
    const panel = box.querySelector(".lb-pool-panel");
    if (!panel) return;
    const destType = (box.querySelector(".dest-type")?.value || "nftables").toLowerCase();
    const modeSelect = panel.querySelector(".lb-mode-select");
    const hintEl = panel.querySelector(".lb-mode-hint");
    if (modeSelect && hintEl) {
        hintEl.textContent = getLbModeHintText(modeSelect.value);
    }
    const noteEl = panel.querySelector(".lb-pool-note");
    if (noteEl) {
        noteEl.textContent = destType === "nftables"
            ? t("modal.lb_nft_family_note", {}, "NFTables requires all pool IPs to be the same family (all IPv4 or all IPv6). Down nodes are auto-excluded.")
            : t("modal.lb_nginx_note", {}, "Nginx passively skips failed TCP targets (max_fails=2) and the engine auto-prunes dead nodes every 15s.");
    }

    const rows = Array.from(panel.querySelectorAll(".lb-target-row"));
    const countEl = panel.querySelector(".lb-count-pill");
    if (countEl) countEl.textContent = `${rows.length} / 16`;

    const addBtn = panel.querySelector(".btn-add-lb-target");
    if (addBtn) addBtn.disabled = rows.length >= 16;

    let totalWeight = 0;
    const ipVersions = new Set();
    const rowMeta = rows.map((row, idx) => {
        const enabled = row.querySelector(".lb-member-enabled")?.checked !== false;
        const rawW = parseInt(row.querySelector(".lb-member-weight")?.value || "1", 10);
        const weight = isNaN(rawW) ? 1 : Math.max(1, Math.min(100, rawW));
        const target = (row.querySelector(".lb-member-target")?.value || "").trim();
        const rmBtn = row.querySelector(".btn-remove-lb-member");
        if (rmBtn) rmBtn.disabled = rows.length <= 2;
        if (enabled) {
            totalWeight += weight;
            const ver = detectIpVersion(target);
            if (ver > 0) ipVersions.add(ver);
        }
        return { row, idx, enabled, weight, target };
    });

    const splitBar = panel.querySelector(".lb-split-bar");
    const segmentsHtml = [];
    rowMeta.forEach((item) => {
        const idxEl = item.row.querySelector(".lb-member-idx");
        if (idxEl) idxEl.textContent = `#${item.idx + 1}`;
        const pctEl = item.row.querySelector(".lb-weight-pct");
        if (!item.enabled || totalWeight <= 0) {
            if (pctEl) {
                pctEl.textContent = t("status.off", {}, "Off");
                pctEl.classList.add("is-off");
            }
            item.row.classList.add("is-member-disabled");
        } else {
            item.row.classList.remove("is-member-disabled");
            const pct = Math.round((item.weight / totalWeight) * 100);
            if (pctEl) {
                pctEl.textContent = `${pct}%`;
                pctEl.classList.remove("is-off");
            }
            const color = LB_SPLIT_COLORS[item.idx % LB_SPLIT_COLORS.length];
            const label = escapeHtml(item.target || `#${item.idx + 1}`);
            segmentsHtml.push(`<div class="lb-split-seg" style="flex:${item.weight}; background:${color};" title="${label}: ${pct}%"><span>${pct >= 12 ? `${pct}%` : ""}</span></div>`);
        }
    });
    if (splitBar) {
        splitBar.innerHTML = segmentsHtml.join("");
    }

    const warnEl = panel.querySelector(".lb-family-warning");
    if (warnEl) {
        const hasMixed = (destType === "nftables" && ipVersions.size > 1);
        warnEl.style.display = hasMixed ? "flex" : "none";
    }
}

function buildLbMemberRowHtml(member, mIdx, destType, isRangeRule, totalCount) {
    const mTarget = member.target || "";
    const mPort = member.port_range || (member.port !== undefined && member.port !== null ? member.port : "");
    const mWeight = Math.max(1, Math.min(100, parseInt(member.weight || 1, 10) || 1));
    const mComment = member.comment || "";
    const mIface = member.tunnel_iface || "";
    const mEnabled = member.enabled !== false;
    const isNft = (destType === "nftables");
    const targetPh = isNft ? "10.88.1.2 / 2001:db8::2" : "192.0.2.1 or host";
    const portPh = isRangeRule ? t("modal.dest_port_range_placeholder", {}, "Same range or port") : "Default";

    const targetLbl = escapeHtml(t("modal.dest_target", {}, "Target Host"));
    const portLbl = escapeHtml(t("modal.dest_port", {}, "Port"));
    const weightLbl = escapeHtml(t("modal.lb_weight_label", {}, "Weight"));
    const ifaceLbl = escapeHtml(t("modal.tunnel_iface", {}, "Outbound Interface"));
    const commentLbl = escapeHtml(t("modal.comment_label", {}, "Label"));

    return `
        <div class="lb-target-row ${mEnabled ? "" : "is-member-disabled"}" data-member-index="${mIdx}">
            <div class="lb-member-top">
                <div class="lb-member-top-left">
                    <span class="lb-member-idx font-mono">#${mIdx + 1}</span>
                    <label class="dest-switch-control lb-member-switch" title="Enable or disable this backend IP">
                        <input type="checkbox" class="lb-member-enabled" ${mEnabled ? "checked" : ""}>
                        <span class="dest-switch-slider"></span>
                    </label>
                    <span class="lb-weight-pct font-mono ${mEnabled ? "" : "is-off"}">${mEnabled ? "--%" : escapeHtml(t("status.off", {}, "Off"))}</span>
                </div>
                <div class="lb-member-top-right">
                    <div class="lb-member-test-wrap">
                        <span class="test-dest-result lb-member-test-result"></span>
                        <button type="button" class="btn-test-dest btn-test-lb-member">
                            <span class="test-pulse-ring"></span>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                            <span>${escapeHtml(t("common.test", {}, "Test"))}</span>
                        </button>
                    </div>
                    <button type="button" class="btn-remove-lb-member" title="Remove backend IP" ${totalCount <= 2 ? "disabled" : ""}>&times;</button>
                </div>
            </div>
            <div class="lb-member-fields">
                <div class="lb-field lb-col-target">
                    <label class="lb-field-label">${targetLbl}</label>
                    <input type="text" class="form-control font-mono lb-member-target" placeholder="${escapeHtml(targetPh)}" value="${escapeHtml(mTarget)}">
                </div>
                <div class="lb-field lb-col-port">
                    <label class="lb-field-label">${portLbl}</label>
                    <input type="text" inputmode="numeric" class="form-control font-mono lb-member-port" placeholder="${escapeHtml(portPh)}" value="${escapeHtml(mPort)}">
                </div>
                <div class="lb-field lb-col-weight">
                    <label class="lb-field-label">${weightLbl}</label>
                    <input type="number" min="1" max="100" class="form-control font-mono lb-member-weight" value="${mWeight}" title="${escapeHtml(t("modal.tip_lb_weight", {}, "Relative traffic share (1-100)"))}">
                </div>
            </div>
            <div class="lb-member-extra">
                <div class="lb-field lb-member-iface-group" style="display:${isNft ? "block" : "none"};">
                    <label class="lb-field-label">${ifaceLbl}</label>
                    <input type="hidden" class="lb-member-iface" value="${escapeHtml(mIface)}">
                    <div class="iface-multiselect" data-auto-mode="outbound">
                        <button type="button" class="form-control iface-select-trigger">
                            <span class="iface-trigger-text">${buildTunnelIfaceTriggerHtml(mIface, false)}</span>
                            <svg class="iface-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="6 9 12 15 18 9"/></svg>
                        </button>
                        <div class="iface-dropdown-menu">${buildTunnelIfaceMenuHtml(mIface, false, mTarget)}</div>
                    </div>
                </div>
                <div class="lb-field lb-member-comment-wrap">
                    <label class="lb-field-label">${commentLbl}</label>
                    <input type="text" class="form-control lb-member-comment" placeholder="${escapeHtml(t("modal.comment_placeholder", {}, "e.g. Node 1"))}" value="${escapeHtml(mComment)}">
                </div>
            </div>
        </div>
    `;
}

function buildDestTypeOptionsHtml(selectedType, isRange) {
    const sel = isRange
        ? (isNftablesType(selectedType) ? String(selectedType).toLowerCase() : "nftables")
        : String(selectedType || "haproxy").toLowerCase();
    const nftOpts = `
        <option value="nftables" ${sel === "nftables" ? "selected" : ""}>NFTables (Kernel DNAT)</option>
        <option value="nftables_dsr" ${sel === "nftables_dsr" ? "selected" : ""}>NFTables DSR (UP)</option>
        <option value="nftables_dsr_relay" ${sel === "nftables_dsr_relay" ? "selected" : ""}>NFTables DSR (Spoof)</option>
    `;
    if (isRange) return nftOpts;
    return `
        <option value="haproxy" ${sel === "haproxy" ? "selected" : ""}>HAProxy (IPv6)</option>
        <option value="nginx" ${sel === "nginx" ? "selected" : ""}>Nginx (Stream)</option>
        ${nftOpts}
    `;
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
            selectEl.innerHTML = buildDestTypeOptionsHtml(prev, isRange);
            if (isRange && !isNftablesType(prev)) selectEl.value = "nftables";
            handleDestTypeChange(selectEl);
        }
        if (portEl) {
            portEl.placeholder = isRange
                ? (t("modal.dest_port_range_placeholder", {}, "Same range or single port"))
                : "Default";
        }
        box.querySelectorAll(".lb-member-port").forEach(mpEl => {
            mpEl.placeholder = isRange
                ? t("modal.dest_port_range_placeholder", {}, "Same range or port")
                : "Default";
        });
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
    lastAutoInboundPort = "";

    currentModalDestinations = [
        { priority: 1, type: "haproxy", target: "", port: "", comment: "", proxy_protocol: false, is_relay: false, enabled: true },
        { priority: 2, type: "nftables", target: "", port: "", comment: "", proxy_protocol: false, is_relay: false, enabled: true }
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
    const rule = (currentRules || []).find(r => getRuleId(r) === currentEditingRuleId);
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
    if (ruleIdInput) ruleIdInput.value = getRuleId(rule);

    const portInput = document.getElementById("formPort");
    if (portInput) portInput.value = rule.port_range || rule.port || "1-65535";
    lastAutoInboundPort = String(rule.port_range || rule.port || "");

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

    currentModalDestinations = (rule.destinations || []).map(d => {
        const normType = (rule.port_range && !isNftablesType(d.type)) ? "nftables" : (d.type || "haproxy");
        return {
            priority: d.priority || 1,
            type: normType,
            target: d.target || "",
            port: d.port_range ? d.port_range : (d.port !== undefined && d.port !== null ? d.port : ""),
            port_range: d.port_range || null,
            tunnel_iface: d.tunnel_iface || "",
            ingress_iface: d.ingress_iface || "",
            spoof_ip: d.spoof_ip || "",
            snat_ip: d.snat_ip || "",
            comment: d.comment || "",
            proxy_protocol: Boolean(d.proxy_protocol),
            is_relay: Boolean(d.is_relay),
            enabled: d.enabled !== undefined ? Boolean(d.enabled) : true,
            lb_enabled: Boolean(d.lb_enabled) && isLbSupportedType(normType),
            lb_mode: normalizeLbModeForType(normType, d.lb_mode || "ip_hash"),
            lb_targets: Array.isArray(d.lb_targets) ? d.lb_targets.map(m => ({
                target: m.target || "",
                port: m.port_range ? m.port_range : (m.port !== undefined && m.port !== null ? m.port : ""),
                port_range: m.port_range || null,
                weight: parseInt(m.weight || 1, 10) || 1,
                tunnel_iface: m.tunnel_iface || "",
                comment: m.comment || "",
                enabled: m.enabled !== undefined ? Boolean(m.enabled) : true
            })) : []
        };
    });

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
                document.querySelectorAll("#destinationsContainer .iface-multiselect").forEach(ms => {
                    const grp = ms.parentElement;
                    const hidden = grp ? grp.querySelector("input[type='hidden']") : null;
                    const menu = ms.querySelector(".iface-dropdown-menu");
                    const triggerText = ms.querySelector(".iface-trigger-text");
                    const prevVal = (hidden && hidden.value) || "";
                    const isIngress = ms.dataset.autoMode === "ingress";
                    if (menu) menu.innerHTML = buildTunnelIfaceMenuHtml(prevVal, isIngress);
                    if (triggerText) triggerText.innerHTML = buildTunnelIfaceTriggerHtml(prevVal, isIngress);
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
        const peerPart = String((tObj && tObj.peer_ip) || "").trim();
        const pingPart = String((tObj && tObj.target_to_ping) || "").trim();
        const statePart = String(tObj.state || "UP").toUpperCase();
        entries.push({
            name,
            ip: ipPart,
            peerIp: peerPart,
            targetToPing: pingPart,
            isTunnel: true,
            up: statePart === "UP",
            label: `${name} (${tObj.type || "Tunnel"}${ipPart ? ` · ${ipPart}` : ""}${peerPart ? ` -> ${peerPart}` : ""} · ${statePart})`
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
            peerIp: "",
            targetToPing: "",
            isTunnel: false,
            up: true,
            label: `${name} (WAN${ipPart ? ` · ${ipPart}` : ""})`
        });
    });

    const primaryName = String(net.primary_interface || "").trim();
    if (primaryName && !seen.has(primaryName)) {
        seen.add(primaryName);
        entries.push({ name: primaryName, ip: "", peerIp: "", targetToPing: "", isTunnel: false, up: true, label: `${primaryName} (Primary WAN)` });
    }
    return entries;
}

function findSuggestedTunnelInterface(list, targetHost = "", isIngress = false) {
    if (!list || list.length === 0) return null;
    const cleanTarget = String(targetHost || "").trim().toLowerCase();

    // 1. Direct match on peer IP, ping target, or local IP
    if (cleanTarget) {
        const direct = list.find(item =>
            item.isTunnel && (
                (item.peerIp && item.peerIp.toLowerCase() === cleanTarget) ||
                (item.targetToPing && item.targetToPing.toLowerCase() === cleanTarget) ||
                (item.ip && item.ip.toLowerCase() === cleanTarget)
            )
        );
        if (direct) return direct.name;

        // 2. Subnet match (/24 or /30, e.g. 10.80.15.x)
        const parts = cleanTarget.split(".");
        if (parts.length === 4) {
            const prefix = `${parts[0]}.${parts[1]}.${parts[2]}.`;
            const subnetMatch = list.find(item => item.isTunnel && item.ip && item.ip.startsWith(prefix));
            if (subnetMatch) return subnetMatch.name;
        }
    }

    // 3. For Inbound Tunnel Interface (DSR Relay), suggest the first active/UP tunnel
    if (isIngress) {
        const upTunnel = list.find(item => item.isTunnel && item.up);
        if (upTunnel) return upTunnel.name;
    }

    return null;
}

function buildTunnelIfaceTriggerHtml(selectedVal = "", isIngress = false) {
    const cur = String(selectedVal || "").trim();
    if (!cur) {
        const autoText = isIngress
            ? t("modal.ingress_iface_auto", {}, "Auto (All Non-WAN)")
            : t("modal.tunnel_iface_auto", {}, "Auto (Kernel Route)");
        return `<span class="iface-trigger-auto">${escapeHtml(autoText)}</span>`;
    }
    const list = getAvailableServerInterfaces();
    const match = list.find(item => item.name === cur);
    const up = match ? match.up : true;
    const ip = match && match.ip ? ` <small>${escapeHtml(match.ip)}</small>` : "";
    return `<span class="iface-dot ${up ? "is-up" : "is-down"}"></span><span class="iface-trigger-name font-mono">${escapeHtml(cur)}</span>${ip}`;
}

function buildTunnelIfaceMenuHtml(selectedVal = "", isIngress = false, targetHost = "") {
    const cur = String(selectedVal || "").trim();
    const autoLabel = escapeHtml(
        isIngress
            ? t("modal.ingress_iface_auto", {}, "Auto (All Non-WAN)")
            : t("modal.tunnel_iface_auto", {}, "Auto (Kernel Route)")
    );
    const checkSvg = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`;
    const list = getAvailableServerInterfaces();
    const suggestedName = findSuggestedTunnelInterface(list, targetHost, isIngress);

    let html = `
        <button type="button" class="iface-option ${!cur ? "is-checked" : ""}" data-iface="">
            <span class="iface-checkbox">${!cur ? checkSvg : ""}</span>
            <span class="iface-opt-name">${autoLabel}</span>
        </button>`;

    // Sort list so that the suggested interface appears right after Auto
    const sortedList = [...list].sort((a, b) => {
        if (a.name === suggestedName) return -1;
        if (b.name === suggestedName) return 1;
        return 0;
    });

    let foundSelected = !cur;
    sortedList.forEach(item => {
        const isSel = Boolean(cur && cur === item.name);
        const isSugg = Boolean(suggestedName && item.name === suggestedName);
        if (isSel) foundSelected = true;
        html += `
        <button type="button" class="iface-option ${isSel ? "is-checked" : ""} ${isSugg ? "is-suggested" : ""}" data-iface="${escapeHtml(item.name)}" title="${escapeHtml(item.label)}">
            <span class="iface-checkbox">${isSel ? checkSvg : ""}</span>
            <span class="iface-dot ${item.up ? "is-up" : "is-down"}"></span>
            <span class="iface-opt-name font-mono">${escapeHtml(item.name)}</span>
            ${item.ip ? `<small class="iface-opt-ip font-mono">${escapeHtml(item.ip)}</small>` : ""}
            ${isSugg ? `<span class="iface-suggest-badge">${escapeHtml(t("modal.suggested", {}, "Suggested"))}</span>` : ""}
        </button>`;
    });
    if (cur && !foundSelected) {
        html += `
        <button type="button" class="iface-option is-checked" data-iface="${escapeHtml(cur)}" title="Saved interface">
            <span class="iface-checkbox">${checkSvg}</span>
            <span class="iface-dot is-up"></span>
            <span class="iface-opt-name font-mono">${escapeHtml(cur)}</span>
            <small class="iface-opt-ip font-mono">saved</small>
        </button>`;
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

function getDetectedServerIps() {
    const net = lastNetwork || {};
    const list = [];
    const seen = new Set();

    (Array.isArray(net.server_ips) ? net.server_ips : []).forEach(sObj => {
        const ip = String((sObj && sObj.ip) || "").trim();
        if (!ip || seen.has(ip)) return;
        seen.add(ip);
        list.push({
            ip,
            iface: String((sObj && sObj.interface) || "WAN").trim(),
            isPrimary: Boolean(sObj && sObj.is_primary),
            version: sObj && sObj.version === 6 ? 6 : 4
        });
    });

    return list;
}

if (typeof window !== "undefined") {
    window.fillDestSpoofIp = function (btn, ip) {
        if (!btn || !ip) return;
        const group = btn.closest(".dest-spoof-ip-group");
        if (!group) return;
        const input = group.querySelector(".dest-spoof-ip");
        if (input) {
            input.value = ip;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
            input.focus();
        }
    };
}

export function renderDestinationRow(dest, index, totalCount) {
    const prio = index + 1;
    const isPrimary = prio === 1;
    const inboundSpec = getCurrentInboundSpec();
    const isRangeRule = Boolean(inboundSpec && inboundSpec.rangeStr);
    const type = (isRangeRule && !isNftablesType(dest.type)) ? "nftables" : (dest.type || (isPrimary ? "haproxy" : "nftables"));
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
        ? "2001:db8:cafe::1 (IPv6 only)"
        : (type === "nftables_dsr_relay"
            ? "198.51.100.10 (Exit Server IP)"
            : (isNftablesType(type) ? "10.88.1.2 (IPv4) or 2001:db8::2 (IPv6)" : "192.0.2.1 or 2001:db8::1"));
    const showOutIface = (type === "nftables" || type === "nftables_dsr");
    const showDsrRow = (type === "nftables_dsr" || type === "nftables_dsr_relay");
    const isDsrRelay = (type === "nftables_dsr_relay");
    const lbSupported = isLbSupportedType(type);
    const lbEnabled = lbSupported && Boolean(dest.lb_enabled);
    const lbMode = normalizeLbModeForType(type, dest.lb_mode || "ip_hash");
    const defaultMemberPort = port || (inboundSpec ? (inboundSpec.rangeStr || inboundSpec.start) : "");
    const lbMembers = (Array.isArray(dest.lb_targets) && dest.lb_targets.length >= 2)
        ? dest.lb_targets
        : [
            { target: target, port: defaultMemberPort, weight: 1, tunnel_iface: dest.tunnel_iface || "", comment: "", enabled: true },
            { target: "", port: defaultMemberPort, weight: 1, tunnel_iface: dest.tunnel_iface || "", comment: "", enabled: true }
        ];
    const lbMembersHtml = lbMembers.map((m, mIdx) => buildLbMemberRowHtml(m, mIdx, type, isRangeRule, lbMembers.length)).join("");
    const spoofLabelText = isDsrRelay
        ? t("modal.spoof_ip", {}, "Iran / Spoof IP")
        : t("modal.spoof_ip_opt", {}, "Ingress IP (Optional)");

    const detectedServerIps = getDetectedServerIps();
    const spoofDatalistId = `destSpoofIpList_${index}_${Math.random().toString(36).substr(2, 6)}`;
    const snatDatalistId = `destSnatIpList_${index}_${Math.random().toString(36).substr(2, 6)}`;
    const serverIpDatalistOptionsHtml = detectedServerIps.map(s =>
        `<option value="${escapeHtml(s.ip)}">${escapeHtml(s.ip)} (${escapeHtml(s.iface)}${s.isPrimary ? ` · ${escapeHtml(t("common.primary", {}, "Primary"))}` : ""})</option>`
    ).join("");

    const spoofQuickChipsHtml = detectedServerIps.length > 0
        ? `<div class="dest-spoof-suggestions">
            <span class="suggestion-hint">${escapeHtml(t("modal.suggested_ip", {}, "Suggested:"))}</span>
            ${detectedServerIps.map(s => `
                <button type="button" class="ip-chip font-mono" title="${escapeHtml(s.iface)}${s.isPrimary ? " (Primary WAN)" : ""}" onclick="window.fillDestSpoofIp(this, '${escapeHtml(s.ip)}')">
                    ${escapeHtml(s.ip)}
                </button>
            `).join("")}
           </div>`
        : "";

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
                    ${buildDestTypeOptionsHtml(type, isRangeRule)}
                </select>
            </div>
            <div class="form-group dest-col-target" style="display:${lbEnabled ? "none" : "block"};">
                <label>${escapeHtml(t("modal.dest_target"))}</label>
                <input type="text" class="form-control dest-target" placeholder="${targetPlaceholder}" value="${escapeHtml(target)}" ${lbEnabled ? "" : "required"}>
            </div>
            <div class="form-group dest-col-port" style="display:${lbEnabled ? "none" : "block"};">
                <label>${escapeHtml(t("modal.dest_port"))}</label>
                <input type="text" inputmode="numeric" class="form-control dest-port" placeholder="${isRangeRule ? escapeHtml(t("modal.dest_port_range_placeholder", {}, "Same range or single port")) : "Default"}" value="${escapeHtml(port)}">
            </div>
            <div class="dest-lb-toggle-bar" style="display:${lbSupported ? "flex" : "none"};">
                <label class="dest-lb-switch-label">
                    <span class="dest-switch-control">
                        <input type="checkbox" class="dest-lb-enabled" ${lbEnabled ? "checked" : ""}>
                        <span class="dest-switch-slider"></span>
                    </span>
                    <span>${escapeHtml(t("modal.lb_toggle", {}, "Load Balance"))}</span>
                </label>
                <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_lb_toggle", {}, "Distribute traffic across multiple backend IPs within this priority."))}" aria-label="Info">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                </span>
            </div>
        </div>
        <div class="lb-pool-panel" style="display:${lbEnabled ? "block" : "none"};">
            <div class="lb-pool-header">
                <div class="lb-mode-wrap">
                    <label class="label-with-tip">
                        <span>${escapeHtml(t("modal.lb_mode_label", {}, "Distribution Algorithm"))}</span>
                        <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_lb_mode", {}, "Choose how connections are distributed across healthy servers."))}" aria-label="Info">
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                        </span>
                    </label>
                    <select class="form-control lb-mode-select">
                        ${buildLbModeOptionsHtml(type, lbMode)}
                    </select>
                </div>
                <div class="lb-header-tools">
                    <button type="button" class="btn btn-secondary btn-sm btn-lb-equalize">${escapeHtml(t("modal.lb_equalize", {}, "Equalize"))}</button>
                    <span class="lb-count-pill font-mono">${lbMembers.length} / 16</span>
                </div>
            </div>
            <div class="lb-mode-hint">${escapeHtml(getLbModeHintText(lbMode))}</div>
            <div class="lb-split-bar" aria-label="Traffic split preview"></div>
            <div class="lb-family-warning" style="display:none;">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                <span>${escapeHtml(t("rules.lb_ip_family_warn", {}, "NFTables LB pool cannot mix IPv4 and IPv6 addresses"))}</span>
            </div>
            <div class="lb-targets-list">${lbMembersHtml}</div>
            <div class="lb-pool-footer">
                <button type="button" class="btn btn-secondary btn-sm btn-add-lb-target">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    <span>${escapeHtml(t("modal.lb_add_target", {}, "Add Backend IP"))}</span>
                </button>
                <span class="lb-pool-note">${escapeHtml(type === "nftables" ? t("modal.lb_nft_family_note", {}, "NFTables requires all pool IPs to be the same family.") : t("modal.lb_nginx_note", {}, "Nginx passively skips failed TCP targets (max_fails=2)."))}</span>
            </div>
        </div>
        <div class="dest-meta-row dest-dsr-row" style="display:${showDsrRow ? "flex" : "none"};">
            <div class="form-group flex-1 dest-spoof-ip-group">
                <label class="label-with-tip">
                    <span class="dest-spoof-label">${escapeHtml(spoofLabelText)}</span>${isDsrRelay ? ' <span class="required">*</span>' : ''}
                    <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_spoof_ip", {}, "Iran server public IP used as spoofed source on direct download return packets."))}" aria-label="Info">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </span>
                </label>
                <input type="text" list="${spoofDatalistId}" class="form-control font-mono dest-spoof-ip" placeholder="${isDsrRelay ? "198.51.100.25 (Required)" : "Auto (WAN Interface)"}" value="${escapeHtml(dest.spoof_ip || "")}">
                <datalist id="${spoofDatalistId}">
                    ${serverIpDatalistOptionsHtml}
                </datalist>
                ${spoofQuickChipsHtml}
            </div>
            <div class="form-group flex-1 dest-ingress-iface-group" style="display:${isDsrRelay ? "block" : "none"};">
                <label class="label-with-tip">
                    <span>${escapeHtml(t("modal.ingress_iface", {}, "Inbound Tunnel Interface"))}</span>
                    <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_ingress_iface", {}, "Tunnel interface receiving packets from the Iran server (e.g. tun1, ipip1)."))}" aria-label="Info">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </span>
                </label>
                <input type="hidden" class="dest-ingress-iface" value="${escapeHtml(dest.ingress_iface || "")}">
                <div class="iface-multiselect" data-auto-mode="ingress">
                    <button type="button" class="form-control iface-select-trigger">
                        <span class="iface-trigger-text">${buildTunnelIfaceTriggerHtml(dest.ingress_iface || "", true)}</span>
                        <svg class="iface-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="6 9 12 15 18 9"/></svg>
                    </button>
                    <div class="iface-dropdown-menu">${buildTunnelIfaceMenuHtml(dest.ingress_iface || "", true, target)}</div>
                </div>
            </div>
            <div class="form-group flex-1 dest-snat-ip-group" style="display:${isDsrRelay ? "block" : "none"};">
                <label class="label-with-tip">
                    <span>${escapeHtml(t("modal.snat_ip", {}, "Relay SNAT IP"))}</span>
                    <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_snat_ip", {}, "Optional public WAN IP of this relay server used for SNAT toward exit nodes."))}" aria-label="Info">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </span>
                </label>
                <input type="text" list="${snatDatalistId}" class="form-control font-mono dest-snat-ip" placeholder="Auto (WAN IP)" value="${escapeHtml(dest.snat_ip || "")}">
                <datalist id="${snatDatalistId}">
                    ${serverIpDatalistOptionsHtml}
                </datalist>
            </div>
        </div>
        <div class="dest-meta-row">
            <div class="form-group dest-iface-group" style="display:${(showOutIface && !lbEnabled) ? "block" : "none"};">
                <label class="label-with-tip">
                    <span>${escapeHtml(t("modal.tunnel_iface", {}, "Outbound Interface"))}</span>
                    <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_outbound_iface", {}, "Optional (NFTables). Bind probes & routing to a specific tunnel or WAN interface."))}" aria-label="Info">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </span>
                </label>
                <input type="hidden" class="dest-tunnel-iface" value="${escapeHtml(dest.tunnel_iface || "")}">
                <div class="iface-multiselect" data-auto-mode="outbound">
                    <button type="button" class="form-control iface-select-trigger">
                        <span class="iface-trigger-text">${buildTunnelIfaceTriggerHtml(dest.tunnel_iface || "", false)}</span>
                        <svg class="iface-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="6 9 12 15 18 9"/></svg>
                    </button>
                    <div class="iface-dropdown-menu">${buildTunnelIfaceMenuHtml(dest.tunnel_iface || "", false, target)}</div>
                </div>
            </div>
            <div class="form-group dest-comment-group">
                <label class="label-with-tip">
                    <span>${escapeHtml(t("modal.comment_label", {}, "Label"))}</span>
                    <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_comment", {}, "Optional note for this path. Example: Foreign Server 1 - IPv6"))}" aria-label="Info">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    </span>
                </label>
                <input type="text" class="form-control dest-comment" placeholder="${escapeHtml(t("modal.comment_placeholder", {}, "e.g. Foreign Node 1"))}" value="${escapeHtml(comment)}">
            </div>
        </div>
        <div class="dest-extra-row" style="flex-wrap: wrap; gap: 10px;">
            <label class="dest-toggle-label">
                <input type="checkbox" class="dest-proxy-proto" ${dest.proxy_protocol ? "checked" : ""}>
                <span>${escapeHtml(t("modal.send_proxy_v2", {}, "PROXY v2"))}</span>
                <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_proxy_v2", {}, "Send PROXY Protocol v2 header. Enable only if upstream expects it."))}" aria-label="Info">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                </span>
            </label>
            <label class="dest-toggle-label">
                <input type="checkbox" class="dest-is-relay" ${dest.is_relay ? "checked" : ""}>
                <span>${escapeHtml(t("modal.mid_server", {}, "Mid Server"))}</span>
                <span class="xfwd-info-tip" tabindex="0" data-tip="${escapeHtml(t("modal.tip_mid_server", {}, "Partial hop node: anchors on Priority #1 unless #1 fails, has loss, or exceeds 150ms."))}" aria-label="Info">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                </span>
            </label>
            <div class="dest-test-group" style="display:${lbEnabled ? "none" : "inline-flex"};">
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

    if (lbEnabled) {
        refreshLbBoxState(div);
    }

    return div;
}

export function handleDestTypeChange(selectEl) {
    const row = selectEl.closest(".priority-box");
    if (!row) return;
    const targetInput = row.querySelector(".dest-target");
    const targetCol = row.querySelector(".dest-col-target");
    const portCol = row.querySelector(".dest-col-port");
    const ifaceGroup = row.querySelector(".dest-iface-group");
    const dsrRow = row.querySelector(".dest-dsr-row");
    const ingressGroup = row.querySelector(".dest-ingress-iface-group");
    const snatGroup = row.querySelector(".dest-snat-ip-group");
    const spoofLabel = row.querySelector(".dest-spoof-label");
    const spoofInput = row.querySelector(".dest-spoof-ip");
    const testGroup = row.querySelector(".dest-test-group");
    const lbBar = row.querySelector(".dest-lb-toggle-bar");
    const lbCheck = row.querySelector(".dest-lb-enabled");
    const lbPanel = row.querySelector(".lb-pool-panel");
    const lbModeSelect = row.querySelector(".lb-mode-select");
    const val = selectEl.value;
    const showOutIface = (val === "nftables" || val === "nftables_dsr");
    const showDsrRow = (val === "nftables_dsr" || val === "nftables_dsr_relay");
    const isDsrRelay = (val === "nftables_dsr_relay");
    const lbSupported = isLbSupportedType(val);

    if (lbBar) {
        lbBar.style.display = lbSupported ? "flex" : "none";
    }
    let lbActive = Boolean(lbSupported && lbCheck && lbCheck.checked);
    if (!lbSupported && lbCheck && lbCheck.checked) {
        // Restore first LB target into single-target input before disabling LB
        const firstT = row.querySelector(".lb-member-target")?.value?.trim() || "";
        const firstP = row.querySelector(".lb-member-port")?.value?.trim() || "";
        if (targetInput && !targetInput.value.trim() && firstT) {
            targetInput.value = firstT;
        }
        const singlePortEl = row.querySelector(".dest-port");
        if (singlePortEl && !singlePortEl.value.trim() && firstP) {
            singlePortEl.value = firstP;
        }
        lbCheck.checked = false;
        lbActive = false;
    }

    if (lbPanel) {
        lbPanel.style.display = lbActive ? "block" : "none";
    }
    if (targetCol) {
        targetCol.style.display = lbActive ? "none" : "block";
    }
    if (portCol) {
        portCol.style.display = lbActive ? "none" : "block";
    }
    if (targetInput) {
        targetInput.required = !lbActive;
    }
    if (testGroup) {
        testGroup.style.display = lbActive ? "none" : "inline-flex";
    }
    if (lbModeSelect) {
        const prevMode = lbModeSelect.value;
        lbModeSelect.innerHTML = buildLbModeOptionsHtml(val, prevMode);
    }
    row.querySelectorAll(".lb-member-iface-group").forEach(grp => {
        grp.style.display = (val === "nftables") ? "block" : "none";
    });

    if (ifaceGroup) {
        ifaceGroup.style.display = (showOutIface && !lbActive) ? "block" : "none";
    }
    if (dsrRow) {
        dsrRow.style.display = showDsrRow ? "flex" : "none";
    }
    if (ingressGroup) {
        ingressGroup.style.display = isDsrRelay ? "block" : "none";
    }
    if (snatGroup) {
        snatGroup.style.display = isDsrRelay ? "block" : "none";
    }
    if (spoofLabel) {
        spoofLabel.textContent = isDsrRelay
            ? t("modal.spoof_ip", {}, "Iran / Spoof IP")
            : t("modal.spoof_ip_opt", {}, "Ingress IP (Optional)");
    }
    if (spoofInput) {
        spoofInput.placeholder = isDsrRelay ? "198.51.100.25 (Required)" : "Auto (WAN Interface)";
        spoofInput.required = isDsrRelay;
    }
    if (lbActive) {
        refreshLbBoxState(row);
    }
    if (!targetInput) return;
    if (val === "haproxy") {
        targetInput.placeholder = "2001:db8:cafe::1 (IPv6 only)";
    } else if (val === "nftables_dsr_relay") {
        targetInput.placeholder = "198.51.100.10 (Exit Server IP)";
    } else if (isNftablesType(val)) {
        targetInput.placeholder = "10.88.1.2 (IPv4) or 2001:db8::2 (IPv6)";
    } else {
        targetInput.placeholder = "192.0.2.1 or 2001:db8::1";
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
        const ingressIfaceEl = box.querySelector(".dest-ingress-iface");
        const spoofIpEl = box.querySelector(".dest-spoof-ip");
        const snatIpEl = box.querySelector(".dest-snat-ip");
        const commentEl = box.querySelector(".dest-comment");
        const proxyProtoEl = box.querySelector(".dest-proxy-proto");
        const relayEl = box.querySelector(".dest-is-relay");
        const enabledEl = box.querySelector(".dest-enabled-check");
        const lbCheckEl = box.querySelector(".dest-lb-enabled");
        const lbModeEl = box.querySelector(".lb-mode-select");

        const rawDPort = portEl ? portEl.value.trim() : "";
        const parsedDPort = rawDPort ? parsePortSpec(rawDPort) : null;
        const dType = typeEl ? typeEl.value : "haproxy";
        const rawIface = ifaceEl ? ifaceEl.value.trim() : "";
        const rawIngressIface = ingressIfaceEl ? ingressIfaceEl.value.trim() : "";
        const rawSpoofIp = spoofIpEl ? spoofIpEl.value.trim() : "";
        const rawSnatIp = snatIpEl ? snatIpEl.value.trim() : "";
        const lbEnabled = Boolean(isLbSupportedType(dType) && lbCheckEl && lbCheckEl.checked);

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
        if ((dType === "nftables" || dType === "nftables_dsr") && rawIface) {
            destObj.tunnel_iface = rawIface;
        }
        if ((dType === "nftables_dsr" || dType === "nftables_dsr_relay") && rawSpoofIp) {
            destObj.spoof_ip = rawSpoofIp;
        }
        if (dType === "nftables_dsr_relay") {
            if (rawIngressIface) destObj.ingress_iface = rawIngressIface;
            if (rawSnatIp) destObj.snat_ip = rawSnatIp;
        }
        if (parsedDPort && parsedDPort.rangeStr) {
            destObj.port_range = parsedDPort.rangeStr;
        } else if (rawDPort && !parsedDPort) {
            destObj._invalidPortInput = rawDPort;
        }

        if (lbEnabled) {
            const members = [];
            box.querySelectorAll(".lb-targets-list .lb-target-row").forEach(mRow => {
                const mTarget = mRow.querySelector(".lb-member-target")?.value.trim() || "";
                const rawMPort = mRow.querySelector(".lb-member-port")?.value.trim() || "";
                const parsedMPort = rawMPort ? parsePortSpec(rawMPort) : null;
                const rawW = parseInt(mRow.querySelector(".lb-member-weight")?.value || "1", 10);
                const mWeight = isNaN(rawW) ? 1 : Math.max(1, Math.min(100, rawW));
                const mIface = mRow.querySelector(".lb-member-iface")?.value.trim() || "";
                const mComment = mRow.querySelector(".lb-member-comment")?.value.trim() || "";
                const mEnabled = mRow.querySelector(".lb-member-enabled")?.checked !== false;
                const mObj = {
                    target: mTarget,
                    port: parsedMPort ? parsedMPort.start : null,
                    weight: mWeight,
                    comment: mComment,
                    enabled: mEnabled
                };
                if (dType === "nftables" && mIface) {
                    mObj.tunnel_iface = mIface;
                }
                if (parsedMPort && parsedMPort.rangeStr) {
                    mObj.port_range = parsedMPort.rangeStr;
                } else if (rawMPort && !parsedMPort) {
                    mObj._invalidPortInput = rawMPort;
                }
                members.push(mObj);
            });
            destObj.lb_enabled = true;
            destObj.lb_mode = normalizeLbModeForType(dType, lbModeEl ? lbModeEl.value : "ip_hash");
            destObj.lb_targets = members;
            const firstEn = members.find(m => m.enabled && m.target) || members[0];
            if (firstEn) {
                if (firstEn.target) destObj.target = firstEn.target;
                if (firstEn.port !== null) destObj.port = firstEn.port;
                if (firstEn.port_range) destObj.port_range = firstEn.port_range;
                if (firstEn.tunnel_iface) destObj.tunnel_iface = firstEn.tunnel_iface;
            }
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
                tunnel_iface: dest.tunnel_iface || "",
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
                is_relay: false,
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
        destContainer.addEventListener("click", async (ev) => {
            const addLbBtn = ev.target.closest(".btn-add-lb-target");
            if (addLbBtn) {
                ev.stopPropagation();
                const box = addLbBtn.closest(".priority-box");
                const listEl = box?.querySelector(".lb-targets-list");
                if (!box || !listEl) return;
                const curRows = listEl.querySelectorAll(".lb-target-row");
                if (curRows.length >= 16) return;
                const dType = (box.querySelector(".dest-type")?.value || "nftables").toLowerCase();
                const inboundSpec = getCurrentInboundSpec();
                const isRangeRule = Boolean(inboundSpec && inboundSpec.rangeStr);
                const defPort = inboundSpec ? (inboundSpec.rangeStr || inboundSpec.start) : "";
                const tmp = document.createElement("div");
                tmp.innerHTML = buildLbMemberRowHtml(
                    { target: "", port: defPort, weight: 1, tunnel_iface: "", comment: "", enabled: true },
                    curRows.length,
                    dType,
                    isRangeRule,
                    curRows.length + 1
                );
                if (tmp.firstElementChild) {
                    listEl.appendChild(tmp.firstElementChild);
                    refreshLbBoxState(box);
                }
                return;
            }

            const rmLbBtn = ev.target.closest(".btn-remove-lb-member");
            if (rmLbBtn) {
                ev.stopPropagation();
                const box = rmLbBtn.closest(".priority-box");
                const listEl = box?.querySelector(".lb-targets-list");
                const mRow = rmLbBtn.closest(".lb-target-row");
                if (!box || !listEl || !mRow) return;
                if (listEl.querySelectorAll(".lb-target-row").length <= 2) return;
                mRow.remove();
                refreshLbBoxState(box);
                return;
            }

            const eqBtn = ev.target.closest(".btn-lb-equalize");
            if (eqBtn) {
                ev.stopPropagation();
                const box = eqBtn.closest(".priority-box");
                if (!box) return;
                box.querySelectorAll(".lb-member-weight").forEach(inp => { inp.value = "1"; });
                refreshLbBoxState(box);
                return;
            }

            const testMemberBtn = ev.target.closest(".btn-test-lb-member");
            if (testMemberBtn) {
                ev.stopPropagation();
                const box = testMemberBtn.closest(".priority-box");
                const mRow = testMemberBtn.closest(".lb-target-row");
                if (!box || !mRow) return;
                const dType = (box.querySelector(".dest-type")?.value || "nftables").toLowerCase();
                const target = (mRow.querySelector(".lb-member-target")?.value || "").trim().replace(/^\[|\]$/g, "");
                const rawMPort = (mRow.querySelector(".lb-member-port")?.value || "").trim();
                const listenRaw = document.getElementById("formPort")?.value.trim() || "";
                const parsedP = parsePortSpec(rawMPort || listenRaw);
                const port = parsedP ? parsedP.start : null;
                const mIface = (mRow.querySelector(".lb-member-iface")?.value || "").trim();
                const resEl = mRow.querySelector(".lb-member-test-result");
                const setRes = (kind, txt, title = "") => {
                    if (!resEl) return;
                    const tAttr = title ? ` title="${escapeHtml(title)}"` : "";
                    resEl.innerHTML = `<span class="test-pill is-${kind}"${tAttr}><span class="test-pill-dot"></span><span>${txt}</span></span>`;
                };
                if (!target) {
                    setRes("warn", escapeHtml(t("status.enter_target", {}, "Enter IP")));
                    return;
                }
                if (!port) {
                    setRes("warn", escapeHtml(t("status.enter_port", {}, "Enter port")));
                    return;
                }
                testMemberBtn.disabled = true;
                testMemberBtn.classList.add("is-probing");
                setRes("probing", escapeHtml(t("status.probing", {}, "Probing...")));
                try {
                    const res = await fetch(`${API_BASE}/test-target`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            target,
                            port: parseInt(port, 10),
                            type: dType,
                            tunnel_iface: mIface,
                            protocol: document.getElementById("formProto")?.value || "both",
                            packets: 10
                        })
                    });
                    const data = await res.json().catch(() => ({}));
                    if (res.ok && data.ok) {
                        const loss = data.packet_loss !== undefined ? data.packet_loss : (data.healthy ? 0 : 100);
                        if (data.healthy) {
                            const lat = (data.latency_ms !== null && data.latency_ms !== undefined && data.latency_ms > 0) ? `${data.latency_ms}ms · ${loss}%` : `${loss}%`;
                            setRes("ok", escapeHtml(lat));
                        } else {
                            setRes("fail", `${escapeHtml(t("status.down", {}, "DOWN"))} (${loss}%)`, data.reason || "");
                        }
                    } else {
                        setRes("fail", escapeHtml(data.error || "Error"));
                    }
                } catch (_) {
                    setRes("fail", escapeHtml(t("status.network_error", {}, "Error")));
                } finally {
                    testMemberBtn.disabled = false;
                    testMemberBtn.classList.remove("is-probing");
                }
                return;
            }

            const trigger = ev.target.closest(".iface-select-trigger");
            if (trigger) {
                ev.stopPropagation();
                const ms = trigger.closest(".iface-multiselect");
                if (!ms) return;
                const wasOpen = ms.classList.contains("open");
                document.querySelectorAll(".iface-multiselect.open").forEach(el => el.classList.remove("open"));
                if (!wasOpen) {
                    const mRow = ms.closest(".lb-target-row");
                    const box = ms.closest(".priority-box");
                    const targetVal = mRow
                        ? (mRow.querySelector(".lb-member-target")?.value || "")
                        : ((box && box.querySelector(".dest-target")) ? box.querySelector(".dest-target").value : "");
                    const hidden = ms.parentElement ? ms.parentElement.querySelector("input[type='hidden']") : null;
                    const curVal = (hidden && hidden.value) || "";
                    const menu = ms.querySelector(".iface-dropdown-menu");
                    const isIngress = ms.dataset.autoMode === "ingress";
                    if (menu) menu.innerHTML = buildTunnelIfaceMenuHtml(curVal, isIngress, targetVal);
                    ms.classList.add("open");
                }
                return;
            }
            const opt = ev.target.closest(".iface-option");
            if (!opt) return;
            ev.stopPropagation();
            const ms = opt.closest(".iface-multiselect");
            const grp = ms ? ms.parentElement : null;
            if (!grp || !ms) return;
            const hidden = grp.querySelector("input[type='hidden']");
            const menu = ms.querySelector(".iface-dropdown-menu");
            const triggerText = ms.querySelector(".iface-trigger-text");
            const isIngress = ms.dataset.autoMode === "ingress";
            const clickedVal = opt.dataset.iface || "";
            const prevVal = (hidden && hidden.value) || "";
            const nextVal = (clickedVal && clickedVal === prevVal) ? "" : clickedVal;
            const mRow = ms.closest(".lb-target-row");
            const box = ms.closest(".priority-box");
            const targetVal = mRow
                ? (mRow.querySelector(".lb-member-target")?.value || "")
                : ((box && box.querySelector(".dest-target")) ? box.querySelector(".dest-target").value : "");
            if (hidden) hidden.value = nextVal;
            if (menu) menu.innerHTML = buildTunnelIfaceMenuHtml(nextVal, isIngress, targetVal);
            if (triggerText) triggerText.innerHTML = buildTunnelIfaceTriggerHtml(nextVal, isIngress);
            ms.classList.remove("open");
        });

        destContainer.addEventListener("change", (ev) => {
            if (ev.target.classList?.contains("dest-lb-enabled")) {
                const box = ev.target.closest(".priority-box");
                const typeSel = box?.querySelector(".dest-type");
                if (box && ev.target.checked) {
                    // Seed first LB row from single target if empty
                    const singleT = box.querySelector(".dest-target")?.value.trim() || "";
                    const singleP = box.querySelector(".dest-port")?.value.trim() || "";
                    const singleI = box.querySelector(".dest-tunnel-iface")?.value.trim() || "";
                    const firstRow = box.querySelector(".lb-targets-list .lb-target-row");
                    if (firstRow) {
                        const mT = firstRow.querySelector(".lb-member-target");
                        const mP = firstRow.querySelector(".lb-member-port");
                        const mI = firstRow.querySelector(".lb-member-iface");
                        if (mT && !mT.value.trim() && singleT) mT.value = singleT;
                        if (mP && !mP.value.trim() && singleP) mP.value = singleP;
                        if (mI && !mI.value.trim() && singleI) {
                            mI.value = singleI;
                            const tTxt = firstRow.querySelector(".iface-trigger-text");
                            if (tTxt) tTxt.innerHTML = buildTunnelIfaceTriggerHtml(singleI, false);
                        }
                    }
                }
                if (typeSel) handleDestTypeChange(typeSel);
                return;
            }
            if (ev.target.classList?.contains("lb-mode-select") || ev.target.classList?.contains("lb-member-enabled")) {
                const box = ev.target.closest(".priority-box");
                if (box) refreshLbBoxState(box);
            }
        });

        destContainer.addEventListener("input", (ev) => {
            if (ev.target.classList?.contains("lb-member-weight") || ev.target.classList?.contains("lb-member-target")) {
                const box = ev.target.closest(".priority-box");
                if (box) refreshLbBoxState(box);
            }
            const targetInput = ev.target.closest(".dest-target, .lb-member-target");
            if (!targetInput) return;
            const mRow = targetInput.closest(".lb-target-row");
            const scopeEl = mRow || targetInput.closest(".priority-box");
            if (!scopeEl) return;
            const newTarget = targetInput.value.trim();
            scopeEl.querySelectorAll(".iface-multiselect").forEach(ms => {
                const hidden = ms.parentElement ? ms.parentElement.querySelector("input[type='hidden']") : null;
                const curVal = (hidden && hidden.value) || "";
                const menu = ms.querySelector(".iface-dropdown-menu");
                const isIngress = ms.dataset.autoMode === "ingress";
                if (menu) menu.innerHTML = buildTunnelIfaceMenuHtml(curVal, isIngress, newTarget);
            });
        });
    }

    document.addEventListener("click", (ev) => {
        if (!ev.target.closest(".iface-multiselect")) {
            document.querySelectorAll(".iface-multiselect.open").forEach(el => el.classList.remove("open"));
        }
    });

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

    if (destContainer) {
        destContainer.addEventListener("input", (ev) => {
            if (!ev.target || !ev.target.classList || !ev.target.classList.contains("dest-port")) return;
            const curVal = ev.target.value.trim();
            const parsedIn = parsePortSpec(formPortInput ? formPortInput.value : "");
            const inVal = parsedIn ? String(parsedIn.rangeStr || parsedIn.start) : (formPortInput ? formPortInput.value.trim() : "");
            ev.target.dataset.autoSynced = (curVal === "" || curVal === inVal) ? "true" : "false";
        });
    }

    if (formPortInput) {
        formPortInput.addEventListener("input", () => {
            const rawVal = formPortInput.value.trim();
            const parsed = parsePortSpec(rawVal);
            if (parsed && parsed.excludedPorts) {
                setExcludedTags(parsed.excludedPorts);
            }
            refreshRangeConstraintUI();
            const fillVal = parsed ? String(parsed.rangeStr || parsed.start) : rawVal;
            const portInputs = document.querySelectorAll("#destinationsContainer .dest-port");
            portInputs.forEach(input => {
                const cur = input.value.trim();
                const wasAuto = input.dataset.autoSynced !== "false";
                if (wasAuto && (cur === "" || cur === lastAutoInboundPort)) {
                    input.value = fillVal;
                    input.dataset.autoSynced = "true";
                }
            });
            lastAutoInboundPort = fillVal;
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
                if (d.lb_enabled) {
                    if (!isLbSupportedType(d.type)) {
                        showToast(`Priority #${i + 1}: Load balancing is only supported for NFTables and Nginx`, "error");
                        return;
                    }
                    const members = Array.isArray(d.lb_targets) ? d.lb_targets : [];
                    if (members.length < 2) {
                        showToast(`Priority #${i + 1}: Load-balanced pool requires at least 2 backend IPs`, "error");
                        return;
                    }
                    const seenEps = new Set();
                    const ipVers = new Set();
                    const rangeModes = new Set();
                    let enabledCount = 0;
                    const cleanMembers = [];
                    for (let mIdx = 0; mIdx < members.length; mIdx++) {
                        const m = members[mIdx];
                        if (!m.target || !m.target.trim()) {
                            showToast(`Priority #${i + 1}: Please enter IP/host for backend #${mIdx + 1}`, "error");
                            return;
                        }
                        if (m._invalidPortInput) {
                            showToast(`Priority #${i + 1}: Backend #${mIdx + 1} has invalid port '${m._invalidPortInput}'`, "error");
                            return;
                        }
                        if (d.type === "nftables") {
                            const ver = detectIpVersion(m.target);
                            if (!ver) {
                                showToast(`Priority #${i + 1}: NFTables backend #${mIdx + 1} must be a valid IPv4 or IPv6 address`, "error");
                                return;
                            }
                            ipVers.add(ver);
                            if (ipVers.size > 1) {
                                showToast(t("rules.lb_ip_family_warn", {}, "NFTables LB pool cannot mix IPv4 and IPv6 addresses"), "error");
                                return;
                            }
                        }
                        if (inbound.rangeStr) {
                            if (m.port_range && m.port_range !== inbound.rangeStr) {
                                showToast(`Priority #${i + 1}: Backend #${mIdx + 1} port range must match ${inbound.rangeStr} or be a single port`, "error");
                                return;
                            }
                            rangeModes.add((m.port_range || m.port === null) ? "range" : "fixed");
                            if (rangeModes.size > 1) {
                                showToast(`Priority #${i + 1}: Range pool members must all use 1:1 range or all target a single port`, "error");
                                return;
                            }
                        } else if (m.port_range) {
                            showToast(`Priority #${i + 1}: Backend #${mIdx + 1} port range requires an inbound range`, "error");
                            return;
                        }
                        const effPortKey = m.port_range || m.port || (inbound.rangeStr || inbound.start);
                        const epKey = `${m.target.trim().toLowerCase()}:${effPortKey}`;
                        if (seenEps.has(epKey)) {
                            showToast(`Priority #${i + 1}: Duplicate backend '${epKey}' in pool`, "error");
                            return;
                        }
                        seenEps.add(epKey);
                        if (m.enabled !== false) enabledCount += 1;
                        const cleanM = { ...m };
                        delete cleanM._invalidPortInput;
                        cleanMembers.push(cleanM);
                    }
                    if (enabledCount < 1) {
                        showToast(`Priority #${i + 1}: At least 1 backend in the LB pool must be enabled`, "error");
                        return;
                    }
                    const cleanDest = { ...d, lb_targets: cleanMembers };
                    delete cleanDest._invalidPortInput;
                    sanitizedDests.push(cleanDest);
                    continue;
                }
                if (!d.target || !d.target.trim()) {
                    showToast(`Please enter target IP for Priority #${i + 1}`, "error");
                    return;
                }
                if (d._invalidPortInput) {
                    showToast(`Priority #${i + 1} has an invalid target port '${d._invalidPortInput}'`, "error");
                    return;
                }
                if (d.type === "nftables_dsr") {
                    const portMismatch = inbound.rangeStr
                        ? (d.port !== null && !d.port_range)
                        : (d.port !== null && d.port !== inbound.start);
                    if (portMismatch) {
                        showToast(`Priority #${i + 1} (NFTables DSR) requires destination port to match inbound port (${inbound.rangeStr || inbound.start})`, "error");
                        return;
                    }
                }
                if (d.type === "nftables_dsr_relay" && (!d.spoof_ip || !d.spoof_ip.trim())) {
                    showToast(`Priority #${i + 1} (NFTables DSR Relay) requires Iran / Spoof IP`, "error");
                    return;
                }
                if (inbound.rangeStr) {
                    if (!isNftablesType(d.type)) {
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
