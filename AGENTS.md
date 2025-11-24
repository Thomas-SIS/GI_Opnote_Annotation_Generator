````markdown
# AGENTS.md

Guidelines for human and AI “agents” working on this web application.  
The goals: **small, composable modules**, **clear structure**, and **up-to-date documentation**.

---

## 1. Backend (Python) Agent Guidelines

### 1.1 General Principles

- Prefer **many small modules** over a few large ones.
- Each file should do **one thing well**.
- Write code that is **easy to delete or replace**, not “clever.”

### 1.2 File Size Limits

- **Hard rule:** No Python source file may exceed **100 lines of code**  
  (this does **not** include comments, docstrings, or blank lines).
- If a file approaches this limit:
  - Extract logic into a **helper module** or **utility function**.
  - Move reusable logic into a shared `utils/` directory where appropriate.

### 1.3 Classes & Functions

* Prefer **small functions** that handle a single responsibility.
* Any function that:

  * is longer than ~20–30 LOC, or
  * has multiple “and then” steps
    should be considered for splitting into smaller helper functions.

### 1.4 Docstrings (Mandatory)

All **public classes, methods, and functions** in the backend **must have docstrings**.

* Docstrings should state:

  * What the function/class does.
  * Meaning of parameters and return values.
  * Any important side effects or exceptions.

Use a consistent style (Google-style in this project):

```python
def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Args:
        password: The plaintext password.

    Returns:
        A salted, hashed representation suitable for storage.
    """
    ...
```

For classes:

```python
class UserService:
    """Business logic for user creation, retrieval, and updates."""

    def create_user(self, payload: CreateUserRequest) -> User:
        """Create a new user from the given payload.

        Args:
            payload: Validated request data for user creation.

        Returns:
            The created User instance.
        """
        ...
```

If you add a function/class without a docstring, **it is considered incomplete work**.

---

## 2. Frontend Agent Guidelines

### 2.1 Component-Based Architecture

* The frontend uses a **component-based architecture**.
* **Each component gets its own directory** containing:

  * one JavaScript file (`*.js`)
  * one HTML template file (`*.html`)
  * one CSS (or equivalent) style file (`*.css`)

**Example layout:**

```bash
frontend/
  components/
    header/
      header.js
      header.html
      header.css
    sidebar/
      sidebar.js
      sidebar.html
      sidebar.css
    user-card/
      user-card.js
      user-card.html
      user-card.css
  assets/
    images/
    fonts/
  utils/
    dom-helpers.js
    api-client.js
```

### 2.2 Component Design Rules

* Each component:

  * Handles a **single UI responsibility** (e.g., `user-card`, `nav-bar`).
  * Does its own DOM wiring and event handling.
  * Exposes a clear interface (props/config) where applicable.

* If a component’s JS grows too large:

  * Factor shared logic into `frontend/utils/` (e.g., `api-client.js`, `formatters.js`).
  * Or split into **smaller subcomponents**.

---

## 3. Documentation Agent Guidelines

### 3.1 Backend Documentation

* **Docstrings are required** for:

  * All public functions and methods.
  * All public classes.
  * Any non-trivial private helpers.

* When adding a new module:

  * Start the file with a **module-level docstring** describing its purpose.

Example:

```python
"""User-related business logic and orchestration.

This module contains services that implement user creation,
retrieval, and updates, separate from API routing concerns.
"""
```

### 3.2 Frontend Documentation

  * A brief **comment block** at the top of the JS file describing the component’s purpose

Example in `user-card/user-card.js`:

```js
/* UserCard component
Renders a single user's avatar, name, and key metadata.
Expected inputs: user object with id, name, email, and avatarUrl.
*/
function renderUserCard(user) {
  ...
}
```

* Any non-obvious logic (complex DOM manipulations, tricky state handling, etc.) must be explained with **inline comments**.

### 3.3 “Document as You Go” Rule

* Code and docs must be committed together.
* No PR should introduce:

  * Undocumented backend functions/classes, or
  * New frontend components without at least minimal description comments.

If you touch logic, **update or add documentation in the same change**.

---

## 4. Additional Conventions (Recommended)

### 4.1 Naming

* Backend:

  * Modules: `snake_case`
  * Classes: `PascalCase`
  * Functions/variables: `snake_case`
* Frontend:

  * Component directories: `kebab-case` (e.g., `user-card`).
  * JS functions/variables: `camelCase`.

### 4.2 Testing (If/When Added)

* Mirror the structure in `tests/`:

  * `tests/backend/...` for Python tests.
  * `tests/frontend/...` for JS/component tests.

---

By following these rules, agents keep this codebase **modular, readable, and well-documented**. Any new work should be checked against this document before being considered done.

```
```
