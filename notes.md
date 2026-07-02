# TalentLens — Complete Project Notes

> This document explains **everything** about how TalentLens is built: what technologies we use, why we chose them, how each piece works, and how secure the system is. It's written so that someone brand new to coding can follow along, but it also has exact file names and code so an engineer can use it as a reference.

---

## Table of Contents

1. [What Is TalentLens?](#1-what-is-talentlens)
2. [The Big Picture: How the Pieces Fit Together](#2-the-big-picture-how-the-pieces-fit-together)
3. [Technology Stack — What & Why](#3-technology-stack--what--why)
4. [The Backend (FastAPI) — How It Works](#4-the-backend-fastapi--how-it-works)
5. [Authentication — Step by Step](#5-authentication--step-by-step)
6. [Middleware — The "Security Guards" of Every Request](#6-middleware--the-security-guards-of-every-request)
7. [How Secure Is TalentLens?](#7-how-secure-is-talentlens)
8. [Background Jobs — Redis & Celery](#8-background-jobs--redis--celery)
9. [The AI Microservice — How Resume/JD Parsing Actually Works](#9-the-ai-microservice--how-resumejd-parsing-actually-works)
10. [The Database — PostgreSQL + pgvector](#10-the-database--postgresql--pgvector)
11. [The Frontend (Next.js) — How It Works](#11-the-frontend-nextjs--how-it-works)
12. [Frontend Authentication Flow (Client Side)](#12-frontend-authentication-flow-client-side)
13. [Docker & Docker Compose — Why Containers?](#13-docker--docker-compose--why-containers)
14. [CI/CD Pipeline — GitHub Actions](#14-cicd-pipeline--github-actions)
15. [Glossary (Plain-English Definitions)](#15-glossary-plain-english-definitions)

---

## 1. What Is TalentLens?

TalentLens is a web application that helps recruiters hire people faster and more fairly. A recruiter:

1. Creates a **campaign** (e.g., "Senior Backend Engineer — Q3 2026").
2. Pastes in or uploads a **job description**.
3. Uploads a batch of **resumes** (PDF, Word, or a ZIP of many).
4. The system automatically **reads and understands** every resume and job description using AI.
5. The system **scores and ranks** every candidate against the job description, with an explanation of *why* each one scored the way it did.

Think of it like a very smart assistant that reads 200 resumes overnight and hands the recruiter a ranked shortlist in the morning, with notes on each candidate's strengths and weaknesses.

The project is split into **three separate applications** that talk to each other over the network:

| App | Language | Job |
|---|---|---|
| **frontend** | TypeScript (Next.js/React) | The website recruiters click around in |
| **backend** | Python (FastAPI) | The "brain" — accounts, campaigns, database, security, business rules |
| **ai-services** | Python (FastAPI) | A specialist that only talks to AI models (Claude/GPT) to read resumes and job descriptions |

---

## 2. The Big Picture: How the Pieces Fit Together

```
                     ┌───────────────────────────┐
                     │      Recruiter's Browser    │
                     └──────────────┬─────────────┘
                                    │ HTTPS
                     ┌──────────────▼─────────────┐
                     │   Next.js Frontend (3000)   │   <- the website
                     └──────────────┬─────────────┘
                                    │ REST API calls (JSON)
                     ┌──────────────▼─────────────┐
                     │   FastAPI Backend (8000)    │   <- the brain
                     │ auth · campaigns · resumes  │
                     │ scoring · RBAC · uploads    │
                     └──┬────────────────┬─────────┘
                        │                │
          ┌─────────────▼───┐   ┌────────▼─────────────┐
          │ PostgreSQL 16 +  │   │ AI Microservice (8001)│  <- the AI specialist
          │ pgvector         │   │ resume/JD parsing,    │
          │ (all real data)  │   │ embeddings (Claude/   │
          └─────────────────┘   │ GPT/local model)      │
                        ▲        └───────────────────────┘
                        │
          ┌─────────────┴───┐
          │  Redis 7         │   <- message queue + cache
          │ (Celery broker)  │
          └──┬───────────────┘
             │
     ┌───────▼────────┐
     │ Celery Worker    │   <- does slow work in the background
     │ (parses files,   │
     │  calls AI svc)   │
     └─────────────────┘
```

**Why split into three apps instead of one big one?**

- **Separation of concerns.** The frontend only knows how to *display* things. The backend only knows business rules (who's allowed to do what, how data is stored). The AI service only knows how to talk to language models. Each piece can be understood, tested, and changed independently — like separating a restaurant into "front of house," "kitchen," and "specialty pastry chef" instead of having one person do everything.
- **Independent scaling.** AI calls (to Claude/GPT) are slow and expensive. If 50 people upload resumes at once, we can run more copies of just the AI service or just the Celery workers, without needing more copies of the whole app.
- **Safety.** The AI service never touches the database directly and never sees user passwords. If it were ever compromised, the blast radius is limited to "it can call an LLM," not "it can read every user's data."

---

## 3. Technology Stack — What & Why

| Technology | What it actually is (plain English) | Why we picked it here |
|---|---|---|
| **Python 3.12** | A general-purpose programming language, popular for backend and AI work | Huge ecosystem for both web servers (FastAPI) and AI/ML libraries |
| **FastAPI** | A Python framework for building APIs (a server that answers requests like "give me campaign #5") | Very fast, automatically generates interactive API docs (`/docs`), and works natively with `async` code (can handle many requests at once without blocking) |
| **SQLAlchemy** | A library that lets Python code talk to a database using Python objects instead of raw SQL | Makes database code safer (protects against SQL injection automatically) and easier to read/maintain |
| **Alembic** | A tool that tracks changes to the database structure over time ("migrations") | Every time we add a new table or column, we save a small script describing the change, so any developer/environment can replay history and end up with an identical database |
| **PostgreSQL 16** | A relational (table-based) database — the permanent home for all real data | Rock-solid, open source, and supports the `pgvector` extension we need for AI search |
| **pgvector** | A PostgreSQL extension that lets the database store and compare "embeddings" (see below) | Lets us do semantic search — "find resumes similar in *meaning* to this job description" — directly inside the database, instead of a separate specialized search engine |
| **Redis** | An extremely fast in-memory key-value store | Used as (a) the message queue between the backend and Celery workers, and (b) general-purpose caching |
| **Celery** | A Python library for running tasks in the background, outside the main web request | Parsing a resume with AI can take several seconds — we don't want the user's browser to sit there waiting. Celery lets the API respond instantly ("upload received!") while the real work happens behind the scenes |
| **JWT (JSON Web Tokens)** | A signed, tamper-proof piece of text that proves "this is user X, logged in until time Y" | Standard, stateless way to do authentication over HTTP APIs — the server doesn't need to store session data for every logged-in user |
| **bcrypt** | An algorithm for turning a password into a scrambled, one-way hash | Industry standard for password storage — even if the database leaks, attackers can't easily reverse bcrypt hashes back into real passwords |
| **Next.js 15 (App Router)** | A React framework for building the website, with built-in routing, server rendering, and build tooling | Gives us fast page loads, file-based routing, and a mature ecosystem, without us having to hand-roll a bundler/router |
| **React 19** | A JavaScript library for building interactive UIs out of reusable components | Industry standard; huge hiring pool and library ecosystem |
| **TypeScript** | JavaScript with optional type-checking bolted on | Catches whole categories of bugs (wrong data shape, typos in property names) *before* the code ever runs |
| **TanStack React Query** | A library that manages "server state" (data that lives on the backend) in the frontend, including caching and re-fetching | Avoids writing manual loading/error/caching logic by hand for every API call |
| **Zod** | A schema-validation library for TypeScript/JavaScript | Used to validate form input (e.g., password length) on the frontend, mirroring the backend's own rules |
| **shadcn/ui + Tailwind CSS** | A set of pre-built, accessible UI components + a utility-first CSS styling system | Lets us build a consistent, good-looking UI quickly without designing every button and input from scratch |
| **Docker / Docker Compose** | A way to package software (and everything it needs to run) into a portable "container" | Guarantees "it works on my machine" also means it works on every other machine — see [Section 13](#13-docker--docker-compose--why-containers) |
| **GitHub Actions** | A CI/CD (Continuous Integration) tool built into GitHub | Automatically lints, type-checks, and tests every change *before* it's allowed to merge — see [Section 14](#14-cicd-pipeline--github-actions) |
| **Anthropic Claude / OpenAI GPT** | Large Language Models (LLMs) — AI that can read text and produce structured answers | Used to turn messy, free-form resume/job-description text into clean structured data (name, skills, experience, etc.) |
| **sentence-transformers** | An open-source library that turns text into "embeddings" (see glossary) without calling an external paid API | Used for the backend's own semantic matching so we're not paying per-API-call for every comparison, and so ranking still works even if an external AI provider is down |

---

## 4. The Backend (FastAPI) — How It Works

The backend lives in `backend/app/`. It's organized in layers — each layer has one job, and only talks to the layer directly below it. This is a very common, beginner-friendly pattern:

```
Request comes in
      │
      ▼
┌─────────────┐   "Is this a valid request? Is the user logged in?
│  api/        │    Do they have the right role?"
└─────┬───────┘
      ▼
┌─────────────┐   "What's the business rule here? e.g. 'only an
│  services/   │    ORG_ADMIN can delete a campaign'"
└─────┬───────┘
      ▼
┌─────────────┐   "Fetch/save rows in the database"
│ repositories/│
└─────┬───────┘
      ▼
┌─────────────┐
│  models/     │   The actual table definitions (SQLAlchemy)
└─────────────┘
```

Folder tour (`backend/app/`):

- **`api/`** — The HTTP layer. `api/v1/endpoints/*.py` defines the actual URLs (e.g. `POST /api/v1/auth/login`). `api/deps.py` defines reusable "dependencies" like *"get me the currently logged-in user"* or *"require this user to be an admin."*
- **`core/`** — Cross-cutting configuration: `config.py` (all environment variables/settings), `security.py` (password hashing + JWT), `logging.py` (structured logs), `redis.py` (Redis connection).
- **`db/`** — Database connection/session setup (`session.py`).
- **`models/`** — SQLAlchemy ORM models — one Python class per database table (`User`, `Organization`, `Campaign`, `ResumeFile`, `Candidate`, `ParsedResume`, `JobDescription`, `OrganizationInvitation`, `ScoringRule`).
- **`repositories/`** — All the actual database queries, one file per entity, so business logic never writes raw SQL/queries directly.
- **`schemas/`** — Pydantic models describing what a valid request/response looks like (e.g., "a login request must have an email and a password").
- **`services/`** — The actual business logic (e.g., `auth.py` handles login/register/refresh; `matching_service.py` computes how well a resume fits a job).
- **`storage/`** — An abstraction for saving uploaded files, currently backed by local disk, but swappable for S3 later without changing any calling code.
- **`workers/`** — Celery background tasks (resume parsing, job-description parsing, embedding generation).
- **`main.py`** — The actual FastAPI app: creates the app, registers middleware, wires up startup/shutdown, and mounts all the routers.

### Key API endpoints (grouped by feature)

| Feature | Endpoints |
|---|---|
| Auth | `POST /api/v1/auth/register`, `/login`, `/refresh` |
| Organizations | `POST /api/v1/organizations/bootstrap` (create a brand-new company account), `POST /{org_id}/invitations` (invite a teammate) |
| Users | `GET /api/v1/users/me` |
| Campaigns | `POST/GET/PATCH/DELETE /api/v1/campaigns` |
| Resumes | `POST .../resumes/upload`, `GET .../resumes/{id}` |
| Job Descriptions | `POST .../job-descriptions` (paste text), `POST .../job-descriptions/upload` (file) |
| Rankings | `GET /api/v1/campaigns/{id}/rankings` — the ranked candidate list with scores and explanations |
| Scoring Rules | CRUD endpoints so an org (or a specific campaign) can customize how heavily skills vs. experience vs. education count |

---

## 5. Authentication — Step by Step

Authentication answers two questions on every request: **"Who are you?"** (authentication) and **"Are you allowed to do this?"** (authorization).

### 5.1 There are no public sign-ups — only invitations

`POST /api/v1/organizations/bootstrap` lets someone create a brand-new organization (this creates the very first `ORG_ADMIN` account). After that, every new teammate must be **invited**:

1. An `ORG_ADMIN` calls `POST /organizations/{org_id}/invitations` with the new teammate's email.
2. The backend generates a random invitation token, stores only a **hash** of it in the database (`organization_invitations.token_hash`), and returns the raw token once (e.g., emailed to the invitee).
3. The invitee visits `/invite?token=...` on the frontend and sets a password.
4. `POST /api/v1/auth/register` checks: does a *pending*, *non-expired* invitation exist whose hash matches, and does the email match? Only then is the account created.

This prevents random strangers from registering accounts and self-assigning roles.

### 5.2 Passwords are never stored in plain text

`backend/app/core/security.py` uses **bcrypt**:

```python
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
```

- `bcrypt.gensalt()` generates a random "salt" so that two users with the same password get *different* stored hashes (defeats precomputed "rainbow table" attacks).
- bcrypt is deliberately slow, which makes brute-forcing a stolen database much more expensive for an attacker.
- Login always calls `verify_password()` and compares result — even the error path returns a generic `"Invalid email or password"` message instead of revealing whether the *email* or the *password* was wrong (prevents attackers from fishing for which emails have accounts).

### 5.3 Logging in produces two tokens

`POST /api/v1/auth/login` checks the password, then issues:

- An **access token** — short-lived (default 30 minutes), sent with every API request to prove identity.
- A **refresh token** — long-lived (default 30 days), used only to get a new access token when the old one expires.

```python
def create_access_token(user_id, role, org_id) -> str:
    payload = {"sub": user_id, "role": role, "org_id": org_id, "type": "access",
               "iat": now, "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
```

Both tokens are **JWTs**: a signed blob of JSON. The signature (made with a server-only secret, `JWT_SECRET`) means the token cannot be edited by a user without the server noticing — e.g., a user can't change `"role": "RECRUITER"` to `"role": "SUPER_ADMIN"` inside their own token, because the signature would no longer match.

**Why two tokens instead of one?** If the short-lived access token leaks (e.g., logged accidentally, intercepted), the damage window is small — it expires in 30 minutes. The refresh token is used far less often, and the backend can detect misuse of it (see next point).

### 5.4 Refresh tokens are rotated (can't be replayed)

Every time a refresh token is used (login or `/auth/refresh`), the backend:

1. Generates a **new** refresh token.
2. Hashes it (SHA-256) and overwrites `users.refresh_token_hash`.
3. Returns the new refresh token to the client.

The *old* refresh token immediately stops working, because its hash no longer matches what's stored. This is called **refresh token rotation** — it limits the damage if a refresh token is ever stolen, because it can only be used once before the legitimate user's next natural refresh invalidates it.

### 5.5 Every protected request is checked centrally

`backend/app/api/deps.py`:

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)

async def get_current_user(db, token) -> User:
    payload = decode_token(token)          # verifies the JWT signature + expiry
    if payload.get("type") != "access":
        raise credentials_exception
    user = await UserRepository(db).get_by_id(uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]
```

Any endpoint that needs "who is logged in" just declares `user: CurrentUser` as a parameter — FastAPI runs this check automatically before the endpoint's own code ever runs. There's no way to accidentally forget to check the token on a route that includes this dependency.

### 5.6 Role-Based Access Control (RBAC)

Four roles exist: `SUPER_ADMIN`, `ORG_ADMIN`, `RECRUITER`, `CANDIDATE`. A small reusable class enforces role checks:

```python
class RequireRoles:
    def __init__(self, *roles: UserRole):
        self.roles = set(roles)

    def __call__(self, user: CurrentUser) -> User:
        if user.role not in self.roles:
            raise HTTPException(status_code=403, detail="You do not have permission.")
        return user
```

Used like: `WriteUser = Annotated[User, Depends(RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN))]`. On top of role checks, business logic also checks **organization ownership** — e.g. a recruiter from Org A can never fetch a campaign belonging to Org B, even if they guess the right ID, because the service layer always filters by `org_id` matching the current user.

---

## 6. Middleware — The "Security Guards" of Every Request

"Middleware" is code that runs *around* every request — before it reaches your actual endpoint logic, and/or after the response is generated. Think of it as a security checkpoint every visitor passes through before reaching the actual office.

**Registered in `backend/app/main.py`:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- **CORS (Cross-Origin Resource Sharing) middleware** — Web browsers block a webpage from calling an API on a *different* domain unless that API explicitly says "yes, I allow requests from this origin." `ALLOWED_ORIGINS` is a configurable list (defaults to `http://localhost:3000`, i.e., our own frontend) — this stops some random other website from silently making authenticated requests to our API using a visitor's browser.

**Other request-level protections that aren't classic "middleware" but serve the same purpose:**

- **`get_current_user` dependency** (Section 5.5) acts like an authentication checkpoint on every protected route.
- **`RequireRoles` dependency** acts like an authorization checkpoint.
- **Structured JSON logging** (`core/logging.py`) — every request/response and error is logged as a JSON line, with SQL and access logs de-noised, so production logs can be aggregated and searched by monitoring tools.
- **Lifespan hooks** (`main.py`) — code that runs once at startup (connect to Redis, preload the local embedding model so the *first* real request isn't slow) and once at shutdown (cleanly close DB/Redis connections).
- **`/health` endpoint** — pings the database (`SELECT 1`) and Redis (`PING`) and reports `ok`/`degraded`, so orchestration tools (Docker, Kubernetes) know if the app is actually healthy, not just "running."

On the frontend, there's a similar concept — see [Section 12.1](#121-two-layer-route-protection) for `frontend/src/middleware.ts`, which is Next.js's own "run before every page request" mechanism (a route guard, not a security boundary — see that section for why).

---

## 7. How Secure Is TalentLens?

Below is an honest checklist of what's implemented today, mapped to *why* it matters.

| Concern | What we do | Why it matters |
|---|---|---|
| **Password storage** | bcrypt with per-password random salt | Even a full database leak doesn't hand attackers plaintext passwords |
| **Session tokens** | Short-lived signed JWT access tokens (30 min) + rotating refresh tokens (30 days) | Limits the value of a stolen token; rotation detects/limits refresh-token replay |
| **Token tampering** | JWTs are cryptographically signed with a server-only secret | A user cannot edit their own role/ID inside the token without the server rejecting it |
| **SQL Injection** | All database access goes through SQLAlchemy's ORM (parameterized queries), never raw string-built SQL | Untrusted input (like a search term) can never be interpreted as SQL code |
| **Broken access control** | Every protected endpoint requires a valid access token (`get_current_user`) and, where relevant, a specific role (`RequireRoles`) *and* an organization-ownership check in the service layer | Prevents both "not logged in" and "logged in but not allowed" access, and stops cross-tenant data leaks (Org A reading Org B's data) |
| **Sign-up abuse** | No open self-registration — accounts are only created via a hashed, single-use, expiring invitation token | Stops random strangers from creating accounts or self-granting admin access |
| **Timing/enumeration attacks on login** | Login returns the same generic error for "wrong email" and "wrong password" | Prevents attackers from discovering which emails have accounts |
| **Open redirect** (frontend) | `sanitizeRedirect()` rejects any redirect target that isn't a same-site path starting with `/` (and blocks `//evil.com`-style tricks) | Stops attackers from crafting a login link that redirects a victim to a phishing site after login |
| **Zip-bomb / oversized uploads** | Configurable caps: `ZIP_MAX_ENTRIES`, `ZIP_MAX_UNCOMPRESSED_TOTAL_MB`, `ZIP_MAX_COMPRESSION_RATIO`, `MAX_UPLOAD_SIZE_MB` | Stops a small malicious ZIP file from exhausting server disk/memory when uncompressed |
| **Data retention / accidental deletion** | Soft deletion (`is_deleted` + `deleted_at` flags) on campaigns and resume files rather than hard `DELETE` | Data can be recovered/audited; deletion is reversible instead of instantly destructive |
| **Secrets management** | All secrets (`JWT_SECRET`, DB password, API keys) come from environment variables / `.env` files, never hardcoded in source | `.env` is git-ignored; different secrets per environment (dev/staging/prod) |
| **Access token storage (frontend)** | Kept in memory only (a JS variable) — never written to `localStorage` or disk | Reduces the attack surface for token theft via XSS, since an in-memory value isn't readable by a separately-injected script the same way persisted storage can be scraped over time |
| **CORS** | Explicit `ALLOWED_ORIGINS` allow-list, not `*` | Stops arbitrary third-party sites from making authenticated cross-origin calls using a logged-in user's browser |
| **CI enforcement** | Every pull request runs linting + type checks + the full test suite before it can merge (see [Section 14](#14-cicd-pipeline--github-actions)) | Catches whole classes of bugs (including some security-relevant ones, like type mismatches) before they reach production |

### Known gaps (things not yet implemented, for transparency)

- **No rate limiting yet** on login/register — brute-force protection (e.g., lockout after N failed attempts) isn't in place.
- **No HTTPS/TLS termination configured in this repo** — that's expected to be handled by the deployment environment (a reverse proxy/load balancer), not the application itself.
- **No CI/CD deployment step yet** — the pipeline currently only lints/tests; it doesn't build+push Docker images or deploy anywhere automatically.
- **Frontend has no service worker yet** — the PWA manifest exists, but offline caching isn't fully wired up.

---

## 8. Background Jobs — Redis & Celery

**The problem:** Parsing a resume involves extracting text, calling an AI model (which can take several seconds), and generating an embedding vector. If we made the user's browser *wait* for all of that inside a single HTTP request, uploads would feel painfully slow, and uploading 50 resumes at once could time out entirely.

**The solution — a task queue:**

1. The API endpoint (`POST .../resumes/upload`) saves the file and creates a database row with status `UPLOADED`, then immediately responds "upload received" to the browser.
2. It also drops a small message onto a **Redis** queue: *"please parse resume #1234."*
3. A separate, always-running process — the **Celery worker** — is constantly watching that queue. It picks up the message, does the actual slow work, and updates the database when done.

```python
def _enqueue_parse(resume_file_id: str) -> None:
    from app.workers.resume_parser import parse_resume as _task
    _task.delay(resume_file_id)   # "delay" = don't run this now, queue it for a worker
```

**Why Redis specifically?** Redis is extremely fast (it keeps data in memory) and is purpose-built for exactly this kind of "many small messages, needs to be processed quickly" workload. It's also reused as a general cache for the app, so we don't need a second piece of infrastructure just for caching.

**What the worker actually does** (`backend/app/workers/resume_parser.py`):

1. Fetch the resume file → mark it `PROCESSING`.
2. Extract raw text from the PDF/DOCX/ZIP (using `pypdf` / `python-docx`).
3. Send that raw text to the **AI microservice** (`POST {AI_SERVICE_URL}/parse-resume`).
4. Save the structured result (name, skills, experience, etc.) → mark `PARSED`.
5. Kick off a *second* background task to generate a semantic embedding for the resume (for matching later).

**Retry behavior:** if the AI service or network has a temporary failure (5xx error), the task retries automatically with increasing delays (30s → 60s → 120s). If it's a *permanent* failure (e.g., the file itself is unreadable — a 4xx error), it doesn't retry — it just marks the file `FAILED` with an error message, since retrying wouldn't help.

The same pattern is used for job descriptions (`job_description_parser.py`) and for embedding generation (`embedding_worker.py`).

---

## 9. The AI Microservice — How Resume/JD Parsing Actually Works

This lives in `ai-services/` and is a *second, independent* FastAPI app (port 8001). It knows nothing about users, campaigns, or the database — its only job is: "given some text, ask an AI model to make sense of it, and hand back clean structured JSON."

### 9.1 Endpoints

- `POST /parse-resume` — turns raw resume text into structured data: candidate info, skills, work experience, education, projects, certifications, plus a confidence score (0.0–1.0).
- `POST /parse-job-description` — turns raw job-description text into structured data: title, experience range, required/preferred skills, employment type, responsibilities, etc.
- `POST /generate-embedding` — turns any text into a numeric vector (an "embedding") used for semantic similarity search.

### 9.2 How parsing actually happens

1. A prompt template file is loaded from `ai-services/app/prompts/parse_resume_v1.txt` — this is carefully written English text that instructs the LLM exactly what JSON shape to return, and how to handle missing data (e.g., "use an empty string, never `null`").
2. That prompt (with the resume text filled in) is sent to whichever LLM provider is configured (`LLM_PROVIDER=anthropic` or `openai`).
3. The LLM's raw text response is parsed as JSON. If it fails (e.g., the model added extra commentary or wrapped it in a code fence), the code cleans that up automatically.
4. If parsing still fails, a **second, more explicit "fallback" prompt** is tried (`parse_resume_v1_fallback.txt`) before giving up and returning an error.

### 9.3 Why two swappable AI providers (Anthropic + OpenAI)?

Both `AnthropicLLMClient` and `OpenAILLMClient` implement the same simple interface (`async complete(prompt) -> str`), and a factory function picks whichever one is configured via environment variable. This means:

- If one provider has an outage or a price change, we can switch providers with a config change, not a code rewrite.
- Local development/testing can use whichever provider is cheaper or already has an API key configured.

### 9.4 Embeddings — what they are and why we need them

An **embedding** is a list of numbers (a vector) that represents the *meaning* of a piece of text. Two pieces of text with similar meaning end up with similar vectors — so "5 years of Python backend experience" and "half a decade building Python APIs" end up mathematically close together, even though they don't share many exact words.

TalentLens generates embeddings for both resumes and job descriptions, stores them in PostgreSQL (via the `pgvector` extension), and then uses vector math (cosine similarity) to answer: *"out of all these candidates, which resumes are semantically closest to this job description?"* This is one ingredient (alongside skills/experience/education matching) in the overall candidate ranking score.

Two embedding sources exist:
- The **backend** has its own local embedding model (`sentence-transformers`, default `BAAI/bge-large-en-v1.5`) that runs entirely on the server — no external API call, no per-call cost, and it still works if an external AI provider is down.
- The **ai-service** can also generate embeddings via OpenAI's embedding API, as an alternative/fallback provider.

---

## 10. The Database — PostgreSQL + pgvector

**Why a relational database?** Recruitment data is naturally tabular and relationship-heavy: an organization *has many* users, a campaign *belongs to* an organization, a resume file *belongs to* a campaign. PostgreSQL is excellent at enforcing and querying these relationships reliably.

**Why pgvector specifically, instead of a separate vector database?** It lets us store embeddings as just another column on the existing `parsed_resumes` / `job_descriptions` tables, and run similarity search with regular SQL — one less moving part to run, monitor, and keep in sync with the "real" data.

**Main tables:**

| Table | Purpose |
|---|---|
| `users` | Accounts — email, hashed password, role, which org they belong to |
| `organizations` | A tenant/company using TalentLens |
| `organization_invitations` | Pending invites (hashed token, expiry, status) |
| `campaigns` | A hiring campaign, scoped to one organization |
| `resume_files` | An uploaded resume file and its parsing status |
| `candidates` | A person, extracted from a parsed resume |
| `parsed_resumes` | The structured JSON + embedding vector for a resume |
| `job_descriptions` | Raw text + structured JSON + embedding vector for a job posting |
| `scoring_rules` | Configurable weights (skills vs. experience vs. education, etc.) per org or per campaign |

**Migrations (Alembic):** every schema change (new table, new column) is captured as a small versioned Python script in `backend/alembic/versions/`. Running `alembic upgrade head` replays all of these in order, so any fresh database (a new developer's laptop, a CI test run, a production server) ends up with an identical structure. This is much safer than manually running SQL by hand and hoping every environment matches.

---

## 11. The Frontend (Next.js) — How It Works

The frontend lives in `frontend/src/` and uses **Next.js 15's App Router** — meaning the folder structure under `src/app/` *is* the site's URL structure.

### 11.1 Route groups

- **`(auth)/`** — Public pages: `/login`, `/register` (redirects to an invite-based flow), `/invite`, `/forgot-password`. Wrapped in a simple centered `AuthLayout`.
- **`(dashboard)/`** — Everything behind login: `/dashboard`, `/campaigns`, `/candidates`, `/assessments`, `/analytics`, `/settings`, `/profile`. Wrapped in `ProtectedShell`, which enforces that the visitor is actually logged in before rendering anything.
- **Special pages**: `error.tsx`/`global-error.tsx` (error boundaries so one broken page doesn't crash the whole app), `not-found.tsx` (404), `forbidden/` (403), `offline/` (shown when there's no network — this app is set up as an installable PWA via `manifest.ts`), `loading.tsx` (a spinner shown automatically while a page's data is loading).

### 11.2 State management — two different tools for two different jobs

- **TanStack React Query** manages *server state* — data that actually lives in the backend (campaigns, candidates, etc.). It automatically handles caching, background refetching, and loading/error states, so we don't hand-write that logic for every single API call.
- **React Context stores** (`frontend/src/store/*`) manage *client state* — things that only make sense in the browser itself, like "is the sidebar collapsed" or "who is currently logged in." This is a simpler alternative to something like Redux, appropriate for an app this size.

### 11.3 Forms & validation

Forms use **React Hook Form** (manages form state/submission) plus **Zod** (declares validation rules like "password must be 8–128 characters"). The same rules that the backend enforces are mirrored here, so users get instant feedback in the browser instead of waiting for a rejected API call — but the backend *always* re-validates independently, since client-side validation can be bypassed.

### 11.4 UI Components

**shadcn/ui** (built on Radix UI primitives) + **Tailwind CSS** give us accessible, consistent, pre-built components (buttons, dialogs, dropdowns) that we can restyle quickly, instead of building every UI primitive from scratch.

---

## 12. Frontend Authentication Flow (Client Side)

### 12.1 Two-layer route protection

There are **two separate checks**, because the frontend cannot fully verify a JWT on its own (that would require it holding the signing secret, which must never leave the backend):

1. **Edge middleware** (`frontend/src/middleware.ts`) — runs before *any* page loads. It only checks for the *presence* of a lightweight, non-sensitive cookie (`tl_session`) that the client sets after a successful login. If a protected page is visited without that cookie, it redirects to `/login`. This is a fast, coarse check — it's a UX convenience (avoid flashing a protected page then redirecting), not a real security boundary.
2. **Client-side `ProtectedShell`** — the *authoritative* check. On load, it actually calls the backend (`GET /users/me` using the real token) to confirm the session is genuinely valid before rendering any protected content. Even if someone forged the `tl_session` cookie, they'd get nothing back from the real API call, because they don't have a valid access token.

### 12.2 Where tokens are stored, and why

| Token | Where it lives | Why |
|---|---|---|
| Access token | In-memory only (a JavaScript variable) | Never touches disk — reduces what a malicious script could steal if it ran on the page, and disappears automatically on tab close/refresh |
| Refresh token | `localStorage` if "Remember me" was checked, otherwise `sessionStorage` | `sessionStorage` clears when the tab closes (safer default); `localStorage` persists across restarts, only when the user explicitly opts in |
| Session marker (`tl_session`) | A plain (non-`httpOnly`) cookie | Only used by the edge middleware for the fast/coarse check above — it carries no secret information itself |

### 12.3 Automatic token refresh

`frontend/src/services/interceptors.ts` wraps every outgoing API call:

1. Before sending, it attaches `Authorization: Bearer <access_token>`.
2. If a response comes back `401 Unauthorized` (token expired), it automatically calls `/auth/refresh` with the stored refresh token, gets a new access token, and **retries the original request** — so the user never sees an error, they just experience a tiny delay.
3. If several requests fail at once, they're queued so only *one* refresh call is made (not one per failed request), then all queued requests are replayed once the new token arrives.
4. If the refresh itself fails (refresh token expired/invalid too), the session is fully cleared and the user is redirected to `/login?session_expired=1`.

---

## 13. Docker & Docker Compose — Why Containers?

**The problem containers solve:** "It works on my machine" is a classic developer headache — one laptop has Python 3.11, another has 3.13, one has Postgres installed locally, another doesn't, etc. A **Docker container** packages an application together with the *exact* versions of everything it needs (system libraries, Python packages, config) into one portable unit that runs identically anywhere Docker is installed.

**`docker-compose.yml`** describes our entire local stack as a set of these containers that can all be started with one command (`docker compose up`):

| Service | Image / build | Purpose |
|---|---|---|
| `backend` | built from `backend/Dockerfile` | The FastAPI app, port 8000, hot-reloads on code changes in dev |
| `postgres` | `pgvector/pgvector:pg16` | PostgreSQL 16 with the pgvector extension already installed |
| `redis` | `redis:7-alpine` | The message broker/cache, with persistence enabled (`--appendonly yes`) |
| `ai-service` | built from `ai-services/Dockerfile` | The AI microservice, port 8001 |
| `worker` | same image as `backend`, different command | Runs `celery ... worker` — the background job processor |

Each Dockerfile is a recipe: start from a small base image (`python:3.12-slim`), install just the required system packages, install Python dependencies, copy the app code, and define how to start it. Health checks (`curl -f http://localhost:8000/health`, `pg_isready`, `redis-cli ping`) let Docker know when a service is actually ready to receive traffic, not just "started" — `backend` and `worker` wait for Postgres and Redis to be healthy before starting, avoiding a race where the app tries to connect to a database that isn't ready yet.

A `docker/postgres/init.sql` script runs once, the very first time the Postgres container starts, to enable the three PostgreSQL extensions we depend on: `uuid-ossp` (generate unique IDs), `vector` (pgvector), and `pg_trgm` (fuzzy text search).

---

## 14. CI/CD Pipeline — GitHub Actions

**CI (Continuous Integration)** means: every time someone proposes a code change, an automated robot checks it *before* a human has to. Our pipeline lives in `.github/workflows/ci.yml` and runs on every push/PR to `main` or `develop`. It has **three independent jobs that run in parallel**, one per app:

1. **Backend — Lint & Test**
   - Spins up real `postgres` and `redis` service containers for the job.
   - Installs dependencies, then runs:
     - `ruff check .` — linting (catches style issues and some bugs automatically).
     - `mypy .` — static type checking (catches type mismatches before runtime).
     - `alembic upgrade head` — actually applies all database migrations to prove they work end-to-end.
     - `pytest` — runs the full backend test suite (unit + integration tests) against a real database.

2. **Frontend — Lint & Test**
   - `npm ci` (clean, reproducible install from the lockfile).
   - `npm run lint` (ESLint).
   - `npm run type-check` (TypeScript compiler, no output, just checking).
   - `npm test` (Jest).

3. **AI Services — Lint & Test**
   - Same idea as backend, minus the database steps (this service doesn't touch a database) — `ruff check .` then `pytest`.

**Why this matters:** a broken build, a type error, or a failing test is caught automatically on every pull request, *before* it can be merged into the shared branch — so bugs are caught at the cheapest possible point (before deployment), and every contributor gets the same consistent bar applied to their code. Currently, the pipeline stops at "lint + test" — it does not yet build/push Docker images or deploy anywhere automatically; that's a natural next step once the app is ready to go live.

---

## 15. Glossary (Plain-English Definitions)

- **API (Application Programming Interface):** A defined way for two programs to talk to each other — in our case, the frontend sends structured requests (like "give me campaign #5") to the backend and gets structured responses back.
- **ORM (Object-Relational Mapper):** A library (SQLAlchemy) that lets you work with database rows as regular Python objects instead of writing raw SQL by hand.
- **Migration:** A small, versioned script describing one change to the database's structure (e.g., "add a `phone_number` column to `candidates`").
- **JWT (JSON Web Token):** A compact, digitally signed piece of text used to prove identity without the server needing to remember every logged-in session.
- **Hashing:** A one-way transformation of data (like a password) into a scrambled fixed-length string that can't practically be reversed back into the original.
- **RBAC (Role-Based Access Control):** Restricting what someone can do based on their assigned role (e.g., `RECRUITER` vs `ORG_ADMIN`).
- **Middleware:** Code that runs automatically before/after every request, regardless of which specific endpoint is being called.
- **CORS (Cross-Origin Resource Sharing):** A browser security rule that blocks a webpage from calling an API on a different domain unless that API explicitly allows it.
- **Embedding:** A list of numbers representing the *meaning* of a piece of text, so similarity between texts can be measured mathematically.
- **Celery task / worker:** A unit of work (like "parse this resume") that gets queued up and processed by a separate background process, instead of blocking the user's request.
- **Container (Docker):** A packaged, portable unit that bundles an application with everything it needs to run, so it behaves identically on any machine.
- **CI/CD (Continuous Integration / Continuous Deployment):** Automated pipelines that test (and eventually deploy) code changes automatically, instead of relying on a human to remember every step.
- **LLM (Large Language Model):** An AI model (like Claude or GPT) trained to understand and generate human language, used here to turn messy resume/job-description text into clean structured data.

---

*This document reflects the state of the codebase as of the current branch (`test-development`). As features are added (rate limiting, deployment automation, SSO, etc.), keep this file up to date rather than letting it drift.*
