// The coworking space's API: what can be booked on a day.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { roomAvailability } from "./availability.ts";
import { isRealDay } from "./dates.ts";
import { DeskInventory } from "./desks.ts";
import { AnnexVendorClient } from "./vendors/annexVendor.ts";
import { RoomVendorClient } from "./vendors/roomVendor.ts";
import type { RoomSource } from "./vendors/roomSource.ts";

type Answer = { status: number; body: unknown };

const port = Number(process.env.PORT);
const desks = await DeskInventory.fromFile("data/desks.json");
const vendors: RoomSource[] = [
  new RoomVendorClient(String(process.env.ROOM_VENDOR_URL)),
  new AnnexVendorClient(String(process.env.ANNEX_VENDOR_URL)),
];

/** Why a request cannot be answered for this date; null when it can. */
function refusal(date: string): Answer | null {
  if (date === "") {
    return { status: 400, body: { error: "date is required" } };
  }
  if (!isRealDay(date)) {
    return { status: 400, body: { error: "date must be a real day, as YYYY-MM-DD" } };
  }
  if (desks.availableOn(date) === undefined) {
    return { status: 404, body: { error: "no desks on sale for that date" } };
  }
  return null;
}

async function desksOn(date: string): Promise<Answer> {
  return refusal(date) ?? { status: 200, body: { date, available: desks.availableOn(date) } };
}

async function availabilityOn(date: string): Promise<Answer> {
  const refused = refusal(date);
  if (refused !== null) {
    return refused;
  }
  const rooms = await roomAvailability(date, vendors);
  return { status: 200, body: { date, desks: { available: desks.availableOn(date) }, rooms } };
}

const routes: Record<string, (date: string) => Promise<Answer>> = {
  "/health": async () => ({ status: 200, body: { status: "ok" } }),
  "/desks": desksOn,
  "/availability": availabilityOn,
};

async function route(request: IncomingMessage): Promise<Answer> {
  const url = new URL(request.url ?? "/", "http://app");
  const handler = Object.hasOwn(routes, url.pathname) ? routes[url.pathname] : undefined;
  if (handler === undefined) {
    return { status: 404, body: { error: "not found" } };
  }
  if (request.method !== "GET") {
    return { status: 405, body: { error: "method not allowed" } };
  }
  return handler(url.searchParams.get("date") ?? "");
}

function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  route(request).then(
    (answer) => send(response, answer),
    (error: unknown) => {
      console.error(error);
      send(response, { status: 500, body: { error: "internal error" } });
    },
  );
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
