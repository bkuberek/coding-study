// What an event on the upload queue says, as S3 writes it: one record per message, naming the
// bucket, the key, URL-encoded, and a sequencer that tells two uploads of one key apart. An event
// that is not a finished upload is answered with nothing to load, so it is deleted, not retried;
// a body that is not an S3 event at all is an error, so it is retried and dead-lettered.

export type Upload = { bucket: string; key: string; sequencer: string };

export class MalformedEvent extends Error {}

type Fields = Record<string, unknown>;

const TEST_EVENT = "s3:TestEvent";
const CREATED = "ObjectCreated:";
// An upload tool writes `name.part` and renames it when the upload is complete.
const PARTIAL_SUFFIX = ".part";

function fields(value: unknown, what: string): Fields {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new MalformedEvent(`${what} is not an object`);
  }
  return value as Fields;
}

function text(value: unknown, what: string): string {
  if (typeof value !== "string" || value === "") {
    throw new MalformedEvent(`${what} is not a string`);
  }
  return value;
}

function parsed(body: string): Fields {
  try {
    return fields(JSON.parse(body), "the event");
  } catch (error) {
    throw error instanceof MalformedEvent ? error : new MalformedEvent("the event is not JSON");
  }
}

// S3 writes a key as a URL's query would: a space as `+`, and `+` itself as `%2B`.
export function decodedKey(encoded: string): string {
  try {
    return decodeURIComponent(encoded.replaceAll("+", " "));
  } catch {
    throw new MalformedEvent(`the key ${encoded} is not URL-encoded`);
  }
}

export function uploadIn(body: string): Upload | undefined {
  const event = parsed(body);
  if (event.Event === TEST_EVENT) {
    return undefined;
  }
  const records = event.Records;
  if (!Array.isArray(records) || records.length !== 1) {
    throw new MalformedEvent("the event does not hold one record");
  }
  const record = fields(records[0], "the record");
  if (!text(record.eventName, "eventName").startsWith(CREATED)) {
    return undefined;
  }
  const s3 = fields(record.s3, "s3");
  const object = fields(s3.object, "s3.object");
  const key = decodedKey(text(object.key, "s3.object.key"));
  if (key.endsWith(PARTIAL_SUFFIX)) {
    return undefined;
  }
  return {
    bucket: text(fields(s3.bucket, "s3.bucket").name, "s3.bucket.name"),
    key,
    sequencer: text(object.sequencer, "s3.object.sequencer"),
  };
}
