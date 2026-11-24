#!/usr/bin/env python3
"""
Unit & HTTP Integration Tests for XForwarder Scoped API Keys, RESTful CRUD,
PUT/PATCH/OPTIONS Methods, Global Settings API, OpenAPI Spec, and Docs IP Hygiene.
Standard Library unittest only.
"""

import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.auth import (
    generate_api_key,
    verify_api_key_hash,
    authenticate_api_key,
    scope_allows,
    sanitize_api_key_record,
    hash_password,
)
from core.config_manager import (
    migrate_and_normalize_config,
    sanitize_config_for_api,
)
from core.openapi_spec import build_openapi_spec
from core.web_server import XForwarderWebHandler


class TestApiKeysAndRestApi(unittest.TestCase):

    def test_api_key_generation_hashing_and_scopes(self):
        """Verifies API key generation, salted hash verification, expiration, and scope hierarchy."""
        raw_key, rec = generate_api_key("Billing Bot", scope="write", expires_in_days=30)
        self.assertTrue(raw_key.startswith("xfwd_key_"))
        self.assertTrue(rec["key_hash"].startswith("sha256$"))
        self.assertEqual(rec["scope"], "write")
        self.assertTrue(rec["enabled"])
        self.assertGreater(rec["expires_at"], time.time())
        self.assertTrue(verify_api_key_hash(raw_key, rec["key_hash"]))
        self.assertFalse(verify_api_key_hash(raw_key + "x", rec["key_hash"]))

        # Scope hierarchy: read < write < admin
        self.assertTrue(scope_allows("admin", "read"))
        self.assertTrue(scope_allows("admin", "write"))
        self.assertTrue(scope_allows("admin", "admin"))
        self.assertTrue(scope_allows("write", "read"))
        self.assertTrue(scope_allows("write", "write"))
        self.assertFalse(scope_allows("write", "admin"))
        self.assertTrue(scope_allows("read", "read"))
        self.assertFalse(scope_allows("read", "write"))

        # Authenticate active key
        meta = authenticate_api_key(raw_key, [rec])
        self.assertIsNotNone(meta)
        self.assertEqual(meta["id"], rec["id"])
        self.assertNotIn("key_hash", meta)

        # Disabled key fails auth
        disabled = dict(rec, enabled=False)
        self.assertIsNone(authenticate_api_key(raw_key, [disabled]))

        # Expired key fails auth
        expired = dict(rec, expires_at=time.time() - 10)
        self.assertIsNone(authenticate_api_key(raw_key, [expired]))
        self.assertTrue(sanitize_api_key_record(expired)["expired"])

    def test_config_migration_and_sanitization(self):
        """Verifies web.api_keys migration idempotence and sensitive hash redaction."""
        cfg = {
            "schema_version": 3,
            "web": {
                "port": 8090,
                "secret_path": "xfwd-admin",
                "auth": {"username": "admin", "password_hash": hash_password("Secret1234!")},
            },
            "rules": [],
        }
        norm, _ = migrate_and_normalize_config(cfg)
        self.assertEqual(norm["web"]["api_keys"], [])
        _, modified_again = migrate_and_normalize_config(norm)
        self.assertFalse(modified_again)

        _, rec = generate_api_key("CI", scope="read")
        norm["web"]["api_keys"].append(rec)
        sanitized = sanitize_config_for_api(norm)
        self.assertNotIn("password_hash", sanitized["web"]["auth"])
        self.assertEqual(len(sanitized["web"]["api_keys"]), 1)
        self.assertNotIn("key_hash", sanitized["web"]["api_keys"][0])

    def test_end_to_end_http_rest_api_and_scopes(self):
        """Tests real HTTP requests across /api/v1/* with Bearer/X-API-Key, scopes, CRUD, PUT/PATCH/DELETE/OPTIONS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            state_path = os.path.join(tmpdir, "state.json")

            admin_raw, admin_rec = generate_api_key("Root Admin", scope="admin")
            write_raw, write_rec = generate_api_key("Rule Writer", scope="write")
            read_raw, read_rec = generate_api_key("Metrics Reader", scope="read")

            init_cfg = {
                "schema_version": 3,
                "web": {
                    "bind_host": "127.0.0.1",
                    "port": 8090,
                    "secret_path": "xfwd-admin",
                    "auth": {"username": "admin", "password_hash": hash_password("AdminPass123!")},
                    "api_keys": [admin_rec, write_rec, read_rec],
                },
                "rules": [],
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(init_cfg, f)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"runtime": {"rules_state": {}, "recent_switches": [{"rule_id": "rule-443", "from": 1, "to": 2}]}}, f)

            class DummyServer:
                is_ssl = False

            old_env_cfg = os.environ.get("XFWD_CONFIG_PATH")
            old_env_st = os.environ.get("XFWD_STATE_PATH")
            os.environ["XFWD_CONFIG_PATH"] = cfg_path
            os.environ["XFWD_STATE_PATH"] = state_path

            XForwarderWebHandler.server_instance = DummyServer()
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()

            def call_api(method, path, body=None, headers=None):
                url = f"http://127.0.0.1:{port}{path}"
                data = json.dumps(body).encode("utf-8") if body is not None else None
                hdrs = {"Accept": "application/json"}
                if body is not None:
                    hdrs["Content-Type"] = "application/json"
                if headers:
                    hdrs.update(headers)
                req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
                try:
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        raw = resp.read().decode("utf-8") if resp.length != 0 else ""
                        return resp.status, (json.loads(raw) if raw else {}), resp.headers
                except urllib.error.HTTPError as e:
                    raw = e.read().decode("utf-8")
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        parsed = {"raw": raw}
                    return e.code, parsed, e.headers

            try:
                with patch("core.web_server.sync_rules_and_notify", return_value=(True, [])), \
                     patch("core.web_server._safe_flush_port_conntrack"), \
                     patch("core.web_server.is_port_in_use_by_external_service", return_value=False):

                    # 1. Unauthenticated access blocked (404 due to secret_path)
                    code, _, _ = call_api("GET", "/api/v1/rules")
                    self.assertEqual(code, 404)

                    # 2. /api/v1/me & /api/v1/health with Bearer read key
                    code, me, _ = call_api("GET", "/api/v1/me", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 200)
                    self.assertTrue(me["authenticated"])
                    self.assertEqual(me["auth_type"], "api_key")
                    self.assertEqual(me["scope"], "read")

                    code, health, _ = call_api("GET", "/api/v1/health", headers={"X-API-Key": read_raw})
                    self.assertEqual(code, 200)
                    self.assertEqual(health["status"], "healthy")

                    # 3. OpenAPI spec endpoint
                    code, spec, _ = call_api("GET", "/api/v1/openapi.json", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(spec["openapi"], "3.0.3")
                    self.assertIn("/api/rules", spec["paths"])

                    # 4. Read key rejected with 403 on write endpoint and admin endpoint
                    code, _, _ = call_api("POST", "/api/v1/rules", body={"port": 443, "destinations": [{"target": "198.51.100.20"}]}, headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 403)
                    code, _, _ = call_api("GET", "/api/v1/api-keys", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 403)

                    # 5. Write key rejected with 403 on admin endpoints (/api-keys, /settings PATCH)
                    code, _, _ = call_api("PATCH", "/api/v1/settings", body={"max_primary_latency_ms": 180}, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 403)

                    # 6. Write key creates rule via POST /api/v1/rules (201) and duplicates fail (409)
                    rule_payload = {
                        "port": 443,
                        "protocol": "both",
                        "category": "Main",
                        "destinations": [
                            {"priority": 1, "type": "haproxy", "target": "2001:db8:1::10", "port": 443},
                            {"priority": 2, "type": "nftables", "target": "10.200.1.2", "port": 443, "tunnel_iface": "gre1"},
                        ],
                    }
                    code, created, _ = call_api("POST", "/api/v1/rules", body=rule_payload, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 201)
                    self.assertEqual(created["rule"]["id"], "rule-443")

                    code, _, _ = call_api("POST", "/api/v1/rules", body=rule_payload, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 409)

                    # 7. GET /api/v1/rules with query filters & GET /api/v1/rules/rule-443
                    code, listed, _ = call_api("GET", "/api/v1/rules?category=Main&port=443", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(listed["count"], 1)

                    code, detail, _ = call_api("GET", "/api/v1/rules/rule-443", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(detail["rule"]["port"], 443)

                    # 8. PATCH /api/v1/rules/rule-443 partial update
                    code, patched, _ = call_api("PATCH", "/api/v1/rules/rule-443", body={"category": "VIP", "max_primary_latency_ms": 200}, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(patched["rule"]["category"], "VIP")
                    self.assertEqual(patched["rule"]["max_primary_latency_ms"], 200)
                    self.assertEqual(len(patched["rule"]["destinations"]), 2)

                    # 9. PUT /api/v1/rules/rule-443 full replacement
                    put_body = {
                        "port": 443,
                        "protocol": "tcp",
                        "category": "Replaced",
                        "destinations": [{"priority": 1, "type": "nginx", "target": "198.51.100.20", "port": 443}],
                    }
                    code, replaced, _ = call_api("PUT", "/api/v1/rules/rule-443", body=put_body, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(replaced["rule"]["protocol"], "tcp")
                    self.assertEqual(replaced["rule"]["destinations"][0]["type"], "nginx")

                    # 10. Override & destination toggle via RESTful subpaths
                    code, ovr, _ = call_api("POST", "/api/v1/rules/rule-443/override", body={"force_override": 1}, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(ovr["force_override"], 1)

                    code, tog, _ = call_api("POST", "/api/v1/rules/rule-443/destinations/1/toggle", body={"enabled": False}, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 200)
                    self.assertFalse(tog["enabled"])

                    # 11. GET /api/v1/logs/switches & GET /api/v1/status (redacted)
                    code, logs_resp, _ = call_api("GET", "/api/v1/logs/switches?limit=10", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(logs_resp["count"], 1)

                    code, status_resp, _ = call_api("GET", "/api/v1/status", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 200)
                    self.assertNotIn("password_hash", status_resp["config"]["web"]["auth"])

                    # 12. Admin GET/PATCH /api/v1/settings
                    code, set_get, _ = call_api("GET", "/api/v1/settings", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 200)
                    self.assertIn("max_primary_latency_ms", set_get["settings"])

                    code, set_patch, _ = call_api("PATCH", "/api/v1/settings", body={"min_hold_seconds": 300}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(set_patch["settings"]["min_hold_seconds"], 300)

                    # 13. Admin API key lifecycle (POST -> GET -> PATCH -> DELETE) + validation edge cases
                    code, _, _ = call_api("POST", "/api/v1/api-keys", body={"name": "<>;\"$", "scope": "read"}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 400)
                    code, _, _ = call_api("POST", "/api/v1/api-keys", body={"name": "BadScope", "scope": "super"}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 400)
                    code, _, _ = call_api("POST", "/api/v1/api-keys", body={"name": "BadExp", "scope": "read", "expires_in_days": True}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 400)

                    code, k_create, _ = call_api("POST", "/api/v1/api-keys", body={"name": "Temp Key", "scope": "read", "expires_in_days": 7}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 201)
                    new_kid = k_create["key"]["id"]
                    new_kraw = k_create["api_key"]

                    code, k_get, _ = call_api("GET", f"/api/v1/api-keys/{new_kid}", headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(k_get["key"]["id"], new_kid)
                    code, _, _ = call_api("GET", "/api/v1/api-keys/key_missing", headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 404)

                    code, k_patch, _ = call_api("PATCH", f"/api/v1/api-keys/{new_kid}", body={"enabled": False}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 200)
                    self.assertFalse(k_patch["key"]["enabled"])

                    # Disabled key now rejected (404 when secret_path active and unauthenticated)
                    code, _, _ = call_api("GET", "/api/v1/rules", headers={"Authorization": f"Bearer {new_kraw}"})
                    self.assertIn(code, (401, 404))

                    code, k_del, _ = call_api("DELETE", f"/api/v1/api-keys/{new_kid}", headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(k_del["deleted"], new_kid)

                    # 13b. Settings & Rule edge-case validation + CSRF with cookie
                    code, _, _ = call_api("PATCH", "/api/v1/settings", body={"unknown_key": 1}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 400)
                    code, _, _ = call_api("PATCH", "/api/v1/settings", body={"min_hold_seconds": True}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 400)
                    code, _, _ = call_api("PATCH", "/api/v1/settings", body={"wan_interface": "eth0;rm"}, headers={"Authorization": f"Bearer {admin_raw}"})
                    self.assertEqual(code, 400)

                    code, _, _ = call_api("PATCH", "/api/v1/rules/443", body={"max_primary_latency_ms": 10}, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 400)
                    code, _, _ = call_api("PATCH", "/api/v1/rules/443", body={"force_override": -2}, headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 400)

                    # Cookie present + mismatched Origin must still fail CSRF (403)
                    code, _, _ = call_api(
                        "POST",
                        "/api/v1/sync",
                        headers={"Authorization": f"Bearer {write_raw}", "Cookie": "xfwd_session=stale", "Origin": "https://evil.example.com"},
                    )
                    self.assertEqual(code, 403)

                    # 14. Port-based DELETE rule, 404 on missing rule, & OPTIONS preflight
                    code, r_del, _ = call_api("DELETE", "/api/v1/rules/443", headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 200)
                    self.assertEqual(r_del["deleted_count"], 1)

                    code, _, _ = call_api("DELETE", "/api/v1/rules/443", headers={"Authorization": f"Bearer {write_raw}"})
                    self.assertEqual(code, 404)

                    code, _, opt_hdrs = call_api("OPTIONS", "/api/v1/rules", headers={"Authorization": f"Bearer {read_raw}"})
                    self.assertEqual(code, 204)
                    self.assertIn("PATCH", opt_hdrs.get("Allow", ""))
                    self.assertIn("PUT", opt_hdrs.get("Allow", ""))
            finally:
                httpd.shutdown()
                httpd.server_close()
                if old_env_cfg is None:
                    os.environ.pop("XFWD_CONFIG_PATH", None)
                else:
                    os.environ["XFWD_CONFIG_PATH"] = old_env_cfg
                if old_env_st is None:
                    os.environ.pop("XFWD_STATE_PATH", None)
                else:
                    os.environ["XFWD_STATE_PATH"] = old_env_st

    def test_docs_use_strictly_fictional_ips_and_ui_elements_exist(self):
        """Verifies API documentation exists, uses no real/codebase IPs, and UI controls are wired."""
        forbidden_tokens = [
            "89.163.231.17",
            "2001:4ba0:",
            "10.88.",
            "1.1.1.1",
            "9.9.9.9",
            "192.168.",
            "2606:4700:",
        ]
        doc_files = [
            os.path.join(REPO_ROOT, "docs", "API.md"),
            os.path.join(REPO_ROOT, "docs", "API.en.md"),
            os.path.join(REPO_ROOT, "core", "openapi_spec.py"),
            os.path.join(REPO_ROOT, "web", "js", "modules", "api_keys.js"),
        ]
        for fpath in doc_files:
            self.assertTrue(os.path.isfile(fpath), f"Missing doc/API file: {fpath}")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for bad_ip in forbidden_tokens:
                self.assertNotIn(bad_ip, content, f"Non-fictional IP '{bad_ip}' found in {fpath}")
            self.assertIn("203.0.113.10", content, f"Expected fictional RFC 5737 IP in {fpath}")

        # OpenAPI spec JSON integrity
        spec = build_openapi_spec(version="1.8.0")
        self.assertIn("/api/api-keys", spec["paths"])
        self.assertIn("/api/settings", spec["paths"])

        # Web UI DOM & CSS wiring
        with open(os.path.join(REPO_ROOT, "web", "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        for dom_id in ("cardApiKeys", "apiKeyCreateForm", "apiKeysList", "apiDocsModal", "btnOpenApiDocsModal", "btnDownloadOpenApi"):
            self.assertIn(f'id="{dom_id}"', html)


if __name__ == "__main__":
    unittest.main()
