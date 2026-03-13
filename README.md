# Rugby Director

Rugby Director is a full-stack rugby union management simulator MVP-plus. You take control of a fictional professional club, set your matchday squad and tactics, manage contracts and transfers, advance through a 10-team double round-robin league, and review text-commentary match simulations with persistent save data. The current build also supports multi-season careers with guided offseason progression, season history, retirements, and academy intake.

## Tech Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router, Zustand, Recharts
- Backend: FastAPI, SQLModel, SQLite, Pydantic
- Tooling: `uv` for Python workflow, `npm` for frontend workflow

## Folder Structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── db
│   │   ├── models
│   │   ├── schemas
│   │   ├── seed
│   │   ├── services
│   │   └── simulation
│   └── tests
├── frontend
│   ├── src
│   │   ├── components
│   │   ├── layout
│   │   ├── lib
│   │   ├── pages
│   │   ├── store
│   │   └── styles
│   └── package.json
├── Makefile
└── pyproject.toml
```

## MVP Features

- New career flow with club selection from a fictional 10-team top division
- Persistent single-save career stored in SQLite
- Fictional squads with 30-40 players per club and rugby-specific positions/attributes
- Matchday XV, bench, captain, and goal-kicker management
- Tactical controls for attacking style, kicking, defense, ruck commitment, set piece intent, goal choice, and training focus
- Rugby-specific text/commentary simulation covering territory, possession, set piece, discipline, injuries, cards, fatigue, and bench impact
- Weekly league progression, fixtures, results, and table updates
- Guided offseason flow with season review, contract resolution, youth intake, and season rollover
- Multi-season persistence with season history and refreshed budgets/objectives
- Aging, annual development/regression, retirements, and simple academy promotions
- Dashboard, squad, tactics, fixtures, league table, transfers, club overview, match centre, and inbox pages
- Lightweight transfer and contract renewal systems
- Backend tests for simulation, lineup validation, progression, and key API flows

## Local Setup

### Prerequisites

- Python 3.12+
- Node.js 24+
- `uv`
- `npm`

### Install Backend Dependencies

```bash
uv sync --group dev
```

### Install Frontend Dependencies

```bash
npm --prefix frontend install
```

## Running The App

### Start the backend

```bash
make dev-backend
```

The API runs at `http://localhost:8000`.

### Start the frontend

```bash
make dev-frontend
```

The web app runs at `http://localhost:5173`.

## Seed Data

The game can generate a full save through the in-app new game flow. If you want an immediate demo save in the database, run:

```bash
make seed
```

This creates a playable active save with seeded clubs, squads, tactics, fixtures, listings, and inbox items.

To reset the local database and recreate the demo save:

```bash
make reset-db
```

## Tests

Run the backend test suite with:

```bash
make test
```

## API Highlights

- `POST /api/saves`
- `GET /api/save/current`
- `GET /api/dashboard`
- `GET /api/career/status`
- `GET /api/squad`
- `PUT /api/tactics`
- `PUT /api/selection`
- `GET /api/fixtures`
- `POST /api/advance-week`
- `GET /api/season/review`
- `GET /api/offseason/status`
- `POST /api/offseason/advance`
- `GET /api/youth-intake`
- `POST /api/youth-intake/{prospect_id}/promote`
- `GET /api/history/seasons`
- `GET /api/table`
- `GET /api/transfers`
- `POST /api/transfers/{listing_id}/bid`
- `POST /api/contracts/{player_id}/renew`
- `GET /api/inbox`
- `GET /api/matches/{fixture_id}`

## Architecture Notes

- The backend keeps game logic out of the route layer by splitting responsibilities across services, seed generation, and a dedicated simulation engine.
- The simulation engine is deterministic per fixture seed and organized around rugby concepts: set piece, territory, discipline, fatigue, tactical fit, and bench impact.
- Career progression is now season-aware: completed years are preserved, offseason actions are state-driven, and roster continuity carries into regenerated seasons.
- The frontend uses a routed app shell with lazy-loaded pages, a small Zustand store for save state and progression transitions, and page-level API loading for clarity.

## Known Limitations

- The game supports one active save at a time.
- Only one competition is implemented.
- Transfer negotiations are intentionally lightweight and immediate.
- The simulation is commentary-based, not live or step-driven.
- Youth development is intentionally simple: annual intake plus promotion decisions, not a full academy subsystem.
- Backend tests are included; frontend automated tests are not yet added.

## Future Improvements

- Multi-season progression with aging, retirements, and youth intake
- Smarter AI squad rotation and transfer behavior
- Richer contract negotiation and player promises
- Additional competitions and cup scheduling
- Expanded analytics, scouting, and finance systems
