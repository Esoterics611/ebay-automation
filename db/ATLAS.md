# db/

JSON store for structural configuration and static test data.

| File | Purpose |
|---|---|
| `environments.json` | Base URL and timeout per `PROFILE` (`dev` / `staging` / `prod`) |

**Never put secrets here.** Secrets belong in `.env` (gitignored).
