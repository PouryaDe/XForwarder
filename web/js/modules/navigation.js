/**
 * XForwarder - Dashboard Navigation & Section Switcher
 */

export function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item[data-section]");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const section = item.getAttribute("data-section");
            switchSection(section);
            closeMobileSidebar();
        });
    });

    const btnHamburger = document.getElementById("btnHamburger");
    if (btnHamburger) {
        btnHamburger.addEventListener("click", openMobileSidebar);
    }

    const btnSidebarClose = document.getElementById("btnSidebarClose");
    if (btnSidebarClose) {
        btnSidebarClose.addEventListener("click", closeMobileSidebar);
    }

    const backdrop = document.getElementById("sidebarBackdrop");
    if (backdrop) {
        backdrop.addEventListener("click", closeMobileSidebar);
    }
}

export function switchSection(sectionId) {
    if (!sectionId) return;

    // Hide all dashboard sections
    const sections = document.querySelectorAll(".dashboard-section");
    sections.forEach(s => s.classList.remove("active"));

    // Deactivate nav items
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(n => n.classList.remove("active"));

    // Activate selected section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add("active");
    }

    const activeNav = document.querySelector(`.nav-item[data-section="${sectionId}"]`);
    if (activeNav) {
        activeNav.classList.add("active");
        const title = activeNav.querySelector(".nav-label") ? activeNav.querySelector(".nav-label").innerText : "";
        const breadcrumbEl = document.getElementById("breadcrumbCurrent");
        if (breadcrumbEl && title) {
            breadcrumbEl.innerText = title;
        }
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
