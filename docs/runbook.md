# HR IAM Portal — Operations Runbook (Azure VMs, Active/Passive)

This runbook is for day-to-day operations and incident response.
Architecture: Application Gateway → Internal Load Balancer → 2 Ubuntu VMs (FastAPI on port 8000).
Database: SQLite (active/passive only).

---

## 0) Definitions

- **ACTIVE VM**: the only VM that should handle real workflow traffic (writes).
- **PASSIVE VM**: standby VM, ready for failover.
- **Service name**: `hr-iam-portal`
- **App port**: `8000`
- **Health endpoint**: `/healthz`

---

## 1) Quick health checks (fast)

### 1.1 External (through Application Gateway)
From your browser:
- `https://<YOUR_PUBLIC_URL>/healthz` should return **200 OK**.

If it fails:
- Go to Application Gateway → **Backend health**.

### 1.2 Internal (on the VM)
SSH to the VM and run:
```bash
curl -i http://127.0.0.1:8000/healthz
```
Expected: **HTTP/1.1 200 OK**

---

## 2) Check and control the app service (systemd)

### 2.1 Status
```bash
sudo systemctl status hr-iam-portal --no-pager
```

### 2.2 Restart
```bash
sudo systemctl restart hr-iam-portal
sudo systemctl status hr-iam-portal --no-pager
```

### 2.3 Stop / Start
```bash
sudo systemctl stop hr-iam-portal
sudo systemctl start hr-iam-portal
```

### 2.4 Logs (last 200 lines)
```bash
sudo journalctl -u hr-iam-portal -n 200 --no-pager
```

---

## 3) Confirm the app is listening on port 8000

```bash
sudo ss -lntp | grep 8000
```

If nothing is listening:
- Service is not running or it crashed.
- Check logs:
  - `sudo journalctl -u hr-iam-portal -n 200 --no-pager`

---

## 4) Azure-side checks

### 4.1 Application Gateway
Azure Portal → Application Gateway → **Backend health**
- Must show backend as **Healthy**.

If backend is unhealthy:
- Verify ILB probe path and port.
- Verify NSG rules allow traffic.
- Verify `/healthz` returns 200 on the ACTIVE VM.

### 4.2 Internal Load Balancer (ILB)
Azure Portal → Load Balancer → **Health probes**
- Probe should target:
  - Port: `8000`
  - Path: `/healthz`

Azure Portal → Load Balancer → **Backend pools**
- Should list the VM NICs you intend to use (active/passive design may keep both NICs, but only ACTIVE should serve writes).

### 4.3 Network Security Groups (NSG)
Confirm inbound rule exists to allow port 8000 from inside the VNet:
- Source: `VirtualNetwork` (or AppGatewaySubnet if you restricted it)
- Destination port: `8000`
- Protocol: TCP

---

## 5) Active/Passive rules (SQLite)

SQLite is a local file DB. To avoid corruption and inconsistent writes:
- Only one VM should be ACTIVE at a time.
- The PASSIVE VM should not be used for normal traffic unless failover happens.

Practical approach:
- ACTIVE VM: `hr-iam-portal` service running
- PASSIVE VM: service can be **stopped** (recommended) or running in standby only if you fully control routing.

---

## 6) Failover procedure (VM-01 → VM-02)

### Goal
Move service from ACTIVE VM to PASSIVE VM safely.

### Step 1 — Confirm ACTIVE VM is really down (or must be removed)
- Check App Gateway Backend health
- Try VM local health check (if you can reach it):
  - `curl -i http://127.0.0.1:8000/healthz`

### Step 2 — Stop service on old ACTIVE (if reachable)
On old ACTIVE VM:
```bash
sudo systemctl stop hr-iam-portal
```

### Step 3 — Start service on PASSIVE VM
On PASSIVE VM:
```bash
sudo systemctl start hr-iam-portal
sudo systemctl status hr-iam-portal --no-pager
curl -i http://127.0.0.1:8000/healthz
```
Expected: 200 OK.

### Step 4 — Ensure routing sends traffic to the new ACTIVE
Choose ONE method:

**Method A (recommended for SQLite): keep only one backend target active**
- In Azure:
  - Remove old ACTIVE VM NIC from ILB backend pool (temporarily), OR
  - Mark it unavailable (stop service so probes fail), so it won’t receive traffic.

**Method B: keep both in pool but only one passes health**
- Configure PASSIVE to return 503 until it becomes ACTIVE (requires app logic).
- (Use only if you already implemented this logic.)

### Step 5 — Validate end-to-end
- App Gateway Backend health shows **Healthy**
- `https://<YOUR_PUBLIC_URL>/healthz` returns 200
- Login works
- Create request → approve → execute works end-to-end

### Step 6 — Record incident notes
Write down:
- time of failover
- root cause (if known)
- what was changed
- how to prevent recurrence

---

## 7) Failback (VM-02 → VM-01)

When VM-01 is fixed:
1) Ensure VM-01 service works locally:
```bash
sudo systemctl start hr-iam-portal
curl -i http://127.0.0.1:8000/healthz
```
2) Make VM-01 the ACTIVE target (reverse the routing method you used).
3) Stop service on VM-02 if it becomes PASSIVE:
```bash
sudo systemctl stop hr-iam-portal
```

---

## 8) Common incidents and fixes

### 8.1 App Gateway shows 502
Most common causes:
- Backend health probe failing
- NSG blocks port 8000
- App service stopped / crashed
- Wrong probe path/port

Fix path:
1) App Gateway → Backend health (see what is unhealthy)
2) ILB probe: confirm port 8000 + `/healthz`
3) On ACTIVE VM:
   - `sudo systemctl status hr-iam-portal`
   - `curl -i http://127.0.0.1:8000/healthz`
4) NSG: allow port 8000 from VNet

### 8.2 Healthz returns 200 locally but backend still unhealthy
- Check whether the app listens on `0.0.0.0:8000` (not only 127.0.0.1)
- Check NSG rules
- Check backend setting port matches (8000)

### 8.3 Service is active but app is not responding
- Check logs:
  - `sudo journalctl -u hr-iam-portal -n 200 --no-pager`
- Check CPU/RAM:
  - `top` or `free -h`

