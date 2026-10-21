---
name: ui-design-consistency
description: "Universal visual design guidelines, dual-theme standards, light-mode shadows, and design consistency across all screens in web/."
always_on: false
trigger: model_decision
---

# UI Design & Universal Consistency Standards (`web/`)

Authoritative visual guidelines, design tokens, and aesthetic rules for **all** screens in XForwarder (Login Screen, Navigation Dashboard, Modals, Banners, and Forms).

---

## 1. Prime Directive: Universal Visual Consistency
**All pages and views must strictly follow the exact same visual design system.**
- The unauthenticated Login Screen, authenticated Dashboard views, Modals, Banners, and Status toasts share identical design tokens, typography, border radiuses, button sizing, and transitions.
- Zero fragmentation: No screen or modal may invent ad-hoc colors, borders, or shadow treatments that deviate from the core tokens.

---

## 2. Dual-Theme Design System (Dark & Light Mode)

### A. Dark Theme (`[data-theme="dark"]`, Default)
- **Background Base:** `#0B0E14` (Nova Slate Navy)
- **Surface Solid:** `#12151f` and `#171b28`
- **Card Fill:** `rgba(255, 255, 255, 0.045)` with `backdrop-filter: blur(20px)`
- **Border Lines:** `rgba(255, 255, 255, 0.08)` (Focus/Active: `rgba(167, 139, 250, 0.45)`)
- **Card Shadows:** Deep subtle depth `0 20px 50px -12px rgba(0, 0, 0, 0.5)`
- **Aurora Ambient Lighting:** 3 floating ambient blobs (`--blob-1: #22315c`, `--blob-2: #3d2255`, `--blob-3: #1c3b3a`)
- **Restrained Highlights Principle (Mandatory):**
  - Never use loud neon glows (`box-shadow: 0 0 16px`) or flood normal/healthy cards with colored fills.
  - Active path routes use refined border-left accents (`border-left: 3px solid var(--accent-emerald)`) instead of neon halos.
  - Normal operational states (Auto Failover, healthy latency <150ms, priority badges, host IPs, engine running state) must remain quiet, clean, and neutral.
  - Saturated highlight colors are strictly reserved for critical conditions: Red/Rose for DOWN/100% loss (`#FB7185`), and Amber for Degraded (>150ms or loss > 0%), Flapping, or Manual Forced testing overrides (`#FBBF6B`).

### B. Light Theme (`[data-theme="light"]`)
- **Background Base:** `#EEF1F7` (Nova Light)
- **Surface & Cards:** `#FFFFFF` and `rgba(255, 255, 255, 0.65)`
- **Border Lines:** `rgba(20, 25, 45, 0.08)` (Focus/Active: `rgba(139, 92, 246, 0.5)`)
- **Card Shadows:** `0 20px 50px -15px rgba(30, 40, 80, 0.14)`
- **Aurora Ambient Lighting (Light):** Soft ambient blobs (`--blob-1: #c9dcfb`, `--blob-2: #f0d9fb`, `--blob-3: #c9f3ea`)

---

## 3. Brand Identity & Iconography Across Screens
- **Official Brand Mark:** Double-chevron forward icon (`<polyline points="13 17 18 12 13 7"></polyline><polyline points="6 17 11 12 6 7"></polyline>`) housed inside `.logo-orb`.
- **Logo Gradient:** `linear-gradient(135deg, var(--accent-primary), var(--accent-cyan))` with crisp white icon.
- **Brand Badge:** Gradient pill badge (`PRO` / `SHIELD`) with `font-weight: 800` and letter-spacing `0.05em`.
- **Consistency:** The brand mark and badge MUST appear identically on both the Dashboard Sidebar (`.sidebar-header .brand`) and the Login Screen (`.login-header .logo-orb`).

---

## 4. Universal Theme Switcher Availability
- The light/dark theme toggle MUST be readily available on **ALL** entry points:
  1. Top-right corner of the **Login Screen** (`.login-top-bar #btnLoginThemeToggle`).
  2. Bottom of the **Dashboard Sidebar** (`.sidebar-footer #btnThemeToggle`).
  3. Mobile/Desktop **Top Navigation Bar** (`.topbar #btnHeaderThemeToggle`).
- Theme selection persists instantly to `localStorage.getItem("xfwd_theme")` and applies across sessions with pre-hydration flicker prevention.

---

## 5. Typography Standards
- **Interface Elements:** Google Fonts **Inter** (`font-family: 'Inter', -apple-system, sans-serif`) for headers, body, buttons, and navigation.
- **Technical Readouts:** Google Fonts **JetBrains Mono** (`font-family: 'JetBrains Mono', monospace`) strictly for all ports (`:8090`), IP addresses (`10.88.1.2`), latencies (`14ms`), configuration filenames, and code snippets.
- **Heading Scale:** Clean, legible sizes with negative tracking (`letter-spacing: -0.02em`).

---

## 6. Components & Form Controls
- **Inputs & Selects:**
  - Height: `42px`-`44px`
  - Border radius: `10px`-`12px`
  - Integrated SVG icons (`.input-with-icon`) aligned left (`left: 14px`)
  - Arrow dropdown spacing: minimum `36px` right padding to avoid chevron-overlap
- **Buttons:**
  - `.btn-primary`: Indigo accent (`--accent-primary`), font-weight 600, smooth hover lift (`transform: translateY(-1px)`).
  - `.btn-secondary`: Subtle translucent fill with 1px border.
  - `.btn-sm`: Compact actions (height `32px`-`34px`, font-size `0.8rem`).
- **Modals:**
  - Glass backdrop: `rgba(0, 0, 0, 0.65)` with `backdrop-filter: blur(8px)`.
  - Card radius: `18px`-`20px`, padding `26px`.
  - Invisible scrollbar (`scrollbar-width: none` / `::-webkit-scrollbar { display: none }`).

---

## 7. Strict Vanilla Technology Stack
- **Zero Third-Party Build Tools:** Pure HTML5, CSS3, and ES6+ JavaScript. No Webpack, Vite, Node.js, or NPM dependencies.
- **Debounced Live Polling:** 3-second auto-refresh cycles must debounce to prevent request stacking.
- **Multi-Tier Mobile Responsive Architecture:**
  - Ultra-Wide (`> 1560px`): Max width 1600px, 3-column rules grid.
  - Balanced Stats Grid (`<= 1350px`): Perfectly balanced 2x2 stats grid.
  - Topbar Condensation (`<= 1280px`): Automatic metric compression (`.ram-short`), `.btn-text` hidden turning actions into uniform 36px icon buttons to prevent topbar squish.
  - Tablet & Mobile Drawer (`<= 1024px`): Off-canvas mobile drawer with `#btnToggleSidebar`, auto-close on navigation item click, and single-column full-width rules matrix.
  - Mobile & Small Tablet (`<= 768px`): 2-row stacked topbar, mobile toolbar, touch-scrollable filter tabs, full-width actions, and mobile modal layout.
  - Extra-Small Devices (`<= 480px`): Compact stat cards, full-width info items, and touch-optimized padding.

---

## 8. Rule Matrix & Card Layout Architecture
- **Multi-Tier Port Cards Grid (`.rules-container`):** Port rule cards are arranged in 3 columns on ultra-wide screens (`> 1560px`), 2 columns on standard desktops (`1025px - 1560px`), and single full-width column on tablet/mobile (`<= 1024px`).
- **Vertical Path Stacking (`.paths-grid`):** Inside each port card, forwarding priorities MUST be stacked strictly in vertical order (Priority 1 on top, Priority 2 directly underneath, Priority 3 below). Never use horizontal wrapping grids for priority paths.
- **Manual Forwarding Mode & Test Controller (`.rule-test-bar`):**
  - Every port card features a prominent segmented test controller:
    - `⚡ Auto Failover`: Activates automatic priority failover (`force_override: 0`).
    - `Force P1`, `Force P2`, ...: Instantly forces traffic onto that specific forwarding method for testing.
  - Path boxes contain individual 1-click test actions (`Force Test P{N}` and `Forced Active (Reset Auto)`).


