// Problem-owned `grade_setup`: puts the bulk delivery file into the upload bucket before your app
// starts. A file of 160 MB is too big for a case to carry, and bigger than your app's memory limit
// of 128 MiB, which is the point: only an app that streams it can load it. It is generated a line
// at a time and streamed to the emulator, so this script holds little of it either. Level 1 has no
// case that reads it, so a graded run of level 1 skips it.
//
// It talks to the emulator as the cases do: plain HTTP, with an Authorization header that names
// the service and region and carries no real signature, since the emulator checks none.

import { once } from "node:events";
import { readFileSync } from "node:fs";
import { request } from "node:http";
import { join } from "node:path";

type Bulk = {
  key: string;
  rows: number;
  skus: number;
  quantity_cycle: number;
  bad_every: number;
  description_length: number;
  filler: string;
};

const AUTHORIZATION =
  "AWS4-HMAC-SHA256 Credential=grader/20270301/us-east-1/s3/aws4_request, " +
  "SignedHeaders=host, Signature=unsigned";
const HEADER = "sku,description,quantity\n";
const CHUNK_BYTES = 1 << 16;
const FIRST_LEVEL_THAT_READS_IT = 2;

const bulk: Bulk = JSON.parse(readFileSync(join(import.meta.dirname, "bulk.json"), "utf8"));
const endpoint = new URL(process.env.AWS_ENDPOINT_URL ?? "");
const bucket = process.env.UPLOAD_BUCKET ?? "";

function line(row: number): string {
  const sku = `BULK-${String(row % bulk.skus).padStart(3, "0")}`;
  const description = `Pallet line ${row} ${bulk.filler.repeat(4)}`.slice(0, bulk.description_length);
  const quantity = row % bulk.bad_every === 0 ? 0 : (row % bulk.quantity_cycle) + 1;
  return `${sku},${description},${quantity}\n`;
}

function* chunks(): Generator<string> {
  let chunk = HEADER;
  for (let row = 1; row <= bulk.rows; row += 1) {
    chunk += line(row);
    if (chunk.length >= CHUNK_BYTES) {
      yield chunk;
      chunk = "";
    }
  }
  yield chunk;
}

function contentLength(): number {
  let length = 0;
  for (const chunk of chunks()) {
    length += Buffer.byteLength(chunk);
  }
  return length;
}

async function put(path: string, length: number, body: Iterable<string>): Promise<void> {
  const sent = request({
    host: endpoint.hostname,
    port: endpoint.port,
    method: "PUT",
    path,
    headers: { Authorization: AUTHORIZATION, "Content-Length": length },
  });
  const answered = once(sent, "response");
  for (const chunk of body) {
    if (!sent.write(chunk)) {
      await once(sent, "drain");
    }
  }
  sent.end();
  const [response] = await answered;
  response.resume();
  if (response.statusCode !== 200) {
    throw new Error(`PUT ${path} answered ${response.statusCode}`);
  }
}

if (Number(process.env.CSTUDY_GRADED_LEVEL) >= FIRST_LEVEL_THAT_READS_IT) {
  await put(`/${bucket}`, 0, []);
  await put(`/${bucket}/${bulk.key}`, contentLength(), chunks());
}
