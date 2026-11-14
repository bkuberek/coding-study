// The company's LLM gateway: one endpoint for every team, in front of two providers.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { Gateway } from "./gateway.ts";
import { answer, header, readBody } from "./http.ts";
import { TeamLedger } from "./ledger.ts";
import { PrimaryProvider } from "./primary.ts";
import { Refusal, budgetTokens, chatRequest } from "./requests.ts";
import { SecondaryProvider } from "./secondary.ts";

const port = Number(process.env.PORT);
const TEAM_ROUTE = /^\/v1\/teams\/(?<team>[^/]+)\/(?<about>budget|usage)$/;

const ledger = new TeamLedger();
const gateway = new Gateway(
  [
    new PrimaryProvider(process.env.PRIMARY_LLM_URL ?? "", process.env.PRIMARY_LLM_KEY ?? ""),
    new SecondaryProvider(process.env.SECONDARY_LLM_URL ?? "", process.env.SECONDARY_LLM_KEY ?? ""),
  ],
  ledger,
);

async function chat(request: IncomingMessage, response: ServerResponse): Promise<void> {
  const asked = chatRequest(header(request, "X-Team"), await readBody(request));
  const maxTokens = ledger.limitFor(asked.team, asked.maxTokens);
  if (maxTokens === null) {
    answer(response, 429, { error: "token budget exhausted" });
    return;
  }
  const caller = new AbortController();
  response.on("close", () => caller.abort());
  const ask = { messages: asked.messages, maxTokens, signal: caller.signal };
  if (asked.stream) {
    await gateway.stream(asked.team, ask, response);
  } else {
    await gateway.whole(asked.team, ask, response);
  }
}

async function setBudget(
  request: IncomingMessage,
  response: ServerResponse,
  team: string,
): Promise<void> {
  const tokens = budgetTokens(await readBody(request));
  ledger.setBudget(team, tokens);
  answer(response, 200, { team, budget_tokens: tokens });
}

async function route(request: IncomingMessage, response: ServerResponse): Promise<void> {
  const { pathname } = new URL(request.url ?? "/", "http://gateway");
  const teamPath = TEAM_ROUTE.exec(pathname)?.groups;
  const team = decodeURIComponent(teamPath?.team ?? "");
  if (pathname === "/health") {
    answer(response, 200, { status: "ok" });
  } else if (pathname === "/v1/chat" && request.method === "POST") {
    await chat(request, response);
  } else if (teamPath?.about === "budget" && request.method === "PUT") {
    await setBudget(request, response, team);
  } else if (teamPath?.about === "usage" && request.method === "GET") {
    answer(response, 200, ledger.usageOf(team));
  } else {
    answer(response, 404, { error: "not found" });
  }
}

const server = createServer((request, response) => {
  route(request, response).catch((error: unknown) => {
    if (error instanceof Refusal) {
      answer(response, 400, { error: error.message });
      return;
    }
    console.error(error);
    if (response.headersSent) {
      response.end();
    } else {
      answer(response, 500, { error: "internal error" });
    }
  });
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
