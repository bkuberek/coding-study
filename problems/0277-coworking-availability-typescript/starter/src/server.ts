// The coworking space's API: what can be booked on a day.

import { createServer } from "node:http";
import type { ServerResponse } from "node:http";

import { DeskInventory } from "./desks.ts";

const port = Number(process.env.PORT);
const desks = await DeskInventory.fromFile("data/desks.json");

function answer(response: ServerResponse, status: number, body: unknown): void {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(body));
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://app");
  if (url.pathname === "/health") {
    answer(response, 200, { status: "ok" });
  } else if (url.pathname === "/desks") {
    const date = url.searchParams.get("date") ?? "";
    answer(response, 200, { date, available: desks.availableOn(date) });
  } else {
    answer(response, 404, { error: "not found" });
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
