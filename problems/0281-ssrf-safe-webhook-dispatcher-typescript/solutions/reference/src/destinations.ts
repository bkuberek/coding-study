// Where a request may go: the host's addresses, looked up once and every one of them checked.

import { isInternal } from "./addresses.ts";
import { HostNotFound, lookup } from "./network.ts";

export type Refusal = "unresolvable_host" | "blocked_destination";

export type Destination = { address: string } | { refusal: Refusal };

/**
 * Looks `url`'s host up once and checks every address it has. The caller connects to `address`,
 * the one checked, and never looks the name up again for that request: a second lookup is a second
 * answer, and the name's owner chooses it.
 */
export async function resolveDestination(url: URL): Promise<Destination> {
  let addresses: string[];
  try {
    addresses = await lookup(url.hostname);
  } catch (error) {
    if (error instanceof HostNotFound) {
      return { refusal: "unresolvable_host" };
    }
    throw error;
  }
  const [first] = addresses;
  if (first === undefined) {
    return { refusal: "unresolvable_host" };
  }
  if (addresses.some((address) => isInternal(address))) {
    return { refusal: "blocked_destination" };
  }
  return { address: first };
}
