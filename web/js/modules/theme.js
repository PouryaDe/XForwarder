/**
 * XForwarder - Dual Theme Subsystem (Nova Dark Base & Crisp Light)
 */

export function initTheme() {
    const saved = localStorage.getItem("xfwd_theme");
    if (saved === "light" || (!saved && window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches)) {
        document.documentElement.setAttribute("data-theme", "light");
    } else {
        document.documentElement.setAttribute("data-theme", "dark");
    }
    updateThemeToggleUI();
}

export function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
        localStorage.setItem("xfwd_theme", next);
    } catch (e) {}
    updateThemeToggleUI();
}

export function updateThemeToggleUI() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const labels = document.querySelectorAll(".theme-toggle-label");
    labels.forEach(el => {
        el.innerText = current === "dark" ? "Light Mode" : "Dark Mode";
    });
}
