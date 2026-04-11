# AGENTS.md — IKNL Infobot (BrabantHack_26)

## Project structure

- `teams/team5/frontend/` — Next.js 14 (App Router) + Tailwind CSS 3
- `teams/team5/backend/` — FastAPI + LiteLLM + ChromaDB connectors
- `teams/team5/.env` — shared env config (loaded by backend via `config.py`)

## Critical rules

### CSS / Tailwind

- **Never add raw CSS to `globals.css`** beyond the three `@tailwind` directives. No `:root` variables, no `body {}` rules, no `@layer utilities` overrides. These break Tailwind's class-based rendering.
- **Never add inline `<style>` tags or CSS-in-JS** in components. Use Tailwind utility classes only.
- If Tailwind classes stop rendering, the fix is almost always: delete `.next/` and restart the dev server (`rm -rf .next && pnpm dev`). Do NOT add CSS workarounds.
- The Tailwind content paths in `tailwind.config.ts` must include `./app/**`, `./components/**`, and `./lib/**`. If you add a new directory with TSX files, add it to the content array.

### Backend / LLM

- All LLM calls go through LiteLLM in `intake.py`. The model name and API keys come from `config.py` (which reads `teams/team5/.env`).
- `config.py` loads `.env` from both `../` and `./` relative to the backend dir. The `teams/team5/.env` file is the source of truth.
- When changing LLM providers, update `LLM_PROVIDER` and `LLM_MODEL` in `teams/team5/.env`. The `main.py` startup code exports the relevant API keys to `os.environ` so LiteLLM can find them.
- Bedrock Mantle tokens are temporary (AWS STS). If you see `Missing Authentication Token`, the token has expired — switch to `LLM_PROVIDER=openrouter` in `.env`.

### Error handling

- Backend uses centralized `logging.basicConfig()` in `main.py`. All modules use `logging.getLogger(__name__)`. Log level is controlled by `LOG_LEVEL` env var (default: INFO).
- Frontend uses `lib/logger.ts` for centralized logging. All catch blocks must log the actual error before showing a user-facing message. Never use bare `catch {}` — always `catch (err)` and log it.
- Backend endpoints must catch exceptions and return structured JSON errors, not let FastAPI return raw 500s.

### Environment

- Backend port: 8001 (configured in .env as `BACKEND_PORT`)
- Frontend port: 3002 (configured in .env as `FRONTEND_PORT`)
- Frontend `NEXT_PUBLIC_API_URL` must point to the backend (production: `https://iknl.datameesters.nl`)
