#!/usr/bin/env python3
"""
XForwarder - Service Controller & System Update Manager
Provides granular service restart controls and decoupled update orchestration.
"""

import os
import sys
import glob
import json
import time
import shutil
import threading
import subprocess
import tempfile
import urllib.request
import re
from typing import Dict, Any, Tuple, Optional, List, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_VERSION = "1.5.0"

_REMOTE_VERSION_CACHE: Dict[str, Any] = {"data": None, "expires": 0}
_REMOTE_VERSION_LOCK = threading.Lock()

_UPDATE_STATE: Dict[str, Any] = {
    "status": "idle",
    "start_time": 0.0,
    "pid": None,
    "error": None
}
_UPDATE_LOCK = threading.Lock()


def get_update_state_file_path() -> str:
    """Returns persistent update state file path in /run/xforwarder or system temp."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "update_state.json")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/update_state.json"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_update_state.json")


def save_update_state(state: dict, path_override: Optional[str] = None) -> None:
    """Atomically persists update progress state to disk."""
    path = path_override or get_update_state_file_path()
    try:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except Exception:
        pass


def load_update_state(path_override: Optional[str] = None) -> None:
    """Loads update progress state across daemon reloads."""
    path = path_override or get_update_state_file_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                with _UPDATE_LOCK:
                    _UPDATE_STATE.update(data)
        except Exception:
            pass


load_update_state()


def get_installed_version() -> str:
    """Reads script version from xforwarder.sh or returns default APP_VERSION."""
    script_candidates = [
        "/opt/xforwarder/xforwarder.sh",
        os.path.join(BASE_DIR, "xforwarder.sh"),
        "/usr/local/bin/xforwarder"
    ]
    for s in script_candidates:
        if os.path.exists(s):
            try:
                with open(s, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("SCRIPT_VERSION="):
                            v = line.split("=")[1].strip().strip('"').strip("'")
                            if v:
                                return v
            except Exception:
                pass
    return APP_VERSION


def get_local_version_info() -> dict:
    """Inspects local git repository, .commit metadata files, or installed package version."""
    version = get_installed_version()
    info = {
        "version": version,
        "commit": None,
        "commit_date": None,
        "is_git": False
    }

    commit_file_candidates = [
        os.path.join(BASE_DIR, ".commit"),
        "/opt/xforwarder/.commit",
        "/etc/xforwarder/.commit",
    ]
    for c_path in commit_file_candidates:
        if os.path.isfile(c_path):
            try:
                with open(c_path, "r", encoding="utf-8", errors="replace") as f:
                    c_val = f.read().strip()
                if c_val:
                    info["commit"] = c_val[:7]
                    d_path = c_path.replace(".commit", ".commit_date")
                    if os.path.isfile(d_path):
                        with open(d_path, "r", encoding="utf-8", errors="replace") as df:
                            info["commit_date"] = df.read().strip()
                    break
            except Exception:
                pass

    git_dirs = [
        BASE_DIR,
        "/opt/xforwarder",
        os.path.join(os.path.dirname(BASE_DIR), "XForwarder"),
        os.path.join(os.path.dirname(BASE_DIR), "Forward-Manager"),
        "/root/XForwarder",
        "/root/Forward-Manager",
    ]
    for g_dir in git_dirs:
        if os.path.isdir(os.path.join(g_dir, ".git")):
            try:
                res = subprocess.run(
                    ["git", "-C", g_dir, "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=2.0
                )
                if res.returncode == 0 and res.stdout.strip():
                    info["commit"] = res.stdout.strip()
                    info["is_git"] = True
                    res_date = subprocess.run(
                        ["git", "-C", g_dir, "log", "-1", "--format=%cd", "--date=short"],
                        capture_output=True, text=True, timeout=2.0
                    )
                    if res_date.returncode == 0 and res_date.stdout.strip():
                        info["commit_date"] = res_date.stdout.strip()
                    break
            except Exception:
                pass

    return info


def get_remote_version_info(force: bool = False) -> dict:
    """Checks remote GitHub repository for the latest commit on main."""
    now = time.time()
    with _REMOTE_VERSION_LOCK:
        if not force and _REMOTE_VERSION_CACHE["data"] and now < _REMOTE_VERSION_CACHE["expires"]:
            return _REMOTE_VERSION_CACHE["data"]

    remote = {
        "remote_commit": None,
        "remote_commit_msg": None,
        "remote_date": None,
        "repo_url": "https://github.com/PouryaDe/XForwarder",
        "checked_at": int(now),
        "error": None
    }

    api_success = False
    url = "https://api.github.com/repos/PouryaDe/XForwarder/commits/main"
    headers = {
        "User-Agent": "XForwarder-Updater/1.0",
        "Accept": "application/vnd.github.v3+json"
    }
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token.strip()}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw)
                sha = body.get("sha", "")
                remote["remote_commit"] = sha[:7] if sha else None
                commit_info = body.get("commit", {})
                msg = commit_info.get("message", "").strip().split("\n")[0]
                remote["remote_commit_msg"] = msg
                author_date = commit_info.get("author", {}).get("date") or commit_info.get("committer", {}).get("date", "")
                if author_date:
                    remote["remote_date"] = author_date[:10]
                api_success = True
    except Exception as e:
        remote["error"] = str(e)

    if not api_success:
        try:
            res = subprocess.run(
                ["git", "ls-remote", "https://github.com/PouryaDe/XForwarder.git", "refs/heads/main"],
                capture_output=True, text=True, timeout=5.0
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split()
                if parts and len(parts[0]) >= 7:
                    remote["remote_commit"] = parts[0][:7]
                    remote["remote_commit_msg"] = "Latest release on main"
                    remote["error"] = None
                    api_success = True
        except Exception:
            pass

    with _REMOTE_VERSION_LOCK:
        _REMOTE_VERSION_CACHE["data"] = remote
        _REMOTE_VERSION_CACHE["expires"] = now + (180.0 if api_success else 30.0)

    return remote


def get_full_version_status(
    force: bool = False,
    get_local_version_fn: Optional[Any] = None,
    get_remote_version_fn: Optional[Any] = None
) -> dict:
    """Returns composite version status comparing local and remote GitHub states."""
    local_fn = get_local_version_fn or get_local_version_info
    remote_fn = get_remote_version_fn or get_remote_version_info
    local_info = local_fn()
    remote_info = remote_fn(force=force)

    update_available = False
    local_commit = (local_info.get("commit") or "").lower()
    remote_commit = (remote_info.get("remote_commit") or "").lower()

    if remote_commit:
        if local_commit:
            if local_commit != remote_commit:
                update_available = True
        else:
            update_available = True

    return {
        "ok": True,
        "current_version": local_info["version"],
        "current_commit": local_info["commit"],
        "current_date": local_info["commit_date"],
        "is_git": local_info["is_git"],
        "remote_commit": remote_info.get("remote_commit"),
        "remote_commit_msg": remote_info.get("remote_commit_msg"),
        "remote_date": remote_info.get("remote_date"),
        "repo_url": remote_info.get("repo_url"),
        "checked_at": remote_info.get("checked_at"),
        "update_available": update_available,
        "check_error": remote_info.get("error")
    }


def get_update_log_path() -> str:
    """Resolves path to update log file in /run/xforwarder or system tempdir."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "update.log")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/update.log"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_update.log")


def get_script_path() -> Optional[str]:
    """Finds executable xforwarder.sh on host."""
    candidates = [
        "/opt/xforwarder/xforwarder.sh",
        os.path.join(BASE_DIR, "xforwarder.sh"),
        "/usr/local/bin/xforwarder",
        "/usr/local/bin/xfwd"
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def start_system_update() -> Tuple[bool, str]:
    """Triggers an unattended background update via systemd-run or detached process."""
    with _UPDATE_LOCK:
        now = time.time()
        if _UPDATE_STATE["status"] == "running" and (now - _UPDATE_STATE["start_time"]) < 180:
            return False, "An update is already in progress"

        script = get_script_path()
        if not script:
            return False, "XForwarder update script (xforwarder.sh) not found on host"

        log_path = get_update_log_path()
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== XForwarder Update Initiated at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.flush()
        except Exception as e:
            return False, f"Failed to initialize update log: {e}"

        _UPDATE_STATE["status"] = "running"
        _UPDATE_STATE["start_time"] = now
        _UPDATE_STATE["error"] = None
        save_update_state(_UPDATE_STATE)

        has_systemd_run = bool(shutil.which("systemd-run"))
        ts = int(now)

        def _worker():
            try:
                cmd_str = f"DEBIAN_FRONTEND=noninteractive bash '{script}' update >> '{log_path}' 2>&1"
                if has_systemd_run:
                    unit_name = f"xfwd-updater-{ts}"
                    run_cmd = [
                        "systemd-run",
                        f"--unit={unit_name}",
                        "--description=XForwarder Web Update",
                        "bash", "-c", cmd_str
                    ]
                    res = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10.0)
                    if res.returncode != 0:
                        subprocess.Popen(["bash", "-c", cmd_str], start_new_session=True)
                else:
                    if sys.platform == "win32":
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write("[OK] XForwarder updated successfully! All services are active and running.\n")
                        with _UPDATE_LOCK:
                            _UPDATE_STATE["status"] = "completed"
                            save_update_state(_UPDATE_STATE)
                    else:
                        subprocess.Popen(["bash", "-c", cmd_str], start_new_session=True)
            except Exception as ex:
                with _UPDATE_LOCK:
                    _UPDATE_STATE["status"] = "failed"
                    _UPDATE_STATE["error"] = str(ex)
                    save_update_state(_UPDATE_STATE)
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n[ERROR] Update runner failure: {ex}\n")
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return True, "Update initiated"


def get_update_status(log_path_fn: Optional[Any] = None) -> dict:
    """Returns current update execution state and sanitized log output."""
    log_path = log_path_fn() if log_path_fn else get_update_log_path()
    raw_log = ""
    mtime = 0.0
    if os.path.exists(log_path):
        try:
            mtime = os.path.getmtime(log_path)
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                raw_log = f.read()
        except Exception:
            pass

    clean_log = re.sub(r'\x1b\[[0-9;]*m', '', raw_log)
    now = time.time()

    with _UPDATE_LOCK:
        mem_status = _UPDATE_STATE["status"]
        start_time = _UPDATE_STATE["start_time"]

    status = "idle"
    is_recent_success = "XForwarder updated successfully!" in clean_log and (
        (start_time > 0 and mtime >= start_time - 5) or (mtime > 0 and (now - mtime) < 180)
    )
    if is_recent_success:
        status = "completed"
        with _UPDATE_LOCK:
            _UPDATE_STATE["status"] = "completed"
            save_update_state(_UPDATE_STATE)
    elif mem_status == "running":
        if (now - start_time) > 300:
            status = "failed"
            with _UPDATE_LOCK:
                _UPDATE_STATE["status"] = "failed"
                save_update_state(_UPDATE_STATE)
        else:
            status = "running"
    elif mtime > 0 and (now - mtime) < 45 and (start_time == 0 or (now - start_time) < 300):
        status = "running"
    elif ("Could not pull updates" in clean_log or "Failed to install" in clean_log or "[ERROR]" in clean_log) and (
        (start_time > 0 and mtime >= start_time - 5) or (mtime > 0 and (now - mtime) < 180)
    ):
        status = "failed"
        with _UPDATE_LOCK:
            _UPDATE_STATE["status"] = "failed"
            save_update_state(_UPDATE_STATE)

    return {
        "ok": True,
        "status": status,
        "start_time": start_time,
        "log": clean_log[-12000:] if len(clean_log) > 12000 else clean_log
    }


def _strip_nginx_comments(text: str) -> str:
    """Strips `#` comments from Nginx configuration lines."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _parse_nginx_listen_directive(arg_str: str) -> Tuple[Optional[int], str]:
    """Parses `listen [addr:]port [udp|...]` into `(port, 'tcp'|'udp')`."""
    tokens = arg_str.strip().split()
    if not tokens:
        return None, "tcp"
    proto = "udp" if any(t.lower() == "udp" for t in tokens[1:]) else "tcp"
    addr_tok = tokens[0].strip()
    m = re.match(r"^(?:\[[^\]]+\]:|[^:\s]+:)?(\d{1,5})$", addr_tok)
    if not m:
        return None, proto
    p = int(m.group(1))
    return (p if 1 <= p <= 65535 else None), proto


def _parse_nginx_host_port(raw_addr: str) -> Tuple[str, Optional[int]]:
    """Extracts `(host, port)` from `host:port` or `[ipv6]:port`."""
    s = raw_addr.strip()
    m_v6 = re.match(r"^\[([0-9a-fA-F:]+)\]:(\d{1,5})$", s)
    if m_v6:
        p = int(m_v6.group(2))
        return m_v6.group(1), (p if 1 <= p <= 65535 else None)
    m_v4 = re.match(r"^([^:\s]+):(\d{1,5})$", s)
    if m_v4:
        p = int(m_v4.group(2))
        return m_v4.group(1), (p if 1 <= p <= 65535 else None)
    return "", None


def parse_nginx_stream_endpoints(
    nginx_paths: Optional[List[str]] = None
) -> Dict[int, List[Tuple[str, str, int]]]:
    """
    Parses active Nginx `stream { server { listen ...; proxy_pass ...; } }` blocks.
    Returns `{inbound_port: [(protocol, target_host, target_port), ...]}`.
    Returns `{}` when Nginx is uninstalled or has no stream forwarding entries.
    """
    if nginx_paths is None:
        paths: List[str] = []
        if os.path.isfile("/etc/nginx/nginx.conf"):
            paths.append("/etc/nginx/nginx.conf")
        for pat in (
            "/etc/nginx/conf.d/*.conf",
            "/etc/nginx/streams-enabled/*",
            "/etc/nginx/stream.d/*.conf",
        ):
            paths.extend(sorted(glob.glob(pat)))
    else:
        paths = [p for p in nginx_paths if os.path.isfile(p)]

    if not paths:
        return {}

    upstreams: Dict[str, Tuple[str, int]] = {}
    raw_entries: Dict[Tuple[int, str, int], Set[str]] = {}

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                cleaned = _strip_nginx_comments(f.read())
        except Exception:
            continue

        # Treat standalone files in streams-enabled / stream.d as already inside stream context
        in_stream_file = ("streams-enabled" in path or "stream.d" in path)
        depth = 0
        stream_depth = 0 if in_stream_file else -1
        http_depth = -1
        upstream_name = ""
        upstream_depth = -1
        in_server = False
        server_depth = -1
        cur_listens: List[Tuple[int, str]] = []
        cur_proxy_raw = ""

        # Tokenize braces and semicolons to handle single-line and multi-line Nginx blocks uniformly
        tokens = re.findall(r"[{}]|\n|[^;{}\n]+;?", cleaned)
        for tok in tokens:
            s = tok.strip()
            if not s:
                continue
            if s == "{":
                depth += 1
                continue
            if s == "}":
                depth = max(0, depth - 1)
                if in_server and depth <= server_depth:
                    if cur_proxy_raw:
                        tgt_host, tgt_port = _parse_nginx_host_port(cur_proxy_raw)
                        if not tgt_host and cur_proxy_raw in upstreams:
                            tgt_host, tgt_port = upstreams[cur_proxy_raw]
                        if tgt_host and tgt_port:
                            for lp, lproto in cur_listens:
                                raw_entries.setdefault((lp, tgt_host, tgt_port), set()).add(lproto)
                    in_server = False
                    server_depth = -1
                    cur_listens = []
                    cur_proxy_raw = ""
                if upstream_name and depth <= upstream_depth:
                    upstream_name = ""
                    upstream_depth = -1
                if not in_stream_file and stream_depth >= 0 and depth <= stream_depth:
                    stream_depth = -1
                if http_depth >= 0 and depth <= http_depth:
                    http_depth = -1
                continue

            stmt = s.rstrip(";").strip()
            low = stmt.lower()
            if re.match(r"^stream\b", low):
                stream_depth = depth
                continue
            if re.match(r"^http\b", low):
                http_depth = depth
                continue
            if http_depth >= 0 and stream_depth < 0:
                continue

            m_up = re.match(r"^upstream\s+(\S+)$", stmt, re.IGNORECASE)
            if m_up and (stream_depth >= 0 or in_stream_file):
                upstream_name = m_up.group(1).strip()
                upstream_depth = depth
                continue

            if upstream_name:
                m_srv = re.match(r"^server\s+(\S+)", stmt, re.IGNORECASE)
                if m_srv and upstream_name not in upstreams:
                    uh, up = _parse_nginx_host_port(m_srv.group(1))
                    if uh and up:
                        upstreams[upstream_name] = (uh, up)
                continue

            if low == "server" and (stream_depth >= 0 or in_stream_file):
                in_server = True
                server_depth = depth
                cur_listens = []
                cur_proxy_raw = ""
                continue

            if in_server:
                m_listen = re.match(r"^listen\s+(.+)$", stmt, re.IGNORECASE)
                if m_listen:
                    lp, lproto = _parse_nginx_listen_directive(m_listen.group(1))
                    if lp is not None:
                        cur_listens.append((lp, lproto))
                    continue
                m_pass = re.match(r"^proxy_pass\s+(\S+)", stmt, re.IGNORECASE)
                if m_pass:
                    cur_proxy_raw = m_pass.group(1).strip()

    grouped: Dict[int, List[Tuple[str, str, int]]] = {}
    for (lp, thost, tport), protos in sorted(raw_entries.items()):
        proto = "both" if protos == {"tcp", "udp"} else next(iter(protos))
        grouped.setdefault(lp, []).append((proto, thost, tport))
    return grouped


def sync_xforwarder_from_nginx(
    config_path: Optional[str] = None,
    nginx_paths: Optional[List[str]] = None,
    sync_rules_func=None,
    notify_func=None,
) -> Tuple[bool, str, bool]:
    """
    Reconciles XForwarder `config.json` from Nginx stream configs (Nginx -> XForwarder).
    Removes `nginx` destinations that no longer exist in Nginx (including all when Nginx is empty)
    and imports missing Nginx stream servers into `config.json` atomically.
    """
    try:
        from core.config_manager import get_config_path, load_config, save_config, validate_rule
    except ImportError:
        from config_manager import get_config_path, load_config, save_config, validate_rule

    path = get_config_path(config_path)
    cfg = load_config(path)
    nginx_map = parse_nginx_stream_endpoints(nginx_paths=nginx_paths)

    removed_dests = 0
    removed_rules = 0
    added_rules = 0
    new_rules: List[Dict[str, Any]] = []
    existing_nginx_keys: Set[Tuple[int, str, int]] = set()
    rules_by_port: Dict[int, Dict[str, Any]] = {}

    for rule in cfg.get("rules", []):
        if not isinstance(rule, dict):
            continue
        r_port = rule.get("port")
        is_range = bool(rule.get("port_range"))
        dests = rule.get("destinations", [])
        if is_range or not isinstance(dests, list):
            new_rules.append(rule)
            continue

        kept_dests: List[Dict[str, Any]] = []
        removed_prios: Set[int] = set()
        active_set = set()
        for proto, thost, tport in nginx_map.get(r_port, []):
            active_set.add((thost.strip("[]"), tport))

        for d in dests:
            if str(d.get("type", "")).lower() == "nginx":
                d_host = str(d.get("target", "")).strip().strip("[]")
                try:
                    d_port = int(d.get("port") or r_port)
                except (ValueError, TypeError):
                    d_port = r_port
                if (d_host, d_port) in active_set:
                    kept_dests.append(d)
                    existing_nginx_keys.add((r_port, d_host, d_port))
                else:
                    removed_dests += 1
                    try:
                        removed_prios.add(int(d.get("priority", 0)))
                    except (ValueError, TypeError):
                        pass
            else:
                kept_dests.append(d)

        if not kept_dests:
            removed_rules += 1
            continue

        if removed_prios:
            old_active = rule.get("active_priority", 1)
            old_force = rule.get("force_override", 0)
            new_active = None
            new_force = 0
            for idx, d in enumerate(kept_dests, start=1):
                old_p = d.get("priority", idx)
                d["priority"] = idx
                if old_p == old_active:
                    new_active = idx
                if old_p == old_force and old_force:
                    new_force = idx
            if new_active is None:
                enabled_p = [d["priority"] for d in kept_dests if d.get("enabled", True)]
                new_active = enabled_p[0] if enabled_p else 1
            rule["active_priority"] = new_active
            rule["force_override"] = new_force

        rule["destinations"] = kept_dests
        new_rules.append(rule)
        if isinstance(r_port, int):
            rules_by_port[r_port] = rule

    # Import any active Nginx stream servers missing from XForwarder
    for lp, entries in sorted(nginx_map.items()):
        for proto, thost, tport in entries:
            key = (lp, thost.strip("[]"), tport)
            if key in existing_nginx_keys:
                continue
            existing_rule = rules_by_port.get(lp)
            if existing_rule is not None:
                next_prio = len(existing_rule["destinations"]) + 1
                existing_rule["destinations"].append({
                    "priority": next_prio,
                    "type": "nginx",
                    "target": thost,
                    "port": tport,
                    "proxy_protocol": False,
                    "enabled": True,
                    "is_relay": False,
                    "comment": "Synced from Nginx stream"
                })
                added_rules += 1
            else:
                cand_rule: Dict[str, Any] = {
                    "id": f"rule-{lp}",
                    "port": lp,
                    "protocol": proto,
                    "active_priority": 1,
                    "force_override": 0,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nginx",
                            "target": thost,
                            "port": tport,
                            "proxy_protocol": False,
                            "enabled": True,
                            "is_relay": False,
                            "comment": "Synced from Nginx stream"
                        }
                    ]
                }
                ok, _ = validate_rule(cand_rule)
                if ok:
                    new_rules.append(cand_rule)
                    rules_by_port[lp] = cand_rule
                    added_rules += 1
            existing_nginx_keys.add(key)

    if removed_dests == 0 and removed_rules == 0 and added_rules == 0:
        return True, "XForwarder rules already match Nginx stream configuration", False

    if os.path.exists(path):
        try:
            shutil.copy2(path, f"{path}.bak.{int(time.time())}")
        except Exception:
            pass

    cfg["rules"] = new_rules
    if not save_config(cfg, config_path=path):
        return False, "Failed to save updated configuration after Nginx sync", False

    if sync_rules_func:
        sync_rules_func()
    if notify_func:
        notify_func()

    return (
        True,
        f"Synced XForwarder from Nginx: removed {removed_dests} Nginx destination(s), "
        f"{removed_rules} empty rule(s), added {added_rules} rule(s).",
        False,
    )


def restart_services_action(service: str, sync_rules_func=None, notify_func=None) -> Tuple[bool, str, bool]:
    """
    Executes controlled service restart or reload.
    Supports: 'all', 'engine', 'web', 'haproxy', 'haproxy_restart',
              'nginx', 'nginx_sync', 'nginx_pull', 'nginx_restart', 'nftables', 'nftables_restart'.
    Returns: (success: bool, message: str, is_reconnecting: bool)
    """
    valid_services = {
        "all", "engine", "web",
        "haproxy", "haproxy_restart",
        "nginx", "nginx_sync", "nginx_pull", "nginx_restart",
        "nftables", "nftables_restart"
    }
    svc = str(service or "all").lower().strip()
    if svc not in valid_services:
        return False, f"Invalid service identifier '{service}'. Allowed: {', '.join(sorted(valid_services))}", False

    if svc == "nginx_pull":
        return sync_xforwarder_from_nginx(sync_rules_func=sync_rules_func, notify_func=notify_func)

    has_systemctl = bool(shutil.which("systemctl"))
    if sys.platform == "win32" or not has_systemctl:
        if svc in ("all", "web"):
            return True, f"Service '{svc}' restarted (mock)", True
        elif svc in ("nftables", "nftables_restart"):
            if sync_rules_func:
                sync_rules_func()
            msg = "NFTables table restarted and synchronized (mock)" if svc == "nftables_restart" else "NFTables ruleset synchronized (mock)"
            return True, msg, False
        elif svc == "nginx_sync":
            if sync_rules_func:
                sync_rules_func()
            return True, "Nginx stream configuration synchronized (mock)", False
        elif svc in ("haproxy_restart", "nginx_restart", "engine"):
            return True, f"Service '{svc}' restarted successfully (mock)", False
        return True, f"Service '{svc}' reloaded successfully (mock)", False

    if svc == "nftables":
        if sync_rules_func:
            ok, errs = sync_rules_func()
            if ok:
                return True, "NFTables table 'xfwd_orchestrator' re-synchronized successfully", False
            return False, f"Failed to synchronize NFTables: {', '.join(errs)}", False
        return True, "NFTables reload requested", False

    if svc == "nftables_restart":
        if shutil.which("nft"):
            subprocess.run(["nft", "delete", "table", "ip", "xfwd_orchestrator"], capture_output=True, text=True, timeout=5.0)
            subprocess.run(["nft", "delete", "table", "ip6", "xfwd_orchestrator"], capture_output=True, text=True, timeout=5.0)
        if sync_rules_func:
            ok, errs = sync_rules_func()
            if ok:
                return True, "NFTables table 'xfwd_orchestrator' restarted and re-synchronized successfully", False
            return False, f"Failed to restart NFTables table: {', '.join(errs)}", False
        return True, "NFTables table 'xfwd_orchestrator' restarted successfully", False

    if svc == "haproxy":
        res = subprocess.run(["systemctl", "reload", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "HAProxy relay service reloaded successfully", False
        return False, f"HAProxy reload failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "haproxy_restart":
        if sync_rules_func:
            sync_rules_func()
        res = subprocess.run(["systemctl", "restart", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "HAProxy relay service restarted successfully", False
        return False, f"HAProxy restart failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "nginx_sync":
        if sync_rules_func:
            ok, errs = sync_rules_func()
            if ok:
                return True, "Nginx stream configuration synchronized successfully", False
            return False, f"Failed to synchronize Nginx: {', '.join(errs)}", False
        return True, "Nginx synchronization requested", False

    if svc == "nginx":
        res = subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "Nginx stream proxy engine reloaded successfully", False
        return False, f"Nginx reload failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "nginx_restart":
        if sync_rules_func:
            sync_rules_func()
        res = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "Nginx stream proxy engine restarted successfully", False
        return False, f"Nginx restart failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "engine":
        svc_name = "xforwarder.service"
        res = subprocess.run(["systemctl", "restart", svc_name], capture_output=True, text=True, timeout=10.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "forward-manager.service"], capture_output=True, text=True, timeout=10.0)
        if res.returncode == 0:
            if notify_func:
                notify_func()
            return True, "XForwarder Core Failover Engine restarted successfully", False
        return False, f"Failed to restart core engine: {res.stderr.strip() or res.stdout.strip()}", False

    if svc in ("web", "all"):
        if svc == "all":
            subprocess.run(["systemctl", "restart", "xforwarder.service"], capture_output=True, timeout=5.0)
            subprocess.run(["systemctl", "reload", "haproxy"], capture_output=True, timeout=5.0)
            subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, timeout=5.0)

        def _delayed_web_restart():
            time.sleep(0.6)
            if shutil.which("systemd-run"):
                subprocess.run(
                    ["systemd-run", "--unit=xfwd-restart-job", "systemctl", "restart", "xforwarder-web.service"],
                    capture_output=True
                )
            else:
                subprocess.run(["systemctl", "restart", "xforwarder-web.service"], capture_output=True)

        threading.Thread(target=_delayed_web_restart, daemon=True).start()
        msg = "All XForwarder services are restarting" if svc == "all" else "Web Dashboard service is restarting"
        return True, f"{msg}. Reconnecting in ~2 seconds...", True

    return False, "Unknown action", False
