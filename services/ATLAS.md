# services/

Business-logic layer. Services orchestrate component calls into meaningful
user-facing actions and return domain values (not `Locator` objects).

**Rules:**
- One class per domain area (search, cart, account, …).
- Services receive `page: Page` at construction.
- Return primitives or dataclasses — never Playwright locators.
- Never import a service from another service; share via the test fixture.

| Module | Responsibility |
|---|---|
| *(add as features grow)* | |
