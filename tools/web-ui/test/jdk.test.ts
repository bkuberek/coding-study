import assert from "node:assert/strict";
import { test } from "node:test";

import { jdkRefusal, jdkRefusals, rangeText, type JdkRange, type SelectedJdk } from "../src/page/jdk.ts";

const DEFAULT_RANGE: JdkRange = { min: 21, max: 26 };

function selected(feature: number, supported = feature >= 21 && feature <= 26, source = "JAVA_HOME"): SelectedJdk {
  return { version: `${feature}.0.1`, feature, source, supported };
}

test("a range reads as its two releases", () => {
  assert.equal(rangeText({ min: 21, max: 26 }), "JDK 21 to 26");
});

test("a range of one release reads as that release", () => {
  assert.equal(rangeText({ min: 24, max: 24 }), "JDK 24");
});

test("a JDK inside the range runs the problem", () => {
  assert.equal(jdkRefusal("two-sum", "java", selected(26), DEFAULT_RANGE), null);
});

test("the bounds of a range are inside it", () => {
  const range = { min: 22, max: 24 };
  assert.deepEqual([22, 24].map((feature) => jdkRefusal("two-sum", "java", selected(feature), range)), [null, null]);
});

test("a JDK above the supported range is not supported yet, in the words of cstudy start", () => {
  assert.equal(
    jdkRefusal("two-sum", "java", selected(27), DEFAULT_RANGE),
    "two-sum runs its java version on JDK 21 to 26; JAVA_HOME selects JDK 27, which cstudy does not support yet",
  );
});

test("a JDK below the range is too old", () => {
  assert.equal(
    jdkRefusal("virtual-gatherers", "kotlin", selected(23), { min: 24, max: 26 }),
    "virtual-gatherers runs its kotlin version on JDK 24 to 26; JAVA_HOME selects JDK 23, which is too old",
  );
});

test("a supported JDK above the problem's own maximum is newer than the problem supports", () => {
  assert.equal(
    jdkRefusal("old-api", "java", selected(26), { min: 21, max: 25 }),
    "old-api runs its java version on JDK 21 to 25; JAVA_HOME selects JDK 26, which is newer than the problem supports",
  );
});

test("the source of the JDK is named as the CLI names it", () => {
  assert.match(jdkRefusal("two-sum", "java", selected(27, false, "PATH"), DEFAULT_RANGE) ?? "", /; PATH selects JDK 27,/);
});

test("without a JDK nothing runs", () => {
  assert.equal(
    jdkRefusal("two-sum", "java", null, DEFAULT_RANGE),
    "two-sum runs its java version on JDK 21 to 26; no JDK was found",
  );
});

test("a JDK below the supported range is too old even though it is not supported", () => {
  assert.match(jdkRefusal("two-sum", "java", selected(17), DEFAULT_RANGE) ?? "", /, which is too old$/);
});

test("a language but Java and Kotlin takes no JDK", () => {
  assert.equal(jdkRefusal("two-sum", "python", selected(27), DEFAULT_RANGE), null);
});

test("a problem without Java and Kotlin has no range to miss", () => {
  assert.equal(jdkRefusal("two-sum", "java", null, null), null);
});

test("only the Java and Kotlin of a problem are refused", () => {
  const refused = jdkRefusals("two-sum", ["python", "typescript", "java", "kotlin"], selected(27), DEFAULT_RANGE);
  assert.deepEqual([...refused.keys()], ["java", "kotlin"]);
});

test("each refused language gets the refusal that names it", () => {
  const refused = jdkRefusals("two-sum", ["java", "kotlin"], selected(27), DEFAULT_RANGE);
  assert.match(refused.get("kotlin") ?? "", /^two-sum runs its kotlin version on /);
});

test("a JDK that runs the problem refuses none of its languages", () => {
  assert.equal(jdkRefusals("two-sum", ["python", "java", "kotlin"], selected(21), DEFAULT_RANGE).size, 0);
});
