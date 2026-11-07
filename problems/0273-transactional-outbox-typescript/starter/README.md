# Transactional Outbox

The back office of a tool rental desk. Staff move rentals through their states, and each move leaves an audit row. Other services will want to hear about these moves, and that is where the trouble starts.

The code is laid out as ports and adapters: `src/core/` holds the rules and says what it needs from the world, and `src/adapters/` provides it.

## Contract

- `src/desk.ts` exports the class `RentalDesk` by name, and `new RentalDesk()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours to change, move or add to.

## Layout

| Path | Holds |
|------|-------|
| `src/desk.ts` | `RentalDesk`: wires the core to the adapters, and answers the outside world |
| `src/core/rental.ts` | The rental, and the table of moves it can make |
| `src/core/rentalService.ts` | `RentalService`: what happens when someone acts on a rental |
| `src/core/ports.ts` | The interfaces the core asks for, and the two failures it knows about |
| `src/adapters/memoryDatabase.ts` | `MemoryDatabase`, with the tables as plain data, and the table classes over it |
| `src/adapters/fakeBroker.ts` | `FakeBroker`, the message broker other services read from |
| `src/json.ts` | `canonicalJson`: JSON with object keys in sorted order |
| `tests/plumbing.test.ts` | Tests of the pieces above |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

## There is no real database or broker

No dependencies are allowed, so the database is a few maps in memory and the broker is a list. Both can fail on cue: `failNextWrite(table)` makes the next write to that table throw, whichever order your code writes in.

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

From the workspace, `cstudy test transactional-outbox-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here: the project uses the workspace's Node and TypeScript.

## Grading

Your tests are feedback only. `cstudy submit transactional-outbox-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.
