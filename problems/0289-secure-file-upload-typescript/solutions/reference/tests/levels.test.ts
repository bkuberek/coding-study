import assert from "node:assert/strict";
import { beforeEach, describe, test } from "node:test";

import { displayName, extensionOf } from "../src/names.ts";
import { hasActiveContent, sniff } from "../src/sniffing.ts";
import { requestsTo, resetMocks, setScenario } from "./mockControl.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;
const gif = Buffer.from("R0lGODlhAQABAAAAACwAAAAAAQABAAACAkQBADs=", "base64");
const png = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13]);
const page = Buffer.from("<!DOCTYPE html><p>hello</p>");

function upload(user: string, name: string, data: Buffer): Promise<Response> {
  return fetch(`${app}/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User": user },
    body: JSON.stringify({ name, data: data.toString("base64") }),
  });
}

async function uploadedId(response: Response): Promise<string> {
  return ((await response.json()) as { id: string }).id;
}

function asUser(user: string, init: RequestInit = {}): RequestInit {
  return { ...init, headers: { "Content-Type": "application/json", "X-User": user } };
}

beforeEach(resetMocks);

describe("names", () => {
  test("only the part after the last slash or backslash is kept", () => {
    assert.equal(displayName("../../etc/passwd.gif"), "passwd.gif");
    assert.equal(displayName("C:\\Users\\kim\\avatar.png"), "avatar.png");
  });

  for (const name of ["", "photos/", "photos/..", "a\u0000.png", 'say "hi".png', "é.png"]) {
    test(`${JSON.stringify(name)} cannot be shown`, () => {
      assert.equal(displayName(name), null);
    });
  }

  test("a name of 255 characters is the longest", () => {
    assert.equal(displayName(`${"a".repeat(251)}.png`)?.length, 255);
    assert.equal(displayName(`${"a".repeat(252)}.png`), null);
  });

  test("the extension is the last one, in lower case", () => {
    assert.equal(extensionOf("report.pdf.PNG"), "png");
    assert.equal(extensionOf("avatar"), "");
  });
});

describe("sniffing", () => {
  test("the first bytes decide the type", () => {
    assert.equal(sniff(png)?.mime, "image/png");
    assert.equal(sniff(gif)?.mime, "image/gif");
    assert.equal(sniff(Buffer.from([0xff, 0xd8, 0xff, 0xe0]))?.mime, "image/jpeg");
    assert.equal(sniff(Buffer.from("%PDF-1.7"))?.mime, "application/pdf");
  });

  test("a page, or a signature cut short, is no allowed type", () => {
    assert.equal(sniff(page), undefined);
    assert.equal(sniff(Buffer.from("GIF89")), undefined);
  });

  test("an image holding markup in any case is active", () => {
    const polyglot = Buffer.concat([png, Buffer.from("<ScRiPt>alert(1)</script>")]);

    assert.equal(hasActiveContent(polyglot, sniff(png)!), true);
    assert.equal(hasActiveContent(png, sniff(png)!), false);
  });

  test("a PDF that names JavaScript is active", () => {
    const pdf = Buffer.from("%PDF-1.4 <</S /JavaScript /JS (app.alert(1))>>");

    assert.equal(hasActiveContent(pdf, sniff(pdf)!), true);
  });
});

describe("the service", () => {
  test("a page named avatar.png is refused", async () => {
    const response = await upload("reference-ana", "avatar.png", page);

    assert.equal(response.status, 415);
    assert.deepEqual(await response.json(), { error: "unsupported_type" });
  });

  test("a scanner outage leaves the file pending, unserved, after 3 attempts", async () => {
    await setScenario("scanner", "outage");

    const response = await upload("reference-ben", "avatar.gif", gif);

    assert.equal(response.status, 202);
    const content = await fetch(`${app}/files/${await uploadedId(response)}/content`, asUser("reference-ben"));
    assert.equal(content.status, 409);
    assert.equal((await requestsTo("scanner")).length, 3);
  });

  test("an infected upload is refused and takes no quota", async () => {
    await setScenario("scanner", "infected");

    const response = await upload("reference-cy", "avatar.gif", gif);

    assert.equal(response.status, 422);
    const usage = await fetch(`${app}/usage`, asUser("reference-cy"));
    assert.deepEqual(await usage.json(), { used_bytes: 0, quota_bytes: Number(process.env.QUOTA_BYTES) });
  });

  test("a link opens the file without X-User, and a forged one does not", async () => {
    const id = await uploadedId(await upload("reference-di", "avatar.gif", gif));
    const created = await fetch(`${app}/files/${id}/links`, {
      ...asUser("reference-di"),
      method: "POST",
      body: JSON.stringify({ expires_in_s: 60 }),
    });
    const { url } = (await created.json()) as { url: string };

    const opened = await fetch(`${app}${url}`);
    const forgedUrl = url.replace(/sig=(.)/, (_, first) => `sig=${first === "0" ? "1" : "0"}`);
    const forged = await fetch(`${app}${forgedUrl}`);

    assert.deepEqual(Buffer.from(await opened.arrayBuffer()), gif);
    assert.equal(forged.status, 403);
  });
});
