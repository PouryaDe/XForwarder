/**
 * XForwarder - Dual Theme Subsystem (Nova Dark Base & Crisp Light)
 */

let lastToggleTimestamp = 0;

export function initTheme() {
    const saved = localStorage.getItem("xfwd_theme");
    if (saved === "light") {
        document.documentElement.setAttribute("data-theme", "light");
    } else {
        document.documentElement.setAttribute("data-theme", "dark");
    }
    updateThemeToggleUI();

    const btnThemeToggle = document.getElementById("btnThemeToggle");
    if (btnThemeToggle) {
        btnThemeToggle.onclick = (e) => toggleTheme(e);
    }

    const btnLoginThemeToggle = document.getElementById("btnLoginThemeToggle");
    if (btnLoginThemeToggle) {
        btnLoginThemeToggle.onclick = (e) => toggleTheme(e);
    }
}

export function toggleTheme(e) {
    if (e && typeof e.preventDefault === "function") {
        e.preventDefault();
    }
    const now = Date.now();
    if (now - lastToggleTimestamp < 350) {
        // Prevent rapid double-invocation from concurrent inline onclick + addEventListener
        return;
    }
    lastToggleTimestamp = now;
    if (typeof window !== "undefined") {
        window._lastThemeToggle = now;
    }

    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
        localStorage.setItem("xfwd_theme", next);
    } catch (err) {}
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

