// The assistant: answers a staff member's question with the model and the shop's tools. The model
// proposes and this loop decides: every call goes through a CallJudge, every reply counts against a
// Budget, and no answer leaves with the system prompt's canary in it.

import { Budget } from "./budget.ts";
import type { Exhausted } from "./budget.ts";
import { CallJudge } from "./calls.ts";
import { chat } from "./model.ts";
import type { Message } from "./model.ts";
import { PROMPT_CANARY, SYSTEM_PROMPT } from "./prompt.ts";
import { mayUse } from "./roles.ts";
import type { Role } from "./roles.ts";
import { TOOLS, specOf } from "./tools.ts";

export type Question = { role: Role; question: string };

/** One tool call the model asked for, and what became of it. */
export type CallRecord = { tool: string; outcome: string };

export type AgentResult = { answer: string; stop: string; steps: number; calls: CallRecord[] };

const MAX_STEPS = Number(process.env.MAX_STEPS);
const TOKEN_BUDGET = Number(process.env.TOKEN_BUDGET);
const TOOL_TIMEOUT_MS = Number(process.env.TOOL_TIMEOUT_MS);

const WITHHELD = "The answer was withheld: it repeated the assistant's instructions.";
const STOPPED: Record<Exhausted, string> = {
  step_limit: "Stopped before a final answer: the step limit was reached.",
  token_budget: "Stopped before a final answer: the token budget was spent.",
};

export async function runAgent({ role, question }: Question): Promise<AgentResult> {
  const tools = TOOLS.filter((tool) => mayUse(role, tool.name)).map(specOf);
  const messages: Message[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: question },
  ];
  const budget = new Budget(MAX_STEPS, TOKEN_BUDGET);
  const judge = new CallJudge(role, question, TOOL_TIMEOUT_MS);
  const calls: CallRecord[] = [];
  for (;;) {
    const { message, usage } = await chat(messages, tools);
    budget.spend(usage);
    const asked = message.tool_calls ?? [];
    if (asked.length === 0) {
      const answer = message.content ?? "";
      return answer.includes(PROMPT_CANARY)
        ? { answer: WITHHELD, stop: "withheld", steps: budget.steps, calls }
        : { answer, stop: "answered", steps: budget.steps, calls };
    }
    const exhausted = budget.exhausted();
    if (exhausted !== null) {
      return { answer: STOPPED[exhausted], stop: exhausted, steps: budget.steps, calls };
    }
    messages.push(message);
    for (const call of asked) {
      const { outcome, content } = await judge.answer(call);
      calls.push({ tool: call.function.name, outcome });
      messages.push({ role: "tool", tool_call_id: call.id, content });
    }
  }
}
