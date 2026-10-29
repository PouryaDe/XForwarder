/**
 * XForwarder - Dashboard Navigation & Section Switcher
 */

import { t } from "./i18n.js";

export const SECTIONS = ["rules", "overview", "services", "security", "logs"];

export function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item[data-section]");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const section = item.getAttribute("data-section");
            switchSection(section);
            closeMobileSidebar();
        });
    });

    const btnHamburger = document.getElementById("btnToggleSidebar") || document.getElementById("btnHamburger");
    if (btnHamburger) {
        btnHamburger.addEventListener("click", openMobileSidebar);
    }

    const btnSidebarClose = document.getElementById("btnCloseSidebar") || document.getElementById("btnSidebarClose");
    if (btnSidebarClose) {
        btnSidebarClose.addEventListener("click", closeMobileSidebar);
    }

    const backdrop = document.getElementById("sidebarBackdrop");
    if (backdrop) {
        backdrop.addEventListener("click", closeMobileSidebar);
    }

    // Support URL hash routing on initial load and popstate/hashchange
    const hash = (window.location.hash || "").replace("#", "").toLowerCase().trim();
    if (hash && SECTIONS.includes(hash)) {
        switchSection(hash);
    }

    window.addEventListener("hashchange", () => {
        const currentHash = (window.location.hash || "").replace("#", "").toLowerCase().trim();
        if (currentHash && SECTIONS.includes(currentHash)) {
            switchSection(currentHash);
        }
    });
}

export function switchSection(sectionId) {
    if (!sectionId) return;
    let sec = String(sectionId).toLowerCase().trim();
    if (sec.startsWith("section")) {
        sec = sec.replace(/^section/, "").toLowerCase();
    }
    if (!SECTIONS.includes(sec)) sec = "rules";

    // Deactivate nav items
    const navItems = document.querySelectorAll(".sidebar-nav .nav-item, .nav-item[data-section]");
    navItems.forEach(item => {
        if (item.getAttribute("data-section") === sec) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    // Toggle sections visibility and active class
    SECTIONS.forEach(s => {
        const secId = `section${s.charAt(0).toUpperCase() + s.slice(1)}`;
        const el = document.getElementById(secId) || document.getElementById(s);
        if (el) {
            const isActive = (s === sec);
            el.style.display = isActive ? "block" : "none";
            if (isActive) {
                el.classList.add("active");
            } else {
                el.classList.remove("active");
            }
        }
    });

    // Update breadcrumb
    const breadcrumb = document.getElementById("breadcrumbSection") || document.getElementById("breadcrumbCurrent");
    if (breadcrumb) {
        const titles = {
            rules: "Port Matrix",
            overview: "Overview & Health",
            services: "Relay Services",
            security: "Security & Access",
            logs: "Logs & Probes"
        };
        breadcrumb.innerText = t(`nav.${sec}`, {}, titles[sec] || "Dashboard");
    }

    // Sync URL hash
    if (window.location.hash !== `#${sec}`) {
        try {
            history.replaceState(null, "", `#${sec}`);
        } catch (_) {}
    }

    // Section specific triggers
    if (sec === "overview") {
        if (typeof window.loadNetworkQualityMetrics === "function") {
            window.loadNetworkQualityMetrics();
        }
        if (typeof window.loadOverviewTrafficChart === "function") {
            window.loadOverviewTrafficChart();
        }
    }
    if (sec === "security" && typeof window.fetchSystemVersionInfo === "function") {
        window.fetchSystemVersionInfo(false);
    }
}

export function openMobileSidebar() {
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    if (sidebar) sidebar.classList.add("open");
    if (backdrop) backdrop.style.display = "block";
}

export function closeMobileSidebar() {
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    if (sidebar) sidebar.classList.remove("open");
    if (backdrop) backdrop.style.display = "none";
}
