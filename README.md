# HR IAM Portal

HR IAM Portal is an internal workflow application for employee onboarding and offboarding requests.

It demonstrates a secure HR-to-IT workflow with role-based approvals and Microsoft Entra ID / Microsoft Graph integration.

---

## What the app does

### Onboarding
- HR Requester creates onboarding request
- HR Approver approves or rejects
- IT Clearance executes provisioning
- App creates user account in Microsoft Entra ID

### Offboarding
- HR Requester creates offboarding request
- HR Approver approves or rejects
- IT Clearance executes offboarding
- App disables user account and revokes sign-in sessions

---

## Key features
- Role-based access (HR.Requester / HR.Approver / IT.Clearance / HR.Auditor optional)
- Approval and rejection workflow
- Microsoft Entra ID sign-in (OAuth)
- Microsoft Graph integration (provisioning and offboarding)
- Audit logging + export
- CSRF protection
- Server-side validation

---

## Tech stack
- Python
- FastAPI
- Microsoft Entra ID (authentication)
- Microsoft Graph API
- SQLite (current local database)

---

## Project status
- Local application working
- Tenant integration completed
- Onboarding tested
- Offboarding tested

---

## Local setup

### 1) Clone repository
```bash
git clone <YOUR_REPO_URL>
cd <YOUR_REPO_FOLDER>
```

### 2) Create virtual environment
```bash
python -m venv .venv
```

### 3) Install dependencies
```bash
# Windows
.venv\Scripts\pip install -r requirements.txt

# Linux/macOS
.venv/bin/pip install -r requirements.txt
```

### 4) Create `.env`
Copy `.env.example` to `.env` and set real values.

Important:
- Do not commit `.env`
- Do not commit SQLite database files (example: `*.db`)

### 5) Run locally
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open:
- App: `http://127.0.0.1:8000`
- OAuth callback route used by this project: `http://localhost:8000/auth/callback`

---

## Microsoft Entra ID setup (Portal)

### Step 1 — App Registration (Web)
Microsoft Entra admin center → App registrations → New registration

- Name: `HR IAM Portal - Web`

Redirect URIs:
- Local dev: `http://localhost:8000/auth/callback`
- Azure/Prod: `<YOUR_PUBLIC_URL>/auth/callback` (placeholder only)

Record:
- Directory (tenant) ID → `TENANT_ID`
- Application (client) ID → `CLIENT_ID`

Create a client secret:
- Secret value → `CLIENT_SECRET`

### Step 2 — Enterprise Application roles
Microsoft Entra admin center → Enterprise applications → select `HR IAM Portal - Web`

Create these roles (value exactly as shown):
- `HR.Requester`
- `HR.Approver`
- `IT.Clearance`
- `HR.Auditor` (optional)

Recommended:
- Properties → Assignment required = Yes

Assign roles:
- Users and groups → Add user/group → select role

### Step 3 — Microsoft Graph permissions
Grant the Microsoft Graph permissions required by your workflow and click:
- “Grant admin consent”

Note:
- The exact permissions depend on what your provisioning/offboarding code does.
- Document the final permissions you used in `docs/entra-graph-permissions.md` (recommended).

---

## Azure deployment (Portal-only, enterprise design)

Target design:
- Public entry: Application Gateway (HTTPS)
- Private backend: Internal Load Balancer (ILB)
- Two Ubuntu VMs running the app on port 8000
- Active/Passive (SQLite)

### Step 1 — Create Resource Group
Azure Portal → Resource groups → Create

- Resource group: `<RG_NAME>`
- Region: `<REGION>`

### Step 2 — Create Virtual Network and subnets
Azure Portal → Virtual networks → Create

Create a VNet:
- Name: `<VNET_NAME>`
- Address space: example `10.10.0.0/16` (use your own plan)

Create subnets (names must be exact for App Gateway/Bastion):
- `AppGatewaySubnet` (example `10.10.0.0/24`)
- `snet-app` (VM subnet) (example `10.10.1.0/24`)
- `AzureBastionSubnet` (optional) (example `10.10.2.0/27`)

### Step 3 — Create NAT Gateway (VM outbound internet)
If your VMs have no public IP, they still need outbound internet for updates and pulling packages.

Azure Portal → NAT gateways → Create

- NAT gateway: `<NAT_NAME>`
- Public IP: Create new
- Subnet association: select `snet-app`

### Step 4 — Create Ubuntu VMs (no public IP)
Azure Portal → Virtual machines → Create

Create two VMs in `snet-app`:
- VM-01: `<VM1_NAME>` (ACTIVE)
- VM-02: `<VM2_NAME>` (PASSIVE standby)

Recommended settings:
- Image: Ubuntu LTS
- Authentication: SSH public key
- Public IP: **None**
- NIC network security group (NSG): Basic is fine (adjust inbound rules below)

Connectivity:
- Use Azure Bastion (recommended) or a jumpbox to SSH privately.

### Step 5 — NSG rules for the VM subnet
You must allow backend traffic to port 8000 from inside your VNet.

Azure Portal → Network security groups → select NSG attached to VM NICs or subnet

Add inbound rule (example):
- Source: VirtualNetwork
- Source port ranges: *
- Destination: Any
- Destination port ranges: 8000
- Protocol: TCP
- Action: Allow
- Priority: 200
- Name: `Allow-VNet-8000`

(If you use Bastion, allow SSH only from Bastion service as needed.)

### Step 6 — Deploy the app on each VM and run as systemd service
On each VM:
- Clone your repo
- Create venv
- Install requirements
- Create `.env`
- Start app as systemd service on port 8000

Service expectations:
- Service name: `hr-iam-portal`
- App listens on: `0.0.0.0:8000`
- Health endpoint: `/healthz` returns 200

### Step 7 — Create Internal Load Balancer (ILB)
Azure Portal → Load balancers → Create

- Type: **Internal**
- SKU: Standard
- VNet: `<VNET_NAME>`
- Subnet: `snet-app`
- Frontend IP: `<ILB_FRONTEND_IP>` (dynamic or static)

Backend pool:
- Add VM NICs (VM-01 and VM-02)

Health probe:
- Name: `probe-8000-healthz`
- Protocol: HTTP
- Port: 8000
- Path: `/healthz`
- Interval/Threshold: keep defaults unless you have issues

Load balancing rule:
- Name: `rule-8000`
- Frontend IP: ILB frontend
- Protocol: TCP (or HTTP if supported in your design)
- Port: 8000
- Backend port: 8000
- Backend pool: your pool
- Health probe: `probe-8000-healthz`

### Step 8 — Create Application Gateway (public entry)
Azure Portal → Application gateways → Create

Basics:
- Name: `<APPGW_NAME>`
- SKU: Standard_v2
- VNet: `<VNET_NAME>`
- Subnet: `AppGatewaySubnet`

Frontend:
- Public IP: create new `<APPGW_PUBLIC_IP_NAME>`

Listener:
- HTTPS listener (recommended)
- Certificate: upload your cert (PFX) or use Key Vault integration if you prefer
- Hostname: do not put your real domain in README (use placeholder `<YOUR_PUBLIC_URL>`)

Backend settings:
- Backend pool target: ILB private IP (or ILB frontend private IP)
- Backend port: 8000
- Health probe: HTTP port 8000 path `/healthz`
- Timeout: increase if your app is slow to respond

Rules:
- Route HTTPS listener → backend pool

### Step 9 — Validate end-to-end
Validation checklist:
- App Gateway → Backend health shows **Healthy**
- `https://<YOUR_PUBLIC_URL>/healthz` returns 200
- Login works
- Create request → approve → execute works end-to-end

---

## SQLite note (active/passive)
SQLite is a local file database. Because of that:
- Run **active/passive** (only one VM serves traffic at a time for write operations)
- The second VM is standby for failover
- Real active/active is planned later when moving to Azure SQL

Operational tip:
- Keep one VM as “ACTIVE” and confirm it is the only node receiving real workflow traffic.
- Use the standby VM for failover testing only.

---

## Health check
The app should expose a health endpoint used by ILB/App Gateway probes:

- `/healthz` should return HTTP 200 when the node is ready to serve.

---

## Troubleshooting (common)

### Login fails or loops
- Confirm the Redirect URI matches exactly:
  - Local: `http://localhost:8000/auth/callback`
  - Prod: `<YOUR_PUBLIC_URL>/auth`
- Confirm your user is assigned a role in the Enterprise Application.

### App Gateway returns 502
- Check Application Gateway → Backend health
- Confirm ILB health probe path is correct (`/healthz`)
- Confirm port 8000 is reachable from the network path (NSG rules)

On VM:
```bash
curl -i http://127.0.0.1:8000/healthz
sudo systemctl status hr-iam-portal --no-pager
sudo journalctl -u hr-iam-portal -n 200 --no-pager
```

---

## Security reminders
- Never commit secrets (`.env`, tokens, client secrets)
- Never commit databases (`*.db`)
- Use placeholders in docs (`<YOUR_PUBLIC_URL>`) and avoid real domains



## Documentation
- `docs/runbook.md` — Operations + failover
- `docs/screenshots/` — Azure + Entra proof