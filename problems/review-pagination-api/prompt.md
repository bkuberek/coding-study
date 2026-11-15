# Review: Pagination API

## Context

An online store's public REST API is written in TypeScript with Express and Postgres (`pg`). `GET /v1/orders` returns the caller's most recent 500 orders; business customers with thousands of orders have asked to see all of them, so this pull request adds pagination.

Facts about the codebase that are not visible in the diff:

- The iOS and Android apps call `GET /v1/orders` and expect a JSON array. About 30% of active users run app versions older than six months, which cannot be forced to update. Partners also call the API directly.
- Every endpoint reports errors as `{"error": {"code": "...", "message": "..."}}` through `sendError(res, status, code, message)`; clients branch on `error.code`.
- `GET /v1/invoices` already paginates with `?limit=` and `?cursor=` and returns `{"items": [...], "next_cursor": "..."}`.
- Other routes validate query parameters with zod schemas from `src/http/validation.ts`.
- `orders` has 400 million rows and an index on `(customer_id, created_at)`. The largest business customers have about 2 million orders each, and new orders arrive continuously, often in bulk imports that share one `created_at`.
- Support staff use a separate internal tool that calls admin endpoints with a support role.

## Pull request

**Paginate GET /v1/orders**

> Adds `page` and `pageSize` query parameters (default 20, max 100) and returns the total so clients can render page numbers. Updated the snapshot test for the new response.

## Task

Review the change as you would a teammate's pull request, in about 30 minutes. For each issue, give its location, its severity (blocker, major, minor or nit), what goes wrong and the change you would ask for. Pay attention to the API contract as well as the code. End with your overall verdict.
