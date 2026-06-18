# Contributing Guide

> ⚠️ GHOST is a **private, proprietary research tool**. External contributions are only accepted from explicitly authorized collaborators. This guide is for internal reference.

---

## Development Setup

```bash
git clone https://github.com/abneeshsingh21/ghost-agent.git
cd ghost-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in GROQ_API_KEY in .env
python ghost.py --debug
```

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `master` | Stable production release |
| `dev` | Active development integration |
| `feature/<name>` | Individual feature development |
| `hotfix/<name>` | Critical bug fixes |

## Commit Format

Use conventional commit messages:

```
feat(arsenal): add binary entropy scoring to synthesize_zeroday()
fix(osint): SemanticLootClassifier missing from module
refactor(governance): simplify MVD path scoring formula
docs(readme): update slash command reference table
```

## Code Standards

- All new engines must follow the `__init__(self, memory_manager, ethics_engine, bridge)` constructor pattern
- Every new plan builder must return a dict with `type`, `tier`, and `phases` keys
- All `phases` entries must have `phase`, `name`, `description`, and `commands` keys
- Never use mutable default arguments in class constructors (use `None` + `or []`)
- All file writes during operation must be wrapped in Shadow Protocol checks

## Testing

Before committing, always verify syntax across all backend modules:

```bash
python -m compileall backend
python -c "from backend.server import create_app; app, sio = create_app(); print('BOOT OK')"
```
