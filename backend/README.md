# AV Suite Backend Foundation

This is the backend foundation for the AV Suite, built with FastAPI, PostgreSQL (via Supabase), and SQLAlchemy. It implements a multi-tenant architecture scoped by `clinic_id` via JWT authentication.

## Environment Variables

The application requires the following environment variables. Copy `.env.example` to `.env` and fill in the placeholders:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:CHANGEME@db.PROJECT_REF.supabase.co:5432/postgres

# JWT
JWT_SECRET_KEY=CHANGEME_GENERATE_WITH_secrets.token_hex_32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Redis
REDIS_URL=redis://localhost:6379

# Runtime
ENVIRONMENT=development
DEBUG=true
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

**Never commit the real `.env` file to version control.**

## Local Development

We use Docker Compose to run the API and Redis locally.

1. Ensure your `.env` is configured.
2. Build and start the containers:

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`. Hot-reloading is enabled because the source code is mounted as a volume.

## Database Migrations

Migrations are managed by Alembic. 

To run migrations against your Supabase database:
```bash
alembic upgrade head
```

To create a new migration after modifying models:
```bash
alembic revision --autogenerate -m "description_of_change"
```
*Note: Make sure your `DATABASE_URL` in `.env` points to the target database before running migrations.*

## Running Tests

To run the automated tests (including the clinic isolation test):

1. Install development dependencies locally:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

2. Run `pytest`:
```bash
pytest tests/
```
