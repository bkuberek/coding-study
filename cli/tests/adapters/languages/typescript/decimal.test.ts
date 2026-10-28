// The Decimal class of runners/typescript/support.ts, run by test_typescript_decimal.py with
// `node --test`. Rounding follows Python's decimal module and Java's BigDecimal.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { Decimal } from "../../../../../runners/typescript/support.ts";

function dec(text: string): Decimal {
  return new Decimal(text);
}

describe("construction", () => {
  it("keeps the scale of a string", () => {
    const value = dec("2500.00");
    assert.deepEqual([value.unscaled, value.scale], [250000n, 2]);
  });

  it("reads a negative string", () => {
    assert.deepEqual([dec("-0.50").unscaled, dec("-0.50").scale], [-50n, 2]);
  });

  it("reads an integer number with scale 0", () => {
    const value = new Decimal(42);
    assert.deepEqual([value.unscaled, value.scale], [42n, 0]);
  });

  it("reads a bigint as the unscaled value with an optional scale", () => {
    const value = new Decimal(12345n, 2);
    assert.equal(value.toString(), "123.45");
    assert.equal(new Decimal(7n).toString(), "7");
  });

  it("copies another Decimal", () => {
    assert.equal(new Decimal(dec("1.10")).toString(), "1.10");
  });

  it("accepts leading zeros like BigDecimal and Decimal do", () => {
    assert.equal(dec("007.50").toString(), "7.50");
  });

  const malformed = ["", " 1", "1 ", "+1", "1e3", ".5", "5.", "1.2.3"];
  for (const text of [...malformed, "abc", "-", "1_0", "NaN"]) {
    it(`rejects the string ${JSON.stringify(text)}`, () => {
      assert.throws(() => dec(text), SyntaxError);
    });
  }

  for (const value of [1.5, Number.NaN, Number.POSITIVE_INFINITY, 2 ** 60]) {
    it(`rejects the number ${String(value)} and asks for a string`, () => {
      assert.throws(() => new Decimal(value), RangeError);
    });
  }

  it("rejects a negative or fractional scale", () => {
    assert.throws(() => new Decimal(1n, -1), RangeError);
    assert.throws(() => new Decimal(1n, 1.5), RangeError);
  });

  it("is immutable", () => {
    assert.ok(Object.isFrozen(dec("1")));
  });
});

describe("toString", () => {
  const cases: [string, string][] = [
    ["2500.00", "2500.00"],
    ["0", "0"],
    ["0.00", "0.00"],
    ["-0.05", "-0.05"],
    ["0.001", "0.001"],
    [
      "123456789012345678901234567890.123456789",
      "123456789012345678901234567890.123456789",
    ],
    ["-7", "-7"],
  ];
  for (const [text, expected] of cases) {
    it(`prints ${text} with its scale`, () => {
      assert.equal(dec(text).toString(), expected);
    });
  }

  it("never prints a negative zero", () => {
    assert.equal(dec("-0.00").toString(), "0.00");
  });
});

describe("arithmetic", () => {
  it("adds across scales and keeps the larger scale", () => {
    assert.equal(dec("1.5").plus(dec("2.25")).toString(), "3.75");
    assert.equal(dec("1.50").plus(dec("2.2")).scale, 2);
  });

  it("subtracts into negative values", () => {
    assert.equal(dec("1.5").minus(dec("2.25")).toString(), "-0.75");
  });

  it("multiplies and adds the scales", () => {
    assert.equal(dec("1.50").times(dec("2.0")).toString(), "3.000");
    assert.equal(dec("-1.5").times(dec("-2")).toString(), "3.0");
  });

  it("does not lose precision beyond 28 digits", () => {
    const big = dec("9999999999999999999999999999.99");
    assert.equal(
      big.plus(dec("0.01")).toString(),
      "10000000000000000000000000000.00",
    );
  });

  it("leaves its operands unchanged", () => {
    const a = dec("1.5");
    a.plus(dec("1")).times(dec("3"));
    assert.equal(a.toString(), "1.5");
  });

  it("negates and takes the absolute value", () => {
    assert.equal(dec("1.50").neg().toString(), "-1.50");
    assert.equal(dec("-1.50").abs().toString(), "1.50");
    assert.equal(dec("-1.50").neg().toString(), "1.50");
    assert.equal(dec("0.0").neg().toString(), "0.0");
  });
});

describe("division", () => {
  it("rounds to the requested scale", () => {
    assert.equal(dec("1").div(dec("3"), 4, "HALF_UP").toString(), "0.3333");
    assert.equal(dec("2").div(dec("3"), 4, "HALF_UP").toString(), "0.6667");
    assert.equal(dec("10").div(dec("4"), 0, "HALF_UP").toString(), "3");
  });

  it("divides decimals with different scales", () => {
    assert.equal(dec("1.50").div(dec("0.5"), 2, "HALF_UP").toString(), "3.00");
    assert.equal(
      dec("100").div(dec("0.003"), 2, "HALF_UP").toString(),
      "33333.33",
    );
  });

  it("breaks ties up with HALF_UP and to the even digit with HALF_EVEN", () => {
    assert.equal(dec("0.125").div(dec("1"), 2, "HALF_UP").toString(), "0.13");
    assert.equal(dec("0.125").div(dec("1"), 2, "HALF_EVEN").toString(), "0.12");
    assert.equal(dec("0.135").div(dec("1"), 2, "HALF_EVEN").toString(), "0.14");
    assert.equal(dec("5").div(dec("2"), 0, "HALF_EVEN").toString(), "2");
    assert.equal(dec("7").div(dec("2"), 0, "HALF_EVEN").toString(), "4");
  });

  it("rounds ties away from zero for negative values with HALF_UP", () => {
    assert.equal(dec("-0.125").div(dec("1"), 2, "HALF_UP").toString(), "-0.13");
    assert.equal(dec("0.125").div(dec("-1"), 2, "HALF_UP").toString(), "-0.13");
    assert.equal(
      dec("-0.125").div(dec("1"), 2, "HALF_EVEN").toString(),
      "-0.12",
    );
  });

  it("never prints a negative zero", () => {
    assert.equal(dec("-0.001").div(dec("1"), 2, "HALF_UP").toString(), "0.00");
  });

  it("rejects a zero divisor", () => {
    assert.throws(() => dec("1").div(dec("0.00"), 2, "HALF_UP"), RangeError);
  });
});

describe("rounding", () => {
  it("rounds to a smaller scale", () => {
    assert.equal(dec("2.675").round(2, "HALF_UP").toString(), "2.68");
    assert.equal(dec("2.665").round(2, "HALF_UP").toString(), "2.67");
    assert.equal(dec("2.665").round(2, "HALF_EVEN").toString(), "2.66");
    assert.equal(dec("2.675").round(2, "HALF_EVEN").toString(), "2.68");
    assert.equal(dec("-2.665").round(2, "HALF_EVEN").toString(), "-2.66");
    assert.equal(dec("0.5").round(0, "HALF_UP").toString(), "1");
    assert.equal(dec("0.5").round(0, "HALF_EVEN").toString(), "0");
  });

  it("rounds only when the dropped digits reach half", () => {
    assert.equal(dec("2.6749999").round(2, "HALF_UP").toString(), "2.67");
    assert.equal(dec("2.6750001").round(2, "HALF_EVEN").toString(), "2.68");
  });

  it("extends a smaller scale with zeros", () => {
    assert.equal(dec("1.5").round(3, "HALF_UP").toString(), "1.500");
    assert.equal(dec("7").round(2, "HALF_EVEN").toString(), "7.00");
  });

  it("formats with toFixed, which defaults to HALF_UP", () => {
    assert.equal(dec("1.005").toFixed(2), "1.01");
    assert.equal(dec("1.005").toFixed(2, "HALF_EVEN"), "1.00");
    assert.equal(dec("1.5").toFixed(0), "2");
    assert.equal(dec("1.5").toFixed(), "1.5");
  });
});

describe("comparison", () => {
  it("compares by value, not by scale", () => {
    assert.ok(dec("1.50").eq(dec("1.5")));
    assert.equal(dec("1.50").cmp(dec("1.5")), 0);
    assert.ok(!dec("1.51").eq(dec("1.5")));
  });

  it("orders values", () => {
    assert.equal(dec("1").cmp(dec("1.01")), -1);
    assert.equal(dec("-1").cmp(dec("-1.01")), 1);
    assert.ok(dec("1").lt(dec("2")));
    assert.ok(dec("2").lte(dec("2.0")));
    assert.ok(dec("3").gt(dec("2.99")));
    assert.ok(dec("2").gte(dec("2.00")));
    assert.ok(!dec("2").gt(dec("2")));
    assert.ok(!dec("2").lt(dec("2")));
  });

  it("treats positive and negative zero alike", () => {
    assert.ok(dec("0.00").eq(dec("-0")));
  });
});
