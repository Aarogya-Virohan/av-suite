# Rollback.md — Know Your Way Out Before You Need It
> **Purpose**: Every high-risk operation has a documented rollback plan written
> BEFORE the change is made. Read the rollback plan first. If there isn't one, write one.

---

## Rollback Plan Template

```markdown
### [RP-NNN] Operation Name
- **Risk Level**: Critical / High / Medium
- **When to Use This Plan**: [What went wrong triggers this]
- **Time to Execute**: ~N minutes
- **Requires Downtime?**: Yes / No

#### What Was Changed
[List of files, database changes, config changes]

#### Signs You Need to Rollback
- [Symptom 1]
- [Symptom 2]

#### Rollback Steps
1. Step 1
2. Step 2

#### Verification After Rollback
- [ ] Check 1
- [ ] Check 2

#### Prevention for Next Time
[What to do differently to avoid needing this plan]
```

---

## Rollback Plans

---

### [RP-001] Database Migration Rollback
- **Risk Level**: Critical
- **When to Use**: Migration caused data loss, schema corruption, or application errors after `alembic upgrade`
- **Time to Execute**: 5–30 minutes (depends on whether data was lost)
- **Requires Downtime?**: Yes

#### Signs You Need to Rollback
- Application throws `sqlalchemy.exc.OperationalError` after migration
- Columns referenced in code are missing in DB
- Data appears missing from tables after migration
- Application fails health check immediately after deployment

#### Rollback Steps
1. **Stop the application** (stop uvicorn / kill Docker container)
   ```bash
   # If running directly:
   pkill -f uvicorn
   # If Docker:
   docker compose down
   ```

2. **Check current migration state**
   ```bash
   cd backend
   alembic current
   ```

3. **Downgrade one revision**
   ```bash
   alembic downgrade -1
   ```
   Or to a specific revision:
   ```bash
   alembic downgrade <revision_id>
   ```

4. **If downgrade fails (destructive migration)**
   - Restore from database backup (see RP-002)
   - Contact your database admin immediately

5. **Restart the application with the previous code version**
   ```bash
   git stash  # or git checkout <previous-commit>
   uvicorn app.main:app --reload
   ```

#### Verification After Rollback
- [ ] `alembic current` shows the expected previous revision
- [ ] Application starts without SQLAlchemy errors
- [ ] `GET /health` returns `{"status": "healthy"}`
- [ ] `GET /api/v1/patients` returns data (not 500)

#### Prevention for Next Time
- Always run `alembic upgrade --sql head` first to review SQL before executing
- Never run a migration that drops columns in a single step
- Always have a database backup before any migration

---

### [RP-002] Database Backup Restore
- **Risk Level**: Critical
- **When to Use**: Data was deleted or corrupted and cannot be recovered via downgrade
- **Time to Execute**: 15–60 minutes
- **Requires Downtime?**: Yes

#### Signs You Need to Rollback
- Production data deleted (patients, appointments, billing records missing)
- Migration with `DROP TABLE` or `DROP COLUMN` ran against live data
- Database is in an unrecoverable state

#### Rollback Steps
1. Stop application immediately
2. Identify most recent clean backup (check your PostgreSQL backup provider)
3. Restore:
   ```bash
   psql $DATABASE_URL < backup_YYYYMMDD.sql
   ```
4. Verify data restored:
   ```sql
   SELECT COUNT(*) FROM patients;
   SELECT COUNT(*) FROM leads;
   ```
5. Run any migration forward from restored state if needed:
   ```bash
   alembic upgrade head
   ```

#### Verification After Rollback
- [ ] Patient count matches pre-incident expected count
- [ ] Application starts cleanly
- [ ] Test a specific known patient record to confirm data integrity

---

### [RP-003] Frontend Deployment Rollback (Next.js)
- **Risk Level**: High
- **When to Use**: New deployment broke the frontend (blank page, auth broken, API calls failing)
- **Time to Execute**: 5–10 minutes
- **Requires Downtime?**: No (brief)

#### Signs You Need to Rollback
- Login page doesn't render
- `isAuthenticated` never becomes true after login
- Console shows CORS errors on all API calls
- All pages show loading spinners indefinitely

#### Rollback Steps
1. **Identify last working commit**
   ```bash
   git log --oneline -10
   ```

2. **Check out previous version**
   ```bash
   git checkout <previous-commit-hash> -- frontend/crm/
   ```

3. **Rebuild and redeploy**
   ```bash
   cd frontend/crm
   npm run build
   # Deploy built files
   ```

4. **If using Vercel / cloud deployment**: Use deployment dashboard to promote previous deployment

#### Verification After Rollback
- [ ] `/login` page renders correctly
- [ ] Login with valid credentials succeeds and redirects to `/dashboard`
- [ ] KPI cards on dashboard show data (or loading state)
- [ ] No console errors on load

---

### [RP-004] ClinicGateMiddleware Change Rollback
- **Risk Level**: Critical
- **When to Use**: Change to `clinic_gate.py` caused 401 on all requests or allowed cross-clinic access
- **Time to Execute**: 2–5 minutes
- **Requires Downtime?**: No

#### Signs You Need to Rollback
- All authenticated requests suddenly return 401
- Different clinic's data visible to wrong clinic
- `/health` starts returning 401 (middleware regression)

#### Rollback Steps
1. **Revert the file to the last known good state**
   ```bash
   git diff backend/app/middleware/clinic_gate.py  # review what changed
   git checkout HEAD~1 -- backend/app/middleware/clinic_gate.py
   ```

2. **Restart the application**
   ```bash
   pkill -f uvicorn
   uvicorn app.main:app --reload
   ```

#### Verification After Rollback
- [ ] `GET /health` returns 200 (no auth needed — should not be blocked by middleware)
- [ ] `POST /api/v1/auth/login` succeeds (public path — not blocked)
- [ ] `GET /api/v1/leads` with a valid JWT returns data (not 401)
- [ ] `GET /api/v1/leads` without a JWT returns 401

---

### [RP-005] API Client Interceptor Change Rollback
- **Risk Level**: High
- **When to Use**: Change to `api-client.ts` broke authentication or error handling
- **Time to Execute**: 2 minutes
- **Requires Downtime?**: No

#### Signs You Need to Rollback
- Login succeeds but subsequent API calls all return 401 (token not attached)
- 401 redirect loop (login page → dashboard → login)
- Error messages not surfacing to users

#### Rollback Steps
```bash
git checkout HEAD~1 -- frontend/crm/src/lib/api-client.ts
# Restart dev server or rebuild
npm run dev
```

#### Verification After Rollback
- [ ] Login → token stored → subsequent GET requests include `Authorization: Bearer ...` header
- [ ] Intentional 401 (log out + try to access API) → redirects to `/login`
- [ ] API errors surface backend's `detail` message, not generic "Network Error"

---

### [RP-006] Environment Variable Change Rollback
- **Risk Level**: High
- **When to Use**: `.env` / `.env.local` change caused API connection failure or CORS errors
- **Time to Execute**: 1 minute
- **Requires Downtime?**: No

#### Rollback Steps
1. Restore previous values from `.env.example` or team vault
2. Restart backend/frontend dev server

#### Verification After Rollback
- [ ] Backend: `GET /health` returns healthy
- [ ] Frontend: API calls don't show CORS errors in console
- [ ] Login flow works end-to-end

---

## Pre-Change Checklist (Before Any High-Risk Change)

Before making changes that require a rollback plan:

- [ ] I have identified the rollback plan for this change (above, or write a new RP-NNN)
- [ ] I have noted the current commit hash: `git rev-parse HEAD`
- [ ] For DB changes: I have confirmed a backup exists or created one
- [ ] I have read the relevant `Constraints.md` entries
- [ ] I have documented my decision in `Decisions.md`

---

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
*Write rollback plans BEFORE making risky changes. Not after.*
