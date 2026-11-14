# Sabong — Specification Set

**Sabong** is a competitive, skill-based **3D web sabong fighting game**. Players control a manok in a circular ruweda and fight a bot (R1), then other players (R3). It is built with **React + TypeScript + Vite + Babylon.js** on **Supabase**, following the **ICT Information System Blueprint 2026**, with Supabase replacing the Laravel backend.

This repository is **spec-driven**: the documents in `/docs` are the source of truth. Code implements the specs; when behavior must change, the spec changes first (or in the same PR).

---

## Document map (organized by the Blueprint's Waterfall SDLC)

| Phase | Document | What it answers |
|---|---|---|
| 1. Requirements | [Product Requirements](docs/01-requirements/product-requirements.md) | What we build and why: scope, roles, releases, FR/NFR with acceptance criteria, open questions |
| 1. Requirements | [Game Design (Combat Rules)](docs/01-requirements/game-design.md) | How the fight works: frame data, meters, win conditions, bot, breeds, economy |
| 2. Design | [Architecture & Tech Stack](docs/02-design/architecture.md) | Blueprint → Supabase mapping, ADRs, repo and folder structure, runtime flows, environments |
| 2. Design | [Database Design](docs/02-design/database-design.md) | ERD, tables, enums, RLS, transactional SQL functions, storage, migrations |
| 2. Design | [API Design](docs/02-design/api-design.md) | Edge Function endpoints, envelope, validation, auth, CORS, rate limits, Axios client |
| 2. Design | [Game Engine Design](docs/02-design/game-engine-design.md) | Deterministic simulation, replay verification, rendering, input, bot, assets |
| 2. Design | [UI/UX Design](docs/02-design/ui-ux-design.md) | Routes, screens, atomic components, state management, forms, accessibility |
| 3. Development | [Conventions & Standards](docs/03-development/conventions.md) | Naming, coding standards, lint/hooks, Git workflow, env vars |
| 3. Development | [Implementation Tasks (R1)](docs/03-development/tasks.md) | Ordered task list with done-criteria and requirement traceability |
| 4. Testing | [Test Plan](docs/04-testing/test-plan.md) | Test levels, coverage rules, key cases, NFR tests, Alpha/Beta/UAT |
| 5–6. Deployment & Maintenance | [Deployment, DevOps & Security](docs/05-deployment/deployment.md) | Infrastructure, quick start, CI/CD (GitHub Actions + Vercel), `vercel.json`, secrets, security checklist, maintenance |
| — | [CLAUDE.md](CLAUDE.md) | Rules for AI coding agents working in this repo |

## Spec-driven workflow

```
Requirement (FR/NFR/AC id)  →  Design section  →  Task (T-xxx)  →  Code + tests  →  PR referencing ids
        ↑                                                                                    │
        └──────────── spec updated first when behavior must change ◄─────────────────────────┘
```

1. Every feature starts as a requirement with an ID and acceptance criteria.
2. The design documents say *how*; tasks say *in what order* and *when it is done*.
3. Every PR lists the task and requirement IDs it implements; tests reference AC/test-case IDs.
4. A requirement is complete only when its acceptance criteria pass in UAT.

## Sign-off (Blueprint SDLC outputs)

| Phase | Output | Status | Date | Signed by |
|---|---|---|---|---|
| Requirements | Product Requirements + Game Design approved; open questions resolved | ☐ Pending | | Carlo |
| Design | Figma screens, ERD, architecture approved (**Certificate of Design Acceptance**) | ☐ Pending | | |
| Development | R1 tasks done, CI green | ☐ Pending | | |
| Testing | Alpha, Beta, UAT passed | ☐ Pending | | |
| Deployment | Staging verified, launched (**Certificate of Acceptance**) | ☐ Pending | | |

## Key decisions at a glance

- **Supabase replaces Laravel:** Postgres + RLS (authorization), Auth (identity, TOTP MFA), Edge Functions with Hono (service layer, Blueprint envelope), Storage (files), Realtime (future PvP).
- **The client never writes game state.** Coins, results and records change only in Edge Functions through transactional SQL functions.
- **A deterministic fixed-point simulation** is shared by the browser and the server, so the server verifies every bot match by replaying it.
- **Hosting:** frontend on **Vercel** (preview URL per PR, staging and production branches); backend on Supabase Cloud.
- **No real money, ever.** Coins are soft currency with no monetary value.

> **Team:** Carlo (project owner, game client), Cliff (simulation, app screens), Patrick (platform). Ramil reviews and approves every PR. Ownership and the parallel plan: [tasks.md](docs/03-development/tasks.md#team--ownership).

> This is a personal hobby project. It follows the ICT Information System Blueprint 2026 voluntarily as a house standard; deviations (Supabase instead of Laravel, Vercel instead of IIS) are recorded in the architecture document.
