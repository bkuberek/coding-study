/**
 * What a code-intelligence session is, and what each way its socket closes means for it
 * (docs/specs/web-ui.md#sessions). Shared by the page, which draws the status bar segment, and by
 * the code-intelligence chunk, which owns the sessions.
 */

export type SessionState =
  | { readonly kind: "starting" }
  | { readonly kind: "ready" }
  | { readonly kind: "reconnecting" }
  /** `why` is the short cause the status bar names ("exit 1"); `reason` the whole close reason. */
  | { readonly kind: "stopped"; readonly why: string; readonly reason: string }
  /** A service project's server cannot start yet: Docker does not answer, or the sidecar's image is not here. Nothing failed. */
  | { readonly kind: "needs-docker"; readonly why: string; readonly reason: string };

export type CloseOutcome =
  /** The page closed the session itself. */
  | { readonly kind: "gone" }
  | { readonly kind: "stopped"; readonly why: string; readonly reason: string }
  | { readonly kind: "needs-docker"; readonly why: string; readonly reason: string }
  /** The connection dropped or the handshake was refused: try again. */
  | { readonly kind: "retry" };

/** The wait before each try after a connection that dropped; a fourth failure gives up. */
export const RECONNECT_DELAYS_MS: readonly number[] = [1000, 2000, 5000];

const NORMAL = 1000;
const SERVER_EXITED = 4002;
const SESSION_LIMIT = 4003;
const NEEDS_DOCKER = 4004;
const STOPS_WITHOUT_CAUSE: ReadonlySet<number> = new Set([1001, 1003, 1008, 1009]);

/** The delay before the try after `failures` failures in a row; null once the tries are spent. */
export function retryDelay(failures: number): number | null {
  return RECONNECT_DELAYS_MS[failures] ?? null;
}

/** What the close code and reason of a session's socket mean, as the spec's table says. */
export function closeOutcome(code: number, reason: string): CloseOutcome {
  if (code === NORMAL) return { kind: "gone" };
  if (code === SERVER_EXITED) return { kind: "stopped", why: causeOf(reason), reason };
  if (code === SESSION_LIMIT) return { kind: "stopped", why: "4 sessions running", reason };
  if (code === NEEDS_DOCKER) return { kind: "needs-docker", why: causeOf(reason), reason };
  if (STOPS_WITHOUT_CAUSE.has(code)) return { kind: "stopped", why: "", reason };
  return { kind: "retry" };
}

/** `exit 1` of `exit 1: Error: …`, `cannot start` of `cannot start: node not found`, `needs the node image` of
 * `needs the node image: docker pull …`. */
function causeOf(reason: string): string {
  const colon = reason.indexOf(":");
  return (colon < 0 ? reason : reason.slice(0, colon)).trim();
}
