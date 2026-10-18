---
name: deploy-update
description: Workflow for updating XForwarder source code and services safely in production.
---

# Workflow: Deploy & Update Services

Use this workflow when applying code or UI updates to a running XForwarder server.

## Step 1: Backup Configuration
Before changing code or restarting services, back up the existing configuration:
```bash
cp /etc/xforwarder/config.json /etc/xforwarder/config.json.bak
```

## Step 2: Copy Updated Files to Installation Directory
```bash
INSTALL_DIR="/opt/xforwarder"
cp -r core "$INSTALL_DIR/"
cp -r web "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/core/engine.py" "$INSTALL_DIR/core/web_server.py"
```

## Step 3: Syntax Verification
Check Python syntax before restarting:
```bash
python3 -m py_compile /opt/xforwarder/core/engine.py
python3 -m py_compile /opt/xforwarder/core/web_server.py
```

## Step 4: Restart Daemons
Restart both services using systemctl:
```bash
systemctl restart xforwarder.service
systemctl restart xforwarder-web.service
```

## Step 5: Post-Deployment Health Check
1. Verify systemd statuses:
   ```bash
   systemctl is-active xforwarder.service
   systemctl is-active xforwarder-web.service
   ```
2. Verify web dashboard endpoint:
   ```bash
   curl -I http://127.0.0.1:8090/
   ```
3. Check runtime state file:
   ```bash
   cat /run/xforwarder/state.json
   ```
