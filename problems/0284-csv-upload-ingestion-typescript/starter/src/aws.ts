// The clients for the AWS services the sandbox emulates, and where each bucket and queue is.
// The region and the keys come from the environment; the emulator accepts any keys.

import { S3Client } from "@aws-sdk/client-s3";
import { SQSClient } from "@aws-sdk/client-sqs";

function setting(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`${name} is not set`);
  }
  return value;
}

const endpoint = setting("AWS_ENDPOINT_URL");

// A bucket is a path on the emulator, `http://aws:5000/uploads/...`, not a host name of its own.
export const s3 = new S3Client({ endpoint, forcePathStyle: true });
export const sqs = new SQSClient({ endpoint });

export const UPLOAD_BUCKET = setting("UPLOAD_BUCKET");
export const REPORT_BUCKET = setting("REPORT_BUCKET");
export const UPLOAD_QUEUE_URL = setting("UPLOAD_QUEUE_URL");
export const RESULT_QUEUE_URL = setting("RESULT_QUEUE_URL");
export const DEAD_LETTER_QUEUE_URL = setting("DEAD_LETTER_QUEUE_URL");
