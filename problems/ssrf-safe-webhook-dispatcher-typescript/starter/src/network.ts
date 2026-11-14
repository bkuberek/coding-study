// The sandbox's stand-in for the internet. Your app has no network beyond its stack, so the names
// and addresses of this problem live here, and mock servers play the hosts behind them.
//
// In production, `lookup` would be the system's resolver and a request would go to the address
// itself. Here `lookup` asks the `resolver` mock server, and `originFor` says which mock server
// plays an address. You should not need to change this file.

import { isIP } from "node:net";

/** The public hosts of this sandbox's internet, and the mock server that plays each. */
const PUBLIC_HOSTS: ReadonlyMap<string, string> = new Map([
  ["203.0.113.10", "http://customer-hooks:8080"],
  ["198.51.100.20", "http://partner-hooks:8080"],
  ["172.32.0.10", "http://partner-hooks:8080"],
]);

/** Every other address leads into your company's own network, which `internal-admin` plays. */
const PRIVATE_NETWORK = "http://internal-admin:8080";

const MAPPED_IPV4 = /^::ffff:([0-9a-f]{1,4}):([0-9a-f]{1,4})$/;

export class HostNotFound extends Error {
  constructor(hostname: string) {
    super(`${hostname} does not resolve`);
    this.name = "HostNotFound";
  }
}

/**
 * Every address `hostname` resolves to, in the order a system resolver gives them. An IP address
 * is its own answer, in any form a resolver reads, so `2130706433`, `0x7f.1` and `127.1` all answer
 * `127.0.0.1`. A name is asked of the resolver mock server, and one it does not know throws
 * `HostNotFound`. `hostname` may keep the brackets a URL puts around an IPv6 address.
 */
export async function lookup(hostname: string): Promise<string[]> {
  const host = canonicalHost(hostname);
  if (isIP(host) !== 0) {
    return [host];
  }
  const response = await fetch(
    `${process.env.RESOLVER_URL}/resolve?name=${encodeURIComponent(host)}`,
  );
  if (response.status === 404) {
    throw new HostNotFound(host);
  }
  if (!response.ok) {
    throw new Error(`the resolver answered ${response.status} for ${host}`);
  }
  const answer = (await response.json()) as { addresses: string[] };
  return answer.addresses;
}

/**
 * The base URL that reaches `address` in the sandbox, such as `http://customer-hooks:8080`. A
 * request sent there, with the path and query of the URL you deliver to, stands for a connection
 * to `address`, whatever the URL's scheme and port: the sandbox has no TLS, and its mock servers
 * listen on one port. An IPv4-mapped IPv6 address reaches the IPv4 address inside it, as it would
 * on a real network.
 */
export function originFor(address: string): string {
  return PUBLIC_HOSTS.get(asIPv4IfMapped(address)) ?? PRIVATE_NETWORK;
}

function canonicalHost(hostname: string): string {
  const bare =
    hostname.startsWith("[") && hostname.endsWith("]") ? hostname.slice(1, -1) : hostname;
  return isIP(bare) !== 0 ? bare : new URL(`http://${bare}`).hostname;
}

function asIPv4IfMapped(address: string): string {
  if (isIP(address) !== 6) {
    return address;
  }
  const compact = new URL(`http://[${address}]`).hostname.slice(1, -1);
  const mapped = MAPPED_IPV4.exec(compact);
  if (mapped === null) {
    return address;
  }
  const high = parseInt(mapped[1], 16);
  const low = parseInt(mapped[2], 16);
  return [high >> 8, high & 255, low >> 8, low & 255].join(".");
}
