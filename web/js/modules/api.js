/**
 * XForwarder - API Client & HTTP Transport Subsystem
 */

import { showToast } from "./utils.js";

// Dynamically compute base API prefix (supports custom security secret paths)
const cleanPath = window.location.pathname.replace(/\/index\.html?$/i, "").replace(/\/+$/, "");
export const API_BASE = cleanPath ? `${cleanPath}/api` : "/api";

export async function fetchApi(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    const headers = {
        "Accept": "application/json",
        ...(options.headers || {})
    };

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
            if (!endpoint.includes("/login") && !endpoint.includes("/me")) {
                localStorage.removeItem("xfwd_authenticated");
                document.documentElement.classList.remove("pre-auth");
                window.location.reload();
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
