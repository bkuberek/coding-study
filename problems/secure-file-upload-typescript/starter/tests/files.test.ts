import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { resetMocks } from "./mockControl.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;
const maxBodyBytes = Number(process.env.MAX_BODY_BYTES);
/** A GIF of one pixel. */
const picture = Buffer.from("R0lGODlhAQABAAAAACwAAAAAAQABAAACAkQBADs=", "base64");

function upload(user: string, name: string, data: Buffer): Promise<Response> {
  return fetch(`${app}/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User": user },
    body: JSON.stringify({ name, content_type: "image/gif", data: data.toString("base64") }),
  });
}

async function uploadedId(user: string, name: string, data: Buffer): Promise<string> {
  const response = await upload(user, name, data);
  assert.equal(response.status, 201);
  return ((await response.json()) as { id: string }).id;
}

async function contentOf(user: string, id: string): Promise<Buffer> {
  const response = await fetch(`${app}/files/${id}/content`, { headers: { "X-User": user } });
  assert.equal(response.status, 200);
  return Buffer.from(await response.arrayBuffer());
}

beforeEach(resetMocks);

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("an upload comes back byte for byte", async () => {
  const id = await uploadedId("starter-ana", "avatar.gif", picture);

  assert.deepEqual(await contentOf("starter-ana", id), picture);
});

test("two users who upload the same name each get their own file back", async () => {
  const other = Buffer.from("R0lGODlhAgABAAAAACwAAAAAAgABAAACAgQKADs=", "base64");
  const first = await uploadedId("starter-ben", "avatar.gif", picture);
  const second = await uploadedId("starter-cy", "avatar.gif", other);

  assert.deepEqual(await contentOf("starter-ben", first), picture);
  assert.deepEqual(await contentOf("starter-cy", second), other);
});

test("a body over MAX_BODY_BYTES is refused", async () => {
  const response = await upload("starter-di", "huge.gif", Buffer.alloc(maxBodyBytes));

  assert.equal(response.status, 413);
  assert.deepEqual(await response.json(), { error: "too_large" });
});
