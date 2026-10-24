// ============================================================================
// XForwarder Web UI - Host Telemetry & Topology Renderer (Native ES Module)
// ============================================================================

import { formatBytes, formatTrafficMB, escapeHtml, showToast } from "./utils.js";
import { lastTrafficData } from "./state.js";

export function renderSystemStats(sys) {
    if (!sys) return;

    const cpuText = document.getElementById("cpuText");
    const ramText = document.getElementById("ramText");
    const loadText = document.getElementById("loadText");
    const trafficText = document.getElementById("trafficText");
    const connsText = document.getElementById("connsText");
    const ovTrafficText = document.getElementById("ovTrafficText");

    if (cpuText) {
        cpuText.innerText = `${Math.round(Number(sys.cpu_percent) || 0)}%`;
    }

    if (ramText) {
        const used = Math.round(Number(sys.ram_used_mb) || 0);
        const total = Math.round(Number(sys.ram_total_mb) || 0);
        const pct = Math.round(Number(sys.ram_percent) || 0);
        ramText.innerHTML = `<span class="ram-full">${used}/${total} MB (${pct}%)</span><span class="ram-short">${pct}%</span>`;
    }

    if (loadText && sys.load_avg) {
        const l1 = Number(sys.load_avg[0] || 0).toFixed(2);
        loadText.innerText = l1;
    }

    if (trafficText) {
        const rRx = (Number(sys.net_rx_rate_bytes || 0) / (1024 * 1024)).toFixed(2);
        const rTx = (Number(sys.net_tx_rate_bytes || 0) / (1024 * 1024)).toFixed(2);
        const rxMb = formatTrafficMB(sys.net_rx_bytes);
        const txMb = formatTrafficMB(sys.net_tx_bytes);

        if (window._trafficModeRate) {
            trafficText.innerText = `↓ ${rRx} MB/s · ↑ ${rTx} MB/s`;
        } else {
            trafficText.innerText = `↓ ${rxMb} MB · ↑ ${txMb} MB`;
        }
    }

    if (connsText) {
        const tcp = Number(sys.established_conns_tcp || 0);
        const udp = Number(sys.active_conns_udp || 0);
        connsText.innerText = `${tcp} TCP · ${udp} UDP`;
    }

    if (ovTrafficText && sys.net_rx_bytes !== undefined) {
        ovTrafficText.innerText = `↓ ${formatBytes(sys.net_rx_bytes)} · ↑ ${formatBytes(sys.net_tx_bytes)}`;
    }
}

export function renderServicesStatus(services) {
    if (!services) return;

    const dotNft = document.getElementById("svcDotNft");
    const dotHaproxy = document.getElementById("svcDotHaproxy");
    const dotNginx = document.getElementById("svcDotNginx");

    if (dotNft) {
        const active = services.nftables && services.nftables.active;
        dotNft.className = `status-dot ${active ? 'dot-active' : 'dot-inactive'}`;
    }
    if (dotHaproxy) {
        const active = services.haproxy && services.haproxy.active;
        dotHaproxy.className = `status-dot ${active ? 'dot-active' : 'dot-inactive'}`;
    }
    if (dotNginx) {
        const active = services.nginx && services.nginx.active;
        dotNginx.className = `status-dot ${active ? 'dot-active' : 'dot-inactive'}`;
    }
}

export function renderStats(rules, runtime) {
    const statTotalRules = document.getElementById("statTotalRules");
    const statActiveHaproxy = document.getElementById("statActiveHaproxy");
    const statActiveNftables = document.getElementById("statActiveNftables");
    const filterCountAll = document.getElementById("filterCountAll");
    const filterCountP1 = document.getElementById("filterCountP1");
    const filterCountP2 = document.getElementById("filterCountP2");
    const filterCountDown = document.getElementById("filterCountDown");

    if (!rules || !statTotalRules) return;
    statTotalRules.innerText = rules.length;

    let haproxyCount = 0;
    let nginxCount = 0;
    let nftablesCount = 0;

    let p1ActiveCount = 0;
    let p2ActiveCount = 0;
    let downCount = 0;

    const rulesState = (runtime && runtime.rules_state) ? runtime.rules_state : {};

    rules.forEach(r => {
        const activePrio = r.active_priority || 1;
        const dest = (r.destinations || []).find(d => d.priority === activePrio) || (r.destinations || [])[0];
        if (dest) {
            if (dest.type === "haproxy") haproxyCount++;
            if (dest.type === "nginx") nginxCount++;
            if (dest.type === "nftables") nftablesCount++;
        }

        const rId = String(r.id || `rule-${r.port}`);
        const rState = rulesState[rId] || {};
        const destStats = rState.dest_stats || {};
        const activeStat = destStats[`prio_${activePrio}`] || {};
        const isHealthy = (activeStat.status === 'healthy');

        if (activePrio === 1 && isHealthy) {
            p1ActiveCount++;
        } else if (activePrio > 1) {
            p2ActiveCount++;
        } else {
            downCount++;
        }
    });

    const totalProxies = haproxyCount + nginxCount;
    if (statActiveHaproxy) {
        statActiveHaproxy.innerText = totalProxies;
        const proxyDetailEl = document.getElementById("statActiveProxyDetail");
        if (proxyDetailEl) {
            if (nginxCount > 0 && haproxyCount > 0) {
                proxyDetailEl.innerText = `${haproxyCount} HA · ${nginxCount} Nginx`;
                proxyDetailEl.style.display = "block";
                statActiveHaproxy.title = `${haproxyCount} via HAProxy, ${nginxCount} via Nginx`;
            } else if (nginxCount > 0) {
                proxyDetailEl.innerText = `${nginxCount} Nginx`;
                proxyDetailEl.style.display = "block";
                statActiveHaproxy.title = `${nginxCount} via Nginx`;
            } else {
                proxyDetailEl.style.display = "none";
                statActiveHaproxy.title = `${haproxyCount} via HAProxy`;
            }
        }
    }

    if (statActiveNftables) statActiveNftables.innerText = nftablesCount;

    if (filterCountAll) filterCountAll.innerText = rules.length;
    if (filterCountP1) filterCountP1.innerText = p1ActiveCount;
    if (filterCountP2) filterCountP2.innerText = p2ActiveCount;
    if (filterCountDown) filterCountDown.innerText = downCount;

    const navRulesCount = document.getElementById("navRulesCount");
    if (navRulesCount) navRulesCount.innerText = rules.length;

    const ovHaproxyCount = document.getElementById("ovHaproxyCount");
    if (ovHaproxyCount) ovHaproxyCount.innerText = `${haproxyCount} rules`;

    const ovNftablesCount = document.getElementById("ovNftablesCount");
    if (ovNftablesCount) ovNftablesCount.innerText = `${nftablesCount} rules`;

    const svcHaproxyBinds = document.getElementById("svcHaproxyBinds");
    if (svcHaproxyBinds) svcHaproxyBinds.innerText = `${haproxyCount} ports`;
}

export function renderNetworkTopology(network) {
    if (!network) return;

    const wanTag = document.getElementById("wanIfaceTag");
    if (wanTag) {
        wanTag.innerText = network.primary_interface || "eth0";
    }

    const serverIpsList = document.getElementById("serverIpsList");
    if (serverIpsList) {
        const ips = network.server_ips || [];
        if (ips.length === 0) {
            serverIpsList.innerHTML = `<span class="ip-pill-empty">No public WAN IP detected</span>`;
        } else {
            serverIpsList.innerHTML = ips.map(s => `
                <div class="server-ip-pill" title="Click to copy IP">
                    <span class="ip-ver-badge ${s.version === 6 ? 'ver-6' : 'ver-4'}">IPv${s.version}</span>
                    <span class="ip-address-text">${escapeHtml(s.ip)}</span>
                    <button type="button" class="btn-copy-ip" onclick="copyIpToClipboard('${escapeHtml(s.ip)}', this)" title="Copy ${escapeHtml(s.ip)}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                </div>
            `).join("");
        }
    }

    const tunnelGrid = document.getElementById("tunnelGrid");
    const rawTunnels = network.tunnel_interfaces || [];

    const ignoredIfaces = new Set([
        "lo", "gre0", "gretap0", "erspan0", "tunl0", "sit0",
        "ip6tnl0", "ip6gre0", "ip6erspan0", "dummy0", "teql0"
    ]);
    const tunnels = rawTunnels.filter(t => {
        if (!t || !t.name) return false;
        const name = String(t.name).toLowerCase().trim();
        if (ignoredIfaces.has(name)) return false;
        if (name.startsWith("veth") || name.startsWith("docker") || name.startsWith("br-") || name.startsWith("virbr")) return false;
        return true;
    });

    if (tunnelGrid) {
        if (tunnels.length === 0) {
            tunnelGrid.innerHTML = `
                <div class="tunnel-empty-box">
                    <div class="tunnel-empty-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
                    </div>
                    <div>
                        <span class="empty-title">No secondary tunnel interfaces detected</span>
                        <span class="empty-sub">Tunnel interfaces (e.g. <code>ipip1</code>, <code>gre1</code>, <code>awg0</code>) will appear here automatically with real-time ping probes.</span>
                    </div>
                </div>
            `;
        } else {
            tunnelGrid.innerHTML = tunnels.map(t => {
                const isUp = t.state === "UP";
                let pingClass = "lat-down";
                let pingText = "Interface Down";
                if (isUp) {
                    if (t.reachable && t.latency_ms !== null && t.latency_ms > 0) {
                        pingClass = t.latency_ms < 60 ? "lat-good" : (t.latency_ms < 150 ? "lat-mid" : "lat-high");
                        pingText = `${t.latency_ms} ms`;
                    } else if (t.target_to_ping) {
                        pingClass = "lat-unreachable";
                        pingText = "Unreachable";
                    } else {
                        pingClass = "lat-down";
                        pingText = "No Peer Target";
                    }
                }

                const tName = String(t.name || "");
                const tTraffic = (lastTrafficData && lastTrafficData.tunnels) ? lastTrafficData.tunnels[tName] : null;
                const tTrafficHtml = tTraffic ? `
                    <div class="tunnel-traffic-bar">
                        <div class="tunnel-traffic-info">
                            <span class="tunnel-traffic-label">Cycle:</span>
                            <span class="tunnel-traffic-val font-mono">${formatBytes(tTraffic.cycle_total)}</span>
                            <span class="tunnel-traffic-sub font-mono">↑ ${formatBytes(tTraffic.cycle_rx)} · ↓ ${formatBytes(tTraffic.cycle_tx)}</span>
                        </div>
                        <div class="tunnel-traffic-actions">
                            <button type="button" class="btn-tunnel-traffic" onclick="openTrafficModal('tunnel', '${escapeHtml(tName)}')" title="View Tunnel Bandwidth Analytics">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                                <span>Stats</span>
                            </button>
                            <button type="button" class="btn-tunnel-traffic btn-reset" onclick="promptResetTraffic('tunnel', '${escapeHtml(tName)}')" title="Reset Billing Cycle">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                            </button>
                        </div>
                    </div>
                ` : '';

                return `
                    <div class="tunnel-card ${isUp ? 'is-up' : 'is-down'}">
                        <div class="tunnel-card-top">
                            <div class="tunnel-title-row">
                                <span class="tunnel-name">${escapeHtml(t.name)}</span>
                                <span class="tunnel-type-tag">${escapeHtml(t.type)}</span>
                            </div>
                            <span class="tunnel-status-pill ${isUp ? 'pill-online' : 'pill-offline'}">
                                <span class="pill-dot"></span>
                                ${t.state}
                            </span>
                        </div>
                        <div class="tunnel-body">
                            <div class="tunnel-ip-row">
                                <span class="tunnel-label">Interface IP:</span>
                                <span class="tunnel-val">${escapeHtml(t.ip)}</span>
                            </div>
                            ${t.peer_ip ? `
                            <div class="tunnel-ip-row">
                                <span class="tunnel-label">Peer Endpoint:</span>
                                <span class="tunnel-val text-cyan">${escapeHtml(t.peer_ip)}</span>
                            </div>` : ""}
                        </div>
                        ${tTrafficHtml}
                        <div class="tunnel-card-footer">
                            <div class="tunnel-ping-pill ${pingClass}" title="Real-time roundtrip latency probe">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                                <span>${pingText}</span>
                            </div>
                            <span class="tunnel-mtu-tag">MTU ${t.mtu || 1500}</span>
                        </div>
                    </div>
                `;
            }).join("");
        }
    }
}

export function copyIpToClipboard(ipText, btnEl) {
    if (!ipText) return;
    navigator.clipboard.writeText(ipText).then(() => {
        showToast(`IP ${ipText} copied to clipboard!`, "success");
        if (btnEl) {
            btnEl.classList.add("copied");
            setTimeout(() => btnEl.classList.remove("copied"), 1200);
        }
    }).catch(() => {
        showToast("Failed to copy IP", "warning");
    });
}
