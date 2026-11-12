const GROUP_GAP_MS = 1000;
const ROOT = 0;

// One recorded edit, kept as a command that can be applied and reverted: at `position`, `removed`
// was replaced by `inserted`. The step is also the history state it leads to.
class Step {
  readonly number: number;
  readonly parent: Step | null;
  readonly position: number;
  removed = "";
  inserted = "";
  readonly children: Step[] = [];
  currentChild: Step | null = null;

  constructor(number: number, parent: Step | null, position: number) {
    this.number = number;
    this.parent = parent;
    this.position = position;
  }

  apply(text: string): string {
    return text.slice(0, this.position) + this.inserted + text.slice(this.position + this.removed.length);
  }

  revert(text: string): string {
    return text.slice(0, this.position) + this.removed + text.slice(this.position + this.inserted.length);
  }

  // This step and every step above it, up to the root.
  ancestors(): Step[] {
    const chain: Step[] = [];
    for (let step: Step | null = this; step !== null; step = step.parent) {
      chain.push(step);
    }
    return chain;
  }
}

export class Editor {
  private content: string;
  private readonly steps: Step[];
  private current: Step;
  private readonly checkpoints = new Map<string, string>();
  private groupOpen = false;
  private lastTypedAt = 0;

  constructor(initial: string) {
    this.content = initial;
    const root = new Step(ROOT, null, 0);
    this.steps = [root];
    this.current = root;
  }

  // Level 1
  insert(position: number, text: string): void {
    this.groupOpen = false;
    this.record(Math.min(position, this.content.length), "", text);
  }

  erase(position: number, count: number): void {
    this.groupOpen = false;
    const start = Math.min(position, this.content.length);
    const end = Math.min(this.content.length, start + count);
    this.record(start, this.content.slice(start, end), "");
  }

  undo(): boolean {
    this.groupOpen = false;
    const parent = this.current.parent;
    if (parent === null) {
      return false;
    }
    this.content = this.current.revert(this.content);
    this.current = parent;
    return true;
  }

  redo(): boolean {
    this.groupOpen = false;
    const child = this.current.currentChild;
    if (child === null) {
      return false;
    }
    this.content = child.apply(this.content);
    this.current = child;
    return true;
  }

  text(): string {
    return this.content;
  }

  // Level 2
  typeText(timestamp: number, position: number, text: string): void {
    const at = Math.min(position, this.content.length);
    if (this.joinsGroup(timestamp, at)) {
      this.content = this.content.slice(0, at) + text + this.content.slice(at);
      this.current.inserted += text;
    } else {
      this.record(at, "", text);
    }
    this.groupOpen = true;
    this.lastTypedAt = timestamp;
  }

  private joinsGroup(timestamp: number, position: number): boolean {
    const group = this.current;
    return (
      this.groupOpen &&
      position === group.position + group.inserted.length &&
      timestamp - this.lastTypedAt <= GROUP_GAP_MS &&
      !group.inserted.endsWith(" ")
    );
  }

  // Level 3
  checkpoint(name: string): void {
    this.groupOpen = false;
    this.checkpoints.set(name, this.content);
  }

  restore(name: string): boolean {
    this.groupOpen = false;
    const saved = this.checkpoints.get(name);
    if (saved === undefined) {
      return false;
    }
    this.record(0, this.content, saved);
    return true;
  }

  // Level 4
  state(): number {
    return this.current.number;
  }

  branches(): number[] {
    return this.current.children.map((child) => child.number);
  }

  jump(state: number): boolean {
    this.groupOpen = false;
    if (!Number.isInteger(state) || state < 0 || state >= this.steps.length) {
      return false;
    }
    const target = this.steps[state];
    const pathDown = target.ancestors();
    const onTargetPath = new Set(pathDown);
    while (!onTargetPath.has(this.current)) {
      this.content = this.current.revert(this.content);
      this.current = this.current.parent as Step;
    }
    const common = pathDown.indexOf(this.current);
    for (let index = common - 1; index >= 0; index--) {
      this.content = pathDown[index].apply(this.content);
    }
    for (let index = 1; index < pathDown.length; index++) {
      pathDown[index].currentChild = pathDown[index - 1];
    }
    this.current = target;
    return true;
  }

  // Records one step, unless it would leave the text as it is.
  private record(position: number, removed: string, inserted: string): void {
    if (removed === inserted) {
      return;
    }
    const step = new Step(this.steps.length, this.current, position);
    step.removed = removed;
    step.inserted = inserted;
    this.steps.push(step);
    this.current.children.push(step);
    this.current.currentChild = step;
    this.content = step.apply(this.content);
    this.current = step;
  }
}
