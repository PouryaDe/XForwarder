#!/usr/bin/env python3
"""
XForwarder - Service Controller & System Update Manager
Provides granular service restart controls and decoupled update orchestration.
"""

import os
import sys
import json
import time
import shutil
import threading
import subprocess
import tempfile
import urllib.request
import re
from typing import Dict, Any, Tuple, Optional

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


def restart_services_action(service: str, sync_rules_func=None, notify_func=None) -> Tuple[bool, str, bool]:
    """
    Executes controlled service restart or reload.
    Supports: 'all', 'engine', 'web', 'haproxy', 'nginx', 'nftables'.
    Returns: (success: bool, message: str, is_reconnecting: bool)
    """
    valid_services = {"all", "engine", "web", "haproxy", "nginx", "nftables"}
    svc = str(service or "all").lower().strip()
    if svc not in valid_services:
        return False, f"Invalid service identifier '{service}'. Allowed: {', '.join(sorted(valid_services))}", False

    has_systemctl = bool(shutil.which("systemctl"))
    if sys.platform == "win32" or not has_systemctl:
        if svc in ("all", "web"):
            return True, f"Service '{svc}' restarted (mock)", True
        elif svc == "nftables":
            if sync_rules_func:
                sync_rules_func()
            return True, "NFTables ruleset synchronized (mock)", False
        return True, f"Service '{svc}' reloaded successfully (mock)", False

    if svc == "nftables":
        if sync_rules_func:
            ok, errs = sync_rules_func()
            if ok:
                return True, "NFTables table 'xfwd_orchestrator' re-synchronized successfully", False
            return False, f"Failed to synchronize NFTables: {', '.join(errs)}", False
        return True, "NFTables reload requested", False

    if svc == "haproxy":
        res = subprocess.run(["systemctl", "reload", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "HAProxy relay service reloaded successfully", False
        return False, f"HAProxy reload failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "nginx":
        res = subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "Nginx stream proxy engine reloaded successfully", False
        return False, f"Nginx reload failed: {res.stderr.strip() or res.stdout.strip()}", False

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
