/**
 * XForwarder - Dual Theme Subsystem (Nova Dark Base & Crisp Light)
 */

export function initTheme() {
    const saved = localStorage.getItem("xfwd_theme");
    if (saved === "light") {
        document.documentElement.setAttribute("data-theme", "light");
    } else {
        document.documentElement.setAttribute("data-theme", "dark");
    }
    updateThemeToggleUI();

    const btnThemeToggle = document.getElementById("btnThemeToggle");
    if (btnThemeToggle && !btnThemeToggle._xfwdThemeBound) {
        btnThemeToggle._xfwdThemeBound = true;
        btnThemeToggle.addEventListener("click", toggleTheme);
    }

    const btnLoginThemeToggle = document.getElementById("btnLoginThemeToggle");
    if (btnLoginThemeToggle && !btnLoginThemeToggle._xfwdThemeBound) {
        btnLoginThemeToggle._xfwdThemeBound = true;
        btnLoginThemeToggle.addEventListener("click", toggleTheme);
    }
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
    const isDark = current === "dark";
    const labelText = isDark ? "Light Mode" : "Dark Mode";
    const titleText = isDark ? "Switch to Light Mode" : "Switch to Dark Mode";

    const labels = document.querySelectorAll(".theme-toggle-label");
    labels.forEach(el => {
        el.innerText = labelText;
    });

    const btnThemeToggle = document.getElementById("btnThemeToggle");
    if (btnThemeToggle) btnThemeToggle.title = titleText;

    const btnLoginThemeToggle = document.getElementById("btnLoginThemeToggle");
    if (btnLoginThemeToggle) btnLoginThemeToggle.title = titleText;
}

if (typeof window !== "undefined") {
    window.toggleTheme = toggleTheme;
}

