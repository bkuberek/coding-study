// Classes shared by stubs, reference solutions and the runner
// (docs/specs/problem-format.md#support-classes). User code imports them as `#support`.
// The runner never relies on `instanceof`: any object with these fields is accepted.

export class ListNode {
  val: number;
  next: ListNode | null;

  constructor(val = 0, next: ListNode | null = null) {
    this.val = val;
    this.next = next;
  }
}

export class TreeNode {
  val: number;
  left: TreeNode | null;
  right: TreeNode | null;

  constructor(
    val = 0,
    left: TreeNode | null = null,
    right: TreeNode | null = null,
  ) {
    this.val = val;
    this.left = left;
    this.right = right;
  }
}

export class GraphNode {
  val: number;
  neighbors: GraphNode[];

  constructor(val = 0, neighbors: GraphNode[] = []) {
    this.val = val;
    this.neighbors = neighbors;
  }
}

/**
 * How `Decimal.div` and `Decimal.round` drop digits, named as in Java's `RoundingMode` (Python's
 * `ROUND_*` constants): `DOWN` toward zero, `UP` away from zero, `FLOOR` and `CEILING` toward
 * negative and positive infinity, and the `HALF_*` modes to the nearest neighbor, breaking a tie
 * away from zero, toward zero, or to the even digit.
 */
export type RoundingMode =
  | "DOWN"
  | "UP"
  | "FLOOR"
  | "CEILING"
  | "HALF_UP"
  | "HALF_DOWN"
  | "HALF_EVEN";

const DECIMAL_TEXT = /^(-?)([0-9]+)(?:\.([0-9]+))?$/;

/**
 * An exact decimal number, `unscaled / 10^scale`, for money (docs/specs/problem-format.md
 * #decimal-and-date). Immutable. `new Decimal("2500.50")` keeps its scale of 2, and `plus`,
 * `minus`, `times` and `movePointLeft`/`movePointRight` (times a power of ten) are exact; `div`
 * and `round` take the result scale and a rounding mode, as
 * Java's `BigDecimal.setScale` and Python's `Decimal.quantize` do. `eq` and the other
 * comparisons ignore the scale (`1.50` equals `1.5`); `toString` keeps it.
 */
export class Decimal {
  readonly unscaled: bigint;
  readonly scale: number;

  /** A decimal from its text (`"2500.50"`), an integer, or another Decimal. */
  constructor(value: string | number | Decimal);
  /** A decimal from its unscaled value and scale: `new Decimal(250050n, 2)` is 2500.50. */
  constructor(unscaled: bigint, scale?: number);
  constructor(value: string | number | bigint | Decimal, scale = 0) {
    if (typeof value === "bigint") {
      this.unscaled = value;
      this.scale = requireScale(scale);
    } else if (typeof value === "string") {
      [this.unscaled, this.scale] = parseDecimal(value);
    } else if (typeof value === "number") {
      this.unscaled = integerBigInt(value);
      this.scale = 0;
    } else {
      this.unscaled = value.unscaled;
      this.scale = value.scale;
    }
    Object.freeze(this);
  }

  plus(other: Decimal): Decimal {
    const scale = Math.max(this.scale, other.scale);
    return new Decimal(this.unscaledAt(scale) + other.unscaledAt(scale), scale);
  }

  minus(other: Decimal): Decimal {
    return this.plus(other.neg());
  }

  times(other: Decimal): Decimal {
    return new Decimal(
      this.unscaled * other.unscaled,
      this.scale + other.scale,
    );
  }

  /** `this / other` rounded to `scale` digits after the point; throws RangeError on zero. */
  div(other: Decimal, scale: number, mode: RoundingMode): Decimal {
    if (other.unscaled === 0n) {
      throw new RangeError("division by zero");
    }
    requireScale(scale);
    const numerator = this.unscaled * powerOfTen(other.scale + scale);
    const denominator = other.unscaled * powerOfTen(this.scale);
    return new Decimal(divideRounded(numerator, denominator, mode), scale);
  }

  /** The same number with exactly `scale` digits after the point. */
  round(scale: number, mode: RoundingMode): Decimal {
    requireScale(scale);
    if (scale >= this.scale) {
      return new Decimal(this.unscaledAt(scale), scale);
    }
    const dropped = powerOfTen(this.scale - scale);
    return new Decimal(divideRounded(this.unscaled, dropped, mode), scale);
  }

  /** `this / 10^places`, exact: the scale grows by `places` (Java's `movePointLeft`). */
  movePointLeft(places: number): Decimal {
    return this.withScale(this.scale + requirePlaces(places));
  }

  /**
   * `this * 10^places`, exact: the scale shrinks by `places`, but not below 0 (Java's
   * `movePointRight`).
   */
  movePointRight(places: number): Decimal {
    return this.withScale(this.scale - requirePlaces(places));
  }

  neg(): Decimal {
    return new Decimal(-this.unscaled, this.scale);
  }

  abs(): Decimal {
    return this.unscaled < 0n ? this.neg() : this;
  }

  /** -1, 0 or 1 by value; the scales do not matter. */
  cmp(other: Decimal): -1 | 0 | 1 {
    const scale = Math.max(this.scale, other.scale);
    const [a, b] = [this.unscaledAt(scale), other.unscaledAt(scale)];
    return a < b ? -1 : a > b ? 1 : 0;
  }

  eq(other: Decimal): boolean {
    return this.cmp(other) === 0;
  }

  lt(other: Decimal): boolean {
    return this.cmp(other) < 0;
  }

  lte(other: Decimal): boolean {
    return this.cmp(other) <= 0;
  }

  gt(other: Decimal): boolean {
    return this.cmp(other) > 0;
  }

  gte(other: Decimal): boolean {
    return this.cmp(other) >= 0;
  }

  /** Plain notation with exactly `scale` digits after the point; the current scale if omitted. */
  toFixed(scale?: number, mode: RoundingMode = "HALF_UP"): string {
    return (scale === undefined ? this : this.round(scale, mode)).toString();
  }

  /** Plain notation, never an exponent, keeping the scale: `2500.00`. */
  toString(): string {
    const digits = abs(this.unscaled).toString();
    const sign = this.unscaled < 0n ? "-" : "";
    if (this.scale === 0) {
      return sign + digits;
    }
    const padded = digits.padStart(this.scale + 1, "0");
    const point = padded.length - this.scale;
    return `${sign}${padded.slice(0, point)}.${padded.slice(point)}`;
  }

  private unscaledAt(scale: number): bigint {
    return this.unscaled * powerOfTen(scale - this.scale);
  }

  /** The same unscaled digits at `scale`; a negative scale becomes trailing zeros at scale 0. */
  private withScale(scale: number): Decimal {
    if (scale >= 0) {
      return new Decimal(this.unscaled, scale);
    }
    return new Decimal(this.unscaled * powerOfTen(-scale), 0);
  }
}

function parseDecimal(text: string): [bigint, number] {
  const match = DECIMAL_TEXT.exec(text);
  if (match === null) {
    throw new SyntaxError(`invalid decimal ${JSON.stringify(text)}`);
  }
  const [, sign, whole = "", fraction = ""] = match;
  const unscaled = BigInt(whole + fraction);
  return [sign === "-" ? -unscaled : unscaled, fraction.length];
}

function integerBigInt(value: number): bigint {
  if (!Number.isSafeInteger(value)) {
    throw new RangeError(
      `${String(value)} is not a safe integer; pass a string such as "2500.50"`,
    );
  }
  return BigInt(value);
}

function requireScale(scale: number): number {
  if (!Number.isSafeInteger(scale) || scale < 0) {
    throw new RangeError(`scale must be a non-negative integer, got ${scale}`);
  }
  return scale;
}

function requirePlaces(places: number): number {
  if (!Number.isSafeInteger(places)) {
    throw new RangeError(`places must be an integer, got ${places}`);
  }
  return places;
}

function powerOfTen(exponent: number): bigint {
  return 10n ** BigInt(exponent);
}

/** `numerator / denominator` rounded to an integer by `mode`. */
function divideRounded(
  numerator: bigint,
  denominator: bigint,
  mode: RoundingMode,
): bigint {
  const negative = numerator < 0n !== denominator < 0n;
  const [n, d] = [abs(numerator), abs(denominator)];
  const quotient = n / d;
  const remainder = n % d;
  const away =
    remainder !== 0n &&
    roundsAwayFromZero(mode, negative, quotient % 2n === 1n, remainder * 2n - d);
  const rounded = away ? quotient + 1n : quotient;
  return negative ? -rounded : rounded;
}

/**
 * Whether an inexact quotient moves away from zero. `pastHalf` is `2 * remainder - divisor`:
 * positive past the halfway point, 0n on a tie, negative before it.
 */
function roundsAwayFromZero(
  mode: RoundingMode,
  negative: boolean,
  odd: boolean,
  pastHalf: bigint,
): boolean {
  switch (mode) {
    case "DOWN":
      return false;
    case "UP":
      return true;
    case "FLOOR":
      return negative;
    case "CEILING":
      return !negative;
    case "HALF_UP":
      return pastHalf >= 0n;
    case "HALF_DOWN":
      return pastHalf > 0n;
    case "HALF_EVEN":
      return pastHalf > 0n || (pastHalf === 0n && odd);
  }
}

function abs(value: bigint): bigint {
  return value < 0n ? -value : value;
}
