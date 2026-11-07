import { readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";

const port = Number(process.env.PORT);
const stock = `${process.env.CSTUDY_DATA_DIR}/stock.json`;
const vendor = process.env.ROOM_VENDOR_URL;
const DEGRADED = { rooms: [], degraded: true };

async function rooms(): Promise<unknown> {
  try {
    const answer = await fetch(`${vendor}/v1/rooms`);
    if (!answer.ok) {
      return DEGRADED;
    }
    const body = (await answer.json()) as { rooms: unknown };
    return { rooms: body.rooms, degraded: false };
  } catch {
    return DEGRADED;
  }
}

const DATE = /^\d{4}-\d{2}-\d{2}$/;

async function available(): Promise<number> {
  return JSON.parse(await readFile(stock, "utf8")).available;
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", "http://app");
  response.setHeader("Content-Type", "application/json");
  const answer = (status: number, body: unknown) => {
    response.statusCode = status;
    response.end(JSON.stringify(body));
  };
  if (url.pathname === "/health") {
    answer(200, { status: "ok" });
  } else if (url.pathname === "/desks/book" && request.method === "POST") {
    const left = (await available()) - 1;
    await writeFile(stock, JSON.stringify({ available: left }));
    answer(201, { available: left });
  } else if (url.pathname === "/desks") {
    const date = url.searchParams.get("date") ?? "";
    if (DATE.test(date)) {
      answer(200, { date, available: await available() });
    } else {
      answer(400, { error: "date is required" });
    }
  } else if (url.pathname === "/rooms") {
    answer(200, await rooms());
  } else {
    answer(404, { error: "not found" });
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
