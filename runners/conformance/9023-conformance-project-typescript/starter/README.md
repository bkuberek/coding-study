# Inventory

A two-file project for the runner conformance suite: `src/inventory.ts` exports the entry class `Inventory`, and `src/labels.ts` formats labels. `package.json` maps `#store/*` to `src/*`, so a file can import a sibling through the package as well as by relative path.

`cstudy` loads `Inventory` from `src/inventory.ts`. Run the tests with `node --test`.
