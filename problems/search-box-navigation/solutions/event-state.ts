const ARROW_DOWN = "ArrowDown";
const ARROW_UP = "ArrowUp";
const ENTER = "Enter";
const NOTHING = -1;

// The list is empty exactly when nothing is highlighted: `show` keeps the two in step.
export class SearchBox {
  private readonly names: string[];
  private readonly loweredNames: string[];
  private shown: string[] = [];
  private highlight = NOTHING;
  private text = "";
  private requestsSent = 0;
  private awaitedRequest: number | null = null;
  private readonly selected: string[] = [];

  constructor(names: string[]) {
    this.names = names;
    this.loweredNames = names.map((name) => name.toLowerCase());
  }

  // Level 1
  keydown(timestamp: number, key: string): void {
    if (key === ARROW_DOWN) {
      this.move(1);
    } else if (key === ARROW_UP) {
      this.move(-1);
    } else if (key === ENTER) {
      this.selectHighlighted();
    }
  }

  // Releasing a key changes nothing: every action happens when the key goes down.
  keyup(timestamp: number, key: string): void {}

  resultsArrived(timestamp: number, items: string[]): void {
    this.show(items);
  }

  results(timestamp: number): string[] {
    return [...this.shown];
  }

  highlighted(timestamp: number): number {
    return this.highlight;
  }

  highlightedText(timestamp: number): string {
    return this.highlight === NOTHING ? "" : this.shown[this.highlight];
  }

  // Level 2
  search(timestamp: number, query: string): void {
    const needle = query.trim().toLowerCase();
    if (needle === "") {
      this.show([]);
      return;
    }
    this.show(this.names.filter((_, index) => this.loweredNames[index].includes(needle)));
  }

  // Level 3
  inputChanged(timestamp: number, text: string): number {
    this.text = text;
    if (text.trim() === "") {
      this.stopAwaiting();
      return NOTHING;
    }
    this.requestsSent += 1;
    this.awaitedRequest = this.requestsSent;
    return this.requestsSent;
  }

  responseArrived(timestamp: number, requestId: number, items: string[]): void {
    if (requestId === this.awaitedRequest) {
      this.show(items);
    }
  }

  inputText(timestamp: number): string {
    return this.text;
  }

  // Level 4
  selections(timestamp: number): string[] {
    return [...this.selected];
  }

  // `%` keeps the sign of the dividend, so adding `count` keeps `-1` from staying negative.
  private move(step: number): void {
    const count = this.shown.length;
    if (count > 0) {
      this.highlight = (this.highlight + step + count) % count;
    }
  }

  private selectHighlighted(): void {
    if (this.highlight === NOTHING) {
      return;
    }
    const choice = this.shown[this.highlight];
    this.selected.push(choice);
    this.text = choice;
    this.stopAwaiting();
  }

  // The input changed without a request: no response sent so far may be shown, and the list
  // closes.
  private stopAwaiting(): void {
    this.awaitedRequest = null;
    this.show([]);
  }

  private show(items: string[]): void {
    this.shown = [...items];
    this.highlight = items.length > 0 ? 0 : NOTHING;
  }
}
