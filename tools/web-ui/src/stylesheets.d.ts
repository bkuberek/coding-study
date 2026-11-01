// esbuild bundles a stylesheet app.ts imports into app.css; one another module imports becomes a
// file of its own that the module links as it loads (scripts/build.ts).
declare module "*.css";
