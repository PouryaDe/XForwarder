---
name: ui-design-consistency
description: "Vanilla dark-mode glassmorphism guidelines, typography, responsive layout, and debounce polling rules for web/."
always_on: false
trigger: model_decision
---

# UI Design & Consistency Standards (`web/`)

The web dashboard provides real-time multi-path monitoring and configuration on intermediate relay servers.

---

## 1. Visual Aesthetics & Theme Guidelines
- **Dark Theme:** Deep dark backgrounds (`#0a0d14`, `#10141f`, `#161c2b`) with subtle border lines (`rgba(255, 255, 255, 0.08)`).
- **Glassmorphism Panels:** Frosted cards using `backdrop-filter: blur(12px)` and soft gradient reflections.
- **Accents & Indicators:**
  - `Healthy / Active Primary`: Neon Emerald (`#10b981`)
  - `Checking / Backup Active`: Amber Orange (`#f59e0b`)
  - `Failed / Outage`: Coral Red (`#ef4444`)
  - `Primary / HAProxy`: Electric Indigo (`#6366f1`)

---

## 2. Typography Standard
- **Interface Elements:** Google Fonts **Inter** (`font-family: 'Inter', sans-serif`).
- **Technical Readouts:** Google Fonts **JetBrains Mono** (`font-family: 'JetBrains Mono', monospace`) for all IP addresses, ports, latencies, and command snippets.

---

## 3. Technology Stack & Runtime
- **Strict Vanilla Policy:** Pure HTML5, CSS3, and Vanilla JavaScript (ES6+).
- **No NPM / Node.js:** The static dashboard must load directly via the native Python `ThreadingHTTPServer` without any pre-compilation step.
- **Debounced Auto-Polling:** The status polling cycle in `app.js` must be debounced to prevent overlapping fetch requests on high latency connections.
- **Responsive Layout:** Must support narrow mobile screens (down to 360px) as well as desktop ultra-wide displays.
