/**
 * XForwarder - API Client & HTTP Transport Subsystem
 */

import { showToast } from "./utils.js";

// Dynamically compute base API prefix (supports custom security secret paths)
const cleanPath = window.location.pathname.replace(/\/index\.html?$/i, "").replace(/\/+$/, "");
export const API_BASE = cleanPath ? `${cleanPath}/api` : "/api";

// Global fetch interceptor: guarantees credentials: "same-origin" and X-Session-Token header across ALL modules
if (typeof window !== "undefined" && typeof window.fetch === "function") {
    const _nativeFetch = window.fetch;
    window.fetch = async function (resource, init = {}) {
        let url = "";
        if (typeof resource === "string") {
            url = resource;
        } else if (resource && typeof resource.url === "string") {
            url = resource.url;
        }

        const isApiCall = url.includes("/api/") || (typeof resource === "string" && resource.startsWith("/api"));

        if (isApiCall) {
            init = init || {};
            const headers = new Headers(init.headers || {});

            if (!init.credentials) {
                init.credentials = "same-origin";
            }

            try {
                const token = localStorage.getItem("xfwd_token");
                if (token && !headers.has("X-Session-Token")) {
                    headers.set("X-Session-Token", token);
                }
            } catch (e) {}

            init.headers = headers;
        }

        return _nativeFetch.call(this, resource, init);
    };
}

export async function fetchApi(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    const headers = {
        "Accept": "application/json",
        ...(options.headers || {})
    };

    try {
        const token = localStorage.getItem("xfwd_token");
        if (token && !headers["X-Session-Token"]) {
            headers["X-Session-Token"] = token;
        }
    } catch (e) {}

    if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(options.body);
    }

    try {
        const res = await fetch(url, {
            ...options,
            headers,
            credentials: "same-origin"
        });

        if (res.status === 401) {
            // Unauthorized / session expired
            const isCurrentlyAuthed = localStorage.getItem("xfwd_authenticated") === "1" || !!localStorage.getItem("xfwd_token");
            if (isCurrentlyAuthed && !url.includes("/login") && !url.includes("/me")) {
                try {
                    localStorage.removeItem("xfwd_authenticated");
                    localStorage.removeItem("xfwd_token");
                    localStorage.removeItem("xfwd_username");
                } catch (e) {}
                document.documentElement.classList.remove("pre-auth");
                const loginScreen = document.getElementById("loginScreen");
                const dashboardScreen = document.getElementById("dashboardScreen");
                if (dashboardScreen) dashboardScreen.style.display = "none";
                if (loginScreen) loginScreen.style.display = "flex";
                showToast("Session expired. Please sign in again.", "warning");
            }
        }

        let data = null;
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            data = await res.json();
        } else {
            const text = await res.text();
            data = { text };
        }

        return {
            ok: res.ok,
            status: res.status,
            data
        };
    } catch (err) {
        return {
            ok: false,
            status: 0,
            error: err.message || "Network error"
        };
    }
}
