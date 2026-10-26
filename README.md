# Employee Access Management API

![CI](https://github.com/kaseeme1/access-management-api/actions/workflows/ci.yml/badge.svg)

An internal REST API for managing employee accounts and system access under a **least-privilege** policy: every employee gets exactly the access their role requires, nothing more. It handles onboarding, role changes, and offboarding, keeps an audit trail of every change, and runs access reviews that flag people whose access doesn't match their job.

> **Status:** in progress.

## Why it matters

Access that outlives its purpose is one of the most common ways organizations get breached: a former employee whose VPN account was never disabled, or someone who changed roles and kept their old admin rights. This service makes access a function of role, removes it automatically when a role changes or someone leaves, and catches drift when it happens anyway.

## Features

| Endpoint | What it does |
|---|---|
| `POST /employees` | Onboard: create the employee and grant their role's access |
| `PATCH /employees/{id}/role` | Role change: grant new access **and revoke** access the new role doesn't include |
| `POST /employees/{id}/offboard` | Offboard: terminate and revoke **all** access immediately |
| `GET /access-review` | Flag mismatches between actual access and policy |
| `GET /audit-log` | Every change: who did it, what changed, and when |
| `GET /employees`, `GET /employees/{id}` | Look up employees and their current access |
| `GET /roles` | The access policy |

### Access review findings

| Issue | Severity | Meaning |
|---|---|---|
| `terminated_with_access` | **CRITICAL** | A former employee still has access |
| `excess_access` | HIGH | Someone has access their role doesn't include |
| `missing_access` | LOW | Someone is missing access their role requires |

### Security controls

- Every endpoint except `/health` requires an API key (`X-API-Key`), compared in constant time
- Every change is written to an audit log with the acting user (`X-Actor`)
- Requests that fail validation are rolled back, so a failed change never leaves partial access behind
- Input is validated (email format, field lengths, known roles) before anything touches the database
- The container runs as a non-root user

## Access policy

| Role | Systems |
|---|---|
| cashier | pos, timeclock, email |
| stocker | inventory, timeclock, email |
| pharmacist | pharmacy_system, timeclock, email |
| store_manager | pos, inventory, scheduling, reports, timeclock, email |
| software_engineer | github, cloud_console, vpn, email |
| it_admin | admin_console, vpn, email |

Defined in `app/roles.py`.

## Quick start

```bash
pip install -r requirements-dev.txt

# load a demo company with a few planted access problems
python scripts/seed_demo_data.py

# start the API (PowerShell: $env:ACCESS_API_KEY="dev-key")
export ACCESS_API_KEY=dev-key
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for interactive API docs. Click **Try it out** on any endpoint and send `dev-key` as the `X-API-Key` header.

### With Docker

```bash
docker build -t access-management-api .
docker run -p 8000:8000 -e ACCESS_API_KEY=dev-key -v access-data:/data access-management-api
```

## Example

```bash
curl -X POST http://localhost:8000/employees \
  -H "X-API-Key: dev-key" -H "X-Actor: hr.portal" -H "Content-Type: application/json" \
  -d '{"name": "Maria Lopez", "email": "maria.lopez@example.com", "department": "Store 112", "role": "cashier"}'
```

Running the access review against the demo data:

```json
[
  {"employee_id": 8, "name": "Sam Rivera",   "issue": "terminated_with_access", "severity": "CRITICAL", "systems": ["vpn"]},
  {"employee_id": 7, "name": "Chris Walker", "issue": "excess_access",          "severity": "HIGH",     "systems": ["admin_console"]},
  {"employee_id": 4, "name": "Daniel Kim",   "issue": "missing_access",         "severity": "LOW",      "systems": ["pharmacy_system"]}
]
```

## Project layout

```
app/
  main.py         API routes, auth, error handling
  services.py     onboarding, role changes, offboarding, access review
  roles.py        role -> access policy
  repository.py   all database reads and writes
  database.py     SQLite connection and schema
  models.py       domain objects and errors
scripts/
  seed_demo_data.py
tests/
```

## Development

```bash
pytest -v
```

GitHub Actions runs the tests on Python 3.10, 3.12, and 3.13, then builds the Docker image and smoke-tests the running container: it checks that requests without an API key are rejected, then onboards and offboards an employee and confirms the access review comes back clean.

## How this was built

Project scaffolding (API routes, database layer, test suite, Docker, and CI pipeline) was set up with help from an AI assistant. The access management logic (onboarding, role changes, offboarding, and access reviews) was written by me. The whole idea of this project is for employers to see that i understand (TDD). Considering the tests aren't the real product, The API is so enjoy looking through my project and thank you for your time!

## License

MIT
