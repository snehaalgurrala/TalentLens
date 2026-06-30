# TalentLens

> AI-powered recruitment intelligence platform — identify and hire top talent faster.

TalentLens analyzes resumes, matches candidates with job descriptions, ranks applicants using customizable scoring rules, and streamlines screening through AI-driven communication assessments.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Roadmap](#roadmap)
- [Getting Started](#getting-started)
- [License](#license)

---

## Overview

Recruiting at scale is slow, inconsistent, and prone to bias. TalentLens brings AI into every step of the hiring funnel — from parsing the first resume to drafting an offer letter — so recruiters spend less time triaging and more time building relationships with candidates who genuinely fit.

---

## Features

- **Resume Parsing & Normalization** — extract structured data (skills, experience, education) from PDF/DOCX resumes using LLMs.
- **JD–Candidate Matching** — semantic vector search aligns job descriptions with the most relevant candidate profiles.
- **Customizable Scoring Engine** — recruiters define weighted criteria; the engine scores and ranks every applicant consistently.
- **AI Communication Assessment** — evaluate written responses and async video transcripts for clarity, tone, and role fit.
- **Screening Automation** — auto-generate personalised outreach, schedule interviews, and send status updates.
- **Analytics Dashboard** — funnel metrics, time-to-hire, source ROI, and diversity insights at a glance.
- **Multi-tenant SaaS** — isolated workspaces per organisation with role-based access control (RBAC).

---

## Architecture

```
                        ┌─────────────────────────────────┐
                        │          Client Browser          │
                        └──────────────┬──────────────────┘
                                       │ HTTPS
                        ┌──────────────▼──────────────────┐
                        │       Next.js Frontend (3000)    │
                        └──────────────┬──────────────────┘
                                       │ REST / WebSocket
          ┌────────────────────────────▼────────────────────────────┐
          │                  FastAPI Backend (8000)                  │
          │  Auth · CRUD · Job Queue · Webhooks · File Upload       │
          └──────┬───────────────────┬──────────────────────────────┘
                 │                   │
   ┌─────────────▼──────┐  ┌────────▼──────────────────────────────┐
   │  PostgreSQL + pgvec│  │          AI Services (8001)            │
   │  (structured data  │  │  Resume Parsing · Matching · Scoring   │
   │   + embeddings)    │  │  Assessment · Generation (Claude API)  │
   └────────────────────┘  └───────────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │  Redis (cache,  │
        │  task queue)    │
        └─────────────────┘
```

All services are containerised and orchestrated with Docker Compose for local development, and are designed to deploy to Kubernetes (or any container platform) in production.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React, TypeScript, Tailwind CSS, shadcn/ui |
| **Backend API** | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic v2 |
| **AI Services** | Python 3.12, Anthropic SDK (Claude), LangChain, pgvector |
| **Database** | PostgreSQL 16 + pgvector extension |
| **Cache / Queue** | Redis 7, Celery |
| **Auth** | JWT (access + refresh), OAuth2 (Google, GitHub) |
| **Storage** | S3-compatible object storage (AWS S3 / MinIO) |
| **Containerisation** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Sentry, structured JSON logging |

---

## Folder Structure

```
TalentLens/
├── backend/            # FastAPI application (API, auth, jobs, models)
├── frontend/           # Next.js application (pages, components, hooks)
├── ai-services/        # AI microservice (parsing, matching, scoring)
├── docker/             # Dockerfiles and service-specific init scripts
├── docs/               # Architecture diagrams, ADRs, API specs
├── scripts/            # Dev/ops helper scripts (seed, migrate, deploy)
├── .github/
│   └── workflows/      # GitHub Actions CI/CD pipelines
├── docker-compose.yml  # Local development stack
├── .env.example        # Environment variable template
├── .gitignore
├── LICENSE
└── README.md
```

---

## Roadmap

### Phase 1 — Foundation (current)
- [x] Repository scaffold and project structure
- [ ] Backend: FastAPI skeleton, auth (JWT), user/org models
- [ ] Frontend: Next.js setup, design system, auth pages
- [ ] Database: schema design, Alembic migrations
- [ ] CI: GitHub Actions lint + test pipeline

### Phase 2 — Core Features
- [ ] Resume upload, parsing, and structured storage
- [ ] Job description management
- [ ] Semantic vector embeddings (pgvector)
- [ ] JD–candidate match scoring API

### Phase 3 — Intelligence Layer
- [ ] Customizable scoring rule builder
- [ ] AI communication assessment (written + async video)
- [ ] Auto-generated screening questions

### Phase 4 — Automation & Analytics
- [ ] Candidate outreach automation
- [ ] Interview scheduling integration (Google Calendar / Calendly)
- [ ] Recruiter analytics dashboard

### Phase 5 — Scale & Enterprise
- [ ] Multi-tenant isolation
- [ ] RBAC and SSO (SAML / OIDC)
- [ ] Audit logs and compliance exports
- [ ] Kubernetes deployment manifests

---

## Getting Started

> Prerequisites: Docker Desktop, Git, Node.js 20+, Python 3.12+

```bash
# 1. Clone the repository
git clone https://github.com/your-org/TalentLens.git
cd TalentLens

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# 3. Start the full stack
docker compose up --build

# Services will be available at:
#   Frontend  → http://localhost:3000
#   Backend   → http://localhost:8000
#   API Docs  → http://localhost:8000/docs
#   AI Svc    → http://localhost:8001
```

> Detailed setup guides for each service are in [docs/](docs/).

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
