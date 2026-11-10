// The connection to the store: a Valkey server, which speaks Redis's protocol, so this is the usual
// Redis client. `REDIS_URL` comes from the sandbox's settings. Every route shares this one client.

import { createClient } from "redis";

export const store = createClient({ url: process.env.REDIS_URL });

// Without a listener, a lost connection is an unhandled `error` event, and that ends the process.
store.on("error", (error: unknown) => {
  console.error("store:", error);
});

await store.connect();
