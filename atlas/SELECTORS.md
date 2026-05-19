# SELECTORS

Selector strategy for every component in this suite.

---

## Priority order

Always reach for the highest-priority locator that works:

1. **`page.get_by_role(role, name=...)`** — first choice. Survives DOM
   churn and is the closest analogue to how a user navigates the page.
2. **`page.get_by_label(...)`** — for form inputs with visible labels.
3. **`page.get_by_test_id(...)`** — when the site exposes a test id.
   eBay's public site rarely does; reserve for the few cases it appears.
4. **`page.get_by_text(...)`** — for static, copy-anchored elements
   (price labels, "Sponsored" badges).
5. **CSS selector** — fallback only when (1)–(4) cannot disambiguate or
   are too brittle for a given region of the page. Prefer stable IDs
   (`#srp-river-results`) and `data-*` attributes over structural CSS.
6. **XPath** — only when the spec explicitly requires positional
   traversal that CSS cannot express. Document the reason inline.

---

## Examples by component

| Component | Element | Preferred locator |
|---|---|---|
| HeaderComponent | Search input | `page.get_by_role("combobox", name="Search for anything")` |
| HeaderComponent | Search submit | `page.get_by_role("button", name="Search")` |
| HeaderComponent | Cart icon | `page.get_by_role("link", name=re.compile(r"^Cart"))` |
| SearchResultsComponent | Result card | `page.locator("ul.srp-results > li.s-item")` |
| SearchResultsComponent | Card title | `card.get_by_role("link").first` |
| SearchResultsComponent | Sponsored badge | `card.get_by_text("SPONSORED", exact=False)` |
| SearchResultsComponent | Next page | `page.get_by_role("link", name="Next page")` |
| ItemComponent | Title | `page.get_by_role("heading", level=1)` |
| ItemComponent | Price | `page.locator('[data-testid="x-price-primary"]')` (CSS fallback) |
| ItemComponent | Variant picker | `page.get_by_role("combobox", name=re.compile(r"select", re.I))` |
| ItemComponent | Add to cart | `page.get_by_role("button", name="Add to cart")` |
| CartComponent | Subtotal | `page.get_by_text(re.compile(r"^Subtotal"))` |
| CartComponent | Remove | `page.get_by_role("button", name="Remove")` |

---

## Anti-patterns

- `:nth-child(N)` — couples the test to result ordering, which eBay
  shuffles per visitor.
- Long XPath chains like `//div[3]/ul/li[2]/...` — break on any DOM
  edit.
- `assert "Add to cart" in page.content()` — use a locator assertion.
- Importing `time` and sleeping for the page to "settle" — always
  prefer `expect(locator).to_be_visible()` / `to_have_text(...)`.

---

## Selector constants

Components store selector strings as class-level constants prefixed
`_SEL_` so they are easy to grep and refactor:

```python
class SearchBarComponent(BaseComponent):
    _SEL_INPUT_NAME = "Search for anything"
    _SEL_SUBMIT_NAME = "Search"

    def search(self, query: str) -> None:
        self.page.get_by_role("combobox", name=self._SEL_INPUT_NAME).fill(query)
        self.page.get_by_role("button", name=self._SEL_SUBMIT_NAME).click()
```
