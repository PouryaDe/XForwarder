/**
 * XForwarder - Authentication, Session & Security Subsystem
 */

import { API_BASE, fetchApi } from "./api.js";
import { showToast } from "./utils.js";

const EYE_OPEN_SVG = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`;
const EYE_OFF_SVG = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>`;

let lockoutCountdownTimer = null;

// Password visibility toggle helper
export function setupPasswordToggle(button, input, icon) {
    if (!button || !input || !icon) return;
    button.addEventListener("click", () => {
        const isPwd = input.getAttribute("type") === "password";
        input.setAttribute("type", isPwd ? "text" : "password");
        icon.innerHTML = isPwd ? EYE_OFF_SVG : EYE_OPEN_SVG;
    });
}

// Caps Lock Detection
export function setupCapsLockDetection(input, warningEl) {
    if (!input || !warningEl) return;
    const checkCaps = (e) => {
        if (e.getModifierState && e.getModifierState("CapsLock")) {
            warningEl.style.display = "flex";
        } else {
            warningEl.style.display = "none";
        }
    };
    input.addEventListener("keyup", checkCaps);
    input.addEventListener("keydown", checkCaps);
}

// Lockout countdown timer
export function startLockoutTimer(remainingSeconds) {
    if (lockoutCountdownTimer) clearInterval(lockoutCountdownTimer);
    let secondsLeft = remainingSeconds;

    const loginUsernameInput = document.getElementById("loginUsername");
    const loginPasswordInput = document.getElementById("loginPassword");
    const btnLogin = document.getElementById("btnLogin");
    const lockoutAlert = document.getElementById("lockoutAlert");
    const lockoutTimer = document.getElementById("lockoutTimer");
    const loginError = document.getElementById("loginError");

    if (loginUsernameInput) loginUsernameInput.disabled = true;
    if (loginPasswordInput) loginPasswordInput.disabled = true;
    if (btnLogin) btnLogin.disabled = true;
    if (lockoutAlert) lockoutAlert.style.display = "block";

    const updateDisplay = () => {
        if (!lockoutTimer) return;
        const m = Math.floor(secondsLeft / 60);
        const s = secondsLeft % 60;
        lockoutTimer.innerText = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    };

    updateDisplay();
    lockoutCountdownTimer = setInterval(() => {
        secondsLeft--;
        if (secondsLeft <= 0) {
            clearInterval(lockoutCountdownTimer);
            lockoutCountdownTimer = null;
            if (lockoutAlert) lockoutAlert.style.display = "none";
            if (loginUsernameInput) loginUsernameInput.disabled = false;
            if (loginPasswordInput) loginPasswordInput.disabled = false;
            if (btnLogin) btnLogin.disabled = false;
            if (loginError) loginError.style.display = "none";
        } else {
            updateDisplay();
        }
    }, 1000);
}

export function showDashboard(username, token) {
    document.documentElement.classList.add("pre-auth");
    try {
        localStorage.setItem("xfwd_authenticated", "1");
        if (token) {
            localStorage.setItem("xfwd_token", token);
        }
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
    const userToDisplay = username || localStorage.getItem("xfwd_username") || "admin";
    if (currentUsernameEl) currentUsernameEl.innerText = userToDisplay;
    if (sidebarUsername) sidebarUsername.innerText = userToDisplay;
}

export function showLogin() {
    document.documentElement.classList.remove("pre-auth");
    try {
        localStorage.removeItem("xfwd_authenticated");
        localStorage.removeItem("xfwd_username");
        localStorage.removeItem("xfwd_token");
    } catch (e) {}

    const loginScreen = document.getElementById("loginScreen");
    const dashboardScreen = document.getElementById("dashboardScreen");
    if (dashboardScreen) dashboardScreen.style.display = "none";
    if (loginScreen) loginScreen.style.display = "flex";
}

export async function checkSession() {
    try {
        const token = localStorage.getItem("xfwd_token") || "";
        const headers = {};
        if (token) {
            headers["X-Session-Token"] = token;
        }
        const res = await fetch(`${API_BASE}/me`, {
            credentials: "same-origin",
            headers
        });
        if (res.ok) {
            const data = await res.json();
            if (data && data.authenticated) {
                showDashboard(data.username || "admin", token);
                return true;
            }
        }
    } catch (err) {}
    showLogin();
    return false;
}

export async function handleLogin(e, onLoginSuccess) {
    if (e) {
        if (typeof e.preventDefault === "function") e.preventDefault();
        if (typeof e.stopPropagation === "function") e.stopPropagation();
    }

    const loginError = document.getElementById("loginError");
    if (loginError) loginError.style.display = "none";

    const usernameInput = document.getElementById("loginUsername");
    const passwordInput = document.getElementById("loginPassword");
    const btnLogin = document.getElementById("btnLogin");
    const lockoutAlert = document.getElementById("lockoutAlert");

    if (btnLogin && (btnLogin.disabled || btnLogin.classList.contains("is-loading"))) {
        return false;
    }

    const username = usernameInput ? usernameInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value : "";

    const originalBtnHtml = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
            <polyline points="10 17 15 12 10 7"/>
            <line x1="15" y1="12" x2="3" y2="12"/>
        </svg>
        <span>Sign In to Dashboard</span>
    `;

    if (btnLogin) {
        btnLogin.disabled = true;
        btnLogin.classList.add("is-loading");
        btnLogin.innerHTML = `
            <span class="btn-spinner"></span>
            <span>Authenticating...</span>
        `;
    }

    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json().catch(() => ({}));

        if (res.ok && data.ok) {
            if (data.token) {
                try {
                    localStorage.setItem("xfwd_token", data.token);
                } catch (e) {}
            }

            if (btnLogin) {
                btnLogin.classList.remove("is-loading");
                btnLogin.classList.add("is-success");
                btnLogin.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    <span>Authenticated! Redirecting...</span>
                `;
            }

            if (lockoutCountdownTimer) {
                clearInterval(lockoutCountdownTimer);
                lockoutCountdownTimer = null;
            }
            if (lockoutAlert) lockoutAlert.style.display = "none";

            setTimeout(async () => {
                if (btnLogin) {
                    btnLogin.classList.remove("is-success");
                    btnLogin.disabled = false;
                    btnLogin.innerHTML = originalBtnHtml;
                }
                const authedUser = data.username || username || "admin";
                showDashboard(authedUser, data.token);
                showToast(`Authenticated securely · Welcome, ${authedUser}!`, "success");

                if (typeof onLoginSuccess === "function") {
                    await onLoginSuccess(authedUser);
                }
            }, 250);
            return true;
        } else if (res.status === 429) {
            const remaining = data.remaining_seconds || 900;
            startLockoutTimer(remaining);
            if (loginError) {
                loginError.innerText = data.error || "Too many failed attempts. Temporary lockout active.";
                loginError.style.display = "block";
            }
            return false;
        } else {
            if (loginError) {
                loginError.innerText = data.error || "Invalid username or password";
                loginError.style.display = "block";
            }
            const card = document.querySelector(".login-card");
            if (card) {
                card.classList.remove("shake-anim");
                void card.offsetWidth;
                card.classList.add("shake-anim");
            }
            return false;
        }
    } catch (err) {
        if (loginError) {
            loginError.innerText = "Connection error. Is the service running?";
            loginError.style.display = "block";
        }
        return false;
    } finally {
        if (btnLogin && !btnLogin.classList.contains("is-success")) {
            btnLogin.classList.remove("is-loading");
            btnLogin.disabled = false;
            btnLogin.innerHTML = originalBtnHtml;
        }
    }
}

export async function handleLogout(onLogout) {
    try {
        await fetch(`${API_BASE}/logout`, { method: "POST" });
    } catch (e) {}
    try {
        localStorage.removeItem("xfwd_authenticated");
        localStorage.removeItem("xfwd_username");
        localStorage.removeItem("xfwd_token");
    } catch (e) {}
    showLogin();
    showToast("Logged out successfully", "info");
    if (typeof onLogout === "function") {
        onLogout();
    }
}

export function evaluatePasswordStrength(pwd) {
    if (!pwd) return { score: 0, text: "--", labelClass: "" };
    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.length >= 12) score++;
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score++;
    if (/\d/.test(pwd)) score++;
    if (/[^a-zA-Z0-9]/.test(pwd)) score++;

    if (score <= 2) {
        return { score: 1, text: "Weak", fillClass: "strength-weak", labelClass: "label-weak" };
    } else if (score <= 4) {
        return { score: 2, text: "Medium", fillClass: "strength-medium", labelClass: "label-medium" };
    } else {
        return { score: 3, text: "Strong", fillClass: "strength-strong", labelClass: "label-strong" };
    }
}

export function closeSecurityModal() {
    const securityModal = document.getElementById("securityModal");
    const securityForm = document.getElementById("securityForm");
    const securityError = document.getElementById("securityError");
    if (securityModal) securityModal.classList.remove("show");
    if (securityForm) securityForm.reset();
    if (securityError) securityError.style.display = "none";
}

export function initSecurityModal() {
    const securityModal = document.getElementById("securityModal");
    const securityForm = document.getElementById("securityForm");
    const btnOpenSecurityModal = document.getElementById("btnOpenSecurityModal");
    const btnCloseSecurityModal = document.getElementById("btnCloseSecurityModal");
    const btnCancelSecurity = document.getElementById("btnCancelSecurity");
    const secCurrentPwd = document.getElementById("secCurrentPwd");
    const secNewUser = document.getElementById("secNewUser");
    const secNewPwd = document.getElementById("secNewPwd");
    const secConfirmPwd = document.getElementById("secConfirmPwd");
    const btnToggleSecPwd = document.getElementById("btnToggleSecPwd");
    const eyeIconSec = document.getElementById("eyeIconSec");
    const pwdStrengthContainer = document.getElementById("pwdStrengthContainer");
    const pwdStrengthFill = document.getElementById("pwdStrengthFill");
    const pwdStrengthLabel = document.getElementById("pwdStrengthLabel");
    const securityError = document.getElementById("securityError");

    if (btnToggleSecPwd && secNewPwd && eyeIconSec) {
        setupPasswordToggle(btnToggleSecPwd, secNewPwd, eyeIconSec);
    }

    if (btnOpenSecurityModal) {
        btnOpenSecurityModal.addEventListener("click", () => {
            if (securityForm) securityForm.reset();
            if (securityError) securityError.style.display = "none";
            if (pwdStrengthContainer) pwdStrengthContainer.style.display = "none";
            const sbUser = document.getElementById("sidebarUsername");
            const curUser = document.getElementById("currentUsername");
            if (secNewUser) {
                secNewUser.value = (sbUser && sbUser.innerText) || (curUser && curUser.innerText) || "";
            }
            if (securityModal) securityModal.classList.add("show");
        });
    }

    if (btnCloseSecurityModal) btnCloseSecurityModal.addEventListener("click", closeSecurityModal);
    if (btnCancelSecurity) btnCancelSecurity.addEventListener("click", closeSecurityModal);

    if (secNewPwd) {
        secNewPwd.addEventListener("input", () => {
            const val = secNewPwd.value;
            if (!val) {
                if (pwdStrengthContainer) pwdStrengthContainer.style.display = "none";
                return;
            }
            if (pwdStrengthContainer) pwdStrengthContainer.style.display = "flex";
            const res = evaluatePasswordStrength(val);
            if (pwdStrengthFill) pwdStrengthFill.className = `pwd-strength-fill ${res.fillClass}`;
            if (pwdStrengthLabel) {
                pwdStrengthLabel.className = `pwd-strength-label ${res.labelClass}`;
                pwdStrengthLabel.innerText = `Strength: ${res.text}`;
            }
        });
    }

    if (securityForm) {
        securityForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (securityError) securityError.style.display = "none";

            const current_password = secCurrentPwd ? secCurrentPwd.value : "";
            const new_username = secNewUser ? secNewUser.value.trim() : "";
            const new_password = secNewPwd ? secNewPwd.value : "";
            const confirm_password = secConfirmPwd ? secConfirmPwd.value : "";

            if (new_password) {
                if (new_password.length < 8) {
                    if (securityError) {
                        securityError.innerText = "New password must be at least 8 characters long";
                        securityError.style.display = "block";
                    }
                    return;
                }
                if (new_password !== confirm_password) {
                    if (securityError) {
                        securityError.innerText = "New password and confirmation do not match";
                        securityError.style.display = "block";
                    }
                    return;
                }
            }

            const btnSaveSecurity = document.getElementById("btnSaveSecurity");
            const originalSecText = btnSaveSecurity ? btnSaveSecurity.innerText : "Update Credentials";
            if (btnSaveSecurity) {
                btnSaveSecurity.disabled = true;
                btnSaveSecurity.innerHTML = '<span class="btn-spinner"></span> <span>Updating...</span>';
            }

            try {
                const res = await fetch(`${API_BASE}/security/credentials`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ current_password, new_username, new_password })
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data.ok) {
                    if (data.username) {
                        const curUser = document.getElementById("currentUsername");
                        const sbUser = document.getElementById("sidebarUsername");
                        if (curUser) curUser.innerText = data.username;
                        if (sbUser) sbUser.innerText = data.username;
                    }
                    showToast("Security credentials updated successfully!", "success");
                    closeSecurityModal();
                } else {
                    if (securityError) {
                        securityError.innerText = data.error || "Failed to update security credentials";
                        securityError.style.display = "block";
                    }
                }
            } catch (err) {
                if (securityError) {
                    securityError.innerText = "Network error. Please try again.";
                    securityError.style.display = "block";
                }
            } finally {
                if (btnSaveSecurity) {
                    btnSaveSecurity.disabled = false;
                    btnSaveSecurity.innerHTML = originalSecText;
                }
            }
        });
    }
}

export function initInlineSecurityForm() {
    const inlineSecurityForm = document.getElementById("inlineSecurityForm");
    if (!inlineSecurityForm) return;

    inlineSecurityForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const currentPwd = document.getElementById("secInlineCurrentPwd")?.value || "";
        const newUser = document.getElementById("secInlineNewUser")?.value?.trim() || "";
        const newPwd = document.getElementById("secInlineNewPwd")?.value || "";
        const confirmPwd = document.getElementById("secInlineConfirmPwd")?.value || "";
        const errorEl = document.getElementById("secInlineError");
        const submitBtn = document.getElementById("btnSaveSecurityInline");

        if (errorEl) errorEl.style.display = "none";

        if (newPwd && newPwd.length < 8) {
            if (errorEl) {
                errorEl.innerText = "New password must be at least 8 characters long";
                errorEl.style.display = "block";
            }
            return;
        }

        if (newPwd && newPwd !== confirmPwd) {
            if (errorEl) {
                errorEl.innerText = "New passwords do not match";
                errorEl.style.display = "block";
            }
            return;
        }

        if (!newUser && !newPwd) {
            if (errorEl) {
                errorEl.innerText = "Please specify a new username or new password to update";
                errorEl.style.display = "block";
            }
            return;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="btn-spinner"></span> <span>Updating...</span>';
        }

        try {
            const res = await fetch(`${API_BASE}/security/credentials`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    current_password: currentPwd,
                    new_username: newUser || undefined,
                    new_password: newPwd || undefined
                })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.ok) {
                showToast("Credentials updated successfully! Please sign in again.", "success");
                setTimeout(() => {
                    showLogin();
                    inlineSecurityForm.reset();
                }, 1200);
            } else {
                if (errorEl) {
                    errorEl.innerText = data.error || "Failed to update credentials";
                    errorEl.style.display = "block";
                }
            }
        } catch (err) {
            if (errorEl) {
                errorEl.innerText = "Network error communicating with server";
                errorEl.style.display = "block";
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = "Update Credentials";
            }
        }
    });
}

export function initAuth(onLoginSuccess, onLogout) {
    const btnToggleLoginPwd = document.getElementById("btnToggleLoginPwd");
    const loginPasswordInput = document.getElementById("loginPassword");
    const loginUsernameInput = document.getElementById("loginUsername");
    const eyeIconLogin = document.getElementById("eyeIconLogin");
    const capsLockWarning = document.getElementById("capsLockWarning");
    const loginForm = document.getElementById("loginForm");
    const btnLogin = document.getElementById("btnLogin");
    const btnLogout = document.getElementById("btnLogout");

    if (btnToggleLoginPwd && loginPasswordInput && eyeIconLogin) {
        setupPasswordToggle(btnToggleLoginPwd, loginPasswordInput, eyeIconLogin);
    }

    if (loginPasswordInput && capsLockWarning) {
        setupCapsLockDetection(loginPasswordInput, capsLockWarning);
    }

    const doLogin = (e) => {
        if (e) {
            if (typeof e.preventDefault === "function") e.preventDefault();
            if (typeof e.stopPropagation === "function") e.stopPropagation();
        }
        return handleLogin(e, onLoginSuccess);
    };

    // Expose globally on window so inline onclick or other triggers work unconditionally
    window.handleLoginSubmit = doLogin;
    window.doLogin = doLogin;

    if (loginForm) {
        loginForm.addEventListener("submit", doLogin);
    }

    if (btnLogin) {
        btnLogin.addEventListener("click", doLogin);
    }

    if (loginUsernameInput) {
        loginUsernameInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") doLogin(e);
        });
    }

    if (loginPasswordInput) {
        loginPasswordInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") doLogin(e);
        });
    }

    if (btnLogout) {
        btnLogout.addEventListener("click", () => handleLogout(onLogout));
    }

    initSecurityModal();
    initInlineSecurityForm();
}
