# CGMS – Contracts & Guarantees Management System

Bilingual (English / Arabic) cloud application for private businesses in Kuwait. Built by International Valor Systems (IVS).
Specification documents are in `docs/` (BRD, FSD, Data Schema). Sprint plan: `docs/SPRINT_PLAN.md`.

**Status:** Phase 1, Sprint 1 (foundations) complete: client (tenant) separation, login with lockout, default roles and
permissions, audit log, English/Arabic with right-to-left layout, and 44 automated tests.

## Run it on your computer (easiest: Docker)
1. Install Docker Desktop.
2. Copy `.env.example` to `.env` (keep the defaults for local use).
3. Run: `docker compose up --build`
4. In a second terminal:
   ```
   docker compose exec web python manage.py create_platform_admin --email you@example.com
   docker compose exec web python manage.py seed_demo
   ```
5. Open http://localhost:8000
   - Demo client login: `admin@alpha.test` / `Demo-Pass-2026!` (other demo users: `manager@`, `officer@`, `finance@`, `legal@`, `viewer@`, `auditor@alpha.test`)
   - Your platform admin sees the list of client companies only, never their contracts.

## Run without Docker (Python 3.12)
```
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DJANGO_DEBUG=1                                    # Windows PowerShell: $env:DJANGO_DEBUG="1"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```
Without `DATABASE_URL` it uses a local SQLite file; production uses PostgreSQL.

## Run the tests
```
DJANGO_DEBUG=1 python manage.py test
```
Every change must keep all tests passing. GitHub runs them automatically on every push (`.github/workflows/ci.yml`).

## Create a real client company
```
python manage.py create_organization --name-en "Client Co" --name-ar "شركة العميل" --admin-email admin@client.com
```
This creates the company, the seven default roles and the first Org Admin (temporary password printed; must be changed at first login).

## Rules for developers (and for Claude)
- Every client-owned table extends `apps.core.models.TenantModel`. This makes queries client-filtered automatically.
- Never accept `organization_id` from a browser. It comes only from the signed-in user.
- Use soft delete (`obj.soft_delete()`); hard delete is blocked.
- All visible text uses translation (`{% trans %}` / `gettext`). Add Arabic in `tools_make_translations.py`, then run it.
- New feature = code + tests (rules, permissions, audit entry, tenant isolation, Arabic).
- Never commit `.env`, passwords or customer data.

## Layout
```
config/            settings, urls
apps/core/         tenant context, base model, audit log, permissions, middleware
apps/accounts/     organization, users, roles, login, dashboard, audit screen, commands
templates/ static/ screens, Bootstrap (LTR + RTL)
locale/ar/         Arabic translations
docs/              BRD, FSD, Data Schema, sprint plan
```

## Not yet done (later sprints)
Subscriptions and seat limits, users/roles screens, configuration, parties, contracts, guarantees, cheques, documents,
alert engine, reports, import, two-step login. Tested on SQLite here; CI runs the same tests on PostgreSQL 16.
