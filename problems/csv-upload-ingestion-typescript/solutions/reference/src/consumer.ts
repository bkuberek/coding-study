// Takes upload events off the queue, one at a time, for as long as the app runs. An event is
// deleted only once its upload is loaded, or once it proves to be nothing to load. One that fails
// is left alone: it comes back after the visibility timeout, and the queue's redrive policy moves
// it to the dead-letter queue after its third receive.

import { setTimeout as sleep } from "node:timers/promises";

import {
  ChangeMessageVisibilityCommand,
  DeleteMessageCommand,
  type Message,
  ReceiveMessageCommand,
} from "@aws-sdk/client-sqs";

import { UPLOAD_QUEUE_URL, sqs } from "./aws.ts";
import { uploadIn } from "./events.ts";
import { ingest } from "./ingest.ts";

const WAIT_S = 5;
const PAUSE_AFTER_FAILURE_MS = 1000;
// While a long file loads, its event is kept hidden a little longer, again and again, so that it
// is not delivered a second time meanwhile; if the app dies, it is visible again within this.
const KEEP_HIDDEN_S = 3;
const KEEP_HIDDEN_EVERY_MS = 1000;

function keepHidden(message: Message): NodeJS.Timeout {
  return setInterval(() => {
    sqs
      .send(
        new ChangeMessageVisibilityCommand({
          QueueUrl: UPLOAD_QUEUE_URL,
          ReceiptHandle: message.ReceiptHandle,
          VisibilityTimeout: KEEP_HIDDEN_S,
        }),
      )
      .catch((error: unknown) => console.error("could not keep the event hidden:", error));
  }, KEEP_HIDDEN_EVERY_MS);
}

// True once the event's upload is loaded, or the event proved to be nothing to load.
async function settled(message: Message): Promise<boolean> {
  const hidden = keepHidden(message);
  try {
    const upload = uploadIn(message.Body ?? "");
    if (upload !== undefined) {
      await ingest(upload);
    }
    return true;
  } catch (error) {
    console.error(`left on the queue to be tried again: ${String(error)}`);
    return false;
  } finally {
    clearInterval(hidden);
  }
}

async function handle(message: Message): Promise<void> {
  if (await settled(message)) {
    await sqs.send(
      new DeleteMessageCommand({ QueueUrl: UPLOAD_QUEUE_URL, ReceiptHandle: message.ReceiptHandle }),
    );
  }
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
