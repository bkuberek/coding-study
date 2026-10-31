// The bank: the class that `cstudy submit` and the tests drive.

import { Account } from "./models.ts";

/** Bank accounts that hold whole amounts of money and send money to one another. */
export class Bank {
  readonly #accounts = new Map<string, Account>();

  createAccount(timestamp: number, accountId: string): boolean {
    throw new Error("Not implemented");
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    throw new Error("Not implemented");
  }

  transfer(timestamp: number, sourceId: string, targetId: string, amount: number): number {
    throw new Error("Not implemented");
  }
}
