// What happens to each tool call the model asks for. The model proposes a call; this code decides
// whether it runs, through checks in a fixed order, and turns every outcome into a result the model
// can read. Only a call that passes every check reaches a system.

import type { ToolCall } from "./model.ts";
import { PROMPT_CANARY } from "./prompt.ts";
import { mayUse } from "./roles.ts";
import type { Role } from "./roles.ts";
import { problemsWith } from "./schema.ts";
import { runTool, toolNamed } from "./tools.ts";

export type Outcome =
  | "ok"
  | "unknown_tool"
  | "not_allowed"
  | "invalid_arguments"
  | "not_requested"
  | "withheld"
  | "repeated"
  | "tool_error"
  | "tool_timeout";

/** What became of a call: its outcome, and the content of the tool message that answers it. */
export type Answered = { outcome: Outcome; content: unknown };

/** For a tool that moves money, the argument that must come from the question, not from a tool. */
const NAMED_IN_QUESTION: Readonly<Record<string, string>> = { issue_refund: "order_id" };

type Fields = Record<string, unknown>;

function isFields(value: unknown): value is Fields {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** A refusal this code wrote itself, so the model reads it as it is, not as a tool's output. */
function refused(error: Outcome, more: Fields = {}): Answered {
  return { outcome: error, content: { error, ...more } };
}

/** The arguments as an object, or undefined when their text is not the JSON of one. */
function parsedArguments(text: string): Fields | undefined {
  try {
    const value: unknown = JSON.parse(text);
    return isFields(value) ? value : undefined;
  } catch {
    return undefined;
  }
}

/** A value's JSON text with its keys sorted, so two values compare by what they hold. */
function canonical(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonical).join(",")}]`;
  }
  if (isFields(value)) {
    const entries = Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`);
    return `{${entries.join(",")}}`;
  }
  return JSON.stringify(value);
}

export class CallJudge {
  readonly #role: Role;
  readonly #question: string;
  readonly #timeoutMs: number;
  /** Each call this conversation has already run, by its tool and canonical arguments. */
  readonly #ran = new Set<string>();

  constructor(role: Role, question: string, timeoutMs: number) {
    this.#role = role;
    this.#question = question;
    this.#timeoutMs = timeoutMs;
  }

  async answer(call: ToolCall): Promise<Answered> {
    const tool = toolNamed(call.function.name);
    if (tool === undefined) {
      return refused("unknown_tool");
    }
    if (!mayUse(this.#role, tool.name)) {
      return refused("not_allowed");
    }
    const args = parsedArguments(call.function.arguments);
    if (args === undefined) {
      return refused("invalid_arguments", { problems: ["arguments: not the JSON of an object"] });
    }
    const problems = problemsWith(tool.parameters, args);
    if (problems.length > 0) {
      return refused("invalid_arguments", { problems });
    }
    const named = NAMED_IN_QUESTION[tool.name];
    if (named !== undefined && !this.#question.includes(String(args[named]))) {
      return refused("not_requested");
    }
    if (JSON.stringify(args).includes(PROMPT_CANARY)) {
      return refused("withheld");
    }
    const signature = `${tool.name} ${canonical(args)}`;
    if (this.#ran.has(signature)) {
      return refused("repeated");
    }
    this.#ran.add(signature);
    const result = await runTool(tool, args, this.#timeoutMs);
    if (!result.ok) {
      return refused(result.error, result.status === undefined ? {} : { status: result.status });
    }
    return { outcome: "ok", content: { tool: tool.name, untrusted: true, data: result.data } };
  }
}
