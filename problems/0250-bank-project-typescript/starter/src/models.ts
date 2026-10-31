// The bank's model types.

/** One bank account. */
export class Account {
  readonly id: string;
  balance = 0;

  constructor(id: string) {
    this.id = id;
  }
}
