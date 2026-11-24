# 📡 XForwarder Complete REST API Documentation

Full programmatic REST API reference for **XForwarder** (automation scripts, billing panels, monitoring, and CI/CD).

> [!NOTE]
> **Fictional Documentation IPs:**  
> Every IP address and hostname in this documentation uses RFC 5737 / RFC 3849 / RFC 1918 documentation ranges:
> - Relay Server Public IPv4: `203.0.113.10`
> - Exit Server Public IPv4: `198.51.100.20`, `198.51.100.21`, `192.0.2.50`
> - Exit Server Public IPv6: `2001:db8:1::10`, `2001:db8:2::20`
> - Tunnel Private IPv4: `10.200.1.2`, `10.200.1.3`, `10.200.2.2`
> - Fictional Hostname: `exit1.example.net`

---

## 1. Base URL, Versioning & Supported Methods

All endpoints are exposed under both `/api/*` and `/api/v1/*`:
- Direct: `https://203.0.113.10:8090/api/v1/...`
- With `secret_path` (e.g. `xfwd-admin`):
  - Login (`POST /login`) requires the secret prefix: `https://203.0.113.10:8090/xfwd-admin/api/v1/login`
  - API Key requests (`Authorization: Bearer` or `X-API-Key`) work on both `/api/v1/...` and `/xfwd-admin/api/v1/...`.

Supported HTTP methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`.

---

## 2. Authentication & Scopes

### A. Scoped API Keys (Recommended)
Generate keys in **Security → REST API & API Keys** or via `POST /api/v1/api-keys` and pass them in either header:
- `Authorization: Bearer xfwd_key_...`
- `X-API-Key: xfwd_key_...`

| Scope | Allowed Operations |
| :--- | :--- |
| `read` | All `GET` endpoints (`/status`, `/health`, `/rules`, `/settings`, `/traffic/*`, `/metrics/*`, `/logs/switches`, `/services/status`, `/network/interfaces`, `/config/export`, `/openapi.json`, `/me`). |
| `write` | All `read` endpoints + rule CRUD (`POST`/`PUT`/`PATCH`/`DELETE`), overrides, destination toggles, `/sync`, `/test-target`, `/test-loss`, `/metrics/trigger-round`, `/traffic/reset`, and imports. |
| `admin` | Full access: all `write` endpoints + `/api-keys*`, `/settings` mutations, `/services/restart`, `/system/update*`, and `/security/*`. |

### B. Session Authentication
- `POST /xfwd-admin/api/v1/login` with `{"username":"admin","password":"StrongPassword!123"}` (5 failures within 5m triggers 15m IP lockout with HTTP `429`).
- Use `X-Session-Token: <token>` header or `xfwd_session` cookie.
- `GET /api/v1/me` inspects current auth context (`authenticated`, `auth_type`, `username`, `scope`, `key_id`, `key_name`).
- `POST /api/v1/logout` invalidates the session.

---

## 3. API Key Management (`admin` scope)

- `GET /api/v1/api-keys` — List API key metadata (never returns raw secret or `key_hash`).
- `POST /api/v1/api-keys` — Create key (`{"name":"Automation","scope":"write","expires_in_days":90}`), returns `201 Created` with one-time `api_key`.
- `PATCH /api/v1/api-keys/{id}` — Update `name`, `scope`, or `enabled`.
- `DELETE /api/v1/api-keys/{id}` — Revoke and delete key.

```bash
curl -s -X POST "https://203.0.113.10:8090/api/v1/api-keys" \
  -H "Authorization: Bearer <ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Billing Sync","scope":"write","expires_in_days":365}'
```

---

## 4. Forwarding Rules CRUD & All Forwarding Modes

### Destination Types (`type`)
- `haproxy` — Direct Layer-4 relay (requires valid IPv6 `target`; optional `proxy_protocol: true`).
- `nginx` — Stream TCP/UDP proxy (IPv4/IPv6/hostname; supports `proxy_protocol` and `lb_enabled` pools with `ip_hash`, `least_conn`, `round_robin`, `random`).
- `nftables` — Kernel Layer-3 DNAT (numeric IPv4/IPv6; supports `tunnel_iface`, `port_range`, `excluded_ports`, and `lb_enabled` pools with `ip_hash`, `round_robin`, `random`).
- `nftables_dsr` — Stateless DSR on relay (`target` port must match inbound port; optional `spoof_ip`, `tunnel_iface`).
- `nftables_dsr_relay` — Intermediate DSR relay (requires `spoof_ip`; optional `ingress_iface`, `snat_ip`).
- `nftables_dsr_synack` — TCP-only IPv4 SYN-ACK DSR (`protocol: "tcp"`).
- `nftables_dsr_direct` — Direct outside DSR receiver (`protocol: "tcp"`, IPv4 only, requires `spoof_ip` and `ingress_iface`).

### Endpoints
- `GET /api/v1/rules` (`read`) — Optional filters: `?category=`, `?protocol=`, `?type=`, `?port=`, `?include_runtime=true|false`
- `GET /api/v1/rules/{id}` (`read`) — Fetch single rule (by ID or port) + runtime metrics
- `POST /api/v1/rules` (`write`) — Create rule (`201 Created`, `409 Conflict` if ID exists)
- `POST /api/v1/rule` (`write`) — Create or upsert rule (`200 OK`)
- `PUT /api/v1/rules/{id}` (`write`) — Full rule replacement
- `PATCH /api/v1/rules/{id}` (`write`) — Partial rule update
- `DELETE /api/v1/rules/{id}` (`write`) — Delete rule by ID or port
- `POST /api/v1/rules/bulk-delete` (`write`) — Delete multiple rules (`{"rule_ids":[...]}`)

```bash
# Create multi-path rule (HAProxy IPv6 + NFTables GRE tunnel backup)
curl -s -X POST "https://203.0.113.10:8090/api/v1/rules" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "port": 443,
    "protocol": "both",
    "category": "Main",
    "destinations": [
      {"priority": 1, "type": "haproxy", "target": "2001:db8:1::10", "port": 443},
      {"priority": 2, "type": "nftables", "target": "10.200.1.2", "port": 443, "tunnel_iface": "gre1", "is_relay": true}
    ]
  }'

# Partial update (PATCH)
curl -s -X PATCH "https://203.0.113.10:8090/api/v1/rules/rule-443" \
  -H "Authorization: Bearer <WRITE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"category":"VIP","max_primary_latency_ms":180}'
```

---

## 5. Failover Control, Global Settings, Probing, Traffic & System

- **Override**: `POST /api/v1/rules/{id}/override` (`{"force_override": 0|1..N}`) & `POST /api/v1/override/batch` (`write`)
- **Toggle Destination**: `POST /api/v1/rules/{id}/destinations/{priority}/toggle` (`{"enabled": true|false}`) (`write`)
- **Sync Rules**: `POST /api/v1/sync` (`write`)
- **Global Settings**: `GET /api/v1/settings` (`read`), `PUT` / `PATCH /api/v1/settings` (`admin`)
- **Probing & Metrics**: `POST /api/v1/test-target`, `POST /api/v1/test-loss`, `POST /api/v1/metrics/trigger-round` (`write`), `GET /api/v1/metrics/loss-history`, `GET /api/v1/logs/switches` (`read`)
- **Traffic**: `GET /api/v1/traffic/summary`, `GET /api/v1/traffic/timeseries` (`read`), `POST /api/v1/traffic/reset` (`write`)
- **Discovery & Backup**: `GET /api/v1/import/discover`, `GET /api/v1/config/export` (`read`), `POST /api/v1/import/haproxy|nftables|all`, `POST /api/v1/config/import` (`write`)
- **Services & Updates**: `GET /api/v1/health`, `GET /api/v1/status`, `GET /api/v1/services/status`, `GET /api/v1/network/interfaces`, `GET /api/v1/system/version`, `GET /api/v1/system/update/transports`, `GET /api/v1/system/update/status` (`read`); `POST /api/v1/services/restart`, `POST /api/v1/system/update`, `POST /api/v1/system/update/transports`, `POST /api/v1/security/credentials`, `POST /api/v1/security/panel` (`admin`)
- **OpenAPI 3.0.3 Schema**: `GET /api/v1/openapi.json` (`read`)
