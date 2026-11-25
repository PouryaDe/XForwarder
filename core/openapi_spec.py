#!/usr/bin/env python3
"""
XForwarder - OpenAPI 3.0.3 Specification Builder
Generates machine-readable REST API schema using strictly fictional RFC documentation IPs.
"""

from typing import Dict, Any


def build_openapi_spec(version: str = "1.9.0", server_url: str = "/") -> Dict[str, Any]:
    """Builds the complete OpenAPI 3.0.3 specification for XForwarder REST API."""
    clean_server = str(server_url or "/").rstrip("/") or "/"
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "XForwarder REST API",
            "version": version,
            "description": (
                "Complete programmatic REST API for managing XForwarder multi-path relay rules, "
                "priorities, failover overrides, health probes, network quality telemetry, "
                "traffic accounting, relay services, API keys, and system updates. "
                "All endpoints are accessible under both `/api/...` and `/api/v1/...`."
            ),
            "license": {"name": "MIT"},
        },
        "servers": [
            {"url": clean_server, "description": "Active XForwarder Instance"},
            {"url": "https://203.0.113.10:8090", "description": "Fictional Direct Relay Example"},
            {"url": "https://203.0.113.10:8090/xfwd-admin", "description": "Fictional Secret Path Example"},
        ],
        "security": [
            {"bearerAuth": []},
            {"apiKeyAuth": []},
            {"sessionCookie": []},
            {"sessionHeader": []},
        ],
        "tags": [
            {"name": "Auth", "description": "Session authentication & identity inspection"},
            {"name": "API Keys", "description": "Scoped API key lifecycle management (admin scope)"},
            {"name": "Rules", "description": "Port forwarding rules CRUD, overrides & destination toggles"},
            {"name": "Settings", "description": "Global failover & probe engine configuration"},
            {"name": "Probing & Metrics", "description": "Live target probing, 50-probe packet loss & switch logs"},
            {"name": "Traffic", "description": "Kernel & proxy bandwidth accounting and resets"},
            {"name": "Import & Backup", "description": "Rule discovery, migration & backup import/export"},
            {"name": "Services & System", "description": "Relay service controls, network interfaces & OTA updates"},
        ],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "xfwd_key_...",
                    "description": "API Key passed via `Authorization: Bearer xfwd_...` header.",
                },
                "apiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API Key passed via `X-API-Key: xfwd_...` header.",
                },
                "sessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "xfwd_session",
                    "description": "HttpOnly session cookie obtained from `POST /api/login`.",
                },
                "sessionHeader": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Session-Token",
                    "description": "Session token header obtained from `POST /api/login`.",
                },
            },
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean", "example": False},
                        "error": {"type": "string", "example": "Unauthorized"},
                    },
                },
                "LoadBalanceTarget": {
                    "type": "object",
                    "required": ["target"],
                    "properties": {
                        "target": {"type": "string", "example": "10.200.1.2"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535, "example": 443},
                        "port_range": {"type": "string", "example": "10000-10100"},
                        "weight": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1},
                        "tunnel_iface": {"type": "string", "example": "gre1"},
                        "enabled": {"type": "boolean", "default": True},
                        "comment": {"type": "string", "example": "Exit Node A"},
                    },
                },
                "Destination": {
                    "type": "object",
                    "required": ["target"],
                    "properties": {
                        "priority": {"type": "integer", "minimum": 1, "example": 1},
                        "type": {
                            "type": "string",
                            "enum": [
                                "haproxy",
                                "nginx",
                                "nftables",
                                "nftables_dsr",
                                "nftables_dsr_relay",
                                "nftables_dsr_synack",
                                "nftables_dsr_direct",
                            ],
                            "example": "haproxy",
                        },
                        "target": {"type": "string", "example": "2001:db8:1::10"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535, "example": 443},
                        "port_range": {"type": "string", "example": "10000-10100"},
                        "tunnel_iface": {"type": "string", "example": "gre1"},
                        "ingress_iface": {"type": "string", "example": "ipip1"},
                        "spoof_ip": {"type": "string", "example": "203.0.113.10"},
                        "snat_ip": {"type": "string", "example": "198.51.100.20"},
                        "exit_target": {"type": "string", "example": "198.51.100.50"},
                        "exit_port": {"type": "integer", "minimum": 1, "maximum": 65535, "example": 1036},
                        "proxy_protocol": {"type": "boolean", "default": False},
                        "is_relay": {"type": "boolean", "default": False},
                        "enabled": {"type": "boolean", "default": True},
                        "comment": {"type": "string", "example": "Primary IPv6 Exit"},
                        "lb_enabled": {"type": "boolean", "default": False},
                        "lb_mode": {
                            "type": "string",
                            "enum": ["ip_hash", "round_robin", "random", "least_conn"],
                            "example": "ip_hash",
                        },
                        "lb_targets": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/LoadBalanceTarget"},
                        },
                    },
                },
                "Rule": {
                    "type": "object",
                    "required": ["port", "destinations"],
                    "properties": {
                        "id": {"type": "string", "example": "rule-443"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535, "example": 443},
                        "port_range": {"type": "string", "example": "10000-20000"},
                        "excluded_ports": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 1, "maximum": 65535},
                            "example": [22, 8090],
                        },
                        "protocol": {"type": "string", "enum": ["tcp", "udp", "both"], "default": "both"},
                        "category": {"type": "string", "maxLength": 48, "example": "Primary Relays"},
                        "active_priority": {"type": "integer", "minimum": 1, "default": 1},
                        "force_override": {"type": "integer", "minimum": 0, "default": 0},
                        "max_primary_latency_ms": {"type": "integer", "minimum": 50, "maximum": 1000, "example": 150},
                        "created_at": {"type": "number", "example": 1760000000.0},
                        "destinations": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"$ref": "#/components/schemas/Destination"},
                        },
                    },
                },
                "ApiKeyCreate": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string", "maxLength": 64, "example": "Automation Bot"},
                        "scope": {"type": "string", "enum": ["read", "write", "admin"], "default": "admin"},
                        "expires_in_days": {"type": "integer", "minimum": 0, "example": 90},
                    },
                },
                "ApiKeyMetadata": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "example": "key_a1b2c3d4"},
                        "name": {"type": "string", "example": "Automation Bot"},
                        "prefix": {"type": "string", "example": "xfwd_key_a1b2c3d4_9f8e..."},
                        "scope": {"type": "string", "enum": ["read", "write", "admin"]},
                        "enabled": {"type": "boolean"},
                        "expired": {"type": "boolean"},
                        "created_at": {"type": "number"},
                        "expires_at": {"type": "number"},
                        "last_used_at": {"type": "number"},
                    },
                },
                "GlobalSettings": {
                    "type": "object",
                    "properties": {
                        "wan_interface": {"type": "string", "example": "auto"},
                        "check_interval_seconds": {"type": "integer", "minimum": 2, "maximum": 120},
                        "probe_count": {"type": "integer", "minimum": 5, "maximum": 20},
                        "probe_interval_ms": {"type": "integer", "minimum": 200, "maximum": 1000},
                        "quality_window_seconds": {"type": "integer", "minimum": 60, "maximum": 1800},
                        "failure_threshold": {"type": "integer", "minimum": 1, "maximum": 10},
                        "recovery_threshold": {"type": "integer", "minimum": 1, "maximum": 10},
                        "fast_failover_enabled": {"type": "boolean"},
                        "max_acceptable_loss": {"type": "integer", "minimum": 5, "maximum": 90},
                        "critical_loss_percent": {"type": "integer", "minimum": 10, "maximum": 90},
                        "cooldown_seconds": {"type": "integer", "minimum": 10, "maximum": 600},
                        "min_hold_seconds": {"type": "integer", "minimum": 60, "maximum": 3600},
                        "switch_confirm_seconds": {"type": "integer", "minimum": 30, "maximum": 900},
                        "hysteresis_percent": {"type": "number", "minimum": 0, "maximum": 50},
                        "loss_penalty_weight": {"type": "integer", "minimum": 1, "maximum": 50},
                        "jitter_penalty_weight": {"type": "integer", "minimum": 0, "maximum": 10},
                        "priority_bias_ms": {"type": "integer", "minimum": 0, "maximum": 200},
                        "fast_probe_burst": {"type": "integer", "minimum": 1, "maximum": 10},
                        "target_probe_interval_seconds": {"type": "integer", "minimum": 5, "maximum": 3600},
                        "fast_liveness_interval_seconds": {"type": "integer", "minimum": 5, "maximum": 300},
                        "max_primary_latency_ms": {"type": "integer", "minimum": 50, "maximum": 1000},
                    },
                },
            },
        },
        "paths": {
            "/api/login": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Authenticate with admin username & password",
                    "security": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["username", "password"],
                                    "properties": {
                                        "username": {"type": "string", "example": "admin"},
                                        "password": {"type": "string", "example": "StrongPassword!123"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Authenticated; returns session token & sets cookie"},
                        "401": {"description": "Invalid credentials"},
                        "429": {"description": "Brute-force lockout active"},
                    },
                }
            },
            "/api/logout": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Invalidate current session token",
                    "responses": {"200": {"description": "Logged out"}},
                }
            },
            "/api/me": {
                "get": {
                    "tags": ["Auth"],
                    "summary": "Inspect current authentication context (session or API key)",
                    "responses": {"200": {"description": "Authentication status, auth_type, username, scope"}},
                }
            },
            "/api/health": {
                "get": {
                    "tags": ["Services & System"],
                    "summary": "Lightweight health check (requires read scope)",
                    "responses": {"200": {"description": "Service healthy"}},
                }
            },
            "/api/status": {
                "get": {
                    "tags": ["Services & System"],
                    "summary": "Full dashboard snapshot (config, runtime state, system stats, services, traffic)",
                    "responses": {"200": {"description": "Complete system status"}},
                }
            },
            "/api/openapi.json": {
                "get": {
                    "tags": ["Services & System"],
                    "summary": "Retrieve OpenAPI 3.0.3 JSON specification",
                    "responses": {"200": {"description": "OpenAPI JSON document"}},
                }
            },
            "/api/api-keys": {
                "get": {
                    "tags": ["API Keys"],
                    "summary": "List configured API keys (admin scope)",
                    "responses": {"200": {"description": "Array of ApiKeyMetadata"}},
                },
                "post": {
                    "tags": ["API Keys"],
                    "summary": "Generate a new scoped API key (admin scope)",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiKeyCreate"}}},
                    },
                    "responses": {"201": {"description": "API key created; raw key returned once"}},
                },
            },
            "/api/api-keys/{id}": {
                "patch": {
                    "tags": ["API Keys"],
                    "summary": "Update API key name, scope, or enabled flag (admin scope)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "API key updated"}, "404": {"description": "Key not found"}},
                },
                "delete": {
                    "tags": ["API Keys"],
                    "summary": "Revoke and delete an API key (admin scope)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "API key deleted"}, "404": {"description": "Key not found"}},
                },
            },
            "/api/rules": {
                "get": {
                    "tags": ["Rules"],
                    "summary": "List forwarding rules with optional filters (read scope)",
                    "parameters": [
                        {"name": "category", "in": "query", "schema": {"type": "string"}},
                        {"name": "protocol", "in": "query", "schema": {"type": "string", "enum": ["tcp", "udp", "both"]}},
                        {"name": "type", "in": "query", "schema": {"type": "string"}},
                        {"name": "port", "in": "query", "schema": {"type": "integer"}},
                        {"name": "include_runtime", "in": "query", "schema": {"type": "boolean"}},
                    ],
                    "responses": {"200": {"description": "List of rules"}},
                },
                "post": {
                    "tags": ["Rules"],
                    "summary": "Create a new forwarding rule (write scope)",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Rule"}}},
                    },
                    "responses": {
                        "201": {"description": "Rule created and synchronized"},
                        "400": {"description": "Validation error"},
                        "409": {"description": "Port/ID conflict"},
                    },
                },
            },
            "/api/rule": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Create or upsert a forwarding rule (write scope)",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Rule"}}},
                    },
                    "responses": {"200": {"description": "Rule saved and synchronized"}},
                }
            },
            "/api/rules/{id}": {
                "get": {
                    "tags": ["Rules"],
                    "summary": "Get single rule details and runtime state (read scope)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Rule found"}, "404": {"description": "Rule not found"}},
                },
                "put": {
                    "tags": ["Rules"],
                    "summary": "Replace an existing forwarding rule (write scope)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Rule"}}},
                    },
                    "responses": {"200": {"description": "Rule replaced"}, "404": {"description": "Rule not found"}},
                },
                "patch": {
                    "tags": ["Rules"],
                    "summary": "Partially update fields of an existing rule (write scope)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "responses": {"200": {"description": "Rule updated"}, "404": {"description": "Rule not found"}},
                },
                "delete": {
                    "tags": ["Rules"],
                    "summary": "Delete a forwarding rule by ID or port (write scope)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Rule deleted"}},
                },
            },
            "/api/rules/bulk-delete": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Delete multiple forwarding rules by ID (write scope)",
                    "responses": {"200": {"description": "Rules deleted"}},
                }
            },
            "/api/rules/{id}/override": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Force specific priority or restore Auto Failover (0) (write scope)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Override applied"}},
                }
            },
            "/api/override": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Set priority override by rule_id in JSON body (write scope)",
                    "responses": {"200": {"description": "Override applied"}},
                }
            },
            "/api/override/batch": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Apply priority override across all rules (write scope)",
                    "responses": {"200": {"description": "Batch override applied"}},
                }
            },
            "/api/rules/{id}/destinations/{priority}/toggle": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Enable/disable a specific destination priority within a rule (write scope)",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "priority", "in": "path", "required": True, "schema": {"type": "integer"}},
                    ],
                    "responses": {"200": {"description": "Destination toggled"}},
                }
            },
            "/api/rule/toggle-destination": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Toggle destination enabled state via body payload (write scope)",
                    "responses": {"200": {"description": "Destination toggled"}},
                }
            },
            "/api/sync": {
                "post": {
                    "tags": ["Rules"],
                    "summary": "Force immediate HAProxy/Nginx/NFTables ruleset sync & engine wakeup (write scope)",
                    "responses": {"200": {"description": "Rules synchronized"}},
                }
            },
            "/api/settings": {
                "get": {
                    "tags": ["Settings"],
                    "summary": "Read global failover & probing settings (read scope)",
                    "responses": {"200": {"description": "Global settings"}},
                },
                "put": {
                    "tags": ["Settings"],
                    "summary": "Replace global failover & probing settings (admin scope)",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GlobalSettings"}}},
                    },
                    "responses": {"200": {"description": "Settings saved"}},
                },
                "patch": {
                    "tags": ["Settings"],
                    "summary": "Partially update global failover & probing settings (admin scope)",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GlobalSettings"}}},
                    },
                    "responses": {"200": {"description": "Settings saved"}},
                },
            },
            "/api/test-target": {
                "post": {
                    "tags": ["Probing & Metrics"],
                    "summary": "Run live ICMP/L4 TCP probe or 50-packet loss test on a destination (write scope)",
                    "responses": {"200": {"description": "Probe result"}},
                }
            },
            "/api/test-loss": {
                "post": {
                    "tags": ["Probing & Metrics"],
                    "summary": "Run 50-probe ICMP packet loss test and store in SQLite (write scope)",
                    "responses": {"200": {"description": "Loss measurement result"}},
                }
            },
            "/api/metrics/loss-history": {
                "get": {
                    "tags": ["Probing & Metrics"],
                    "summary": "Query 30-day packet loss & latency history (read scope)",
                    "responses": {"200": {"description": "Metrics history"}},
                }
            },
            "/api/metrics/trigger-round": {
                "post": {
                    "tags": ["Probing & Metrics"],
                    "summary": "Trigger immediate 50-probe round across all unique targets (write scope)",
                    "responses": {"200": {"description": "Round results"}},
                }
            },
            "/api/logs/switches": {
                "get": {
                    "tags": ["Probing & Metrics"],
                    "summary": "Retrieve recent automated failover switch decision events (read scope)",
                    "parameters": [
                        {"name": "rule_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                    ],
                    "responses": {"200": {"description": "Switch events list"}},
                }
            },
            "/api/traffic/summary": {
                "get": {
                    "tags": ["Traffic"],
                    "summary": "Get bandwidth accounting summary (read scope)",
                    "responses": {"200": {"description": "Traffic summary"}},
                }
            },
            "/api/traffic/timeseries": {
                "get": {
                    "tags": ["Traffic"],
                    "summary": "Get hourly/daily/monthly bandwidth time-series (read scope)",
                    "responses": {"200": {"description": "Traffic timeseries"}},
                }
            },
            "/api/traffic/reset": {
                "post": {
                    "tags": ["Traffic"],
                    "summary": "Reset billing cycle counter or wipe entity history (write scope)",
                    "responses": {"200": {"description": "Counter reset"}},
                }
            },
            "/api/import/discover": {
                "get": {
                    "tags": ["Import & Backup"],
                    "summary": "Discover unmanaged HAProxy/Nginx/NFTables rules on host (read scope)",
                    "responses": {"200": {"description": "Discovered rules"}},
                }
            },
            "/api/import/haproxy": {
                "post": {"tags": ["Import & Backup"], "summary": "Import discovered HAProxy rules (write scope)", "responses": {"200": {"description": "Imported"}}}
            },
            "/api/import/nftables": {
                "post": {"tags": ["Import & Backup"], "summary": "Import discovered NFTables rules (write scope)", "responses": {"200": {"description": "Imported"}}}
            },
            "/api/import/all": {
                "post": {"tags": ["Import & Backup"], "summary": "Import all discovered relay rules (write scope)", "responses": {"200": {"description": "Imported"}}}
            },
            "/api/config/export": {
                "get": {
                    "tags": ["Import & Backup"],
                    "summary": "Export sanitized configuration JSON backup (read scope)",
                    "responses": {"200": {"description": "Sanitized backup JSON"}},
                }
            },
            "/api/config/import": {
                "post": {
                    "tags": ["Import & Backup"],
                    "summary": "Import configuration JSON in merge or replace mode (write scope)",
                    "responses": {"200": {"description": "Configuration imported"}},
                }
            },
            "/api/services/status": {
                "get": {"tags": ["Services & System"], "summary": "Get relay engines installation & active state (read scope)", "responses": {"200": {"description": "Services status"}}}
            },
            "/api/services/restart": {
                "post": {"tags": ["Services & System"], "summary": "Reload or restart relay/web/engine services (admin scope)", "responses": {"200": {"description": "Action executed"}}}
            },
            "/api/network/interfaces": {
                "get": {"tags": ["Services & System"], "summary": "Inspect WAN IPs and tunnel interfaces (read scope)", "responses": {"200": {"description": "Network topology"}}}
            },
            "/api/system/version": {
                "get": {"tags": ["Services & System"], "summary": "Get installed & remote version status (read scope)", "responses": {"200": {"description": "Version info"}}}
            },
            "/api/system/update/transports": {
                "get": {"tags": ["Services & System"], "summary": "Discover update transport options (read scope)", "responses": {"200": {"description": "Available transports"}}},
                "post": {"tags": ["Services & System"], "summary": "Configure update transport mode (admin scope)", "responses": {"200": {"description": "Transport saved"}}},
            },
            "/api/system/update": {
                "post": {"tags": ["Services & System"], "summary": "Trigger asynchronous system update (admin scope)", "responses": {"200": {"description": "Update started"}}}
            },
            "/api/system/update/status": {
                "get": {"tags": ["Services & System"], "summary": "Poll system update status & logs (read scope)", "responses": {"200": {"description": "Update status"}}}
            },
            "/api/system/optimize": {
                "get": {"tags": ["Services & System"], "summary": "Inspect live kernel & network tuning status and conflicts (read scope)", "responses": {"200": {"description": "Kernel optimization telemetry"}}},
                "post": {"tags": ["Services & System"], "summary": "Apply ESP/DSR-safe kernel & BBR tuning with optional cleanup reset (admin scope)", "responses": {"200": {"description": "Tuning applied"}}}
            },
            "/api/security/credentials": {
                "post": {"tags": ["Auth"], "summary": "Update admin username/password (admin scope)", "responses": {"200": {"description": "Credentials updated"}}}
            },
            "/api/security/panel": {
                "post": {"tags": ["Auth"], "summary": "Update web panel listening port & secret path (admin scope)", "responses": {"200": {"description": "Panel access updated"}}}
            },
        },
    }
