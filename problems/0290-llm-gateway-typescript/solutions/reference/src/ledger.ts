// What each team may spend, what it has used and what that cost, from the usage providers report.

import type { Usage } from "./provider.ts";

type Price = { prompt: number; completion: number };

/** Credits per 1,000,000 tokens, which is micro-credits per token, by model. */
export const PRICES: Readonly<Record<string, Price>> = {
  "brisk-1": { prompt: 2, completion: 6 },
  "steady-2": { prompt: 3, completion: 15 },
};

type Account = { budget: number | null; prompt: number; completion: number; costMicros: number };

export type TeamUsage = {
  team: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_micros: number;
  remaining_tokens: number | null;
};

export class TeamLedger {
  readonly #accounts = new Map<string, Account>();

  setBudget(team: string, tokens: number): void {
    this.#account(team).budget = tokens;
  }

  /** The limit to send a provider for this team: the caller's, lowered to what remains; null when
   * nothing remains. A team with no budget keeps the caller's. */
  limitFor(team: string, asked: number): number | null {
    const remaining = remainingOf(this.#account(team));
    if (remaining === null) {
      return asked;
    }
    return remaining > 0 ? Math.min(asked, remaining) : null;
  }

  record(team: string, model: string, usage: Usage): void {
    const account = this.#account(team);
    const price = PRICES[model];
    account.prompt += usage.prompt_tokens;
    account.completion += usage.completion_tokens;
    account.costMicros += usage.prompt_tokens * price.prompt + usage.completion_tokens * price.completion;
  }

  usageOf(team: string): TeamUsage {
    const account = this.#account(team);
    return {
      team,
      prompt_tokens: account.prompt,
      completion_tokens: account.completion,
      cost_micros: account.costMicros,
      remaining_tokens: remainingOf(account),
    };
  }

  #account(team: string): Account {
    let account = this.#accounts.get(team);
    if (account === undefined) {
      account = { budget: null, prompt: 0, completion: 0, costMicros: 0 };
      this.#accounts.set(team, account);
    }
    return account;
  }
}

function remainingOf(account: Account): number | null {
  if (account.budget === null) {
    return null;
  }
  return Math.max(0, account.budget - account.prompt - account.completion);
}
