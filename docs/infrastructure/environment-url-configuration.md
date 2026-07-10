# Environment-Based Public URL Configuration

How TalentLens generates the URL inside an assessment invitation email, and
how to point the whole stack (backend CORS + frontend API calls + email
links) at a different environment — local, LAN, staging, or production —
by editing environment variables only. No file in this repo hardcodes
`localhost` or an IP address as the value actually used at runtime; every
place below reads a setting that defaults to `localhost` for a frictionless
local checkout, and every one of those defaults is overridable via `.env`.

## 1. Where the assessment link is actually built

One line, one place:

```python
# backend/app/services/assessment_invitation.py
def _build_assessment_url(self, token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL}/assessment/start/{token}"
```

`settings.FRONTEND_BASE_URL` comes from `app/core/config.py`:

```python
FRONTEND_BASE_URL: str = "http://localhost:3000"
```

That default only applies if the `FRONTEND_BASE_URL` environment variable is
unset — Pydantic Settings reads the real environment first. There is exactly
one call site (`AssessmentInvitationService._send_one`, which builds the
"Begin Assessment" link that goes into the invitation email via
`EmailService.send_assessment_invitation`) and exactly one setting that
feeds it. Changing environments never means touching this file.

### The other half: CORS

The frontend calls the backend from whatever origin it's actually served on
(`http://localhost:3000` locally, `http://192.168.1.25:3000` on your LAN,
`https://staging.talentlens.ai` in staging). The backend must allow that
origin, via `ALLOWED_ORIGINS` (`app/core/config.py`, also env-driven, also
defaulting to localhost). `FRONTEND_BASE_URL` and `ALLOWED_ORIGINS` are two
different settings serving two different purposes — get both right:

| Setting | Used for | Read by |
|---|---|---|
| `FRONTEND_BASE_URL` | The link text inside invitation emails | Backend only |
| `ALLOWED_ORIGINS` | Which origins may call the API (CORS) | Backend only |
| `NEXT_PUBLIC_API_URL` | Where the browser sends API requests | Frontend only |

### The two `.env` files — don't mix them up

- **Root `.env`** (next to `docker-compose.yml`) — read by `docker compose`,
  passed into the **backend** container's real environment, from which
  Pydantic Settings reads `FRONTEND_BASE_URL` / `ALLOWED_ORIGINS` / `SMTP_*`.
  Copy from `.env.example`.
- **`frontend/.env.local`** — read directly by Next.js for the **frontend**
  dev server (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_URL`). Copy from
  `frontend/.env.example`. The frontend is not containerized yet
  (`docker-compose.yml` lists it under "Pending services"), so this file is
  separate from the root one — editing the root `.env` does nothing for the
  frontend, and vice versa.

Moving between environments means editing both files' URLs to match; no code
in either app needs to change.

## 2. Local Development

Everything defaults to this — an empty/absent `.env` already behaves this
way. To be explicit, root `.env`:

```dotenv
FRONTEND_BASE_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002
```

`frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

Run:

```bash
docker compose up -d          # backend + postgres + redis + ai-service + worker
cd frontend && npm run dev    # frontend, localhost:3000 only
```

## 3. LAN / Wi-Fi Testing

For testing on a phone/tablet/another laptop on the same network — e.g. to
click a real invitation link from a phone, or to have a candidate test the
assessment flow without deploying anywhere.

**Find your LAN IP first** (see §6), then root `.env`:

```dotenv
FRONTEND_BASE_URL=http://192.168.1.25:3000
ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.25:3000
```

`frontend/.env.local` — this is the one people forget. `NEXT_PUBLIC_API_URL`
is compiled into the browser bundle, so it must be an address *other
devices* can reach — `localhost` would resolve to the phone itself, not your
machine:

```dotenv
NEXT_PUBLIC_API_URL=http://192.168.1.25:8000
NEXT_PUBLIC_APP_URL=http://192.168.1.25:3000
```

Recreate the backend so it picks up the new `.env` (a plain `restart` does
**not** re-read compose env changes):

```bash
docker compose up -d backend
```

Run the frontend bound to all interfaces, not just `localhost`:

```bash
cd frontend
npm run dev:lan          # next dev --turbopack -H 0.0.0.0 — added for this
# or equivalently:
npm run dev -- -H 0.0.0.0
```

(Vite projects would use `npm run dev -- --host`; this repo is Next.js, so
it's `-H 0.0.0.0`. `dev:lan` in `package.json` is just that command with a
name, so nobody has to remember the flag.)

Now `http://192.168.1.25:3000` works from any device on the same network,
and any invitation sent while `FRONTEND_BASE_URL` is set this way will
contain a link that phone/tablet can actually open.

## 4. Staging

Root `.env` (or however your staging host injects environment variables —
same variable names either way):

```dotenv
FRONTEND_BASE_URL=https://staging.talentlens.ai
ALLOWED_ORIGINS=https://staging.talentlens.ai
```

Frontend build-time environment (`frontend/.env.production` if staging
builds from that file, or your CI/CD's injected env — same names):

```dotenv
NEXT_PUBLIC_API_URL=https://api-staging.talentlens.ai
NEXT_PUBLIC_APP_URL=https://staging.talentlens.ai
```

## 5. Production

```dotenv
FRONTEND_BASE_URL=https://talentlens.ai
ALLOWED_ORIGINS=https://talentlens.ai
```

```dotenv
NEXT_PUBLIC_API_URL=https://api.talentlens.ai
NEXT_PUBLIC_APP_URL=https://talentlens.ai
```

Also set real `SMTP_*` values (see `.env.example`) — production must send
through a real provider, not the local/dev SMTP defaults. No other setting
in this document changes for production; `docker-compose.yml` itself is
development tooling and is not part of what ships to production (per this
sprint's instruction, it was not touched beyond adding the `${VAR:-default}`
passthroughs already needed for LAN/staging testing).

## 6. How to find your local IP

**Windows:**
```powershell
ipconfig
# Look for "IPv4 Address" under your active adapter (Wi-Fi or Ethernet),
# e.g. 192.168.1.25
```

**macOS:**
```bash
ipconfig getifaddr en0   # Wi-Fi on most Macs; try en1 if en0 is empty
```

**Linux:**
```bash
hostname -I | awk '{print $1}'
# or: ip addr show | grep "inet " | grep -v 127.0.0.1
```

The address must start with `192.168.`, `10.`, or `172.16.`–`172.31.` (a
private LAN range) — if it doesn't, you're not looking at your Wi-Fi/Ethernet
adapter's address.

## 7. Firewall requirements

For LAN testing, other devices need inbound access to two ports on your
machine: **3000** (frontend) and **8000** (backend API).

**Windows Firewall** — the first time `next dev`/Docker Desktop binds a
port, Windows normally prompts "Windows Defender Firewall has blocked some
features of this app" — click **Allow access**, and make sure the **Private
networks** checkbox is ticked (not Public). If you don't get the prompt (or
dismissed it before), add rules manually:

```powershell
New-NetFirewallRule -DisplayName "TalentLens Frontend (3000)" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "TalentLens Backend (8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
```

**macOS**: System Settings → Network → Firewall — either turn it off for
local testing, or allow incoming connections for `node` when prompted.

**Router-level**: both devices must be on the same Wi-Fi network/SSID —
guest networks and "AP/client isolation" settings on some routers block
device-to-device traffic even on the same SSID.

## 8. Common troubleshooting steps

| Symptom | Cause | Fix |
|---|---|---|
| Invitation email link points to the wrong host | `FRONTEND_BASE_URL` wasn't updated, or the backend container wasn't recreated after editing `.env` | Set `FRONTEND_BASE_URL` in root `.env`, then `docker compose up -d backend` (not `restart`) |
| Browser console: CORS error calling the API | The frontend's actual origin isn't in `ALLOWED_ORIGINS` | Add it to `ALLOWED_ORIGINS` in root `.env`, recreate the backend container |
| Other device loads the frontend but every API call fails/hangs | `NEXT_PUBLIC_API_URL` is still `localhost` — that resolves to the *other device*, not your machine | Set it to your LAN IP in `frontend/.env.local`, restart `npm run dev:lan` |
| Other device can't even load the frontend page | Frontend bound to `localhost` only, or firewall blocking | Use `npm run dev:lan` (binds `0.0.0.0`); check §7 |
| Works on your machine's browser, not on phone/other laptop | Same as above, plus: confirm both devices are on the same network and not on a guest/isolated Wi-Fi | Re-check §6/§7 |
| Editing `.env` seems to have no effect | Backend was `restart`ed instead of recreated, or you edited `frontend/.env.local` when the value lives in root `.env` (or vice versa) | Re-read §1's "two `.env` files" note; use `docker compose up -d backend` |
| `docker compose config` shows the old value | Compose only re-reads `.env` when you run a compose command — a shell left open from before your edit won't reflect it until re-run | Run `docker compose config` again after saving `.env` |

## Confirmation

No source file hardcodes `localhost` or an IP address as the value actually
used to build an assessment link or an allowed CORS origin — every one of
those is a `Settings` field (or `NEXT_PUBLIC_*` env var) with a
`localhost`-for-convenience *default*, fully overridden by environment
variables. Moving this app from local → LAN → staging → production is
strictly a matter of changing the values in §2–§5 above; no file in
`backend/app/` or `frontend/src/` needs to change.
