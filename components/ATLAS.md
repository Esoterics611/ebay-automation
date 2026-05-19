# components/

Page-Object layer. Each subdirectory owns one UI region of the eBay site.

**Rules:**
- Components interact with Playwright only (`page.*`, `locator.*`).
- No business logic — that lives in `services/`.
- No assertions — that lives in `tests/`.
- Selector strings are class-level constants: `_SEL_<ELEMENT> = "css=…"`.
- All classes extend `BaseComponent` (components/base.py).

| Package | UI region |
|---|---|
| `header/` | Global nav, logo, sign-in link |
| `search/` | Search bar, search button, autocomplete |
| `listing/` | Item title, price, condition, add-to-cart button |
