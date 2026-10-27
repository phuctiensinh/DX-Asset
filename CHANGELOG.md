# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [Unreleased]

### Added

- AI asset risk explanation on the asset detail page (`POST /api/v1/intelligence/assets/{asset_id}/ai/explain`): the local Ollama model explains the existing risk score, its largest contributing factors and warning reasons, with at most 2 recommendations. Same access rule as `GET /api/v1/intelligence/assets/{asset_id}` (employees only for the asset currently assigned to them).
- AI asset lifecycle summary on the asset detail page (`POST /api/v1/assets/{asset_id}/ai/summary`): a 3–6 sentence summary of assignments, incidents, maintenance, repair cost and warranty. The context sends true totals plus a limited number of recent records; employees can only summarize the asset they currently hold and do not see previous holders' names.
- AI Process Mining report on the Process Mining page (`POST /api/v1/process-mining/ai/report`, same filters as the page): a 5–8 sentence Vietnamese report on overview, bottlenecks, rework and conformance with at most 3 recommendations, built from `ProcessMiningService` results. Same roles as the existing Process Mining endpoints.
- The three features above only interpret metrics already computed by the backend, reuse the existing `ollama_client`, reject AI answers that contain numbers not present in the context, fall back to a deterministic rule-based result when Ollama is unavailable, slow or invalid, run only when the user clicks, and store nothing.

### Fixed

- `test_explain_rejects_invented_numbers` no longer fails at random when a generated asset code happens to contain the digits used by the test.

## [1.0.0] - 2026-10-15

First public MVP release for the OLP 2026 open-source software competition.

### Added

- Process Mining case list and detail API responses include `reference_code` and `title`; case events include `performed_by_name` and `target_user_name`.

- AI triage suggestion on the incident report form: the local Ollama model suggests category and priority, and the user chooses whether to apply it (`POST /api/v1/incidents/ai/triage-suggestion`).
- AI incident summary in the incident detail view (`POST /api/v1/incidents/{id}/ai/summary`; employees only for incidents they reported).
- AI troubleshooting steps for IT staff, based on the incident and similar resolved incidents (`POST /api/v1/incidents/{id}/ai/troubleshooting`; ADMIN and IT_ASSET_MANAGER).
- Every AI feature falls back to rule-based results when Ollama is off, slow or returns invalid output, and the UI labels whether a result came from AI or from the fallback.

- Added Phase 14 read-only allocation, technician-capacity, and replacement/depreciation simulations, plus transparent replacement-priority recommendations.
- Added a role-protected Optimization API and responsive `/intelligence/optimization` page; recommendations are never applied automatically.
- Added deterministic Phase 14 assistant intents and restricted employee assistant queries to currently assigned asset information; global analytics remain management-only.

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

- The whole user interface is now consistently Vietnamese: internal codes (`IN_STOCK`, `IN_PROGRESS`, `ADMIN`, `HARDWARE_SUPPORT`, risk levels, ...) are shown as Vietnamese labels from the shared `frontend/src/lib/labels.ts`; English headings, buttons, placeholders and HTTP codes in messages were translated.
- Backend messages shown to users are Vietnamese: API error details, request validation errors (new global handler for HTTP 422), asset history details, smart-routing and similar-incident reasons, optimization assumptions/warnings, asset risk reasons and AI assistant answers. Status codes inside these texts use `backend/app/core/labels.py`.
- The AI assistant answers process questions in Vietnamese and accepts real ticket codes (e.g. "Phiếu INC-2026-001 đã trải qua những bước nào?"); `CASE-<id>` is still accepted.
- Keycloak login and registration pages are Vietnamese via the new `dx-asset` login theme (`docker/keycloak/themes/dx-asset`); the realm uses it by default.

- Redesigned the Process Mining page as "Phân tích quy trình xử lý": all text is in Vietnamese, with a "how to read this page" guide, typical processing/response times, common paths ("Luồng 1, 2…"), slowest transitions ranked, and the data-quality details moved into a collapsible section.
- Internal codes (`INCIDENT_CREATED`, `IN_PROGRESS`, `variant-<hash>`, `CASE-001`, user IDs) are no longer shown to users; the page shows Vietnamese labels, ticket codes, titles and people's names instead. The API keeps the codes unchanged.
- The "Đến ngày" filter is now inclusive of the selected day.

- `POST /api/v1/incidents/{id}/classify` now uses Ollama for queue classification, with keyword rules as fallback.
- Default `OLLAMA_TIMEOUT_SECONDS` raised from 10 to 30 so the first request after loading the model does not time out.

- The frontend Docker image now builds and runs in production mode (`next build` + `next start`) instead of the dev server.
- Added `.dockerignore` files so host `node_modules`, `.next` and `.venv` are not copied into images.
- Added the `ollama-pull` one-shot service that downloads the AI model automatically.
- `.sh` files are forced to LF line endings so the backend container works when cloned on Windows.
- `start-dev.bat` uses the GPU when `nvidia-smi` is available and stops the Docker backend/frontend to free ports 8000/3000.
- Rewrote the README installation guide (Docker mode, local dev mode, accounts, common commands, troubleshooting).

- Configured the development environment for Node.js, Python, Docker, and PostgreSQL.
- Configured PostgreSQL connection for the local Docker development environment.

### Fixed

- "Đăng ký tài khoản mới" now opens the Keycloak registration form directly (`/registrations` endpoint) instead of the login page.

- `start-dev.bat` now points the local backend to `http://localhost:11434`; before this, local dev could never reach Ollama and always used the fallback.

- Fixed newly registered Keycloak users getting `401`/`500` on `/auth/me`: `SYSTEM_OWNER_EMAIL` was not defined in `app/api/deps.py`.
- Fixed the Docker backend rejecting every Keycloak token: JWKS is now fetched via the `keycloak` service name, and `pyjwt[crypto]` is installed for RS256 verification.
- Fixed the Ollama healthcheck, which always failed and blocked the Docker backend from starting.
- Fixed `docker compose up` failing on machines without an NVIDIA GPU; GPU support moved to the optional `docker-compose.gpu.yml`.

### Notes

- Phase 5A, 5B, 5C, Phase 6 (Asset Assignment), and Phase 7 (Incident Management) are fully implemented and verified.

[Unreleased]: https://github.com/phuctiensinh/DX-Asset/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/phuctiensinh/DX-Asset/releases/tag/v1.0.0
