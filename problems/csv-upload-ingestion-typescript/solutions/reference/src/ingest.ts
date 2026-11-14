// Loads one upload, whole or not at all: the claim, the rows and the import's counts are one
// transaction, so a crash halfway leaves nothing behind and the event, never deleted, comes back.
// The report is written before the commit and the result announced after it, so whoever reads
// the result finds the rows already there.

import type { Readable } from "node:stream";

import { GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { SendMessageCommand } from "@aws-sdk/client-sqs";
import type { PoolClient } from "pg";

import { REPORT_BUCKET, RESULT_QUEUE_URL, s3, sqs } from "./aws.ts";
import { pool } from "./db.ts";
import type { Upload } from "./events.ts";
import { claim, finish, summary } from "./imports.ts";
import { linesOf } from "./lines.ts";
import { type Outcome, loadFile } from "./load.ts";

async function inTransaction<T>(work: (client: PoolClient) => Promise<T>): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await work(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

// A missing object throws `NoSuchKey`, which rolls the claim back: the event stays on the queue
// and is tried again once it comes back.
async function readAndLoad(client: PoolClient, upload: Upload): Promise<Outcome> {
  const object = await s3.send(new GetObjectCommand({ Bucket: upload.bucket, Key: upload.key }));
  const body = object.Body as Readable;
  try {
    return await loadFile(client, linesOf(body));
  } finally {
    body.destroy();
  }
}

async function writeReport(upload: Upload, report: string[]): Promise<void> {
  await s3.send(
    new PutObjectCommand({
      Bucket: REPORT_BUCKET,
      Key: upload.key,
      Body: `${report.join("\n")}\n`,
      ContentType: "text/csv",
    }),
  );
}

async function announce(upload: Upload, outcome: Outcome): Promise<void> {
  await sqs.send(
    new SendMessageCommand({
      QueueUrl: RESULT_QUEUE_URL,
      MessageBody: JSON.stringify({ bucket: upload.bucket, ...summary(upload.key, outcome) }),
    }),
  );
}

export async function ingest(upload: Upload): Promise<void> {
  const outcome = await inTransaction(async (client) => {
    if (!(await claim(client, upload))) {
      return undefined;
    }
    const loaded = await readAndLoad(client, upload);
    if (loaded.report.length > 1) {
      await writeReport(upload, loaded.report);
    }
    await finish(client, upload, loaded);
    return loaded;
  });
  if (outcome !== undefined) {
    await announce(upload, outcome);
  }
}
