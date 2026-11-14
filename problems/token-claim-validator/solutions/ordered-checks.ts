const SINGLE_VALUED = ["iss", "exp", "nbf"];
const TIMESTAMPS = ["exp", "nbf"];
const REQUIRED = ["iss", "aud", "exp"];
// Number() and parseInt() both accept more than digits, so the text is checked before parsing.
const WHOLE_SECONDS = /^[0-9]+$/;

function isMalformed(valuesOf: Map<string, string[]>): boolean {
  if (SINGLE_VALUED.some((name) => valuesOf.has(name) && valuesOf.get(name)!.length !== 1)) {
    return true;
  }
  if (valuesOf.has("aud") && valuesOf.get("aud")!.length === 0) {
    return true;
  }
  return TIMESTAMPS.some(
    (name) => valuesOf.has(name) && !WHOLE_SECONDS.test(valuesOf.get(name)![0]),
  );
}

export function validateClaims(
  claims: string[][],
  now: number,
  clockSkewSeconds: number,
  expectedIssuer: string,
  expectedAudience: string,
  requiredScopes: string[],
): string {
  const valuesOf = new Map<string, string[]>();
  for (const [name, ...values] of claims) {
    if (valuesOf.has(name)) {
      return "malformed-claim";
    }
    valuesOf.set(name, values);
  }
  if (isMalformed(valuesOf)) {
    return "malformed-claim";
  }
  if (REQUIRED.some((name) => !valuesOf.has(name))) {
    return "missing-claim";
  }
  if (valuesOf.get("iss")![0] !== expectedIssuer) {
    return "wrong-issuer";
  }
  if (!valuesOf.get("aud")!.includes(expectedAudience)) {
    return "wrong-audience";
  }
  if (now >= Number(valuesOf.get("exp")![0]) + clockSkewSeconds) {
    return "expired";
  }
  if (valuesOf.has("nbf") && now + clockSkewSeconds < Number(valuesOf.get("nbf")![0])) {
    return "not-yet-valid";
  }
  const granted = new Set(valuesOf.get("scope") ?? []);
  if (requiredScopes.some((scope) => !granted.has(scope))) {
    return "insufficient-scope";
  }
  return "ok";
}
