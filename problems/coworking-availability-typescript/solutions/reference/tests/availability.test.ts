import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { waitBeforeRetry } from "../src/vendors/roomVendor.ts";
import { resetVendors, setScenario } from "./vendorScenario.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;

afterEach(resetVendors);

async function roomsOn(date: string): Promise<{ slots: unknown[]; unavailable: string[] }> {
  const response = await fetch(`${app}/availability?date=${date}`);
  assert.equal(response.status, 200);
  return ((await response.json()) as { rooms: { slots: unknown[]; unavailable: string[] } }).rooms;
}

test("a 429 waits as long as it says, and a 5xx a little", () => {
  assert.equal(waitBeforeRetry(429, "2"), 2000);
  assert.equal(waitBeforeRetry(429, null), 200);
  assert.equal(waitBeforeRetry(500, null), 200);
});

test("another 4xx is not worth asking again", () => {
  assert.equal(waitBeforeRetry(403, null), null);
});

test("both vendors answer in one list", async () => {
  const rooms = await roomsOn("2027-03-08");

  assert.equal(rooms.slots.length, 5);
  assert.deepEqual(rooms.unavailable, []);
});

test("a vendor that is down costs only its own slots", async () => {
  await setScenario("room-vendor", "outage");

  const rooms = await roomsOn("2027-03-08");

  assert.equal(rooms.slots.length, 3);
  assert.deepEqual(rooms.unavailable, ["room-vendor"]);
});

test("both vendors down still answers the desks", async () => {
  await setScenario("room-vendor", "outage");
  await setScenario("annex-vendor", "maintenance");

  assert.deepEqual(await roomsOn("2027-03-08"), {
    slots: [],
    unavailable: ["annex-vendor", "room-vendor"],
  });
});
