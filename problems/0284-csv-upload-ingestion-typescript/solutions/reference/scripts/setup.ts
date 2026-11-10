// `commands.bootstrap`, run before your app starts: it makes the buckets and the queues in the
// emulator, then applies the migrations. Running it twice changes nothing.

import { CreateBucketCommand } from "@aws-sdk/client-s3";
import { CreateQueueCommand, GetQueueAttributesCommand } from "@aws-sdk/client-sqs";
import { runner } from "node-pg-migrate";

import {
  DEAD_LETTER_QUEUE_URL,
  REPORT_BUCKET,
  RESULT_QUEUE_URL,
  UPLOAD_BUCKET,
  UPLOAD_QUEUE_URL,
  s3,
  sqs,
} from "../src/aws.ts";

// An event your app received and did not delete comes back this many seconds later.
const VISIBILITY_TIMEOUT_S = "3";
// The receive after this many moves the event to the dead-letter queue instead.
const MAX_RECEIVES = "3";

function queueName(url: string): string {
  return url.slice(url.lastIndexOf("/") + 1);
}

await s3.send(new CreateBucketCommand({ Bucket: UPLOAD_BUCKET }));
await s3.send(new CreateBucketCommand({ Bucket: REPORT_BUCKET }));

await sqs.send(new CreateQueueCommand({ QueueName: queueName(DEAD_LETTER_QUEUE_URL) }));
const deadLetter = await sqs.send(
  new GetQueueAttributesCommand({ QueueUrl: DEAD_LETTER_QUEUE_URL, AttributeNames: ["QueueArn"] }),
);
await sqs.send(
  new CreateQueueCommand({
    QueueName: queueName(UPLOAD_QUEUE_URL),
    Attributes: {
      VisibilityTimeout: VISIBILITY_TIMEOUT_S,
      RedrivePolicy: JSON.stringify({
        deadLetterTargetArn: deadLetter.Attributes?.QueueArn,
        maxReceiveCount: MAX_RECEIVES,
      }),
    },
  }),
);
await sqs.send(new CreateQueueCommand({ QueueName: queueName(RESULT_QUEUE_URL) }));

await runner({
  databaseUrl: process.env.DATABASE_URL ?? "",
  dir: "migrations",
  direction: "up",
  migrationsTable: "pgmigrations",
});
