// Takes upload events off the queue, one at a time, for as long as the app runs.

import { setTimeout as sleep } from "node:timers/promises";

import { type Message, ReceiveMessageCommand } from "@aws-sdk/client-sqs";

import { UPLOAD_QUEUE_URL, sqs } from "./aws.ts";

// A receive waits this long for an event before it answers with none, and the loop asks again.
const WAIT_S = 5;
const PAUSE_AFTER_FAILURE_MS = 1000;

// Level 1 starts here: read the file the event names, load its rows, and only then delete the
// event. An event nobody deletes comes back once its visibility timeout runs out.
async function handle(message: Message): Promise<void> {
  console.log(`an upload event arrived, and nothing loads it yet: ${message.Body}`);
}

export async function consume(): Promise<void> {
  for (;;) {
    try {
      const received = await sqs.send(
        new ReceiveMessageCommand({
          QueueUrl: UPLOAD_QUEUE_URL,
          MaxNumberOfMessages: 1,
          WaitTimeSeconds: WAIT_S,
        }),
      );
      for (const message of received.Messages ?? []) {
        await handle(message);
      }
    } catch (error) {
      console.error("receiving upload events failed:", error);
      await sleep(PAUSE_AFTER_FAILURE_MS);
    }
  }
}
