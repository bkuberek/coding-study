import assert from "node:assert/strict";
import { beforeEach, describe, test } from "node:test";

import { isInternal } from "../src/addresses.ts";
import { webhookUrl } from "../src/urls.ts";
import { requestsTo, resetMocks, setScenario } from "./mockControl.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;
const secret = "reference-secret-0123456789";
const event = { id: "evt_9", type: "invoice.paid" };

function post(path: string, body: unknown): Promise<Response> {
  return fetch(`${app}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function register(id: string, url: string): Promise<Response> {
  return post("/endpoints", { id, url, secret });
}

async function deliverTo(...ids: string[]): Promise<Array<Record<string, unknown>>> {
  const response = await post("/deliveries", { endpoints: ids, event });
  assert.equal(response.status, 200);
  const body = (await response.json()) as { results: Array<Record<string, unknown>> };
  return body.results;
}

async function refusalOf(response: Response): Promise<unknown> {
  assert.equal(response.status, 400);
  return ((await response.json()) as { error: unknown }).error;
}

beforeEach(resetMocks);

describe("addresses", () => {
  for (const address of ["127.0.0.1", "10.20.0.5", "172.31.255.255", "169.254.169.254", "0.0.0.0"]) {
    test(`${address} is internal`, () => {
      assert.equal(isInternal(address), true);
    });
  }

  for (const address of ["::1", "::", "fd12:3456::7", "fe80::1", "::ffff:7f00:1"]) {
    test(`${address} is internal`, () => {
      assert.equal(isInternal(address), true);
    });
  }

  for (const address of ["203.0.113.10", "172.32.0.10", "172.15.255.255", "100.128.0.1"]) {
    test(`${address} is public`, () => {
      assert.equal(isInternal(address), false);
    });
  }

  test("what is not an address is refused", () => {
    assert.equal(isInternal("hooks.shop.test"), true);
  });
});

describe("URLs", () => {
  test("a user name in a URL is refused, whatever the text starts with", () => {
    assert.equal(webhookUrl("https://hooks.shop.test@127.0.0.1/"), null);
  });

  test("a port outside the allowed four is refused", () => {
    assert.equal(webhookUrl("http://hooks.shop.test:6379/"), null);
  });

  test("a relative redirect is read against the URL that answered", () => {
    const base = new URL("https://hooks.shop.test/events");

    assert.equal(webhookUrl("/v2/events", base)?.href, "https://hooks.shop.test/v2/events");
  });

  test("an encoded loopback address is parsed to its standard form", () => {
    assert.equal(webhookUrl("http://0x7f.1/")?.hostname, "127.0.0.1");
  });
});

describe("level 1", () => {
  test("a server slower than the limit fails the delivery with timeout", async () => {
    await setScenario("customer-hooks", "slow");
    await register("ref-slow", "https://ref-slow.shop.test/events");

    const [result] = await deliverTo("ref-slow");

    assert.equal(result?.error, "timeout");
  });

  test("a body past the limit fails the delivery, and is not asked for again", async () => {
    await setScenario("customer-hooks", "huge_response");
    await register("ref-huge", "https://ref-huge.shop.test/events");

    const [result] = await deliverTo("ref-huge");

    assert.equal(result?.error, "response_too_large");
    assert.equal((await requestsTo("customer-hooks")).length, 1);
  });
});

describe("level 2", () => {
  test("a name that resolves to a private address is refused", async () => {
    const response = await register("ref-intranet", "https://intranet.attacker.test/events");

    assert.equal(await refusalOf(response), "blocked_destination");
  });

  test("a decimal loopback address is refused", async () => {
    const response = await register("ref-decimal", "http://2130706433/admin");

    assert.equal(await refusalOf(response), "blocked_destination");
  });

  test("a name that changes its answer is looked up again, and refused", async () => {
    await setScenario("resolver", "rebinding");
    await register("ref-rebind", "https://rebind.attacker.test/events");

    const [result] = await deliverTo("ref-rebind");

    assert.equal(result?.error, "blocked_destination");
    assert.equal((await requestsTo("internal-admin")).length, 0);
  });
});

describe("level 3", () => {
  test("a 503 is tried again after a wait, and the third attempt delivers", async () => {
    await setScenario("customer-hooks", "flaky");
    await register("ref-flaky", "https://ref-flaky.shop.test/events");

    const [result] = await deliverTo("ref-flaky");

    assert.equal(result?.status, "delivered");
    assert.equal((await requestsTo("customer-hooks")).length, 3);
  });

  test("a redirect to the metadata address never reaches it", async () => {
    await setScenario("customer-hooks", "redirect_to_metadata");
    await register("ref-redirect", "https://ref-redirect.shop.test/events");

    const [result] = await deliverTo("ref-redirect");

    assert.equal(result?.error, "blocked_destination");
    assert.equal((await requestsTo("internal-admin")).length, 0);
  });

  test("every attempt carries the same signed body", async () => {
    await setScenario("customer-hooks", "outage");
    await register("ref-outage", "https://ref-outage.shop.test/events");

    const [result] = await deliverTo("ref-outage");

    const signatures = (await requestsTo("customer-hooks")).map(
      (request) => request.headers["x-webhook-signature"],
    );
    assert.deepEqual(signatures, [result?.signature, result?.signature, result?.signature]);
  });
});

describe("level 4", () => {
  test("the sixth delivery to one host in a burst is skipped", async () => {
    const ids = ["a", "b", "c", "d", "e", "f"].map((letter) => `ref-burst-${letter}`);
    for (const id of ids) {
      await register(id, "https://ref-burst.shop.test/events");
    }

    const results = await deliverTo(...ids);

    assert.deepEqual(
      results.map((result) => result.error),
      [null, null, null, null, null, "rate_limited"],
    );
  });

  test("three failures in a row disable the endpoint", async () => {
    await setScenario("customer-hooks", "gone");
    await register("ref-gone", "https://ref-gone.shop.test/events");
    for (let delivery = 0; delivery < 3; delivery += 1) {
      await deliverTo("ref-gone");
    }

    const response = await fetch(`${app}/endpoints/ref-gone`);

    assert.equal(((await response.json()) as { status: string }).status, "disabled");
  });
});
