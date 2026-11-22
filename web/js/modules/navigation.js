/**
 * XForwarder - Dashboard Navigation & Section Switcher
 */

import { t } from "./i18n.js";
import { BASE_PATH } from "./api.js";
import { updateNavIndicator } from "./effects.js";

export const SECTIONS = ["overview", "rules", "traffic", "services", "security", "updates", "logs"];

export function getSectionFromLocation() {
    const pathParts = String(window.location.pathname || "")
        .replace(/\/index\.html?$/i, "")
        .replace(/\/+$/, "")
        .split("/")
        .filter(Boolean);
    const lastPart = (pathParts[pathParts.length - 1] || "").toLowerCase();
    if (SECTIONS.includes(lastPart)) {
        return lastPart;
    }
    // One-time fallback if a legacy bookmark uses a hash; immediately normalized without #
    const legacyHash = (window.location.hash || "").replace("#", "").toLowerCase().trim();
    if (legacyHash && SECTIONS.includes(legacyHash)) {
        return legacyHash;
    }
    return "rules";
}

export function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item[data-section]");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const section = item.getAttribute("data-section");
            switchSection(section, { pushHistory: true });
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

    // Initialize section from clean URL pathname (no # hash in URL)
    const initialSection = getSectionFromLocation();
    switchSection(initialSection, { replaceHistory: true });

    window.addEventListener("popstate", () => {
        switchSection(getSectionFromLocation(), { pushHistory: false, replaceHistory: false });
    });

    window.addEventListener("xfwd:langchange", () => {
        requestAnimationFrame(updateNavIndicator);
    });
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => updateNavIndicator()).catch(() => {});
    }
    requestAnimationFrame(updateNavIndicator);
}

export function switchSection(sectionId, options = {}) {
    if (!sectionId) return;
    let sec = String(sectionId).toLowerCase().trim();
    if (sec.startsWith("section")) {
        sec = sec.replace(/^section/, "").toLowerCase();
    }
    if (!SECTIONS.includes(sec)) sec = "rules";

    const pushHistory = Boolean(options.pushHistory);
    const replaceHistory = Boolean(options.replaceHistory);

    // Deactivate nav items
    const navItems = document.querySelectorAll(".sidebar-nav .nav-item, .nav-item[data-section]");
    navItems.forEach(item => {
        if (item.getAttribute("data-section") === sec) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });
    requestAnimationFrame(updateNavIndicator);

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

    // Sync clean path URL without # hash
    const targetPath = `${BASE_PATH || ""}/${sec}${window.location.search || ""}`;
    const currentFull = `${window.location.pathname || "/"}${window.location.search || ""}${window.location.hash || ""}`;
    if (currentFull !== targetPath && (pushHistory || replaceHistory || window.location.hash)) {
        try {
            if (pushHistory) {
                history.pushState({ section: sec }, "", targetPath);
            } else {
                history.replaceState({ section: sec }, "", targetPath);
            }
        } catch (_) {}
    }

    // Section specific triggers
    if (sec === "traffic" || sec === "overview") {
        if (typeof window.loadNetworkQualityMetrics === "function") {
            window.loadNetworkQualityMetrics();
        }
        if (typeof window.loadOverviewTrafficChart === "function") {
            window.loadOverviewTrafficChart();
        }
    }
    if (sec === "updates" && typeof window.fetchSystemVersionInfo === "function") {
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
