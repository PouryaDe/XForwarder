#!/usr/bin/env python3
"""
Unit tests for XForwarder Internationalization (i18n), Persian (Farsi) localization,
and RTL (Right-to-Left) layout safety and BiDi direction protection.
Standard Library unittest only.
"""

import os
import sys
import unittest
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class TestI18nAndRTL(unittest.TestCase):
    """Verifies internationalization dictionary completeness, RTL CSS rules, and DOM integration."""

    @classmethod
    def setUpClass(cls):
        cls.i18n_js_path = os.path.join(REPO_ROOT, "web", "js", "modules", "i18n.js")
        cls.rtl_css_path = os.path.join(REPO_ROOT, "web", "css", "rtl.css")
        cls.index_html_path = os.path.join(REPO_ROOT, "web", "index.html")
        cls.style_css_path = os.path.join(REPO_ROOT, "web", "css", "style.css")
        cls.flat_style_css_path = os.path.join(REPO_ROOT, "web", "style.css")

        with open(cls.i18n_js_path, "r", encoding="utf-8") as f:
            cls.i18n_content = f.read()

        with open(cls.rtl_css_path, "r", encoding="utf-8") as f:
            cls.rtl_css_content = f.read()

        with open(cls.index_html_path, "r", encoding="utf-8") as f:
            cls.index_html_content = f.read()

        # Parse translations dictionary
        cls.en_keys, cls.en_dict = cls._parse_dict_keys(cls.i18n_content, "en")
        cls.fa_keys, cls.fa_dict = cls._parse_dict_keys(cls.i18n_content, "fa")

    @classmethod
    def _parse_dict_keys(cls, content, lang):
        """Extract keys and raw string values for a language block."""
        start_pattern = rf"{lang}:\s*\{{"
        m = re.search(start_pattern, content)
        if not m:
            return set(), {}
        start_idx = m.end()

        # Find matching closing brace
        depth = 1
        i = start_idx
        while i < len(content) and depth > 0:
            ch = content[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            i += 1
        block = content[start_idx:i-1]

        # Extract "key": "value" pairs
        # Keys match: "key.name":
        # Values match: "value" or 'value'
        kv_pairs = {}
        pair_pattern = re.compile(r'"([a-zA-Z0-9_.-]+)"\s*:\s*"((?:[^"\\]|\\.)*)"')
        for match in pair_pattern.finditer(block):
            k = match.group(1)
            v = match.group(2)
            kv_pairs[k] = v

        return set(kv_pairs.keys()), kv_pairs

    def test_i18n_file_structure_and_exports(self):
        """Verify i18n.js exists and exports all required functions and objects."""
        self.assertTrue(os.path.isfile(self.i18n_js_path), "i18n.js must exist")
        self.assertIn("export const TRANSLATIONS", self.i18n_content)
        self.assertIn("export function t(", self.i18n_content)
        self.assertIn("export function setLanguage(", self.i18n_content)
        self.assertIn("export function toggleLanguage(", self.i18n_content)
        self.assertIn("export function getCurrentLang(", self.i18n_content)
        self.assertIn("export function initI18n(", self.i18n_content)
        self.assertIn("export function applyI18nToDOM(", self.i18n_content)
        self.assertIn("export function onLanguageChanged(", self.i18n_content)

    def test_dictionary_parity_and_completeness(self):
        """Verify 100% key parity between English and Persian dictionaries (zero missing keys)."""
        self.assertGreater(len(self.en_keys), 100, "English dictionary should have >100 keys")
        self.assertGreater(len(self.fa_keys), 100, "Persian dictionary should have >100 keys")

        missing_in_fa = self.en_keys - self.fa_keys
        missing_in_en = self.fa_keys - self.en_keys

        self.assertEqual(
            missing_in_fa,
            set(),
            f"Keys defined in English but missing in Persian: {missing_in_fa}"
        )
        self.assertEqual(
            missing_in_en,
            set(),
            f"Keys defined in Persian but missing in English: {missing_in_en}"
        )

    def test_dictionary_non_empty_values(self):
        """Ensure no translation keys have empty string values."""
        for k, v in self.en_dict.items():
            self.assertTrue(v.strip(), f"English key '{k}' has empty translation value")
        for k, v in self.fa_dict.items():
            self.assertTrue(v.strip(), f"Persian key '{k}' has empty translation value")

    def test_translation_placeholder_consistency(self):
        """Verify placeholder tokens like {count}, {sec}, {prio} match between EN and FA."""
        token_pattern = re.compile(r'\{([a-zA-Z0-9_]+)\}')
        for key in self.en_keys:
            en_val = self.en_dict[key]
            fa_val = self.fa_dict[key]
            en_tokens = set(token_pattern.findall(en_val))
            fa_tokens = set(token_pattern.findall(fa_val))
            self.assertEqual(
                en_tokens,
                fa_tokens,
                f"Placeholder mismatch for key '{key}': EN has {en_tokens}, FA has {fa_tokens}"
            )

    def test_parameter_replacement_logic(self):
        """Verify simulated t() parameter replacement handles edge cases, special characters, and non-strings."""
        def sim_t(template, params):
            res = template
            for pKey, val in params.items():
                escaped_key = re.escape(pKey)
                res = re.sub(r'\{' + escaped_key + r'\}', lambda _: str(val), res)
            return res

        # Normal substitution
        self.assertEqual(
            sim_t("Switch in {sec}s", {"sec": 120}),
            "Switch in 120s"
        )
        # Dollar signs in values must not trigger regex backreference bugs
        self.assertEqual(
            sim_t("Price is {val}", {"val": "$100"}),
            "Price is $100"
        )
        # Regex special characters in parameter names
        self.assertEqual(
            sim_t("Info: {user.name}", {"user.name": "Admin"}),
            "Info: Admin"
        )
        # Empty parameters dict
        self.assertEqual(
            sim_t("No params {sec}", {}),
            "No params {sec}"
        )

    def test_html_data_i18n_keys_exist_in_dictionary(self):
        """Verify every data-i18n attribute in index.html exists in the TRANSLATIONS dictionary."""
        # Find all data-i18n="..."
        i18n_keys = set(re.findall(r'data-i18n=["\']([^"\']+)["\']', self.index_html_content))
        placeholder_keys = set(re.findall(r'data-i18n-placeholder=["\']([^"\']+)["\']', self.index_html_content))
        title_keys = set(re.findall(r'data-i18n-title=["\']([^"\']+)["\']', self.index_html_content))
        label_keys = set(re.findall(r'data-i18n-label=["\']([^"\']+)["\']', self.index_html_content))

        all_dom_keys = i18n_keys | placeholder_keys | title_keys | label_keys
        self.assertGreater(len(all_dom_keys), 50, "index.html should have >50 i18n data tags")

        missing_keys = all_dom_keys - self.en_keys
        self.assertEqual(
            missing_keys,
            set(),
            f"DOM elements reference i18n keys not defined in TRANSLATIONS: {missing_keys}"
        )

    def test_vazirmatn_font_and_prehydration_in_html(self):
        """Verify Vazirmatn font inclusion and flicker-free pre-hydration script in index.html head."""
        self.assertIn("Vazirmatn", self.index_html_content, "Google Fonts link must include Vazirmatn")
        self.assertIn("localStorage.getItem(\"xfwd_lang\")", self.index_html_content,
                      "Head pre-hydration must check saved language")
        self.assertIn("document.documentElement.setAttribute(\"lang\", \"fa\")", self.index_html_content,
                      "Head pre-hydration must set lang='fa'")
        self.assertIn("document.documentElement.setAttribute(\"dir\", \"rtl\")", self.index_html_content,
                      "Head pre-hydration must set dir='rtl'")

    def test_language_toggle_buttons_in_html(self):
        """Verify language toggle buttons exist in Topbar, Sidebar, and Login screen."""
        self.assertIn('id="btnLangToggle"', self.index_html_content, "Topbar language toggle button must exist")
        self.assertIn('id="btnSidebarLangToggle"', self.index_html_content, "Sidebar language toggle button must exist")
        self.assertIn('id="btnLoginLangToggle"', self.index_html_content, "Login language toggle button must exist")

    def test_rtl_css_bidi_and_ltr_preservation(self):
        """Verify directional styling, Vazirmatn font variables, and BiDi LTR protection."""
        self.assertTrue(os.path.isfile(self.rtl_css_path), "rtl.css must exist")

        # Must define Vazirmatn
        self.assertIn("'Vazirmatn'", self.rtl_css_content)
        self.assertIn("[dir=\"rtl\"]", self.rtl_css_content)
        self.assertIn("direction: rtl;", self.rtl_css_content)

        # Monospace & numerical BiDi LTR protection
        self.assertIn(".font-mono", self.rtl_css_content)
        self.assertIn(".dest-ip", self.rtl_css_content)
        self.assertIn(".dest-port", self.rtl_css_content)
        self.assertIn(".latency-pill", self.rtl_css_content)
        self.assertIn(".loss50-pill", self.rtl_css_content)
        self.assertIn(".rule-port", self.rtl_css_content)
        self.assertIn("direction: ltr !important;", self.rtl_css_content)
        self.assertIn("unicode-bidi: embed !important;", self.rtl_css_content)

    def test_rtl_css_included_in_stylesheets(self):
        """Verify rtl.css is included in web/css/style.css and web/style.css."""
        with open(self.style_css_path, "r", encoding="utf-8") as f:
            modular_style = f.read()
        self.assertIn('@import "rtl.css";', modular_style, "modular style.css must import rtl.css")

        with open(self.flat_style_css_path, "r", encoding="utf-8") as f:
            flat_style = f.read()
        self.assertIn("[dir=\"rtl\"]", flat_style, "flat style.css must include RTL definitions")
        self.assertIn("'Vazirmatn'", flat_style, "flat style.css must include Vazirmatn")

    def test_lang_toggle_btn_no_hover_border(self):
        """Ensure lang-toggle-btn respects design rules without hover border transitions."""
        # Check rtl.css and flat style.css for no border-color on .lang-toggle-btn:hover
        self.assertNotIn(".lang-toggle-btn:hover {\n    border-color", self.rtl_css_content)
        with open(self.flat_style_css_path, "r", encoding="utf-8") as f:
            flat_style = f.read()
        self.assertNotIn(".lang-toggle-btn:hover {\n    border-color", flat_style)

    def test_js_modules_i18n_integration(self):
        """Verify all core JS modules import t() or related i18n functions from i18n.js."""
        modules = [
            "web/app.js",
            "web/js/modules/navigation.js",
            "web/js/modules/rules.js",
            "web/js/modules/rule_modal.js",
            "web/js/modules/stats.js",
            "web/js/modules/traffic.js",
            "web/js/modules/auth.js"
        ]
        for rel_path in modules:
            full_path = os.path.join(REPO_ROOT, rel_path)
            self.assertTrue(os.path.isfile(full_path), f"{rel_path} must exist")
            with open(full_path, "r", encoding="utf-8") as f:
                code = f.read()
            self.assertTrue(
                "i18n.js" in code or "i18n" in code,
                f"{rel_path} must import from i18n.js"
            )

    def test_comprehensive_button_and_input_font_inheritance(self):
        """Verify button, input, select, textarea inherit font-family and receive Vazirmatn in RTL."""
        with open(os.path.join(REPO_ROOT, "web", "css", "base.css"), "r", encoding="utf-8") as f:
            base_css = f.read()
        self.assertIn("button,", base_css)
        self.assertIn("input,", base_css)
        self.assertIn("font-family: inherit;", base_css)

        # Check RTL rules in rtl.css
        self.assertIn('[dir="rtl"] button,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] input,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] select,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] textarea,', self.rtl_css_content)

        # Language toggle button must always display Vazirmatn for "فارسی"
        self.assertIn('.lang-toggle-btn,', self.rtl_css_content)
        self.assertIn('#topbarLangName,', self.rtl_css_content)
        self.assertIn('#sidebarLangLabel,', self.rtl_css_content)

    def test_rtl_alignment_rules_and_navigation(self):
        """Verify complete RTL directional alignment across sidebar menus, modals, selects, and tables."""
        # Sidebar nav item right alignment and active indicator
        self.assertIn('[dir="rtl"] .nav-item {', self.rtl_css_content)
        self.assertIn('text-align: right !important;', self.rtl_css_content)
        self.assertIn('[dir="rtl"] .nav-item.active::before {', self.rtl_css_content)
        self.assertIn('right: 0 !important;', self.rtl_css_content)

        # Modal close button on the left edge
        self.assertIn('[dir="rtl"] .modal-close {', self.rtl_css_content)
        self.assertIn('left: 20px !important;', self.rtl_css_content)

        # Select dropdown padding & arrow position
        self.assertIn('[dir="rtl"] select.form-control,', self.rtl_css_content)
        self.assertIn('padding-left: 40px !important;', self.rtl_css_content)
        self.assertIn('background-position: left 14px center !important;', self.rtl_css_content)

        # Tables right alignment
        self.assertIn('[dir="rtl"] .traffic-table th,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] .table-disruptions th,', self.rtl_css_content)

    def test_login_top_bar_layout_and_rtl_alignment(self):
        """Verify login screen theme and language toggle buttons are side-by-side with gap and mirrored in RTL."""
        with open(os.path.join(REPO_ROOT, "web", "css", "base.css"), "r", encoding="utf-8") as f:
            base_css = f.read()

        # Check horizontal flex container with gap
        self.assertIn(".login-top-bar {", base_css)
        self.assertIn("display: flex;", base_css)
        self.assertIn("gap: 10px;", base_css)

        # Check height and border-radius consistency
        self.assertIn(".login-lang-toggle {", base_css)
        self.assertIn(".login-theme-toggle {", base_css)

        # Check RTL positioning mirrors to top-left
        self.assertIn('[dir="rtl"] .login-top-bar {', self.rtl_css_content)
        self.assertIn('left: 24px !important;', self.rtl_css_content)
        self.assertIn('right: auto !important;', self.rtl_css_content)

    def test_technical_ltr_layout_preservation_for_rule_cards_and_categories(self):
        """Verify rule cards, category headers, and list rows maintain technical LTR layout in RTL mode."""
        # Check rule cards and category headers are explicitly LTR
        self.assertIn('[dir="rtl"] .rule-category-section,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] .rule-category-header,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] .rule-card,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] .rule-list-row,', self.rtl_css_content)
        self.assertIn('[dir="rtl"] .path-box,', self.rtl_css_content)

        # Check toggle slider knob translates to the right (+16px and +12px)
        self.assertIn('translateX(16px) !important;', self.rtl_css_content)
        self.assertIn('translateX(12px) !important;', self.rtl_css_content)

        # Check rule actions align to the right edge (margin-left: auto)
        self.assertIn('[dir="rtl"] .rule-card .rule-actions {', self.rtl_css_content)
        self.assertIn('margin-left: auto !important;', self.rtl_css_content)

    def test_rule_card_and_category_i18n_keys_completeness(self):
        """Verify all new i18n keys for rule cards and category divider exist in both EN and FA."""
        required_keys = [
            "rules.ports_count",
            "rules.copy_category_json",
            "rules.copy_category_json_tooltip",
            "rules.forwarding_label",
            "rules.copy_port_num",
            "rules.copy_dest_ip",
            "rules.edit_rule",
            "rules.delete_rule",
            "rules.switch_logs_tooltip",
            "rules.traffic_analytics_tooltip",
            "rules.copy_rule_json",
            "rules.priority_on_tooltip",
            "rules.priority_off_tooltip",
            "rules.relay_tooltip",
            "rules.switch_pending_tooltip",
            "rules.min_hold_tooltip",
            "rules.cooldown_tooltip",
            "rules.flapping_tooltip",
            "rules.flap_guard",
            "rules.traffic_cycle_tooltip",
            "status.failover"
        ]
        for k in required_keys:
            self.assertIn(k, self.en_keys, f"Key '{k}' must exist in English dictionary")
            self.assertIn(k, self.fa_keys, f"Key '{k}' must exist in Persian dictionary")

    def test_terminal_consoles_and_update_modal_ltr_alignment(self):
        """Verify terminal consoles, log streams, and update modal status banner maintain strict LTR alignment."""
        # Reload content from updated files
        with open(self.rtl_css_path, "r", encoding="utf-8") as f:
            rtl_css = f.read()
        with open(self.index_html_path, "r", encoding="utf-8") as f:
            index_html = f.read()

        # Log consoles must be flex column, LTR, and left-aligned
        self.assertIn('[dir="rtl"] .log-console,', rtl_css)
        self.assertIn('[dir="rtl"] #updateConsole {', rtl_css)
        self.assertIn('[dir="rtl"] #logConsole,', rtl_css)

        # Log entries and messages must be LTR and left-aligned
        self.assertIn('[dir="rtl"] .log-entry {', rtl_css)
        self.assertIn('[dir="rtl"] .log-msg {', rtl_css)

        # Update modal progress view and status banner must be LTR
        self.assertIn('[dir="rtl"] #updateProgressView {', rtl_css)
        self.assertIn('[dir="rtl"] .update-status-banner,', rtl_css)
        self.assertIn('[dir="rtl"] #updateStatusBanner {', rtl_css)
        self.assertIn('[dir="rtl"] #updateStatusText {', rtl_css)

        # Check inline LTR safeguards in index.html for update modal
        self.assertIn('id="updateProgressView" style="display:none; direction:ltr; text-align:left;"', index_html)
        self.assertIn('id="updateStatusBanner" style="display:flex; align-items:center; justify-content:flex-start; gap:10px;', index_html)


if __name__ == "__main__":
    unittest.main()
