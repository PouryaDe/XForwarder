---
name: reverse-prompting
description: "Reverse Prompt Engineering: single-question interactive clarification for ambiguous or architectural requests."
always_on: false
trigger: model_decision
---

# Interactive Requirements Clarification (Reverse Prompt Engineering)

Enforces proactive clarification for underspecified, multi-faceted, or architectural requests to eliminate rework.

---

## 1. Zero-Assumption Policy & Triggers

- **Exempt Direct Requests (Proceed immediately without questioning ONLY for):**
  1. Pure exploratory questions ("how does failover work?").
  2. Running verification scripts or linters without modifying code.
  3. Fixing a deterministic syntax error or literal typo with 100% specified fix.

- **Mandatory Clarification Triggers (MUST pause execution immediately for):**
  1. **New Routing Features:** Adding new protocols, proxy modes, or tunnel interface types.
  2. **UI/UX Changes:** Adding or modifying modals, controls, or dashboard cards.
  3. **Configuration Schema Changes:** Modifying `config.json` keys or threshold defaults.
  4. **Multi-State Requests:** Multiple architectural choices with distinct trade-offs.

---

## 2. Rules of Engagement

1. **Strict Single-Question Constraint:** Ask **ONLY ONE question per turn**. Never present multi-part questionnaires.
2. **Options with Recommendation:** Provide 2 to 4 concrete options with concise pros/cons, highlighting the agent's recommended option.
3. **Adaptive Cadence:** Formulate subsequent questions dynamically based on preceding user answers.
