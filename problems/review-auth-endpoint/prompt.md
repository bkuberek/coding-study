# Review: Login Endpoint

## Context

The accounts API is a Python 3.12 FastAPI service backed by Postgres through psycopg2 (DB-API placeholders are `%s`). Login currently lives in a legacy monolith that is being retired; this pull request moves it into the accounts API.

Facts about the codebase that are not visible in the diff:

- The `users` table was migrated from the monolith. It stores a per-user `salt` and `password_hash = sha256(salt + password)`. The security team has asked for a modern password hash in the new service.
- Application logs are shipped to a third-party log platform, kept for 90 days and readable by every engineer and the support team.
- The public login form was the target of a credential-stuffing attack last quarter.
- Internal services call the revoke endpoint with a shared key after a password reset.
- `tests/conftest.py` provides a `db` fixture and overrides `get_connection` so the app and the tests share one transaction.

## Pull request

**Move login to the accounts API**

> Ports `POST /login` from the monolith, keeping the same password hashing so existing users can log in. Sessions are random tokens stored in the `sessions` table and set as a cookie. Also adds the internal endpoint that revokes a user's sessions. Tests cover a successful login and a wrong password.

## Task

Review the change as you would a teammate's pull request, in about 30 minutes. For each issue, give its location, its severity (blocker, major, minor or nit), what goes wrong and the change you would ask for. Say which problems an attacker could exploit and how. End with your overall verdict.
