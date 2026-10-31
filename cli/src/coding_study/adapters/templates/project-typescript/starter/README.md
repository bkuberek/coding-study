# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- `src/main.ts` exports the class `{{class_name}}` by name. Keep the file and the export where they are: `cstudy submit` imports `{{class_name}}` from `src/main.ts`.
- `new {{class_name}}()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours: add modules under `src/`, and your own tests under `tests/`.

## Running the tests

From this folder:

```sh
node --test
```

From the workspace, `cstudy test {{slug}}` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test {{slug}} --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Keep `package.json` free of dependencies: the project uses the workspace's Node and TypeScript, and nothing is installed here.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
