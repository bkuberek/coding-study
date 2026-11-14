const FINAL = "final";
const ERROR = "error";
const ACCEPTED = "accepted";
const REJECTED = "rejected";
const PASS = "pass";
const NO_VERDICT = "no verdict";
const NO_LIMIT = -1;

type Phase = "before" | "after";

// What the last run did: the counters the loop keeps and the reports it builds.
class RunState {
  iterations = 0;
  tokens = 0;
  millis = 0;
  reason = "";
  tripped: string[][] = [];
  summary: string[][] = [];
}

// The arguments as compact JSON with the keys of every object sorted.
function canonicalArgs(args: string): string {
  const render = (value: unknown): string => {
    if (Array.isArray(value)) {
      return `[${value.map(render).join(",")}]`;
    }
    if (value !== null && typeof value === "object") {
      const record = value as Record<string, unknown>;
      const members = Object.keys(record)
        .sort()
        .map((key) => `${JSON.stringify(key)}:${render(record[key])}`);
      return `{${members.join(",")}}`;
    }
    return JSON.stringify(value);
  };
  return render(JSON.parse(args));
}

// Trim, collapse white space to one space, and replace each run of digits with `#`.
function canonicalError(text: string): string {
  return text
    .split(/\s+/)
    .filter((word) => word !== "")
    .join(" ")
    .replace(/[0-9]+/g, "#");
}

export class LoopController {
  private noProgressLimit = 0;
  private maxTokens = NO_LIMIT;
  private maxMillis = NO_LIMIT;
  private verdicts: Map<string, string> | null = null;
  private last = new RunState();

  // Level 1
  run(maxIterations: number, steps: string[][]): string {
    const state = new RunState();
    this.last = state;
    let streakSignature: string | null = null;
    let streak = 0;
    while (state.reason === "") {
      state.reason = this.stopBefore(state, maxIterations, steps.length);
      if (state.reason !== "") {
        break;
      }
      const [action, args, status, result, tokens, millis] = steps[state.iterations];
      state.iterations += 1;
      state.tokens += Number(tokens);
      state.millis += Number(millis);
      const [outcome, feedback] = this.judge(action, status, result);
      state.summary.push([
        "step",
        String(state.iterations),
        action,
        outcome,
        String(state.tokens),
        String(state.millis),
      ]);
      if (feedback !== "") {
        state.summary.push(["feedback", String(state.iterations), feedback]);
      }
      if (outcome === ACCEPTED) {
        state.reason = FINAL;
        break;
      }
      let signature: string | null = null;
      if (outcome === ERROR || outcome === REJECTED) {
        const text = outcome === REJECTED ? feedback : result;
        signature = JSON.stringify([action, canonicalArgs(args), canonicalError(text)]);
      }
      if (signature === null) {
        streak = 0;
      } else if (signature === streakSignature) {
        streak += 1;
      } else {
        streak = 1;
      }
      streakSignature = signature;
      state.reason = this.stopAfter(state, streak);
    }
    state.summary.push([
      "stop",
      state.reason,
      String(state.iterations),
      String(state.tokens),
      String(state.millis),
    ]);
    return state.reason;
  }

  iterations(): number {
    return this.last.iterations;
  }

  // Level 2
  setNoProgressLimit(limit: number): void {
    this.noProgressLimit = limit;
  }

  // Level 3
  setBudgets(maxTokens: number, maxMillis: number): void {
    this.maxTokens = maxTokens;
    this.maxMillis = maxMillis;
  }

  tripped(): string[][] {
    return this.last.tripped;
  }

  // Level 4
  setCheck(claims: string[], verdicts: string[]): void {
    this.verdicts = new Map(claims.map((claim, i) => [claim, verdicts[i]]));
  }

  summary(): string[][] {
    return this.last.summary;
  }

  // The outcome of a step and the feedback it produces.
  private judge(action: string, status: string, result: string): [string, string] {
    if (action !== FINAL) {
      return [status, ""];
    }
    if (this.verdicts === null) {
      return [ACCEPTED, ""];
    }
    const verdict = this.verdicts.get(result) ?? NO_VERDICT;
    return verdict === PASS ? [ACCEPTED, ""] : [REJECTED, verdict];
  }

  private stopBefore(state: RunState, maxIterations: number, available: number): string {
    if (state.iterations >= maxIterations) {
      return "max_iterations";
    }
    const reason = this.tripBudgets(state, "before");
    if (reason !== "") {
      return reason;
    }
    return state.iterations >= available ? "out_of_steps" : "";
  }

  private stopAfter(state: RunState, streak: number): string {
    const reason = this.tripBudgets(state, "after");
    if (reason !== "") {
      return reason;
    }
    return this.noProgressLimit > 0 && streak >= this.noProgressLimit ? "no_progress" : "";
  }

  // Records the budgets that trip at this check and returns the first one's name. A budget is
  // spent (>=) when a step is about to start and exceeded (>) after a step.
  private tripBudgets(state: RunState, phase: Phase): string {
    const budgets: [string, number, number][] = [
      ["token_budget", state.tokens, this.maxTokens],
      ["time_budget", state.millis, this.maxMillis],
    ];
    for (const [reason, used, limit] of budgets) {
      if (limit === NO_LIMIT) {
        continue;
      }
      if (phase === "before" ? used >= limit : used > limit) {
        state.tripped.push([reason, phase, String(state.iterations), String(used), String(limit)]);
      }
    }
    return state.tripped.length > 0 ? state.tripped[0][0] : "";
  }
}
