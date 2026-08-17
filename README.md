SentinelAI

AI-Powered AWS Cloud Security Auditor — connects to an AWS account with read-only credentials, audits IAM, S3, EC2, CloudTrail, CloudWatch, Lambda, RDS, KMS, and Secrets Manager, scores risk, maps findings to CIS/NIST/ISO 27001/SOC 2/AWS Well-Architected, explains findings with AI, and generates executive/technical/compliance reports.

SentinelAI never modifies AWS resources. Every AWS API call made by the collectors is Describe/Get/List-class, and a runtime guard (services/aws/client_factory.py) blocks any mutating call before it reaches the network — see Read-only enforcement below.

Overview





Backend

FastAPI, Python 3.12, SQLAlchemy 2.0, SQLite, Alembic, boto3, Groq

Frontend

React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Recharts

AI

Groq API — configurable model, streaming, retry, JSON structured output; verified with openai/gpt-oss-20b

Auth

JWT (access + refresh), bcrypt password hashing

Design

Dark-mode-only enterprise SaaS UI (Stripe/Linear/GitHub/AWS Console inspired)

Screenshots

DashboardFindings







Finding DetailCompliance







ReportsAI Security Chat







Architecture

See ARCHITECTURE.md for the full system design: high-level architecture diagram, ER diagram, API flow, Figma page map, and component hierarchy.

Browser (React/Vite) → FastAPI (/api/v1/*) → Service Layer → Repository Layer → SQLite
                                    ├── services/aws     (boto3, read-only guarded)
                                    ├── services/risk     (scoring, compliance mapping)
                                    ├── services/ai       (Groq client)
                                    └── services/reports  (PDF/CSV/JSON)


Read-only enforcement

Three independent layers ensure SentinelAI can never change your AWS account:

Code convention — every collector in services/aws/*.py calls only Describe*, Get*, List*, Head*, or Generate* operations.

Runtime guard — client_factory.py attaches a botocore event handler to every client that raises WriteOperationBlocked before any non-read operation reaches the network. This was verified in testing: DeleteBucket, CreateUser, AttachUserPolicy, TerminateInstances, DeleteDBInstance, and ScheduleKeyDeletion calls are all blocked pre-flight.

IAM policy boundary — the credentials you give SentinelAI should themselves only grant read permissions (see below), so even a bug in the first two layers can't cause damage.

Folder structure

sentinelai/
├── ARCHITECTURE.md
├── README.md
├── docs/
│   ├── iam-readonly-policy.json
│   ├── iam-trust-policy.json
│   └── screenshots/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # auth, aws, audit, findings, compliance, reports, chat, dashboard
│   │   ├── core/             # config, database, security (JWT/encryption)
│   │   ├── models/           # 9 SQLAlchemy tables
│   │   ├── schemas/          # Pydantic v2 request/response contracts
│   │   ├── repositories/     # DB access layer
│   │   ├── services/
│   │   │   ├── aws/          # 9 read-only collectors + client factory + orchestrator
│   │   │   ├── risk/         # scoring + CIS/NIST/ISO/SOC2/Well-Architected mapping
│   │   │   ├── ai/           # Groq client, explanations, chat, summaries
│   │   │   └── reports/      # PDF (ReportLab) / CSV / JSON generation
│   │   ├── middleware/       # JWT auth, rate limiting, exception handling
│   │   ├── prompts/          # AI prompt templates
│   │   └── main.py
│   ├── alembic/               # migrations
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/
        ├── components/        # Button, Card, Badge, Modal, Table, RiskIndicator, ...
        ├── layouts/            # AppShell, AuthLayout
        ├── features/           # dashboard, aws, audit, findings, compliance, reports, chat, settings
        ├── pages/              # Login, Register, Profile, 404
        ├── services/           # axios instance + per-domain API modules
        ├── store/              # auth context
        ├── routes/             # React Router config
        └── types/              # shared TS types mirroring backend schemas


Features

AWS security audit across IAM, S3, EC2, CloudTrail, CloudWatch, Lambda, RDS, KMS, Secrets Manager

Risk engine: 0–100 risk score per finding (likelihood × business impact × exploitability), 0–100 overall Security Score per audit

Compliance mapping: CIS AWS Foundations, NIST CSF, ISO 27001, SOC 2, AWS Well-Architected — PASS/WARNING/FAIL per control

AI features (Groq): per-finding explanations (cached), Terraform/CloudFormation/AWS CLI remediation snippets, executive/technical/compliance summaries, grounded AI chat (answers strictly from that audit's findings)

Reports: PDF, CSV, JSON — Executive, Technical, Compliance, Risk, Audit History categories

Dashboard: security score, findings by severity/service, score trend, recent audits

Auth: JWT access + refresh tokens, bcrypt hashing

Installation

Prerequisites

Python 3.12+

Node.js 20+

A Groq API key (for AI features)

An AWS account with a ReadOnly IAM role (see below) — only needed to run real audits; the app itself runs without one

Backend

cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit .env — see Configuration below
alembic upgrade head              # creates all tables
uvicorn app.main:app --reload --port 8000

API docs: http://localhost:8000/api/docs

Frontend

cd frontend
npm install
npm run dev

App: http://localhost:5173 (Vite proxies /api/* to http://localhost:8000)

Configuration / Environment variables

All backend config lives in backend/.env (see backend/.env.example for the full template):

VariablePurpose



JWT_SECRET_KEY

Signs access/refresh tokens. Generate: python -c "import secrets; print(secrets.token_urlsafe(64))"

CREDENTIALS_ENCRYPTION_KEY

Fernet key encrypting any static AWS access keys at rest. Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

DATABASE_URL

Defaults to sqlite:///./sentinelai.db

CORS_ORIGINS

Comma-separated allowed origins (default http://localhost:5173)

GROQ_API_KEY

Required for all AI features

GROQ_MODEL

Default model; per-task overrides live in app/core/config/groq_config.py

RATE_LIMIT_PER_MINUTE

Default 60

RAG_SEMANTIC_CANDIDATE_K

FAISS candidates per authorized audit (default 10)

RAG_KEYWORD_CANDIDATE_K

BM25 candidates per authorized audit (default 10)

RAG_RERANK_CANDIDATE_K

Maximum fused candidates sent to the cross-encoder (default 15)

RAG_FINAL_TOP_K

Findings supplied to Groq after reranking (default 5)

The app refuses to start with placeholder secrets (JWT_SECRET_KEY/CREDENTIALS_ENCRYPTION_KEY left as change-me...), by design.

Hybrid RAG retrieval

Chat retrieval is scoped to one authorized audit. FastEmbed (BAAI/bge-small-en-v1.5) searches that audit's FAISS index while audit-local BM25 searches canonical finding text (service, severity, CIS/NIST controls, remediation, and references). The two ranked ID lists are combined with Reciprocal Rank Fusion (sum(1 / (60 + rank))), so incomparable FAISS and BM25 scores are never mixed directly. At most RAG_RERANK_CANDIDATE_K fused documents are then scored by FastEmbed's ONNX cross-encoder (Xenova/ms-marco-MiniLM-L-6-v2), and the top RAG_FINAL_TOP_K are re-hydrated from canonical SQL before Groq receives them.

The cross-encoder is loaded lazily and cached; it adds model download/storage and per-query latency, but only for the bounded candidate set. If it is disabled (RAG_RERANK_ENABLED=false), the fused ranking is used directly. The deterministic retrieval evaluation records this example for an unrestricted-SSH query: FAISS [s3, iam], hybrid [s3, ssh, iam], then reranked [ssh, iam, s3]. It demonstrates an intentional ranking change, not a measured quality claim.

RAG evaluation

The repeatable 20-query security fixture is evaluated through the same progression used by chat: semantic FAISS retrieval, hybrid FAISS + BM25 retrieval with Reciprocal Rank Fusion, then hybrid retrieval plus cross-encoder reranking. Run it from backend with python -m app.services.rag.evaluation --output rag_evaluation_report.json. The command writes per-query retrieved/relevant IDs, ranks, Hit@K/Recall@K, semantic scores, and Hit@5 failure records to JSON.

Measured on the fixture with the local FastEmbed models:

SystemHit@1Hit@3Hit@5Recall@1Recall@3Recall@5MRR















FAISS

0.850

1.000

1.000

0.733

0.967

1.000

0.917

Hybrid

0.900

0.950

1.000

0.783

0.875

0.958

0.929

Hybrid + Reranking

0.950

1.000

1.000

0.833

0.983

1.000

0.975

Hit@K checks whether any relevant finding appears within K; Recall@K preserves multiple relevant findings per query; MRR rewards the rank of the first relevant finding. Hybrid + Reranking has the highest MRR on this fixture. These are fixture-specific retrieval metrics, not a general performance claim. Answer-level quality is intentionally not scored: groundedness and relevance need either a documented heuristic, manual review, or an LLM judge and are outside this lightweight retrieval benchmark.

Controlled chat tools

Security Chat can ask Groq to call seven read-only application tools: audit summary, filtered findings, one finding by ID, critical findings, findings by service, findings by CIS/NIST mapping, and affected resources. The model receives only typed tool schemas; it never receives database, filesystem, AWS credential, shell, or arbitrary-query access.

Every call is validated against an explicit allowlist and strict Pydantic arguments. The audit ID is taken only from the authenticated request context, then ownership is re-validated before each tool query. Groq can make at most three tool-call rounds. Tool results are marked as authoritative application data and are combined with the existing audit-scoped RAG context before the final answer.

Agentic Security Investigation

User request -> bounded agent controller -> approved tools + RAG
             -> evidence collection -> grounded security report


services/ai/agent provides one investigation workflow for requests such as “Investigate my highest-risk issue.” It uses a deterministic, five-step maximum plan: critical findings, canonical finding details, affected resources, audit-scoped hybrid RAG, then a grounded Groq synthesis. The report keeps observed findings, retrieved guidance, AI analysis, and remediation recommendations separate.

The agent is bounded, audit-scoped, tool-allowlisted, authorization-controlled, non-mutating, and evidence-grounded. Its controller—not the model or any retrieved content—owns the authorized audit ID, action enum, and hard limit. It cannot run shell/SQL/file operations or modify cloud infrastructure; remediation is a recommendation only.

The investigation API is POST /api/v1/audit/{audit_session_id}/investigate with { "question": "Investigate my highest-risk security issue." }. It authenticates the caller and revalidates ownership of the route audit before invoking the existing controller; inaccessible audit IDs receive the same not-found response used by the other audit routes.

AI Security Controls

SentinelAI implements layered defenses against prompt injection and unauthorized tool use; it does not claim that prompt injection is solved. Clear attempts to override instructions, expose secrets, manipulate audit scope, execute SQL-like requests, or read filesystem paths are rejected before model execution, while normal security-analysis questions remain valid.

Retrieved findings are explicitly wrapped as untrusted data. The chat policy tells the model never to follow instructions embedded in retrieved content or tool data. Deterministic application code—not the model—enforces the tool allowlist, strict Pydantic arguments, authenticated audit ownership, a three-round tool limit, and the configurable AI_TOOL_RESULT_LIMIT cap.

Structured top-risk responses are Pydantic-validated against the supplied finding IDs. Chat output is redacted for obvious secret patterns and removes explicit finding references that were not present in the retrieved or authorized tool data. Prompts and tools never include credentials, authorization headers, database connection details, or filesystem contents.

AI Observability

SentinelAI provides local structured AI telemetry with request, audit, and operation correlation IDs. It records safe metadata only: Groq model/latency/response size/retries, RAG and reranking latency plus candidate counts and finding IDs, and tool name/latency/result bounds. In-process counters cover LLM, RAG, empty-retrieval, and tool success/error totals; errors are classified without exposing stack traces to users.

AI_OBSERVABILITY_ENABLED and AI_METRICS_ENABLED default to true; AI_LOG_SENSITIVE_DATA defaults to false. Prompts, responses, tool arguments, credentials, headers, and secret-shaped values are not logged. This is development-friendly application telemetry, not production monitoring infrastructure. Streaming records inference timing and size, but retains its existing incremental-output limitation.

Deployment

SentinelAI has been deployed on AWS EC2 with:

Backend: FastAPI + Uvicorn managed by systemd

Reverse proxy: Nginx

Frontend: Vite production build served through Nginx

Database: SQLite

AI provider: Groq API

AWS access: AssumeRole with a dedicated read-only IAM role

Secrets: kept in the server-side .env file and excluded from Git

Production health checks

Backend health:

curl -i http://127.0.0.1/api/health

Expected response:

{"status":"ok","service":"SentinelAI"}

Check the backend service:

sudo systemctl status sentinelai --no-pager

Production AI model

The deployed configuration uses:

GROQ_MODEL=openai/gpt-oss-20b

Do not commit the real GROQ_API_KEY. Configure it only in the deployment environment.

Git / deployment safety

The repository intentionally ignores:

.env and environment-specific secrets

Python virtual environments

frontend dependencies and build output

local SQLite databases

RAG/model caches

generated reports and logs

This keeps production credentials and machine-specific runtime data out of GitHub.

AWS IAM ReadOnly policy

SentinelAI supports two auth methods when connecting an AWS account — AssumeRole is recommended since it requires no long-lived secrets.

Option A — AssumeRole (recommended)

Create an IAM role in the target account using the trust policy in docs/iam-trust-policy.json (fill in your SentinelAI deployment account ID and choose your own External ID).

Attach the permissions policy in docs/iam-readonly-policy.json — scoped to exactly the read-only API calls SentinelAI's collectors make (35 actions across 11 services, no wildcards beyond Resource: "*", which is required since these are account-wide Describe/List/Get calls with no ARN-level granularity in AWS).

In the "Connect AWS Account" form, provide the role's ARN and your chosen External ID.

Option B — Static access keys (fallback)

Create an IAM user with the same permissions policy, generate an access key, and enter it directly. Keys are encrypted (Fernet/AES) before being stored and are never returned by any API response.

Running the backend

cd backend
uvicorn app.main:app --reload --port 8000

Health check: GET /api/health. Swagger UI: /api/docs.

Running the frontend

cd frontend
npm run dev

Running tests / verifying the read-only guard

The read-only enforcement can be sanity-checked directly:

from app.services.aws.client_factory import _attach_read_only_guard, WriteOperationBlocked
import boto3

client = _attach_read_only_guard(boto3.client("s3", region_name="us-east-1"))
client.delete_bucket(Bucket="anything")  # raises WriteOperationBlocked before any network call

Future improvements

Additional AWS services: VPC Flow Logs, GuardDuty, Config, WAF, ACM

Scheduled/recurring audits with diffing between runs

Slack/email notifications on new critical findings (settings scaffolding already exists)

Multi-account / AWS Organizations support with a consolidated org-wide dashboard

Role-based access control for team accounts (currently single-user-owns-account model)

Code-splitting the frontend bundle (currently a single ~880KB chunk — flagged by Vite's build output)

Terraform module for one-click ReadOnly role provisioning instead of manual policy creation
