import assert from "node:assert/strict";
import { test } from "node:test";

test("the service answers its health path", async () => {
  const response = await fetch(`http://127.0.0.1:${process.env.PORT}/health`);

  assert.equal(response.status, 200);
});
