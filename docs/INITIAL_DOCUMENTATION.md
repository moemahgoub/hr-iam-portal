# HR IAM Portal - Initial Documentation

## 1. Project Overview

HR IAM Portal is an internal workflow application for managing employee onboarding and offboarding requests through a controlled approval process.

The project is designed to demonstrate enterprise-style identity lifecycle management by combining:
- role-based access control
- approval workflow
- IT execution controls
- Microsoft Entra authentication
- Microsoft Graph integration
- audit logging

---

## 2. Business Use Case

Organizations often manage onboarding and offboarding tasks through email, chat, or manual handoffs. This creates risks such as:
- missing approvals
- inconsistent execution
- delayed account actions
- poor auditability

HR IAM Portal provides a structured workflow that helps coordinate HR and IT responsibilities for identity lifecycle tasks.

### Main Use Cases
- **Onboarding:** Submit and approve a request before creating a new employee account
- **Offboarding:** Submit and approve a request before disabling access and revoking sessions

---

## 3. Core Features

- Role-based access control (RBAC)
- Onboarding request submission
- Offboarding request submission
- Approval and rejection workflow
- IT execution step for identity actions
- Microsoft Graph integration for provisioning/deprovisioning
- Audit logging for key actions
- CSRF protection for form submissions
- Server-side validation
- Duplicate request protection

---

## 4. Workflow Summary

### Onboarding Workflow
1. HR Requester submits onboarding request
2. HR Approver reviews and approves or rejects the request
3. IT Clearance executes the approved onboarding action
4. The system provisions the user account through Microsoft Graph
5. Request status and audit log are updated

### Offboarding Workflow
1. HR Requester submits offboarding request using employee number
2. HR Approver reviews and approves or rejects the request
3. IT Clearance executes the approved offboarding action
4. The system locates the user, disables the account, and revokes sign-in sessions through Microsoft Graph
5. Request status and audit log are updated

---

## 5. Identity and Access Model

The portal uses app roles for authorization and separates interactive login from privileged backend automation.

### Supported Roles
- **HR Requester**
- **HR Approver**
- **IT Clearance**
- **HR Auditor** (optional / future use)

### Role Assignment Model
Roles are assigned through Microsoft Entra enterprise application assignments.  
Users (or groups in supported/licensed environments) receive app roles that control access to portal features and execution steps.

---

## 6. Security Design Principles

The project applies the following security principles:

### Separation of Duties
HR request submission/approval is separated from IT execution actions.

### Least Privilege by Design (Application Split)
The interactive portal application is separated from the backend worker identity used for privileged Microsoft Graph operations.

### Backend Authorization Enforcement
Role checks are enforced on the server side and not only in the user interface.

### Secret Management
Sensitive values (tenant IDs, client IDs, secrets, session secret) are stored in environment variables and should not be committed to source control.

### Form Security
CSRF protection is enabled for form submissions.

---

## 7. Application Components

The solution uses two Microsoft Entra app registrations with different responsibilities.

### A) HR Portal (Browser Login Application)
Used for:
- interactive user sign-in
- session authentication
- app role claims used for authorization in the portal

### B) HR-Provisioning-Worker (Automation Identity)
Used for:
- backend Microsoft Graph operations
- identity lifecycle actions such as user provisioning and deprovisioning

This separation reduces exposure of privileged Graph permissions in the user-facing application.

---

## 8. Environment Configuration (Structure Only)

The application uses environment variables for configuration.

### Example Structure

```env
# ===== HR PORTAL (Browser Login App) =====
TENANT_ID=<tenant-id>
CLIENT_ID=<portal-app-client-id>
CLIENT_SECRET=<portal-app-secret-value>
REDIRECT_URI=http://localhost:8000/auth/callback
SESSION_SECRET=<random-session-secret>
DATABASE_PATH=hr_portal.db

# === Provisioning App (automation identity) ===
PROV_TENANT_ID=<tenant-id>
PROV_CLIENT_ID=<worker-app-client-id>
PROV_CLIENT_SECRET=<worker-app-secret-value>
TENANT_DOMAIN=<tenant>.onmicrosoft.com