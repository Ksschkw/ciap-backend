# CIAP Data Layer Alignment Note

This repository is using the `app/` package as the live backend runtime, while `DATA/` is the shared contract/package namespace that the backend is meant to stay aligned with.

## Current repo shape

- FastAPI entry point: `app/main.py`
- Settings and environment loading: `app/config.py`
- Async SQLAlchemy session management: `app/db/session.py`
- ORM models and repository implementations: `app/db/models/` and `app/db/repositories/`
- Alembic migrations: root `alembic/` with `alembic.ini`
- Seed data and bootstrapping: `seeds/`

## Practical rule

- Treat `DATA/` as the contract layer for shared shapes, enums, repository interfaces, and external client interfaces.
- Treat `app/` as the runtime implementation layer that consumes those contracts.
- When the two diverge, fix the contract and the implementation together instead of assuming the handover paths are already present.

## What to watch for

- The handover references a sync `DATA/core/database.py` flow, but this repo currently uses async engine/session wiring in `app/db/session.py`.
- The handover references `DATA/models/` and `DATA/schemas/` modules as populated packages, but in this workspace the `DATA/` tree is mostly a namespace shell and the active ORM code lives under `app/db/`.
- The handover dependency list is outdated relative to the live backend; only add a package when the code actually imports or needs it.
- The repo-specific documentation should therefore describe the live `app/` implementation first, then note how `DATA/` should mirror it.

## Working expectation

- Keep API contracts stable in `DATA/` where possible.
- Keep ORM, service, and endpoint code in `app/` consistent with those contracts.
- If strict parity with the handover dependency set is ever required, treat that as a separate migration project because it would also affect the database/session model, not just `pyproject.toml`.
- Update this note whenever the real runtime layout changes.