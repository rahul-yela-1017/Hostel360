# Hostel Management System

A clean full-stack hostel operations application built with React, FastAPI, SQLAlchemy and MySQL. It starts with permanent infrastructure only: **431 rooms numbered 0–430 and 1,724 vacant beds**. No sample students, staff, attendance, menus or notices are inserted.

## First run

1. Start the API and frontend.
2. Open `/login`.
3. The application detects that no Administrator exists and displays a one-time Admin setup form.
4. Create the real Administrator account.
5. The setup endpoint permanently closes after the first Admin is created.
6. Use the Admin account to add Wardens and Cooks. Admin or Warden can then add students and assign vacant beds.

There are no built-in demo credentials.

## Functional modules

- One-time secure Administrator setup
- Bcrypt password hashes and JWT authentication
- Universal initial Student password (`MRBH@Student2026` locally, configurable with `STUDENT_INITIAL_PASSWORD`)
- Forced password change for newly created Warden, Cook and Student accounts
- Backend-enforced RBAC for `ADMIN`, `WARDEN`, `COOK` and `STUDENT`
- Admin management of Warden and Cook accounts, including enable/disable controls
- Student creation, editing, disable control, room assignment and atomic room transfer
- Exactly 431 rooms and exactly four beds per room
- Database constraints preventing duplicate active bed assignments
- Room occupancy search, filters and full bed-level details
- Attendance search by student, room, status and date
- Configurable gate closing time and automatic late classification
- Duplicate-safe daily attendance records
- Cook/Warden direct menu publishing with no approval step
- Menu history, hostel timings, Warden directory and notices
- Student dashboard using only the logged-in student’s real records
- Server-generated CSV, Excel and room-wise ZIP reports
- Audit logging for sensitive administrative actions and report downloads
- Responsive Admin, Warden, Cook and Student interfaces

Non-functional presentation controls and sample metrics were removed. Empty dashboards now show genuine onboarding or empty states until real data is added.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Local development defaults to SQLite. API documentation is available at `http://localhost:8000/api/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to the FastAPI service.

## Permanent GitHub deployment

The repository includes:

- `Dockerfile.production` — unified React + FastAPI production image
- `railway.toml` — Railway build, health-check and restart configuration
- `.github/workflows/ci.yml` — backend tests, frontend build and Docker build on every change
- `DEPLOYMENT.md` — complete GitHub, Railway and managed MySQL instructions

The production container serves the React SPA and `/api` from one HTTPS domain. Railway MySQL starts with only the permanent hostel rooms and beds; the real Administrator is created through the first-run screen.

## MySQL production setup

Copy `.env.example` to `.env`, set unique secrets and use a MySQL 8 database. The included `docker-compose.yml` remains available for a private server deployment.

Before production deployment:

- Generate and review Alembic migrations from the SQLAlchemy metadata.
- Put the application behind HTTPS.
- Store secrets and biometric encryption keys in a managed secret service.
- Replace in-process rate limiting with a Redis or gateway-backed limiter.
- Configure backups, restore tests, monitoring and structured logs.
- Complete privacy and security reviews.

## Face attendance boundary

The backend includes encrypted face-template enrollment, embedding matching, liveness-score enforcement and duplicate-safe kiosk attendance APIs. The fake demo-student scan and public demo kiosk were removed. A real kiosk should only be enabled after connecting a certified camera-side face/liveness provider that supplies versioned embeddings and verified liveness scores.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

The test suite creates its own clean database, completes first-run Admin setup, verifies room invariants and RBAC, creates real role accounts and students, checks bed conflicts, direct menu publishing, attendance rules and secure report generation.
