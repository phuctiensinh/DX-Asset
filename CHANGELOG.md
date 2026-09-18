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

### Changed

- Configured the development environment for Node.js, Python, Docker, and PostgreSQL.
- Configured PostgreSQL connection for the local Docker development environment.

### Notes

- The database schema and demo data are available.
- Backend authentication API, CRUD APIs, frontend business screens, dashboard, and AI features have not been implemented yet.
