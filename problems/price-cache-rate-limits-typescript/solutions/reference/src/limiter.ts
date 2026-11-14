// Each client's limit: at most LIMIT requests in any WINDOW_MS. The store keeps a sorted set per
// client of the requests it let through, scored by when they came. The script runs in the store
// whole, so requests that arrive together are counted one after another, never side by side.

import { randomUUID } from "node:crypto";

import { store } from "./store.ts";

const LIMIT = 5;
const WINDOW_MS = 1000;

// KEYS[1] the client's set; ARGV the limit, the window and a member unique to this request.
// Answers 0 when the request goes through, and otherwise the milliseconds until one would.
const SLIDING_WINDOW = `
local now = redis.call('TIME')
local now_ms = now[1] * 1000 + math.floor(now[2] / 1000)
local window_ms = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms - window_ms)
if redis.call('ZCARD', KEYS[1]) < tonumber(ARGV[1]) then
  redis.call('ZADD', KEYS[1], now_ms, ARGV[3])
  redis.call('PEXPIRE', KEYS[1], window_ms)
  return 0
end
local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
return tonumber(oldest[2]) + window_ms - now_ms
`;

// 0 when the client's request may go through; otherwise how many milliseconds it must wait.
export async function waitBeforeNext(client: string): Promise<number> {
  const reply = await store.eval(SLIDING_WINDOW, {
    keys: [`limit:${client}`],
    arguments: [String(LIMIT), String(WINDOW_MS), randomUUID()],
  });
  return Number(reply);
}
