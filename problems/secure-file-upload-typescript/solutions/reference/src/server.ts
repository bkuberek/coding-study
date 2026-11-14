// The upload service: users upload attachments and avatars, see them, and share them by link.

import { createServer } from "node:http";
import type { IncomingMessage } from "node:http";

import { DATA_DIR, MAX_BODY_BYTES, PORT, QUOTA_BYTES } from "./config.ts";
import { jsonObject, readBody, refusal, send } from "./http.ts";
import type { Answer } from "./http.ts";
import { MAX_LINK_SECONDS, MAX_SMALL_BODY_BYTES, MIN_LINK_SECONDS } from "./limits.ts";
import { checkLink, linkTo, nowSeconds } from "./links.ts";
import { Quarantine } from "./quarantine.ts";
import { content } from "./serving.ts";
import { FileStore } from "./store.ts";
import type { StoredFile } from "./store.ts";
import { metadata, Uploads } from "./uploads.ts";

const USER = /^[A-Za-z0-9_-]{1,64}$/;
const FILE_PATH = /^\/files\/([^/]+)(?:\/(content|scan|links))?$/;
const SHARED_PATH = /^\/shared\/([^/]+)$/;

const store = new FileStore(DATA_DIR, QUOTA_BYTES);
const quarantine = new Quarantine(store);
const uploads = new Uploads(store, quarantine);

/** The refusal goes out on a connection that closes, since the rest of the body is never read. */
const TOO_LARGE: Answer = { ...refusal(413, "too_large"), headers: { Connection: "close" } };

async function createLink(request: IncomingMessage, file: StoredFile): Promise<Answer> {
  const body = await readBody(request, MAX_SMALL_BODY_BYTES);
  if (body === null) {
    return TOO_LARGE;
  }
  const seconds = jsonObject(body)?.expires_in_s;
  if (
    typeof seconds !== "number" ||
    !Number.isInteger(seconds) ||
    seconds < MIN_LINK_SECONDS ||
    seconds > MAX_LINK_SECONDS
  ) {
    return refusal(400, "invalid_request");
  }
  if (file.status === "pending") {
    return refusal(409, "scan_pending");
  }
  if (file.status === "infected") {
    return refusal(410, "infected");
  }
  const link = linkTo(file.id, nowSeconds() + seconds);
  return { status: 201, body: link, headers: { Location: link.url } };
}

async function shared(id: string, query: URLSearchParams): Promise<Answer> {
  const check = checkLink(id, query.get("expires"), query.get("sig"), nowSeconds());
  if (check === "invalid") {
    return refusal(403, "invalid_link");
  }
  if (check === "expired") {
    return refusal(410, "link_expired");
  }
  const file = store.findShared(id);
  return file === undefined ? refusal(404, "not_found") : content(store, file);
}

async function onFile(request: IncomingMessage, file: StoredFile, part = ""): Promise<Answer> {
  switch (`${request.method} ${part}`) {
    case "GET ":
      return { status: 200, body: metadata(file) };
    case "DELETE ":
      await store.forget(file);
      return { status: 204 };
    case "GET content":
      return content(store, file);
    case "GET scan":
      return { status: 200, body: { status: file.status } };
    case "POST scan":
      return { status: 200, body: { status: await quarantine.rescan(file) } };
    case "POST links":
      return createLink(request, file);
    default:
      return refusal(404, "not_found");
  }
}

async function route(request: IncomingMessage, url: URL): Promise<Answer> {
  const path = url.pathname;
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  const sharedPath = SHARED_PATH.exec(path);
  if (request.method === "GET" && sharedPath !== null) {
    return shared(sharedPath[1], url.searchParams);
  }
  // Before any body is read: a stranger's upload costs nothing.
  const owner = request.headers["x-user"];
  if (typeof owner !== "string" || !USER.test(owner)) {
    return refusal(401, "unauthenticated");
  }
  if (request.method === "POST" && path === "/files") {
    const body = await readBody(request, MAX_BODY_BYTES);
    return body === null ? TOO_LARGE : uploads.receive(owner, body);
  }
  if (request.method === "GET" && path === "/usage") {
    return { status: 200, body: { used_bytes: store.usage(owner), quota_bytes: QUOTA_BYTES } };
  }
  const filePath = FILE_PATH.exec(path);
  const file = filePath === null ? undefined : store.find(owner, filePath[1]);
  return file === undefined ? refusal(404, "not_found") : onFile(request, file, filePath?.[2]);
}

// A client has 2 s to send its whole request, and then gets 408: no connection waits forever on
// one that stopped sending. It bounds the time a request takes; `readBody` bounds its bytes.
const limits = { headersTimeout: 2000, requestTimeout: 2000, connectionsCheckingInterval: 250 };

const server = createServer(limits, (request, response) => {
  route(request, new URL(request.url ?? "/", "http://app"))
    .catch((error: unknown) => {
      console.error(error);
      return refusal(500, "internal_error");
    })
    .then((answer) => send(response, answer));
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`listening on ${PORT}`);
});
