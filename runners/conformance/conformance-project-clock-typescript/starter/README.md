# Inbox

A TypeScript project for the runner conformance suite on the virtual clock: `src/inbox.ts` exports the entry class `Inbox`, whose waiting methods return a `Promise`.

`cstudy` loads `Inbox` from `src/inbox.ts` and grades each case on `node:test`'s mock timers, which `tests/virtual-clock.ts` drives. Run the tests with `node --test`; they import the same helper.
