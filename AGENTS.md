# AGENTS.md

## 1. Project Overview

This project is named **DX-Asset**.

Full name:

> DX-Asset: Open-Source Digital Asset Lifecycle Management Platform

DX-Asset is an open-source web platform for managing the lifecycle of enterprise assets and internal equipment, such as:

* Laptops
* Desktop computers
* Monitors
* Printers
* Routers
* Network devices
* Office equipment
* Other internal company assets

The platform focuses on helping organizations manage asset information, assignment, return, maintenance, incident reporting, and asset history in one centralized system.

The project is designed for the **Phần mềm Nguồn mở OLP 2026** competition, whose theme is related to the DX-OS/DX-Lab digital transformation framework.

---

## 2. Developer Context

The main developer is:

* Name: Nguyễn Phạm Đại Phúc
* University: Trường Đại học Thủ Dầu Một
* Major: Software Engineering / Kỹ thuật Phần mềm
* Current level: Third-year university student

The developer is familiar with basic programming and web development but may need explanations for unfamiliar technologies, architectural decisions, deployment processes, authentication systems, database design, and AI integration.

When introducing a new technology or concept:

1. Explain what it is in simple Vietnamese.
2. Explain why the project needs it.
3. Explain how it will be used in this project.
4. Avoid introducing unnecessary complexity.

---

## 3. Main Project Goal

Build a functional, understandable, maintainable, and open-source MVP that demonstrates a complete asset-management workflow.

The project should prioritize:

* A working product over excessive features
* A clear main workflow
* A clean and usable interface
* A consistent database structure
* Traceable asset history
* Practical AI assistance
* Easy local setup
* Public source code
* Clear documentation
* Reproducible builds

The project should not attempt to become a complete ERP system.

---

## 4. Competition Context

The project should align with the four DX-OS spaces:

### H — Human

Includes:

* Users
* Employees
* Departments
* Roles
* Permissions
* Managers
* IT staff
* Asset managers

### P — Process

Includes:

* Asset creation
* Asset import
* Asset assignment
* Asset return
* Asset transfer
* Incident reporting
* Maintenance processing
* Asset status updates
* Approval processes where necessary

### D — Data

Includes:

* Asset records
* Employee records
* Department records
* Assignment history
* Maintenance history
* Incident records
* Asset status
* Dashboard statistics
* Knowledge-base documents

### I — Intelligence / AI

Includes:

* Automatic incident categorization
* Suggested incident priority
* Suggested responsible department
* Incident summarization
* Search over maintenance guides
* AI-assisted troubleshooting
* Retrieval-Augmented Generation when appropriate

AI must support users rather than replace important human decisions.

---

## 5. Main Demonstration Workflow

The primary demo workflow should be:

1. An administrator creates an asset.
2. The system generates or attaches a QR code to the asset.
3. The administrator assigns the asset to an employee.
4. The employee views the asset information or scans its QR code.
5. The employee reports a problem.
6. The system creates an incident or maintenance ticket.
7. IT staff receives and processes the ticket.
8. IT staff updates the repair status and resolution details.
9. The system stores the complete history.
10. A manager views asset and maintenance statistics on the dashboard.

This workflow is the central product path.

All major implementation decisions should support this workflow.

---

## 6. MVP Features

### 6.1 Authentication and Authorization

Implement a basic authentication system with role-based access control.

Suggested roles:

* `ADMIN`
* `IT_ASSET_MANAGER`
* `EMPLOYEE`
* `MANAGER`

Expected behavior:

* Admin can manage users, departments, and assets.
* IT/Asset Manager can manage assets and process maintenance tickets.
* Employees can view assigned assets and submit incident reports.
* Managers can view relevant reports and dashboards.

Do not implement overly complex enterprise identity management unless required.

Never hardcode passwords or secrets in source code.

---

### 6.2 Asset Management

The system should support:

* Create an asset
* View asset details
* Edit an asset
* Archive or deactivate an asset
* Search assets
* Filter assets
* Categorize assets
* View asset status
* View current assignee
* View asset location or department
* Generate or display QR code

Suggested asset fields:

* Asset code
* Asset name
* Category
* Brand
* Model
* Serial number
* Purchase date
* Warranty expiration date
* Current status
* Current location
* Assigned user
* Department
* Description
* Created date
* Updated date

Suggested asset statuses:

* `IN_STOCK`
* `ASSIGNED`
* `IN_MAINTENANCE`
* `DAMAGED`
* `RETIRED`
* `LOST`

Use a consistent status model. Avoid unnecessary status values.

---

### 6.3 Asset Assignment and Return

The system should support:

* Assigning an asset to an employee
* Returning an asset
* Transferring an asset to another employee
* Recording assignment date
* Recording return date
* Recording the responsible person
* Viewing assignment history

Assignment history must not be overwritten when an asset changes owner.

The system should preserve historical records for traceability.

---

### 6.4 Incident and Maintenance Management

Employees should be able to report an issue related to an asset.

Incident fields may include:

* Asset
* Reporter
* Title
* Description
* Category
* Priority
* Status
* Attached image, if supported
* Created date
* Assigned IT staff
* Resolution
* Repair cost, if applicable
* Completed date

Suggested incident categories:

* Hardware
* Software
* Network
* Power
* Physical damage
* Other

Suggested priority levels:

* Low
* Medium
* High
* Critical

Suggested incident statuses:

* `OPEN`
* `IN_REVIEW`
* `IN_PROGRESS`
* `WAITING_FOR_INFORMATION`
* `RESOLVED`
* `CLOSED`
* `CANCELLED`

The system should preserve incident history and status changes where practical.

---

### 6.5 Dashboard

The dashboard should display useful summary information, such as:

* Total number of assets
* Number of assets in stock
* Number of assigned assets
* Number of assets under maintenance
* Number of damaged assets
* Number of retired assets
* Number of open incidents
* Number of incidents by priority
* Number of assets by department
* Recent asset activities
* Recent maintenance tickets

Do not add charts only for decoration. Every dashboard component should support an actual management question.

---

### 6.6 QR Code

Each asset should have a unique QR code or QR identifier.

Scanning the QR code should lead to an asset detail page or asset-related action page, depending on the user's permission.

The QR workflow should be simple and reliable.

Do not require a native mobile application for the MVP. A responsive web page is sufficient.

---

### 6.7 AI Assistance

AI should be implemented as an assistant feature, not as an autonomous decision-maker.

Possible AI functions:

1. Classify an incident category.
2. Suggest incident priority.
3. Suggest the responsible department or team.
4. Summarize a long incident description.
5. Suggest troubleshooting steps.
6. Search maintenance documentation.
7. Explain common equipment problems.

AI output should be presented as a suggestion that users can review and modify.

The system must not:

* Automatically approve expensive repairs.
* Automatically delete or retire assets.
* Automatically assign legal or financial responsibility.
* Automatically execute critical operational actions.
* Treat AI output as guaranteed truth.

If an external AI API is used, provide a fallback mode or clearly explain the required environment variables.

Do not expose API keys in frontend code.

---

## 7. Suggested Technology Stack

The initial suggested stack is:

### Frontend

* Next.js
* TypeScript
* Tailwind CSS
* shadcn/ui or another accessible component system

### Backend

* FastAPI
* Python
* REST API

### Database

* PostgreSQL

SQLite may be used for a lightweight local prototype only if PostgreSQL would unnecessarily delay development.

### Infrastructure

* Docker Compose
* GitHub
* GitHub Actions

### Documentation

* Markdown
* README
* Changelog
* Issue templates
* Contribution guide

The stack may be changed if there is a strong technical reason. Do not change technologies merely because another framework is popular.

---

## 8. Architecture Guidelines

Use a clear separation of responsibilities.

Suggested structure:

```text
frontend/
backend/
database/
docs/
scripts/
docker-compose.yml
README.md
AGENTS.md
CHANGELOG.md
LICENSE
```

The exact folder structure may change if the selected framework has a better standard structure.

### Frontend Responsibilities

* User interface
* Routing
* Form validation
* API communication
* Loading and error states
* Role-based UI visibility
* Responsive layout

### Backend Responsibilities

* Authentication
* Authorization
* Business rules
* Input validation
* Database access
* Asset lifecycle logic
* Incident processing
* AI integration
* API error handling

### Database Responsibilities

* Persistent storage
* Relationships
* Constraints
* Indexes where necessary
* Audit and history records

Do not place business logic entirely inside frontend components.

Do not duplicate important business rules across frontend and backend.

---

## 9. Development Workflow for the AI Agent

The AI Agent should follow this sequence.

### Phase 1 — Analyze

Before writing code:

1. Inspect the repository.
2. Identify existing files.
3. Identify installed tools and dependencies.
4. Check whether the project is already initialized.
5. Identify missing configuration.
6. Summarize the current state.
7. Propose a small implementation plan.

Do not overwrite existing work without checking it first.

### Phase 2 — Design

Define:

* Main entities
* Database relationships
* API endpoints
* User roles
* Main screens
* Main workflow
* Error states
* Authentication approach

Keep the design appropriate for an MVP.

### Phase 3 — Initialize

Set up:

* Frontend
* Backend
* Database
* Environment configuration
* Docker Compose, if applicable
* Basic README
* Git repository structure

Verify that the application can run locally.

### Phase 4 — Implement Core Features

Implement in this order unless there is a strong reason to change it:

1. Database schema
2. Backend foundation
3. Authentication and roles
4. Asset management
5. Assignment and return
6. Incident and maintenance
7. Dashboard
8. QR code
9. AI assistance
10. Documentation and polish

Each phase should produce a testable result.

### Phase 5 — Test

After implementing a feature:

* Run the application.
* Check for build errors.
* Check API errors.
* Test the main user flow.
* Test invalid input.
* Test permission restrictions.
* Test empty states.
* Test loading states.
* Test error states.
* Fix issues before moving on.

Do not claim a feature is complete if it has not been tested.

### Phase 6 — Document

Update:

* README
* Installation instructions
* Environment variables
* API documentation
* Changelog
* Known limitations
* Contribution guide
* License information

---

## 10. Coding Principles

Follow these principles:

* Prefer simple and readable code.
* Avoid unnecessary abstractions.
* Avoid premature optimization.
* Avoid overengineering.
* Use meaningful names.
* Keep functions and components reasonably focused.
* Validate user input.
* Handle errors explicitly.
* Do not silently ignore exceptions.
* Avoid duplicated business logic.
* Keep secrets out of source control.
* Use environment variables for configuration.
* Use migrations for database changes.
* Keep dependencies minimal.
* Prefer stable and well-documented libraries.

When there are multiple valid solutions, choose the solution that is easiest for a student team to understand, maintain, demonstrate, and deploy.

---

## 11. Open-Source Requirements

The project must be genuinely open source.

Required considerations:

* Public source repository
* An OSI-approved open-source license
* A clear `LICENSE` file
* A complete `README.md`
* Build and run instructions
* Dependency license compatibility
* Public issue tracker
* Changelog
* Reproducible setup
* No private secrets committed to the repository

Before adding a dependency, check:

1. Its license.
2. Whether it is compatible with the project license.
3. Whether it is actively maintained enough for the project.
4. Whether it is actually necessary.

Do not copy code from an unknown source without checking its license.

---

## 12. Security Requirements

At minimum:

* Never commit API keys.
* Never commit database passwords.
* Never expose backend secrets to the frontend.
* Hash passwords using a secure password-hashing algorithm.
* Validate authentication tokens.
* Enforce authorization on the backend.
* Validate uploaded files.
* Restrict file types and sizes.
* Avoid SQL injection.
* Avoid trusting role information sent by the frontend.
* Do not expose sensitive user information unnecessarily.
* Use safe error messages in production.

This is an MVP, but basic security must not be ignored.

---

## 13. UI and UX Guidelines

The interface should be:

* Clean
* Modern
* Responsive
* Easy to understand
* Consistent
* Suitable for an enterprise internal tool

Important screens may include:

* Login
* Dashboard
* Asset list
* Asset detail
* Create/edit asset
* Assignment history
* Incident list
* Incident detail
* User management
* Department management
* Knowledge base or AI assistant

Every page should include appropriate:

* Loading states
* Empty states
* Error states
* Success feedback
* Form validation messages

Avoid unnecessary animations and decorative elements that do not improve usability.

---

## 14. Scope Restrictions

Do not expand the MVP into the following unless explicitly requested:

* Full ERP system
* Accounting and depreciation management
* Complete procurement management
* Payroll management
* GPS tracking
* IoT hardware integration
* Facial recognition
* Native Android and iOS applications
* Complex enterprise SSO
* Advanced predictive maintenance
* Fully autonomous AI agents
* Complex microservices architecture
* Kubernetes deployment
* Multi-region infrastructure
* Excessive analytics
* Unnecessary real-time infrastructure

The main goal is a polished, demonstrable MVP.

---

## 15. Communication Style

When responding to the developer:

* Use Vietnamese by default.
* Explain unfamiliar concepts simply.
* Be direct and practical.
* Clearly distinguish facts, assumptions, and recommendations.
* Mention trade-offs when important.
* Do not pretend that a command was executed if it was not.
* Do not claim that code was tested unless it was actually tested.
* If information is missing, ask for it or state the assumption.
* If an approach is overcomplicated, explain why and suggest a simpler alternative.
* When providing code, provide complete files when possible.
* Avoid giving only partial code patches if a full replacement is clearer.

---

## 16. Definition of Done

A feature is considered complete only when:

* The code is implemented.
* The application can start successfully.
* The main flow works.
* Input validation exists.
* Errors are handled.
* Permissions are respected.
* The UI is usable.
* The feature is documented where necessary.
* No secrets are exposed.
* The implementation does not unnecessarily expand the project scope.

The overall MVP is complete when a user can demonstrate:

1. Creating an asset.
2. Assigning it to an employee.
3. Viewing the asset and its QR code.
4. Reporting a problem.
5. Processing the maintenance ticket.
6. Updating the asset status.
7. Viewing the asset history.
8. Viewing dashboard statistics.
9. Using at least one practical AI-assisted feature.
10. Running the project using documented instructions.
