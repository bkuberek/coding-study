const EMPTY = 0;
const COVERED = 1;
const MIXED = 2;
const LOW = 1;
const HIGH = 1_000_000_000; // every range lies inside [1, 10^9)

/** EMPTY or COVERED with no children, or MIXED with both children. */
class CoverNode {
  state: number;
  left: CoverNode | null = null;
  right: CoverNode | null = null;

  constructor(state: number) {
    this.state = state;
  }
}

export class RangeModule {
  private readonly root = new CoverNode(EMPTY);

  constructor() {}

  addRange(left: number, right: number): void {
    this.assign(this.root, LOW, HIGH, left, right, COVERED);
  }

  queryRange(left: number, right: number): boolean {
    return this.covered(this.root, LOW, HIGH, left, right);
  }

  removeRange(left: number, right: number): void {
    this.assign(this.root, LOW, HIGH, left, right, EMPTY);
  }

  private assign(node: CoverNode, low: number, high: number, left: number, right: number, value: number): void {
    if (right <= low || high <= left) {
      return;
    }
    if (left <= low && high <= right) {
      node.state = value;
      node.left = node.right = null;
      return;
    }
    if (node.left === null || node.right === null) {
      // A uniform node is split: both halves inherit its state.
      node.left = new CoverNode(node.state);
      node.right = new CoverNode(node.state);
    }
    const middle = Math.floor((low + high) / 2);
    this.assign(node.left, low, middle, left, right, value);
    this.assign(node.right, middle, high, left, right, value);
    if (node.left.state === node.right.state && node.left.state !== MIXED) {
      node.state = node.left.state; // both halves agree: collapse
      node.left = node.right = null;
    } else {
      node.state = MIXED;
    }
  }

  private covered(node: CoverNode, low: number, high: number, left: number, right: number): boolean {
    if (right <= low || high <= left) {
      return true;
    }
    if (node.left === null || node.right === null) {
      return node.state === COVERED;
    }
    const middle = Math.floor((low + high) / 2);
    return (
      this.covered(node.left, low, middle, left, right) &&
      this.covered(node.right, middle, high, left, right)
    );
  }
}
