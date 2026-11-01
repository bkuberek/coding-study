/**
 * Loaded before the unit tests (`--import`): a stylesheet a module imports is an empty module, as
 * it has no effect outside the page, so the tests can import a view's pure parts with it.
 */
import { registerHooks } from "node:module";

registerHooks({
  load(url, context, nextLoad) {
    if (url.endsWith(".css")) return { format: "module", source: "", shortCircuit: true };
    return nextLoad(url, context);
  },
});
