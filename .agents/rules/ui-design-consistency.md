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

### A. Dark Theme (`[data-theme="dark"]`, Default — Ovira Mint)
- **Background Base (`--ground`):** `#05090a` (Obsidian Teal)
- **Surface Hierarchy:** `#0a1112` (`--raise`), `#101a1b` (`--raise-2`), `#172425` (`--raise-3`)
- **Card Fill:** `rgba(10, 17, 18, 0.78)` with `backdrop-filter: blur(22px)` and radial pointer spotlight
- **Border Lines:** `rgba(154, 245, 207, 0.09)` (Strong: `rgba(154, 245, 207, 0.19)`, Focus/Active: `rgba(52, 224, 161, 0.5)`)
- **Card Shadows:** `inset 0 1px 0 var(--edge), 0 24px 48px -32px rgba(0, 0, 0, 0.72)`
- **Ambient Lighting:** Drifting blobs (`--blob-a`, `--blob-b`, `--blob-c`), cursor-lit dot matrix (`.dots` / `.dots.lit`), and film-grain overlay
- **Restrained Highlights Principle (Mandatory):**
  - Never flood normal/healthy cards with saturated colored fills.
  - Active path routes use refined border-left accents (`border-left: 3px solid var(--accent-emerald)`).
  - Normal operational states stay calm in obsidian-teal & ink hierarchy; Mint (`#34e0a1`) highlights active selections and primary CTAs with dark `#001a0f` (`--accent-ink`) label ink.
  - Saturated alert colors are reserved for critical conditions: Coral/Red for DOWN/100% loss (`#ff6b57`), and Amber for Degraded (>150ms or loss > 0%), Flapping, or Manual Forced testing overrides (`#ffb648`).

### B. Light Theme (`[data-theme="light"]` — Ovira Warm Stone & Forest Mint)
- **Background Base (`--ground`):** `#e8e7de` (Warm Stone)
- **Surface & Cards:** `#f6f5ee` (`--raise`), `#eceadf` (`--raise-2`), `rgba(246, 245, 238, 0.86)` (`--bg-card`)
- **Border Lines:** `rgba(0, 107, 74, 0.11)` (Strong: `rgba(0, 107, 74, 0.22)`, Focus/Active: `rgba(0, 107, 74, 0.50)`)
- **Primary Accent & Accessible Text:** `--accent: #2fd896` with `#001a0f` button ink; `--accent-text: #006b4a` for legible Mint text/icons on light surfaces
- **Card Shadows:** `inset 0 1px 0 var(--edge), 0 16px 36px -24px rgba(20, 30, 20, 0.16)`
- **Ambient Lighting (Light):** Mint & Cyan blobs (`--blob-a: rgba(47, 216, 150, 0.22)`, `--blob-b: rgba(11, 140, 155, 0.16)`)

---

## 3. Brand Identity & Iconography Across Screens
- **Official Brand Mark:** Double-chevron forward icon (`<polyline points="13 17 18 12 13 7"></polyline><polyline points="6 17 11 12 6 7"></polyline>`) housed inside `.logo-orb`.
- **Logo Treatment:** Solid Mint `var(--accent)` orb with deep `--accent-ink` (`#001a0f`) SVG strokes and subtle Mint glow.
- **Brand Badge:** Mint-washed outline pill (`PRO` / `SHIELD`) with `font-weight: 800` and letter-spacing `0.05em`.
- **Consistency:** The brand mark and badge MUST appear identically on both the Dashboard Sidebar (`.sidebar-header .brand`) and the Login Screen (`.login-header .logo-orb`), alongside the split-screen SVG Bore Tunnel artwork (`.login-art`).

---

## 4. Universal Theme Switcher Availability
- The light/dark theme toggle MUST be readily available on **ALL** entry points:
  1. Top-right corner of the **Login Screen** (`.login-top-bar #btnLoginThemeToggle`).
  2. Bottom of the **Dashboard Sidebar** (`.sidebar-footer #btnThemeToggle`).
  3. Mobile/Desktop **Top Navigation Bar** (`.topbar #btnHeaderThemeToggle`).
- Theme selection persists instantly to `localStorage.getItem("xfwd_theme")` and applies across sessions with pre-hydration flicker prevention.

---

## 5. Typography Standards
- **Display & Headings:** Google Fonts **Bricolage Grotesque** (`--font-display`) with tight tracking (`letter-spacing: -0.025em`).
- **Interface Elements:** Google Fonts **Hanken Grotesk** (`--font-sans`) and **Vazirmatn** for Persian RTL.
- **Technical Readouts:** Google Fonts **JetBrains Mono** (`--font-mono`) strictly for all ports (`:8090`), IP addresses (`10.88.1.2`), latencies (`14ms`), configuration filenames, and code snippets.
- **Heading Scale:** Clean, legible sizes with negative tracking (`letter-spacing: -0.025em`).

---

## 6. Components & Form Controls
- **Inputs & Selects:**
  - Height: `42px`-`44px`
  - Border radius: `10px`-`12px`
  - Integrated SVG icons (`.input-with-icon`) aligned left (`left: 14px`)
  - Arrow dropdown spacing: minimum `36px` right padding to avoid chevron-overlap
- **Buttons:**
  - `.btn-primary`: Glossy Mint surface (`--accent`) with `#001a0f` ink, diagonal hover light-sweep (`::after`), font-weight 650, subtle hover lift (`transform: translateY(-1px)`).
  - `.btn-secondary`: Tactile raised gradient (`var(--raise-2)` to `var(--raise)`) with 1px `--line-strong` border.
  - `.btn-sm`: Compact actions (height `32px`-`34px`, font-size `0.8rem`).
- **Modals:**
  - Glass backdrop: `rgba(0, 0, 0, 0.65)` with `backdrop-filter: blur(8px)`.
  - Card radius: `18px`-`20px`, padding `26px`.
  - Invisible scrollbar (`scrollbar-width: none` / `::-webkit-scrollbar { display: none }`).
- **Strict Centering Inside Frames & Buttons (Mandatory):**
  - Every text label, badge, icon, SVG, or image placed inside a button, pill, circle, or framed container MUST be centered both vertically and horizontally (`display: inline-flex; align-items: center; justify-content: center;`).
  - Explicitly reset browser defaults on framed controls (`padding: 0` on icon-only/circle buttons, `box-sizing: border-box`, `line-height: 1` for text/numbers or `line-height: 0` + `display: block` for SVGs/images).
  - Match inner icon/SVG dimensions to the container's inner box parity (even-inside-even or odd-inside-odd, e.g., `12x12` SVG inside a `14x14` inner circle) to prevent subpixel off-center rendering.

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


