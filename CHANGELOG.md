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

### Changed

- Configured the development environment for Node.js, Python, Docker, and PostgreSQL.
- Configured PostgreSQL connection for the local Docker development environment.

### Notes

- Phase 5A authentication and RBAC foundation complete.
- CRUD APIs (Assets, Departments, Users), Asset Assignment workflows, Incident/Maintenance APIs, Dashboard, Frontend UI integration, and AI features have not been implemented yet and will be added in upcoming phases.
