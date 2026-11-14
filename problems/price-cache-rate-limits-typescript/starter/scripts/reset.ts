// `commands.reset`, run by cstudy with your app stopped. `apply` empties the store before a case
// that starts fresh, so its prices and limits start from nothing; `prepare` has nothing to keep.
// You should not need to change it.

import { createClient } from "redis";

if (process.env.CSTUDY_RESET_PHASE === "apply") {
  const store = createClient({ url: process.env.REDIS_URL });
  await store.connect();
  try {
    await store.flushAll();
  } finally {
    await store.close();
  }
}
