// A link anyone may follow, for a while. It carries the file's id and the second it expires,
// signed with a key only this service holds, so changing either one breaks the signature.

import { createHmac, timingSafeEqual } from "node:crypto";

import { LINK_SIGNING_KEY } from "./config.ts";

export type Link = { url: string; expires: number };
export type LinkCheck = "valid" | "invalid" | "expired";

const EXPIRES = /^[1-9]\d{0,11}$/;
const SIGNATURE = /^[0-9a-f]{64}$/;

function signature(id: string, expires: string): Buffer {
  return createHmac("sha256", LINK_SIGNING_KEY).update(`${id}.${expires}`).digest();
}

export function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

export function linkTo(id: string, expires: number): Link {
  const sig = signature(id, String(expires)).toString("hex");
  return { url: `/shared/${id}?expires=${expires}&sig=${sig}`, expires };
}

/** The signature first, so a forged link learns nothing, not even whether it expired. */
export function checkLink(
  id: string,
  expires: string | null,
  sig: string | null,
  now: number,
): LinkCheck {
  if (expires === null || sig === null || !EXPIRES.test(expires) || !SIGNATURE.test(sig)) {
    return "invalid";
  }
  // Compares every byte whatever the first difference, so the time taken tells nothing.
  if (!timingSafeEqual(Buffer.from(sig, "hex"), signature(id, expires))) {
    return "invalid";
  }
  return now < Number(expires) ? "valid" : "expired";
}
