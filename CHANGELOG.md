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

- Added Phase 5C Asset CRUD:
  - Asset management API endpoints (`GET /api/v1/assets`, `GET /api/v1/assets/{id}`, `POST /api/v1/assets`, `PATCH /api/v1/assets/{id}`, `DELETE /api/v1/assets/{id}`).
  - Asset Pydantic schemas (`AssetCreate`, `AssetUpdate`, `AssetResponse`, `AssetListResponse`).
  - Frontend Asset Management page (`app/assets/page.tsx`) with search, filter, pagination, create, edit, detail modals.
- Added Phase 6 Asset Assignment:
  - Assignment API endpoints (`GET /api/v1/assignments`, `GET /api/v1/assignments/{id}`, `POST /api/v1/assignments`, `PATCH /api/v1/assignments/{id}/return`, `PATCH /api/v1/assignments/{id}/transfer`).
  - Helper endpoints `GET /api/v1/users` and `GET /api/v1/departments`.
  - Frontend Asset Assignment page (`app/assignments/page.tsx`) with Cấp phát, Thu hồi, Chuyển giao workflows.
  - Partial unique index DB constraint protection and IntegrityError 409 Conflict handling.
- Added Phase 7 Incident Management:
  - Incident API endpoints (`GET /api/v1/incidents`, `GET /api/v1/incidents/{id}`, `POST /api/v1/incidents`, `PATCH /api/v1/incidents/{id}`).
  - Incident Pydantic schemas (`IncidentCreate`, `IncidentUpdate`, `IncidentResponse`, `IncidentListResponse`).
  - Valid status transition validation (`OPEN` -> `IN_REVIEW` -> `IN_PROGRESS` -> `RESOLVED` / `CLOSED` / `CANCELLED`).
  - Asset history audit recording (`INCIDENT_REPORTED`, `MAINTENANCE_UPDATED`).
  - Frontend Incident Management page (`app/incidents/page.tsx`) with reporting modal and IT ticket processing modal.
- Added Phase 8 Dashboard & Statistics:
  - Dashboard API endpoint (`GET /api/v1/dashboard/summary`) returning real-time PostgreSQL SQL aggregation data.
  - Pydantic response models (`DashboardSummaryResponse`, `AssetStatusCounts`, `AssignmentStatusCounts`, `IncidentStatusCounts`, `DepartmentAssetStats`, `RecentActivityItem`).
  - SQL aggregation queries for asset statuses, assignment statuses, incident statuses, department allocation metrics (`outerjoin` and status filter case statements), and top 10 recent asset history events.
  - Complete real-time Frontend Dashboard UI (`app/dashboard/page.tsx`) with 5 metric summary cards, status progress bar distribution, incident breakdown grid, department allocation table, and activity feed.
  - Automated unit tests (`tests/test_dashboard.py`) with full RBAC, dynamic update, and 100% test idempotency.
- Added Phase 9 AI Assistant for Asset Management:
  - Natural language Vietnamese query API (`POST /api/v1/assistant/chat`).
  - Pydantic schemas (`AssistantChatRequest`, `AssistantChatResponse`, `AssistantSource`).
  - AIAssistantService implementing intent recognition, PostgreSQL real-data tools, and read-only mutation guards (`MUTATION_REJECTED`).
  - Rule-Based Fallback Engine automatically activated when optional AI API key is unconfigured or unavailable.
  - Interactive Frontend AI Chat interface (`app/assistant/page.tsx`) with suggested question chips, real data source tags, typing animations, and Navbar link.
  - Automated unit test suite (`tests/test_assistant.py`) covering read-only policy, asset lookups, count queries, ticket lookups, and idempotency.
- Added Phase 10 Asset Maintenance & Incident Workflow:
  - Database schema: `MaintenanceStatus` enum (`SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`), `maintenances` table, relations in `Asset` and `Incident` models, and Alembic migration `002_add_maintenance_table.py`.
  - Added `MAINTENANCE_STARTED` and `MAINTENANCE_COMPLETED` action types to `AssetActionType`.
  - Maintenance Pydantic schemas (`MaintenanceCreate`, `MaintenanceUpdate`, `MaintenanceStart`, `MaintenanceComplete`, `MaintenanceResponse`, `MaintenanceListResponse`).
  - Maintenance API endpoints (`GET /api/v1/maintenances`, `GET /api/v1/maintenances/{id}`, `POST /api/v1/maintenances`, `PATCH /api/v1/maintenances/{id}/start`, `PATCH /api/v1/maintenances/{id}/complete`, `PATCH /api/v1/maintenances/{id}`).
  - Atomic asset status transitions: asset changes to `IN_MAINTENANCE` on start without losing `current_user_id` or `department_id`, and safely reverts to `ASSIGNED` if active assignment exists or `IN_STOCK` if unassigned upon completion.
  - Linked maintenance resolution guard on `PATCH /api/v1/incidents/{id}`: prevents moving incident to `RESOLVED` or `CLOSED` when linked maintenance is active (`SCHEDULED` or `IN_PROGRESS`).
  - Full audit tracking in `AssetHistory` for maintenance scheduling, start, completion, and updates.
  - Frontend Maintenance Management page (`app/maintenance/page.tsx`) with status filters, search, aggregation metrics, plan creation modal, complete modal, detail modal, and navbar link.
  - Updated AI Assistant service (`app/services/ai_assistant.py`) with `MNT-` maintenance code lookup and maintenance stats support.
  - Automated unit test suite (`tests/test_maintenances.py`) with 65 total passing tests.


### Changed

- Configured the development environment for Node.js, Python, Docker, and PostgreSQL.
- Configured PostgreSQL connection for the local Docker development environment.

### Notes

- Phase 5A, 5B, 5C, Phase 6 (Asset Assignment), and Phase 7 (Incident Management) are fully implemented and verified.

