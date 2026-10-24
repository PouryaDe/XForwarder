/**
 * XForwarder - Authentication & Session Lifecycle Subsystem
 */

import { fetchApi } from "./api.js";
import { showToast } from "./utils.js";

export function showDashboard(username) {
    document.documentElement.classList.add("pre-auth");
    try {
        localStorage.setItem("xfwd_authenticated", "1");
        if (username) {
            localStorage.setItem("xfwd_username", username);
        }
    } catch (e) {}

    const loginScreen = document.getElementById("loginScreen");
    const dashboardScreen = document.getElementById("dashboardScreen");
    if (loginScreen) loginScreen.style.display = "none";
    if (dashboardScreen) dashboardScreen.style.display = "flex";

    const currentUsernameEl = document.getElementById("currentUsername");
    const sidebarUsername = document.getElementById("sidebarUsername");
    if (username) {
        if (currentUsernameEl) currentUsernameEl.innerText = username;
        if (sidebarUsername) sidebarUsername.innerText = username;
    }
}

export function showLogin() {
    document.documentElement.classList.remove("pre-auth");
    try {
        localStorage.removeItem("xfwd_authenticated");
        localStorage.removeItem("xfwd_username");
    } catch (e) {}

    const loginScreen = document.getElementById("loginScreen");
    const dashboardScreen = document.getElementById("dashboardScreen");
    if (dashboardScreen) dashboardScreen.style.display = "none";
    if (loginScreen) loginScreen.style.display = "flex";
}

export async function checkSession() {
    const res = await fetchApi("/me");
    if (res.ok && res.data && res.data.authenticated) {
        showDashboard(res.data.username || "admin");
        return true;
    } else {
        showLogin();
        return false;
    }
}

export async function handleLogin(username, password) {
    const loginError = document.getElementById("loginError");
    if (loginError) loginError.style.display = "none";

    const res = await fetchApi("/login", {
        method: "POST",
        body: { username, password }
    });

    if (res.ok) {
        showDashboard(username);
        showToast("Logged in successfully", "success");
        return true;
    } else {
        const msg = (res.data && res.data.error) ? res.data.error : "Invalid credentials";
        if (loginError) {
            loginError.innerText = msg;
            loginError.style.display = "block";
        }
        return false;
    }
}

export async function handleLogout() {
    await fetchApi("/logout", { method: "POST" });
    showLogin();
    showToast("Logged out successfully", "info");
}
