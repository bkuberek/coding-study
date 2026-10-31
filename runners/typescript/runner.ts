// The TypeScript runner (docs/specs/runners.md). Usage:
//
//   node runners/typescript/runner.ts --request <request.json> --out <events.jsonl>
//
// Reads the request, writes `hello`, runs every job in order, writes `bye` and exits 0. A request
// it cannot execute exits 2 before any case; any other exit is a crash the CLI reports.

import { runBenchJob } from "./lib/bench.ts";
import { blockProcessExit } from "./lib/capture.ts";
import { runConcurrentJob } from "./lib/concurrent.ts";
import { runJob } from "./lib/execute.ts";
import {
  BadRequest,
  EventWriter,
  PROTOCOL_VERSION,
  readRequest,
  type TestJob,
} from "./lib/protocol.ts";
import { runSuiteJob } from "./lib/suite.ts";

const RUNNER_NAME = "typescript";
/** Protocol additions this runner implements (docs/specs/runners.md#capability). */
const FEATURES = ["stress", "project", "suite"];
const BAD_REQUEST_EXIT_CODE = 2;

interface Options {
  readonly request: string;
  readonly out: string;
}

function parseOptions(argv: readonly string[]): Options {
  const value = (flag: string): string => {
    const index = argv.indexOf(flag);
    const found = index < 0 ? undefined : argv[index + 1];
    if (found === undefined) {
      throw new BadRequest(`missing ${flag} <path>`);
    }
    return found;
  };
  return { request: value("--request"), out: value("--out") };
}

async function runTestJob(job: TestJob, events: EventWriter): Promise<void> {
  switch (job.shape) {
    case "concurrent":
      return runConcurrentJob(job, events);
    case "suite":
      return runSuiteJob(job, events);
    default:
      return runJob(job, events);
  }
}

const exit = blockProcessExit();
try {
  const options = parseOptions(process.argv.slice(2));
  const request = readRequest(options.request);
  const events = new EventWriter(options.out);
  events.write({
    event: "hello",
    runner: RUNNER_NAME,
    protocol: PROTOCOL_VERSION,
    runtime: process.versions.node,
    features: FEATURES,
  });
  if (request.mode === "test") {
    for (const job of request.jobs) {
      await runTestJob(job, events);
    }
  } else {
    for (const job of request.jobs) {
      await runBenchJob(job, events);
    }
  }
  events.write({ event: "bye" });
} catch (error) {
  if (!(error instanceof BadRequest)) {
    throw error;
  }
  process.stderr.write(`bad request: ${error.message}\n`);
  exit(BAD_REQUEST_EXIT_CODE);
}
// Exit explicitly: timers or handles left open by user code must not keep the runner alive.
exit(0);
