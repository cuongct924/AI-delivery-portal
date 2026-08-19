# Python OOP Code Rules (Team Standards)

## 0. Toolchain
*   **Formatter/Linter:** `ruff` — config in the repo-root `pyproject.toml` (`[tool.ruff]`).
*   **Type Checker:** `pyright` — config in `pyproject.toml` (`[tool.pyright]`).
*   **Tests:** `pytest` — config in `pyproject.toml` (`[tool.pytest.ini_options]`).
*   **Run everything:** `make check` (= `make lint typecheck test`). Install deps first with `make install`.

## 1. Naming Conventions
*   **Class / Type Alias:** `PascalCase` (Nouns).
*   **Method / Function:** `snake_case` (Verbs).
*   **Attribute / Module / Package:** `snake_case`.
*   **Private Member:** Prefix with `_` (e.g., `_password`).
*   **Constant:** `UPPER_CASE`.

## 2. Mandatory Typing (Python 3.12+)
*   **No Legacy Typing:** Never import `List`, `Dict`, `Union`, or `Optional` from `typing`.
*   **100% Annotation:** Fully type hint all public functions, methods, and constructors (`-> None`).
*   **Restrict `Any`:** Do not use `Any` unless explicitly justified with a comment (e.g., `# TODO: Legacy API`).

## 3. Standard Class Structure (Top-to-Bottom Order)
1.  Class attributes (with `ClassVar`).
2.  Constructor (`__init__`).
3.  Magic methods (`__str__`, `__repr__`, `__eq__`, etc.).
4.  Properties (`@property`).
5.  Public methods.
6.  Class methods (`@classmethod`).
7.  Static methods (`@staticmethod`).
8.  Private methods (`_method`).

## 4. Code Organization & Formatting
*   **Import Order (PEP 8):**
    1. Standard library.
    2. Third-party packages.
    3. Internal modules.
*   **Docstrings:** Use **Google Style** for all complex classes/functions (clearly specify Args, Returns, Raises).

## 5. CI/CD Merge Checklist
- [ ] Targets Python 3.12+.
- [ ] Passes `pyright` (`make typecheck`) with zero errors.
- [ ] Passes `ruff check` and `ruff format --check` (`make lint`).
- [ ] Passes `pytest` (`make test`).
- [ ] Uses `Self` for methods returning the instance.
- [ ] Constants are wrapped in `Final`.
- [ ] Complex dictionaries are typed via `TypedDict`.
- [ ] Uses the `type` statement for all type aliases.