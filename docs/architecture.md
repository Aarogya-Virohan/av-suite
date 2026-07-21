# AV Suite CRM Backend Architecture

## Technology Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x (Async ORM)
- PostgreSQL
- Alembic
- Pydantic v2
- Docker
- uv

---

## Architecture

The application follows a layered architecture.

```
HTTP Request
      │
      ▼
Router
      │
      ▼
Service
      │
      ▼
Repository
      │
      ▼
SQLAlchemy
      │
      ▼
PostgreSQL
```

Each layer has a single responsibility.

---

## Layer Responsibilities

### Router

Responsible for:

- Request validation
- Dependency injection
- Authentication
- Returning API responses

Must NOT:

- Execute SQL
- Contain business logic
- Commit transactions

---

### Service

Responsible for:

- Business rules
- Validation
- Authorization checks
- Calling repositories
- Coordinating multiple repositories

Must NOT:

- Execute raw SQL
- Access FastAPI Request objects
- Return HTTP responses

---

### Repository

Responsible for:

- Database queries
- Persistence
- SQLAlchemy ORM operations

Must NOT:

- Contain business rules
- Raise HTTP exceptions
- Perform authentication

---

### Models

Represent database tables only.

Models must never contain business logic.

---

### Schemas

Represent API contracts.

Use Pydantic v2.

No business logic.

---

## Repository Pattern

Every repository inherits from BaseRepository.

Required methods:

- create
- get_by_id
- get_all
- update
- delete
- exists

Repositories may add entity-specific methods only.

Example:

ClinicRepository

- get_by_email
- search_by_name

PatientRepository

- get_by_phone
- get_by_clinic

---

## Service Pattern

Every service inherits from BaseService.

Required methods:

- create
- get
- list
- update
- delete

Services may implement business-specific logic.

Example:

ClinicService

- validate_timezone
- ensure_unique_email

AppointmentService

- reschedule
- cancel

---

## Transactions

Repositories never commit.

Services own transactions.

---

## Exception Handling

Repositories raise database exceptions only.

Services translate them into domain exceptions.

Routers translate domain exceptions into HTTP responses.

---

## Async Rules

Everything touching the database is async.

Never block the event loop.

---

## SQLAlchemy Rules

- SQLAlchemy 2.x only
- Mapped[]
- mapped_column()
- select()
- AsyncSession
- UUID primary keys

No legacy ORM syntax.

---

## Naming

Tables:
plural

Models:
singular

Clinic
Patient
Appointment

Repositories:

ClinicRepository

Services:

ClinicService

Schemas:

ClinicCreate
ClinicUpdate
ClinicRead

---

## Dependency Injection

Routers receive:

- AsyncSession
- Current user

Services receive repositories.

Repositories receive AsyncSession.

---

## Logging

Only services log business events.

Repositories never log successful queries.

---

## Testing

Repositories should be covered by database tests.

Services should be covered by business logic tests.

Routers should be covered by API tests.

---

## Principle

If code is reused twice, move it into a shared abstraction.
