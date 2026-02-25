# HR IAM Portal

HR IAM Portal is an internal workflow application for employee onboarding and offboarding requests.

It is built to demonstrate a secure HR-to-IT workflow with role-based approvals and Microsoft Entra / Microsoft Graph integration.

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

## Key features

- Role-based access (HR Requester / HR Approver / IT Clearance)
- Approval and rejection workflow
- Microsoft Entra ID sign-in
- Microsoft Graph integration (provisioning and offboarding)
- Audit logging
- CSRF protection
- Server-side validation

## Tech stack

- Python
- FastAPI
- Microsoft Entra ID (authentication)
- Microsoft Graph API
- SQLite (current local database)

## Project status (current)

- Local application working
- New tenant integration completed
- Onboarding provisioning tested
- Offboarding execution tested

## Local setup (basic)

1. Create Python virtual environment
2. Install project dependencies
3. Create `.env` file with tenant and app registration values
4. Run the app locally

Example run command:

```bash
uvicorn main:app --reload