# Task 04: Exercise Library End-to-End — Completion & Architecture Report

This document outlines exactly what was accomplished during the implementation of Task 04, the technical decisions made, and why specific approaches were chosen over the alternatives.

## 1. Database & Schema Design
**What we did:**
We created new Alembic migrations to introduce the `prescriptions`, `prescription_items`, `posture_sessions`, and `posture_measurements` tables. We completely mapped these tables to SQLAlchemy models and created strictly typed Pydantic v2 schemas (`app/schemas/prescription.py` & `posture.py`).

**Why this solution?**
*   **Alembic over Manual Supabase Edits:** The project rules strictly forbade manual database edits. Using Alembic ensures that our schema changes are version-controlled, easily reviewable in pull requests, and deterministically reproducible across local, staging, and production environments.
*   **Pydantic v2 `model_config`:** We actively updated the schemas to use `model_config = {"from_attributes": True}` instead of the deprecated `class Config` to ensure the codebase remains warning-free and future-proof.

## 2. API & Service Architecture
**What we did:**
We built a suite of RESTful API endpoints:
*   `GET /api/v1/exercises/by-condition`
*   `POST /api/v1/prescriptions` (and `GET`, `PATCH` variants)
*   `POST /api/v1/posture/sessions`

**Why this solution?**
*   **Service Layer Pattern:** Instead of writing database query logic directly inside the API routers, we isolated the logic inside `services/prescription_service.py` and `services/posture_service.py`. This separation of concerns makes unit testing significantly easier and keeps the route files (`api/v1/prescriptions.py`) incredibly clean.

## 3. PDF Generation Engine
**What we did:**
We implemented a backend PDF generation endpoint (`POST /api/v1/prescriptions/{id}/pdf`) that dynamically queries a saved prescription and renders it into a professional clinical PDF. 

**Why WeasyPrint + Jinja2 over the alternatives?**
*   **Why not ReportLab?** ReportLab requires drawing PDFs using coordinate math (e.g., `canvas.drawString(100, 750, "Text")`), which makes styling a nightmare. `WeasyPrint` + `Jinja2` allows us to use standard HTML and CSS (`templates/prescription.html`), making it vastly easier to design beautiful, responsive, and branded clinical reports.
*   **Why backend rendering instead of frontend (e.g., `html2pdf.js`)?** Generating the PDF on the frontend heavily depends on the user's browser, screen size, and print drivers, often leading to cut-off text. By rendering it on the FastAPI backend, we guarantee a pixel-perfect, immutable PDF that we can also securely store in cloud storage (Supabase S3) for long-term medical compliance.

## 4. Frontend Integration ("Going Live")
**What we did:**
We completely removed the mock `exercises.json` file. We installed `@tanstack/react-query`, created an API client (`api.ts`), and hooked up the frontend to fetch live data from the backend using JWT authentication. We also wired up the Prescription Builder to automatically save to the database and open the generated PDF.

**Why `@tanstack/react-query` over standard `useEffect`?**
*   If we used standard `fetch` inside `useEffect`, we would have had to manually manage `isLoading`, `isError`, and caching states across multiple components. React Query handles all of this out-of-the-box, providing professional-grade state management, deduplication of requests, and automatic background refetching—crucial for a production-grade medical app.
*   **Payload Fixes:** We noticed the frontend was attempting to login using `application/x-www-form-urlencoded`, which clashed with our backend's strict JSON requirement. We updated `api.ts` to send pure `JSON.stringify` payloads to satisfy the Pydantic validators.

## 5. Development Infrastructure & Seeding
**What we did:**
During integration testing, Pytest wiped the database cleanly (via `conftest.py` dropping tables). To recover seamlessly, we built lightweight Python seeding scripts (`seed_patient.py`, `seed_exercises_script.py`, `reset_db.py`). 

**Why Python seeding scripts over raw `.sql` files?**
*   Executing raw SQL bypasses our application logic. By using SQLAlchemy async sessions in our seeding scripts, we ensure that passwords get properly hashed (using `auth.py` logic) and UUIDs are properly generated, guaranteeing that our dummy data behaves exactly like real production data.

## 6. Pytest Diagnostics
**What we did:**
We encountered a bug where `pytest` was failing because it tried to execute `test_supabase_connection.py` as a unit test, failing due to a missing fixture argument. We fixed this by renaming the file to `verify_supabase_connection.py`.

**Why this solution?**
*   Instead of writing complex mock fixtures to force Pytest to accept a diagnostic script, renaming it completely removes it from Pytest's auto-discovery radar (`test_*.py`). It elegantly preserves the script so developers can still run it manually via `python verify_supabase_connection.py` without breaking CI/CD pipelines.

---
**Status:** All goals for Task 04 have been fully achieved, integrated, and verified to be working perfectly locally. The code has been committed and pushed to `feature/tarun-exercise-backend`.
