# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [Unreleased]

### Added

- Added initial project skeleton for the DX-Asset asset management platform.
- Added frontend foundation using Next.js, React, TypeScript, Tailwind CSS, and shadcn/ui.
- Added backend foundation using FastAPI, Python, Pydantic, SQLAlchemy, and Alembic.
- Added Docker Compose configuration for PostgreSQL.
- Added SQLAlchemy models for:
  - Departments
  - Users
  - Assets
  - Asset assignments
  - Incidents
  - Asset histories
- Added initial Alembic migration `001_initial_schema`.
- Added database constraints, foreign keys, indexes, and the active asset assignment unique index.
- Added seed script with demo departments, users, assets, assignments, incidents, and histories.
- Added demo accounts for the supported roles:
  - ADMIN
  - IT_ASSET_MANAGER
  - MANAGER
  - EMPLOYEE
- Added Phase 5A Backend Foundation:
  - FastAPI app structure, API router v1 (`/api/v1`), CORS middleware, and environment configurations.
  - Health Check API (`GET /api/v1/health`) with database connection check.
  - Security module (`app/core/security.py`) for password verification (`bcrypt`) and JWT token creation/decoding.
  - Authentication APIs (`POST /api/v1/auth/login`, `GET /api/v1/auth/me`).
  - FastAPI dependencies (`app/api/deps.py`) for `get_current_user` and RBAC role verification (`require_roles`).
  - Pydantic schemas for authentication and user profiles (`LoginRequest`, `TokenResponse`, `UserResponse`, `DepartmentResponse`).
  - Automated test suite for Phase 5A (`tests/test_auth.py`, `tests/test_health.py`, `tests/test_rbac.py`).
- Added Phase 5B Frontend Authentication:
  - Configured Tailwind CSS and global styling system for Next.js App Router (`tailwind.config.js`, `postcss.config.js`, `globals.css`).
  - Added TypeScript type definitions (`types/auth.ts`) for authentication, roles, users, and tokens.
  - Added API client utility (`lib/api.ts`) supporting configurable API base URL and automatic JWT Bearer token authorization header injection.
  - Added React Auth Context & Provider (`lib/auth-context.tsx`) managing login, logout, current user profile fetching, token storage in `localStorage`, and error state handling.
  - Added ProtectedRoute client-side guard component (`components/ProtectedRoute.tsx`) to protect authenticated pages with loading state.
  - Implemented Enterprise Login Page (`app/login/page.tsx`) with password visibility toggle, error alert messaging, and local demo accounts quick-fill functionality.
  - Implemented Protected Dashboard shell (`app/dashboard/page.tsx`) displaying logged-in user profile, role badges, JWT session security info, and logout mechanism.
  - Configured root route (`app/page.tsx`) to redirect users based on authentication status.

### Changed

- Configured the development environment for Node.js, Python, Docker, and PostgreSQL.
- Configured PostgreSQL connection for the local Docker development environment.

### Notes

- Phase 5A (Backend Auth & RBAC) and Phase 5B (Frontend Authentication) complete.
- CRUD APIs (Assets, Departments, Users), Asset Assignment workflows, Incident/Maintenance APIs, Business Dashboard stats, and AI features have not been implemented yet and will be added in upcoming phases.
