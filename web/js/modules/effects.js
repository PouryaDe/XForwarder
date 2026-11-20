/**
 * XForwarder - Ovira Ambient Lighting, Cursor Dot-Matrix, Card Spotlight & Spring Nav Indicator
 * Pure Vanilla ES6+ Module (zero external dependencies)
 */

const SPOTLIGHT_SELECTOR = [
    ".rule-card",
    ".rule-list-row",
    ".stat-card",
    ".telemetry-card",
    ".overview-card",
    ".network-card",
    ".engines-card",
    ".main-panel",
    ".login-card",
    ".tunnel-card",
    ".metrics-kpi-card",
    ".switch-log-card"
].join(", ");

let effectsInitialized = false;
let navResizeObserver = null;

/**
 * Computes and writes CSS custom properties for the active navigation pill.
 * Hides the indicator cleanly when the sidebar is collapsed/hidden (offsetHeight === 0).
 * @param {HTMLElement} nav - The `.sidebar-nav` container element.
 */
function syncNavIndicatorMetrics(nav) {
    if (!nav) return;
    const active = nav.querySelector(".nav-item.active");
    if (active && active.offsetHeight > 0) {
        nav.style.setProperty("--ind-x", `${active.offsetLeft}px`);
        nav.style.setProperty("--ind-y", `${active.offsetTop}px`);
        nav.style.setProperty("--ind-w", `${active.offsetWidth}px`);
        nav.style.setProperty("--ind-h", `${active.offsetHeight}px`);
        nav.style.setProperty("--ind-o", "1");
    } else {
        nav.style.setProperty("--ind-o", "0");
    }
}

/**
 * Tracks fine pointer coordinates via requestAnimationFrame for the cursor-lit
 * ambient dot matrix and per-card radial spotlight hover effect.
 */
export function initAmbientEffects() {
    if (effectsInitialized || typeof window === "undefined") return;
    effectsInitialized = true;

    const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const finePointer = window.matchMedia && window.matchMedia("(pointer: fine)").matches;
    if (reducedMotion || !finePointer) return;

    const root = document.documentElement;
    let rafId = 0;
    let lastEvent = null;

    const flush = () => {
        rafId = 0;
        if (!lastEvent) return;
        root.style.setProperty("--cx", `${lastEvent.clientX}px`);
        root.style.setProperty("--cy", `${lastEvent.clientY}px`);

        const target = lastEvent.target;
        const card = target && typeof target.closest === "function" ? target.closest(SPOTLIGHT_SELECTOR) : null;
        if (card) {
            const rect = card.getBoundingClientRect();
            card.style.setProperty("--mx", `${lastEvent.clientX - rect.left}px`);
            card.style.setProperty("--my", `${lastEvent.clientY - rect.top}px`);
        }
    };

    const clearPointer = () => {
        lastEvent = null;
        if (rafId && typeof cancelAnimationFrame === "function") {
            cancelAnimationFrame(rafId);
            rafId = 0;
        }
        delete root.dataset.pointer;
    };

    window.addEventListener(
        "pointermove",
        (e) => {
            lastEvent = e;
            root.dataset.pointer = "on";
            if (!rafId) {
                rafId = requestAnimationFrame(flush);
            }
        },
        { passive: true }
    );

    // Clear ambient cursor glow when leaving the viewport or switching windows
    root.addEventListener("mouseleave", clearPointer, { passive: true });
    window.addEventListener("pointercancel", clearPointer, { passive: true });
    window.addEventListener("blur", clearPointer);
}

/**
 * Synchronizes the spring-animated sliding indicator behind the active `.nav-item`
 * and attaches a single ResizeObserver for responsive / font-load reflows.
 */
export function updateNavIndicator() {
    if (typeof document === "undefined") return;
    const nav = document.querySelector(".sidebar-nav");
    if (!nav) return;

    syncNavIndicatorMetrics(nav);

    // Defer `data-ready` by one frame so the initial mount snaps without an unwanted slide
    if (!nav.hasAttribute("data-ready")) {
        requestAnimationFrame(() => nav.setAttribute("data-ready", ""));
    }

    if (!navResizeObserver && typeof ResizeObserver !== "undefined") {
        navResizeObserver = new ResizeObserver(() => syncNavIndicatorMetrics(nav));
        navResizeObserver.observe(nav);
    }
}
