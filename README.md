# HR IAM Portal

HR IAM Portal is an internal workflow application for employee onboarding and offboarding requests.

It demonstrates a secure HR-to-IT workflow with role-based approvals and Microsoft Entra ID sign-in, plus Microsoft Graph automation for provisioning and offboarding.

---

## What the app does

### Onboarding
- HR Requester creates an onboarding request
- HR Approver approves or rejects
- IT Clearance executes provisioning
- The app can create a user account in Microsoft Entra ID (via Microsoft Graph) **when the provisioning app is configured**

### Offboarding
- HR Requester creates an offboarding request
- HR Approver approves or rejects
- IT Clearance executes offboarding
- The app can disable the user account and revoke sign-in sessions (via Microsoft Graph) **when the provisioning app is configured**

---

## Key features
- Role-based access (HR.Requester / HR.Approver / IT.Clearance / HR.Auditor optional)
- Approval and rejection workflow
- Microsoft Entra ID sign-in (OAuth 2.0 / OpenID Connect)
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
- SQLite (local database for demo)

---

## Project status
- Local application working
- Entra integration tested
- Onboarding flow tested
- Offboarding flow tested

---

## Repository layout (high level)
- `main.py` — FastAPI app (routes, auth flow, workflow)
- `graph_client.py` — Graph client helpers (app-only token + calls)
- `config.py` — configuration loader (reads environment variables)
- `templates/` — UI templates
- `docs/` — runbook and screenshots

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
- Never commit `.env`
- Never commit SQLite database files (example: `*.db`)

### 5) Run locally
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open the app:
- `http://127.0.0.1:8000`

OAuth callback used by this project:
- `http://localhost:8000/auth/callback`

Note:
- Redirect URIs must match exactly in Entra.
- If you register `localhost`, use `localhost` in the browser for sign-in flows.

---

## Environment variables

The app uses `.env` locally (loaded at startup). Example placeholders are in `.env.example`.

### Portal app (interactive login)
- `TENANT_ID` — Entra tenant (Directory) ID
- `CLIENT_ID` — Portal app (client) ID
- `CLIENT_SECRET` — Portal app secret
- `REDIRECT_URI` — callback URL (example: `http://localhost:8000/auth/callback`)
- `SESSION_SECRET` — random secret used to sign session cookies
- `DATABASE_PATH` — SQLite db file path (example: `hr_portal.db`)

### Provisioning app (automation identity)
Used only if you enable Graph provisioning/offboarding features.

- `PROV_TENANT_ID` — Entra tenant (Directory) ID
- `PROV_CLIENT_ID` — Provisioning app (client) ID
- `PROV_CLIENT_SECRET` — Provisioning app secret
- `TENANT_DOMAIN` — `<tenant>.onmicrosoft.com`

---

## Microsoft Entra ID setup (Portal app)

### Step 1 — App Registration (Web)
Microsoft Entra admin center → App registrations → New registration

- Name: `HR IAM Portal - Web`
- Supported account type: choose what fits your tenant
- Redirect URI (Web):
  - Local dev: `http://localhost:8000/auth/callback`
  - Azure/Prod: `<YOUR_PUBLIC_URL>/auth/callback` (placeholder only)

Record these values:
- Directory (tenant) ID → `TENANT_ID`
- Application (client) ID → `CLIENT_ID`

Create a client secret:
- Certificates & secrets → New client secret
- Secret value → `CLIENT_SECRET`

### Step 2 — Define app roles (on the App Registration)
Microsoft Entra admin center → App registrations → `HR IAM Portal - Web` → App roles

Create these roles (Value exactly as shown):
- `HR.Requester`
- `HR.Approver`
- `IT.Clearance`
- `HR.Auditor` (optional)

Tip:
- Keep role values stable because your authorization logic expects these strings.

### Step 3 — Assign app roles (via Enterprise Applications)
Microsoft Entra admin center → Enterprise applications → select `HR IAM Portal - Web`

Recommended:
- Properties → Assignment required = Yes

Assign roles:
- Users and groups → Add user/group → select role

### Step 4 — API permissions (Portal app)
Microsoft Entra admin center → App registrations → `HR IAM Portal - Web` → API permissions

- Add only the permissions the portal needs for sign-in and basic functionality.
- Grant admin consent if required by your tenant policy.

Note:
- The portal app is for interactive sign-in. It should not require high-privilege Graph permissions for provisioning.

---

## Microsoft Entra ID setup (Provisioning app for Graph automation)

This is a separate app registration used for app-only token (client credential flow). It is responsible for:
- Creating users (onboarding)
- Disabling users + revoking sessions (offboarding)

### Step 1 — App Registration (confidential client)
Microsoft Entra admin center → App registrations → New registration

- Name: `HR IAM Portal - Provisioning`

Record:
- Directory (tenant) ID → `PROV_TENANT_ID`
- Application (client) ID → `PROV_CLIENT_ID`

Create a client secret:
- Secret value → `PROV_CLIENT_SECRET`

Set:
- `TENANT_DOMAIN` → `<tenant>.onmicrosoft.com`

### Step 2 — Microsoft Graph application permissions
Microsoft Entra admin center → App registrations → `HR IAM Portal - Provisioning` → API permissions

Add **Application permissions** needed by your provisioning/offboarding logic, then:
- Click “Grant admin consent”

Important:
- The exact permissions depend on what your code does.
- Document your final permissions in: `docs/entra-graph-permissions.md`

---

## Health endpoint (required for load balancer probes)

The app should expose a health endpoint used by ILB/App Gateway probes:

- `GET /healthz` returns HTTP 200 when the node is ready to serve traffic

---

## Azure deployment (reference architecture)

This is a generic enterprise-style reference architecture.

Target design:
- Public entry: Application Gateway (HTTPS)
- Private backend: Internal Load Balancer (ILB)
- Two Ubuntu VMs running the app
- Active/Passive while using SQLite

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

Note:
- NAT is for outbound only. Inbound traffic still comes through Application Gateway.

### Step 4 — Create Ubuntu VMs (no public IP)
Azure Portal → Virtual machines → Create

Create two VMs in `snet-app`:
- VM-01: `<VM1_NAME>`
- VM-02: `<VM2_NAME>`

Recommended settings:
- Image: Ubuntu LTS
- Authentication: SSH public key
- Public IP: None

Connectivity:
- Use Azure Bastion (recommended) or a jumpbox to SSH privately.

### Step 5 — NSG rules for the VM subnet
Allow backend traffic to the application port from inside your VNet.

Azure Portal → Network security groups → select NSG attached to VM NICs or subnet

Add inbound rule (example):
- Source: VirtualNetwork
- Destination port: 8000
- Protocol: TCP
- Action: Allow
- Priority: 200
- Name: `Allow-VNet-AppPort`

(If you use Bastion, allow SSH only as needed for your access design.)

### Step 6 — Deploy the app on each VM (systemd)
On each VM:
- Clone your repo
- Create venv
- Install requirements
- Create `.env` on the VM (do not copy your local `.env` to Git)
- Run the app as a systemd service

Service expectations:
- Service name: `hr-iam-portal`
- App listens on: `0.0.0.0:8000`
- Health endpoint: `/healthz` returns 200

### Step 7 — Create Internal Load Balancer (ILB)
Azure Portal → Load balancers → Create

- Type: Internal
- SKU: Standard
- VNet: `<VNET_NAME>`
- Subnet: `snet-app`

Backend pool:
- Add VM NICs (VM-01 and VM-02)

Health probe:
- Name: `probe-app-healthz`
- Protocol: HTTP
- Port: 8000
- Path: `/healthz`

Load balancing rule:
- Name: `rule-app`
- Protocol: TCP
- Frontend port: 8000
- Backend port: 8000
- Backend pool: your pool
- Health probe: `probe-app-healthz`

### Step 8 — Create Application Gateway (public entry)
Azure Portal → Application gateways → Create

Basics:
- Name: `<APPGW_NAME>`
- SKU: Standard_v2 (or WAF_v2 if you enable WAF)
- VNet: `<VNET_NAME>`
- Subnet: `AppGatewaySubnet`

Frontend:
- Public IP: create new `<APPGW_PUBLIC_IP_NAME>`

Listener:
- HTTPS listener (recommended)
- Certificate: upload your cert (PFX) or integrate with Key Vault
- Hostname: use placeholder `<YOUR_PUBLIC_URL>` in docs (do not include real domains)

Backend settings:
- Backend pool: ILB frontend private IP
- Backend port: 8000
- Health probe: HTTP port 8000 path `/healthz`
- Timeout: increase if your app is slow to respond

Rules:
- Route HTTPS listener → backend pool

### Step 9 — Validate end-to-end
Validation checklist:
- App Gateway → Backend health shows Healthy
- `https://<YOUR_PUBLIC_URL>/healthz` returns 200
- Login works
- Create request → approve → execute works end-to-end

---

## SQLite note (active/passive)

SQLite is a local file database. Because of that:
- Treat the deployment as active/passive while SQLite is used
- Do not run active/active writes across two nodes

Recommended operation in SQLite mode:
- Keep only ONE VM in the active backend pool at a time
- Use the second VM for failover testing or standby

Future improvement:
- Move to a shared database (example: Azure SQL) to support true scale-out.

---

## Troubleshooting (common)

### Login fails or loops
- Confirm the Redirect URI matches exactly:
  - Local: `http://localhost:8000/auth/callback`
  - Prod: `<YOUR_PUBLIC_URL>/auth/callback`
- Confirm your user is assigned a role in the Enterprise Application
- Confirm your app roles values match the role checks used in the code

### Application Gateway returns 502
- Check Application Gateway → Backend health
- Confirm ILB health probe path is correct (`/healthz`)
- Confirm the app is listening on the expected port
- Confirm NSG rules allow the backend traffic inside the VNet

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
- For production, use a secret store (example: Key Vault) and rotate secrets regularly

---

## Documentation
- `docs/runbook.md` — operations + failover
- `docs/screenshots/` — Azure + Entra screenshots (scrubbed / generic)
- `docs/entra-graph-permissions.md` — Graph permissions used by your implementation

---

## License
Add a license file before making the repo public (example: MIT).
