// The assistant: answers a staff member's question with the model and the shop's tools.

import { chat } from "./model.ts";
import type { Message } from "./model.ts";
import { SYSTEM_PROMPT } from "./prompt.ts";
import type { Role } from "./roles.ts";
import { TOOLS, specOf } from "./tools.ts";

export type Question = { role: Role; question: string };

/** One tool call the model asked for, and what became of it. */
export type CallRecord = { tool: string; outcome: string };

export type AgentResult = { answer: string; stop: string; steps: number; calls: CallRecord[] };

/** For now it asks the model once and returns what it says, even when the model asks for a tool. */
export async function runAgent(question: Question): Promise<AgentResult> {
  const messages: Message[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: question.question },
  ];
  const reply = await chat(messages, TOOLS.map(specOf));
  return { answer: reply.message.content ?? "", stop: "answered", steps: 1, calls: [] };
}
