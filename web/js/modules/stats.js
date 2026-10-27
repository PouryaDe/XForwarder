// ============================================================================
// XForwarder Web UI - Host Telemetry & Topology Renderer (Native ES Module)
// ============================================================================

import { formatBytes, formatTrafficMB, formatEngineVersion, escapeHtml, showToast } from "./utils.js";
import { lastTrafficData } from "./state.js";

export let _trafficModeRate = true;
if (typeof window !== "undefined") {
    window._trafficModeRate = true;
}
export let lastSystemStats = null;

export function renderSystemStats(sys) {
    if (!sys) return;
    lastSystemStats = sys;

    const cpuText = document.getElementById("cpuText");
    const ramText = document.getElementById("ramText");
    const ramPill = document.getElementById("ramPill");
    const loadText = document.getElementById("loadText");
    const loadPill = document.getElementById("loadPill");
    const trafficText = document.getElementById("trafficText");
    const trafficPill = document.getElementById("trafficPill");
    const connsText = document.getElementById("connsText");
    const connsPill = document.getElementById("connsPill");
    const ovTrafficText = document.getElementById("ovTrafficText");

    // 1. CPU Usage
    if (sys.cpu_percent !== undefined) {
        const cpuPct = Number(sys.cpu_percent) || 0;
        if (cpuText) cpuText.textContent = `CPU: ${cpuPct}%`;
        const ovCpuText = document.getElementById("ovCpuText");
        const ovCpuBar = document.getElementById("ovCpuBar");
        if (ovCpuText) ovCpuText.innerText = `${cpuPct}%`;
        if (ovCpuBar) ovCpuBar.style.width = `${Math.min(100, Math.max(0, cpuPct))}%`;

        // Graphical Circular SVG Ring & Badge
        const ovCpuRing = document.getElementById("ovCpuRing");
        if (ovCpuRing) {
            // Circumference of r=18 is ~113.1
            const offset = 113.1 * (1 - Math.min(100, Math.max(0, cpuPct)) / 100);
            ovCpuRing.style.strokeDashoffset = offset;
            if (cpuPct > 80) {
                ovCpuRing.style.stroke = "var(--accent-rose)";
            } else if (cpuPct > 55) {
                ovCpuRing.style.stroke = "var(--accent-amber)";
            } else {
                ovCpuRing.style.stroke = "var(--accent-cyan)";
            }
        }
        const ovCpuVal = document.getElementById("ovCpuVal");
        if (ovCpuVal) ovCpuVal.innerText = `${cpuPct}%`;

        const ovCpuBadge = document.getElementById("ovCpuBadge");
        if (ovCpuBadge) {
            if (cpuPct > 80) {
                ovCpuBadge.innerText = "Heavy";
                ovCpuBadge.className = "telemetry-badge text-rose";
            } else if (cpuPct > 55) {
                ovCpuBadge.innerText = "Elevated";
                ovCpuBadge.className = "telemetry-badge text-amber";
            } else {
                ovCpuBadge.innerText = "Normal";
                ovCpuBadge.className = "telemetry-badge text-cyan";
            }
        }
    }

    // 2. RAM Usage
    if (sys.ram_total_mb > 0) {
        const used = Number(sys.ram_used_mb) || 0;
        const total = Number(sys.ram_total_mb) || 0;
        const pct = Number(sys.ram_percent) || 0;
        if (ramText) ramText.innerHTML = `<span class="ram-full">RAM: ${pct}%</span><span class="ram-short">${pct}%</span>`;
        if (ramPill) ramPill.title = `Memory Usage: ${used} MB / ${total} MB (${pct}%)`;

        const ovRamText = document.getElementById("ovRamText");
        const ovRamBar = document.getElementById("ovRamBar");
        if (ovRamText) ovRamText.innerText = `${used} / ${total} MB (${pct}%)`;
        if (ovRamBar) {
            ovRamBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
            if (pct > 85) {
                ovRamBar.style.background = "var(--accent-rose)";
            } else if (pct > 70) {
                ovRamBar.style.background = "var(--accent-amber)";
            } else {
                ovRamBar.style.background = "var(--accent-emerald)";
            }
        }

        const ovRamPctChip = document.getElementById("ovRamPctChip");
        if (ovRamPctChip) ovRamPctChip.innerText = `${pct}%`;

        const ovRamBadge = document.getElementById("ovRamBadge");
        if (ovRamBadge) {
            if (pct > 85) {
                ovRamBadge.innerText = "Critical";
                ovRamBadge.className = "telemetry-badge text-rose";
            } else if (pct > 70) {
                ovRamBadge.innerText = "Elevated";
                ovRamBadge.className = "telemetry-badge text-amber";
            } else {
                ovRamBadge.innerText = "Optimal";
                ovRamBadge.className = "telemetry-badge text-emerald";
            }
        }
    }

    // 3. System Load Average
    if (loadText) {
        const l1 = sys.load_str || (sys.load_1 !== undefined ? Number(sys.load_1).toFixed(2) : "--");
        loadText.textContent = `Load: ${l1}`;
        if (loadPill) {
            const l5 = sys.load_5 !== undefined ? Number(sys.load_5).toFixed(2) : "--";
            const l15 = sys.load_15 !== undefined ? Number(sys.load_15).toFixed(2) : "--";
            loadPill.title = `System Load Average: ${l1} (1m), ${l5} (5m), ${l15} (15m)`;
        }
        const ovLoadText = document.getElementById("ovLoadText");
        if (ovLoadText) {
            const l5 = sys.load_5 !== undefined ? Number(sys.load_5).toFixed(2) : "--";
            const l15 = sys.load_15 !== undefined ? Number(sys.load_15).toFixed(2) : "--";
            ovLoadText.textContent = `${l1} (1m), ${l5} (5m), ${l15} (15m)`;
        }

        // Graphical 3-tier visual load bars
        const val1 = Number(sys.load_1) || 0;
        const val5 = Number(sys.load_5) || 0;
        const val15 = Number(sys.load_15) || 0;
        const b1 = document.getElementById("ovLoadBar1m");
        const b5 = document.getElementById("ovLoadBar5m");
        const b15 = document.getElementById("ovLoadBar15m");
        if (b1) b1.style.height = `${Math.min(100, Math.max(8, Math.round(val1 * 35)))}%`;
        if (b5) b5.style.height = `${Math.min(100, Math.max(8, Math.round(val5 * 35)))}%`;
        if (b15) b15.style.height = `${Math.min(100, Math.max(8, Math.round(val15 * 35)))}%`;

        const ovLoadBadge = document.getElementById("ovLoadBadge");
        if (ovLoadBadge) {
            if (val1 > 3.0) {
                ovLoadBadge.innerText = "Heavy";
                ovLoadBadge.className = "telemetry-badge text-rose";
            } else if (val1 > 1.5) {
                ovLoadBadge.innerText = "Elevated";
                ovLoadBadge.className = "telemetry-badge text-amber";
            } else {
                ovLoadBadge.innerText = "Balanced";
                ovLoadBadge.className = "telemetry-badge text-emerald";
            }
        }
    }

    // 4. Live Network Bandwidth (strictly download/upload speed per second in MB/s by default)
    if (trafficText) {
        function formatTrafficMB(rawMb) {
            if (rawMb === undefined || rawMb === null || isNaN(rawMb)) return "0.00";
            const num = Number(rawMb);
            if (num < 10) return num.toFixed(2);
            if (num < 100) return num.toFixed(1);
            return Math.round(num).toLocaleString();
        }

        const rawRateRx = sys.net_rx_rate_mb !== undefined ? sys.net_rx_rate_mb : (sys.net_rx_rate_kb ? sys.net_rx_rate_kb / 1024 : 0);
        const rawRateTx = sys.net_tx_rate_mb !== undefined ? sys.net_tx_rate_mb : (sys.net_tx_rate_kb ? sys.net_tx_rate_kb / 1024 : 0);
        const rRx = formatTrafficMB(rawRateRx);
        const rTx = formatTrafficMB(rawRateTx);
        const rxMb = formatTrafficMB(sys.net_rx_mb);
        const txMb = formatTrafficMB(sys.net_tx_mb);

        if (_trafficModeRate) {
            trafficText.textContent = `↓ ${rRx} MB/s · ↑ ${rTx} MB/s`;
        } else {
            trafficText.textContent = `↓ ${rxMb} MB · ↑ ${txMb} MB`;
        }

        if (ovTrafficText) {
            ovTrafficText.textContent = `↓ ${rRx} MB/s · ↑ ${rTx} MB/s`;
        }

        // Graphical Network Speed Visual Bars
        const netRxFill = document.getElementById("ovNetRxFill");
        const netTxFill = document.getElementById("ovNetTxFill");
        const netRxSpeed = document.getElementById("ovNetRxSpeed");
        const netTxSpeed = document.getElementById("ovNetTxSpeed");
        if (netRxFill) netRxFill.style.width = `${Math.min(100, Math.max(4, Math.round((Number(rawRateRx) / 25) * 100)))}%`;
        if (netTxFill) netTxFill.style.width = `${Math.min(100, Math.max(4, Math.round((Number(rawRateTx) / 25) * 100)))}%`;
        if (netRxSpeed) netRxSpeed.textContent = _trafficModeRate ? `${rRx} MB/s` : `${rxMb} MB`;
        if (netTxSpeed) netTxSpeed.textContent = _trafficModeRate ? `${rTx} MB/s` : `${txMb} MB`;

        const ovTrafficRateBadge = document.getElementById("ovTrafficRateBadge");
        if (ovTrafficRateBadge) {
            ovTrafficRateBadge.textContent = _trafficModeRate ? "Live MB/s" : "Total MB";
        }

        if (trafficPill) {
            const modeTip = _trafficModeRate ? "Mode: Live Speed (Click to view Total MB)" : "Mode: Total MB (Click to view Live MB/s)";
            trafficPill.title = `Live Bandwidth: ↓ ${rRx} MB/s, ↑ ${rTx} MB/s | Total Cumulative: ↓ ${rxMb} MB, ↑ ${txMb} MB (${modeTip})`;
            if (!trafficPill._hasToggle) {
                trafficPill._hasToggle = true;
                trafficPill.style.cursor = "pointer";
                trafficPill.addEventListener("click", () => {
                    _trafficModeRate = !_trafficModeRate;
                    if (typeof window !== "undefined") window._trafficModeRate = _trafficModeRate;
                    if (lastSystemStats) renderSystemStats(lastSystemStats);
                });
            }
        }
    }

    // 5. Active Sockets (TCP & UDP)
    if (connsText) {
        const tcpVal = sys.tcp_connections !== undefined ? sys.tcp_connections : (sys.established_conns_tcp !== undefined ? sys.established_conns_tcp : "--");
        const udpVal = sys.udp_connections !== undefined ? sys.udp_connections : (sys.active_conns_udp !== undefined ? sys.active_conns_udp : "--");
        const tcp = typeof tcpVal === "number" ? tcpVal.toLocaleString() : tcpVal;
        const udp = typeof udpVal === "number" ? udpVal.toLocaleString() : udpVal;
        connsText.textContent = `${tcp} TCP · ${udp} UDP`;

        if (connsPill) {
            connsPill.title = `Active Sockets: ${tcp} TCP connections, ${udp} UDP connections`;
        }
        const ovConnsText = document.getElementById("ovConnsText");
        if (ovConnsText) {
            ovConnsText.textContent = `${tcp} TCP · ${udp} UDP`;
        }

        // Graphical Socket Ratio Split
        const tcpNum = Number(tcpVal) || 0;
        const udpNum = Number(udpVal) || 0;
        const totalConns = tcpNum + udpNum;
        const tcpSeg = document.getElementById("ovSocketTcpSeg");
        const udpSeg = document.getElementById("ovSocketUdpSeg");
        const ovTcpCount = document.getElementById("ovTcpCount");
        const ovUdpCount = document.getElementById("ovUdpCount");
        if (tcpSeg && udpSeg) {
            const tcpPct = totalConns > 0 ? Math.round((tcpNum / totalConns) * 100) : 50;
            const udpPct = 100 - tcpPct;
            tcpSeg.style.width = `${tcpPct}%`;
            udpSeg.style.width = `${udpPct}%`;
        }
        if (ovTcpCount) ovTcpCount.innerText = tcp;
        if (ovUdpCount) ovUdpCount.innerText = udp;
    }
}

export function renderServicesStatus(services) {
    if (!services) return;

    const nft = services.nftables || {};
    const ha = services.haproxy || {};
    const ngx = services.nginx || {};

    // 1. Relay Engines status pills
    const dotNft = document.getElementById("svcDotNft");
    const valNft = document.getElementById("svcValNft");
    if (dotNft && valNft) {
        if (!nft.installed) {
            dotNft.className = "svc-pill-dot dot-rose";
            valNft.innerText = "Not Installed";
            valNft.className = "svc-pill-val text-rose";
            valNft.title = "";
        } else if (nft.active) {
            dotNft.className = "svc-pill-dot dot-emerald";
            const nftVerShort = formatEngineVersion(nft.version);
            const verStr = nftVerShort ? ` (${nftVerShort})` : "";
            valNft.innerText = nft.table_active ? `Active & Synced${verStr}` : `Active${verStr}`;
            valNft.className = "svc-pill-val";
            valNft.title = nft.version || "";
        } else {
            dotNft.className = "svc-pill-dot dot-amber";
            valNft.innerText = "Inactive";
            valNft.className = "svc-pill-val text-muted";
            valNft.title = "";
        }
    }

    const dotHa = document.getElementById("svcDotHaproxy");
    const valHa = document.getElementById("svcValHaproxy");
    if (dotHa && valHa) {
        const haVerShort = formatEngineVersion(ha.version);
        if (!ha.installed) {
            dotHa.className = "svc-pill-dot dot-rose";
            valHa.innerText = "Not Installed";
            valHa.className = "svc-pill-val text-rose";
            valHa.title = "";
        } else if (ha.active) {
            dotHa.className = "svc-pill-dot dot-emerald";
            valHa.innerText = haVerShort ? `Running (${haVerShort})` : "Running";
            valHa.className = "svc-pill-val";
            valHa.title = ha.version || "";
        } else {
            dotHa.className = "svc-pill-dot dot-amber";
            valHa.innerText = haVerShort ? `Standby (${haVerShort})` : "Standby";
            valHa.className = "svc-pill-val text-muted";
            valHa.title = ha.version || "";
        }
    }

    const dotNgx = document.getElementById("svcDotNginx");
    const valNgx = document.getElementById("svcValNginx");
    if (dotNgx && valNgx) {
        const ngxVerShort = formatEngineVersion(ngx.version);
        if (!ngx.installed) {
            dotNgx.className = "svc-pill-dot dot-rose";
            valNgx.innerText = "Not Installed";
            valNgx.className = "svc-pill-val text-rose";
            valNgx.title = "";
        } else if (ngx.active) {
            dotNgx.className = "svc-pill-dot dot-emerald";
            valNgx.innerText = ngxVerShort ? `Running (${ngxVerShort})` : "Running";
            valNgx.className = "svc-pill-val";
            valNgx.title = ngx.version || "";
        } else {
            dotNgx.className = "svc-pill-dot dot-amber";
            valNgx.innerText = ngxVerShort ? `Standby (${ngxVerShort})` : "Standby";
            valNgx.className = "svc-pill-val text-muted";
            valNgx.title = ngx.version || "";
        }
    }

    // 2. Missing Services Warning Banner
    const warningBanner = document.getElementById("servicesWarningBanner");
    const warningText = document.getElementById("servicesWarningText");
    const missing = [];
    if (!nft.installed) missing.push("NFTables");
    if (!ha.installed) missing.push("HAProxy");
    if (!ngx.installed) missing.push("Nginx");

    if (warningBanner && warningText) {
        if (missing.length > 0 && !sessionStorage.getItem("xfwd_dismiss_services_warning")) {
            warningText.innerText = `The following core packages are missing on this server: ${missing.join(", ")}. Run 'xfwd' in your server terminal or reinstall to auto-configure them.`;
            warningBanner.style.display = "flex";
        } else {
            warningBanner.style.display = "none";
        }

        const btnDismissServicesWarning = document.getElementById("btnDismissServicesWarning");
        if (btnDismissServicesWarning && !btnDismissServicesWarning._xfwdBound) {
            btnDismissServicesWarning._xfwdBound = true;
            btnDismissServicesWarning.addEventListener("click", () => {
                sessionStorage.setItem("xfwd_dismiss_services_warning", "1");
                warningBanner.style.display = "none";
            });
        }
    }

    // 3. Top Relay Active Badge in 2-column header
    const topRelayBadge = document.getElementById("topRelayActiveBadge");
    if (topRelayBadge) {
        if (missing.length > 0) {
            topRelayBadge.className = "stat-badge badge-warn";
            topRelayBadge.innerText = `${3 - missing.length}/3 ACTIVE`;
        } else {
            topRelayBadge.className = "stat-badge badge-active";
            topRelayBadge.innerText = "ALL ACTIVE";
        }
    }

    // 4. Fallback items (if present in DOM)
    const ovNftStatus = document.getElementById("ovNftStatus");
    if (ovNftStatus) {
        const nftVerShort = formatEngineVersion(nft.version);
        if (!nft.installed) {
            ovNftStatus.innerHTML = `<span class="text-rose">Not Installed</span>`;
            ovNftStatus.title = "";
        } else if (nft.active) {
            ovNftStatus.innerHTML = `<span class="text-emerald">Active (${nftVerShort || "Installed"})</span>`;
            ovNftStatus.title = nft.version || "";
        } else {
            ovNftStatus.innerHTML = `<span class="text-amber">Inactive</span>`;
            ovNftStatus.title = "";
        }
    }

    const ovHaproxyStatus = document.getElementById("ovHaproxyStatus");
    if (ovHaproxyStatus) {
        const haVerShort = formatEngineVersion(ha.version);
        if (!ha.installed) {
            ovHaproxyStatus.innerHTML = `<span class="text-rose">Not Installed</span>`;
            ovHaproxyStatus.title = "";
        } else if (ha.active) {
            ovHaproxyStatus.innerHTML = `<span class="text-emerald">Running (${haVerShort || "v?"})</span>`;
            ovHaproxyStatus.title = ha.version || "";
        } else {
            ovHaproxyStatus.innerHTML = `<span class="text-amber">Standby (${haVerShort || "v?"})</span>`;
            ovHaproxyStatus.title = ha.version || "";
        }
    }

    const ovNginxStatus = document.getElementById("ovNginxStatus");
    if (ovNginxStatus) {
        const ngxVerShort = formatEngineVersion(ngx.version);
        if (!ngx.installed) {
            ovNginxStatus.innerHTML = `<span class="text-rose">Not Installed</span>`;
            ovNginxStatus.title = "";
        } else if (ngx.active) {
            ovNginxStatus.innerHTML = `<span class="text-emerald">Running (${ngxVerShort || "v?"})</span>`;
            ovNginxStatus.title = ngx.version || "";
        } else {
            ovNginxStatus.innerHTML = `<span class="text-amber">Standby (${ngxVerShort || "v?"})</span>`;
            ovNginxStatus.title = ngx.version || "";
        }
    }

    const ovEnginesSummaryBadge = document.getElementById("ovEnginesSummaryBadge");
    if (ovEnginesSummaryBadge) {
        if (missing.length === 0) {
            ovEnginesSummaryBadge.className = "stat-badge badge-active";
            ovEnginesSummaryBadge.innerText = "READY";
        } else {
            ovEnginesSummaryBadge.className = "stat-badge badge-warn";
            ovEnginesSummaryBadge.innerText = `${3 - missing.length}/3 READY`;
        }
    }
}

export function renderStats(rules, runtime, traffic) {
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

    // 6. Traffic (24h) Stat Card
    const statTrafficTotal = document.getElementById("statTrafficTotal");
    const statTrafficSubtext = document.getElementById("statTrafficSubtext");
    const tData = traffic || lastTrafficData;
    if (statTrafficTotal) {
        if (tData) {
            const totalBytes = tData.total_bytes !== undefined ? tData.total_bytes : (tData.cycle_bytes || 0);
            const rxBytes = tData.total_rx !== undefined ? tData.total_rx : (tData.rx_bytes || 0);
            const txBytes = tData.total_tx !== undefined ? tData.total_tx : (tData.tx_bytes || 0);
            statTrafficTotal.textContent = formatBytes(totalBytes);
            if (statTrafficSubtext) {
                statTrafficSubtext.innerHTML = `<span class="text-cyan">↓ ${formatBytes(rxBytes)}</span> &middot; <span class="text-mint">↑ ${formatBytes(txBytes)}</span>`;
            }
        } else {
            statTrafficTotal.textContent = "0 B";
            if (statTrafficSubtext) {
                statTrafficSubtext.innerHTML = `<span class="text-cyan">↓ 0 B</span> &middot; <span class="text-mint">↑ 0 B</span>`;
            }
        }
    }
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
                const encodedTName = encodeURIComponent(tName).replace(/'/g, "%27");
                const tTraffic = (lastTrafficData && lastTrafficData.tunnels) ? lastTrafficData.tunnels[tName] : null;
                const tTrafficHtml = tTraffic ? `
                    <div class="tunnel-traffic-bar">
                        <div class="tunnel-traffic-info">
                            <span class="tunnel-traffic-label">Cycle:</span>
                            <span class="tunnel-traffic-val font-mono">${formatBytes(tTraffic.cycle_total)}</span>
                            <span class="tunnel-traffic-sub font-mono">↑ ${formatBytes(tTraffic.cycle_rx)} · ↓ ${formatBytes(tTraffic.cycle_tx)}</span>
                        </div>
                        <div class="tunnel-traffic-actions">
                            <button type="button" class="btn-tunnel-traffic" onclick="openTrafficModal('tunnel', decodeURIComponent('${encodedTName}'))" title="View Tunnel Bandwidth Analytics">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                                <span>Stats</span>
                            </button>
                            <button type="button" class="btn-tunnel-traffic btn-reset" onclick="promptResetTraffic('tunnel', decodeURIComponent('${encodedTName}'))" title="Reset Billing Cycle">
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
