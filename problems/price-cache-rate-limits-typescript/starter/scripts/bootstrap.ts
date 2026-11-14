// `commands.bootstrap`, run by cstudy once the store is up and before your app starts. A store
// holds no schema to migrate, so this only checks that it answers. You should not need to change it.

import { createClient } from "redis";

const store = createClient({ url: process.env.REDIS_URL });

await store.connect();
try {
  console.log(`the store answers ${await store.ping()}`);
} finally {
  await store.close();
}
