# Permanent Deployment: GitHub + Railway + MySQL

This project is configured to deploy as one production container. The container builds the React application, copies it into FastAPI, and serves both the UI and `/api` from one domain. Railway provides the public HTTPS URL and managed MySQL database.

## 1. Push the repository to GitHub

Create an empty private GitHub repository, then run from the project directory:

```bash
git init
git branch -M main
git add .
git commit -m "Initial Malla Reddy Boys Hostel application"
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

Do not commit `.env`, `smart_hostel.db`, tokens or biometric keys. They are excluded by `.gitignore` and `.dockerignore`.

Every push to `main` runs GitHub Actions for:

- Backend tests
- Frontend production build
- Unified production Docker image build

## 2. Create the Railway project

1. Sign in to Railway.
2. Select **New Project → Deploy from GitHub repo**.
3. Connect the repository created above.
4. Railway detects `railway.toml` and builds `Dockerfile.production`.
5. Add a **MySQL** service to the same project.
6. In the application service, create `DATABASE_URL` as a reference to the MySQL service’s connection URL. If Railway exposes `MYSQL_URL`, reference that value. The backend automatically converts `mysql://` to SQLAlchemy’s `mysql+pymysql://` driver form.

## 3. Application environment variables

Set these variables on the application service:

```env
APP_ENV=production
DEMO_MODE=false
DATABASE_URL=<reference to the Railway MySQL connection URL>
SECRET_KEY=<at least 32 random characters>
STUDENT_INITIAL_PASSWORD=<your controlled initial Student password>
KIOSK_API_KEY=<separate random device key>
BIOMETRIC_ENCRYPTION_KEY=<Fernet key>
ACCESS_TOKEN_MINUTES=480
CORS_ORIGINS=https://YOUR-RAILWAY-DOMAIN
```

Generate secure values locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use the first output for `SECRET_KEY` or `KIOSK_API_KEY` and the second output only for `BIOMETRIC_ENCRYPTION_KEY`.

## 4. Public domain

1. Open the Railway application service.
2. Select **Settings → Networking → Generate Domain**.
3. Railway provides a permanent HTTPS URL.
4. Update `CORS_ORIGINS` with that URL and redeploy.

A custom college domain can later be added in the same Networking section by creating the DNS record Railway displays.

## 5. First production login

The production MySQL database starts with:

- Malla Reddy Boys Hostel
- Rooms 0–430
- Four vacant beds per room
- No sample users or attendance records

Open the permanent domain. The one-time setup screen creates the real Administrator. The endpoint closes immediately after the first Admin is saved.

## 6. Deployment verification

Check:

```text
https://YOUR-DOMAIN/api/health
https://YOUR-DOMAIN/api/docs
```

Then verify:

1. Administrator setup and login
2. Warden and Cook account creation
3. Student creation and forced first-login password change
4. Bed allocation and transfer conflict protection
5. Manual attendance and Student attendance refresh
6. Direct menu publication
7. CSV, Excel and ZIP report downloads
8. Audit log creation

## 7. Production operations

Before real biometric use, connect a certified liveness/embedding provider and configure the kiosk key. Also configure MySQL backups, application monitoring, log retention, a custom domain and organisational privacy policy.
