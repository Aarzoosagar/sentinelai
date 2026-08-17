# SentinelAI — Architecture Specification

AI-Powered AWS Cloud Security Auditor (Read-Only). This document is the single source of truth for structure before any code is written, per project rules.

---

## 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             CLIENT (Browser)                              │
│   React + TypeScript + Vite + Tailwind + TanStack Query + Framer Motion   │
└───────────────────────────────┬────────────────────────────────────────-─┘
                                 │ HTTPS / JWT Bearer
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI APPLICATION (Python 3.12)                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │  Auth API   │  │ Audit API  │  │ Findings   │  │ Compliance API    │  │
│  ├────────────┤  ├────────────┤  ├────────────┤  ├───────────────────┤  │
│  │ Reports API│  │ Chat API   │  │ Dashboard  │  │ AWS Account API   │  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────────┬─────────┘  │
│        │               │               │                    │           │
│        └───────────────┴───────┬───────┴────────────────────┘           │
│                                 ▼                                        │
│                    ┌─────────────────────────┐                          │
│                    │     Service Layer        │                         │
│                    │  - AWS Collector Service  │                        │
│                    │  - Risk Engine            │                        │
│                    │  - AI Service (Groq)      │                        │
│                    │  - Report Generator       │                        │
│                    └───────────┬───────────────┘                        │
│                                 ▼                                        │
│                    ┌─────────────────────────┐                          │
│                    │   Repository Layer        │                        │
│                    │  (SQLAlchemy ORM)          │                       │
│                    └───────────┬───────────────┘                        │
└────────────────────────────────┼─────────────────────────────────────-──┘
                                  ▼
                        ┌──────────────────┐
                        │   SQLite (via     │
                        │   Alembic migr.)  │
                        └──────────────────┘

        External integrations (outbound only, read-only where AWS is concerned):
        ┌─────────────────────┐        ┌──────────────────────┐
        │  AWS APIs (boto3)    │        │   Groq LLM API        │
        │  ReadOnly IAM creds  │        │  (chat completions)   │
        └─────────────────────┘        └──────────────────────┘
```

**Core invariant:** every `services/aws/*` call uses a boto3 client constructed from a **ReadOnlyAccess**-scoped role/credentials. No `Create*`, `Put*`, `Delete*`, `Update*`, `Modify*`, `Attach*`, `Terminate*`, or `Authorize*` boto3 calls exist anywhere in the codebase. This is enforced both by code convention and by an IAM policy boundary (see README).

---

## 2. Low-Level Architecture (Backend)

```
Request → CORS Middleware → Auth Middleware (JWT decode) → Rate Limiter
        → Router (api/v1/*) → Pydantic Schema Validation
        → Service Layer (business logic, orchestration)
        → Repository Layer (DB access, SQLAlchemy sessions)
        → Response Schema (Pydantic) → Central Exception Handler → JSON

Audit Execution Pipeline (async background flow):
  1. POST /api/v1/audit/start {aws_account_id}
  2. AuditOrchestrator creates `audit_sessions` row (status=RUNNING)
  3. Collector modules run per-service (IAM, S3, EC2, CloudTrail, CloudWatch,
     Lambda, RDS, KMS, Secrets Manager) via boto3 ReadOnly clients
  4. Raw resource metadata normalized → passed to Risk Engine
  5. Risk Engine scores each finding (severity, likelihood, business impact,
     CIS/NIST mapping, MITRE ATT&CK mapping where applicable)
  6. Findings persisted to `findings` + `risk_scores`
  7. Compliance Engine maps findings → CIS/NIST/ISO/SOC2 controls → PASS/WARN/FAIL
  8. AI Service (Groq) generates narrative explanations per finding (on-demand,
     cached in `findings.ai_explanation`, not blocking collection)
  9. Audit session marked COMPLETED, overall Security Score (0-100) computed
  10. Dashboard aggregates refresh from `findings` + `compliance_results`
```

---

## 3. Database ER Diagram

```
┌────────────────┐       ┌─────────────────────┐       ┌──────────────────┐
│     users        │      │    aws_accounts       │      │  audit_sessions    │
├────────────────┤       ├─────────────────────┤       ├──────────────────┤
│ id (PK)          │◄──┐  │ id (PK)                │◄──┐  │ id (PK)             │
│ email             │   │  │ user_id (FK)           │   │  │ aws_account_id (FK) │
│ hashed_password   │   └──┤ account_alias          │   └──┤ status              │
│ full_name         │      │ role_arn / access_key* │      │ started_at          │
│ created_at        │      │ region                 │      │ completed_at        │
└────────────────┘       │ validated_at           │      │ resources_scanned   │
                            │ created_at             │      │ security_score      │
                            └─────────────────────┘      └────────┬─────────┘
                                                                    │
                        ┌──────────────────────────────────────────┤
                        ▼                                          ▼
              ┌──────────────────┐                       ┌───────────────────┐
              │    findings        │                      │  compliance_results │
              ├──────────────────┤                       ├───────────────────┤
              │ id (PK)             │                      │ id (PK)              │
              │ audit_session_id(FK)│                      │ audit_session_id(FK) │
              │ service (IAM/S3/…)  │                      │ framework (CIS/NIST…)│
              │ title                │                      │ control_id           │
              │ description          │                      │ status (PASS/WARN/FAIL)│
              │ severity             │                      │ related_finding_id   │
              │ resource_arn         │                      └───────────────────┘
              │ cis_control          │
              │ nist_control         │              ┌──────────────────┐
              │ mitre_attack         │              │   risk_scores      │
              │ remediation          │              ├──────────────────┤
              │ ai_explanation       │◄─────────────┤ id (PK)             │
              │ status                │              │ finding_id (FK)     │
              │ created_at            │              │ risk_score (0-100)  │
              └──────────┬───────────┘              │ likelihood          │
                         │                            │ business_impact     │
                         ▼                            └──────────────────┘
              ┌──────────────────┐
              │     reports         │
              ├──────────────────┤
              │ id (PK)             │
              │ audit_session_id(FK)│
              │ type (PDF/CSV/JSON) │
              │ category (exec/tech/│
              │   compliance/risk)  │
              │ file_path            │
              │ generated_at          │
              └──────────────────┘

┌──────────────────┐            ┌──────────────────┐
│   ai_messages       │            │     settings        │
├──────────────────┤            ├──────────────────┤
│ id (PK)             │            │ id (PK)             │
│ user_id (FK)        │            │ user_id (FK)        │
│ audit_session_id(FK)│            │ groq_model           │
│ role (user/assistant│            │ notification_prefs   │
│ content              │            │ theme                │
│ created_at           │            │ updated_at           │
└──────────────────┘            └──────────────────┘

* access keys, if used instead of AssumeRole, are encrypted at rest (Fernet)
  and never returned by any API response.
```

---

## 4. API Flow Diagram

```
Auth flow:
  POST /api/v1/auth/register  → hash pw (bcrypt) → create user
  POST /api/v1/auth/login     → verify pw → issue JWT (python-jose)
  GET  /api/v1/auth/me        → JWT required

Onboarding flow:
  POST /api/v1/aws/accounts             → store account (role_arn or encrypted keys)
  POST /api/v1/aws/accounts/{id}/validate → sts:GetCallerIdentity (read-only check)

Audit flow:
  POST /api/v1/audit/start                → kick off collector pipeline
  GET  /api/v1/audit/{id}/status          → poll progress
  GET  /api/v1/audit/history              → past sessions

Findings flow:
  GET  /api/v1/findings?severity=&service=&status=&region=
  GET  /api/v1/findings/{id}
  POST /api/v1/findings/{id}/ai-explain   → Groq-generated narrative

Compliance flow:
  GET  /api/v1/compliance/{audit_id}?framework=CIS

Reports flow:
  POST /api/v1/reports/generate  {audit_id, type, category}
  GET  /api/v1/reports/{id}/download

Chat flow:
  POST /api/v1/chat/message  {audit_id, message} → Groq, grounded only in
       that audit's persisted findings (RAG over `findings` table, no
       hallucinated infra state)

Dashboard flow:
  GET /api/v1/dashboard/summary   → widgets (score, findings counts, trend)
```

---

## 5. Complete Folder Tree

```
sentinelai/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth/        audit/        dashboard/     reports/
│   │   │   ├── findings/    chat/         compliance/    aws/
│   │   ├── core/
│   │   │   ├── config/      (settings.py, groq_config.py)
│   │   │   └── database/    (session.py, base.py)
│   │   ├── models/          (SQLAlchemy ORM models, 1 file per table)
│   │   ├── schemas/         (Pydantic v2 request/response schemas)
│   │   ├── repositories/    (DB access layer, 1 per aggregate)
│   │   ├── services/
│   │   │   ├── aws/         (iam.py, s3.py, ec2.py, cloudtrail.py,
│   │   │   │                 cloudwatch.py, lambda_svc.py, rds.py, kms.py,
│   │   │   │                 secrets_manager.py, client_factory.py)
│   │   │   ├── ai/          (groq_client.py, explain.py, chat.py)
│   │   │   ├── risk/        (scoring.py, cis_mapping.py, mitre_mapping.py)
│   │   │   └── reports/     (pdf_report.py, csv_report.py, json_report.py)
│   │   ├── middleware/      (auth.py, rate_limit.py, cors.py, exceptions.py)
│   │   ├── utils/
│   │   ├── prompts/         (Groq prompt templates, versioned)
│   │   ├── tests/
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── assets/
    │   ├── components/      (shared UI: Button, Card, Badge, Modal, Table…)
    │   ├── layouts/          (AppShell, AuthLayout)
    │   ├── pages/             (route-level pages)
    │   ├── features/
    │   │   ├── dashboard/    audit/      findings/    reports/
    │   │   ├── chat/         settings/
    │   ├── hooks/            (useAudit, useFindings, useAuth…)
    │   ├── services/          (axios instance, api/*.ts per domain)
    │   ├── store/              (auth/session state)
    │   ├── routes/             (React Router config, protected routes)
    │   ├── types/              (shared TS types/interfaces)
    │   ├── utils/
    │   ├── styles/             (tailwind.css, tokens)
    │   └── App.tsx
    ├── index.html
    ├── package.json
    ├── tailwind.config.ts
    └── vite.config.ts
```

*(Full directory tree already scaffolded on disk under `sentinelai/`.)*

---

## 6. Figma Page Map

| # | Page | Key states |
|---|------|-----------|
| 1 | Login | default, error, loading |
| 2 | Register | default, validation error |
| 3 | Dashboard | populated, empty (no audits yet) |
| 4 | AWS Connection | form, validating, success, failure |
| 5 | Audit Wizard | select account → scope → running → complete |
| 6 | Findings List | filtered, empty, loading |
| 7 | Finding Details | with AI explanation, without |
| 8 | AI Security Chat | empty thread, streaming response |
| 9 | Compliance Dashboard | per-framework tabs |
| 10 | Reports | list + generate modal |
| 11 | Audit History | timeline view |
| 12 | User Profile | view/edit |
| 13 | Settings | Groq model config, notifications |
| 14 | 404 | — |
| 15 | Empty States | per-module illustration set |
| 16 | Loading States | skeletons per widget type |
| 17 | Error States | network error, auth error, server error |

**Typography:** Heading XL/L/M, Body Large/Small, Caption, Monospace (ARNs/IDs).
**Color tokens:** bg `#050505`, card `#111111`, border `#222222`, text primary white, text secondary gray, accent blue `#3B82F6` / green `#10B981` / yellow `#F59E0B` / red `#EF4444`. 12px radius, 8pt spacing grid, dark mode only, no gradients/glassmorphism/neon.

---

## 7. Component Hierarchy (Frontend)

```
App
├── AuthLayout
│   ├── LoginPage
│   └── RegisterPage
└── AppShell (protected)
    ├── Sidebar (nav items, collapse)
    ├── TopNavigation (search, profile menu, notifications)
    └── <Outlet>
        ├── DashboardPage
        │   ├── MetricCard × N (Security Score, Resources Scanned, …)
        │   ├── RiskByServiceChart / RiskBySeverityChart (Recharts)
        │   ├── SecurityScoreTrendChart
        │   └── RecentAuditsTable
        ├── AwsConnectionPage → AccountForm, ValidationStatus
        ├── AuditWizardPage → ScopeSelector, ProgressTimeline
        ├── FindingsListPage → FilterBar, FindingsTable, SeverityBadge
        ├── FindingDetailPage → RiskIndicator, RemediationSteps, AIExplanationPanel
        ├── CompliancePage → ComplianceCard × framework, ControlTable
        ├── ReportsPage → ReportCard × N, GenerateReportModal
        ├── AuditHistoryPage → Timeline
        ├── ChatPage → ChatBubble × N, ChatInput, SuggestedQuestions
        ├── ProfilePage
        └── SettingsPage → GroqModelConfig, NotificationPrefs

Shared components/: Button, Input, Dropdown, SearchBar, Badge, Card, Modal,
Drawer, Toast, Breadcrumb, Tabs, Pagination, ProgressBar, StatusChip,
RiskIndicator, ReportCard, ComplianceCard, ChatBubble, ResourceCard, MetricCard
```

---

## 8. Build Sequence (post-architecture)

Per project rules, code is generated file-by-file, no placeholders, no TODOs. Sequence:

1. Backend `core/` (config, database, security) → `models/` → `schemas/`
2. Backend `services/aws/` (read-only collectors, one file per AWS service)
3. Backend `services/risk/` (scoring + CIS/NIST/MITRE mappings)
4. Backend `services/ai/` (Groq client + prompt templates)
5. Backend `repositories/` → `api/v1/*` routers → `main.py`
6. Frontend design tokens/Tailwind config → shared `components/`
7. Frontend `features/*` pages in the order: auth → aws connection → audit → dashboard → findings → compliance → reports → chat → settings
8. README + IAM ReadOnly policy document

This document is now finalized. Next message will begin Step 1 of the build sequence with complete backend core files.
