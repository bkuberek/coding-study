// Which addresses a webhook must never reach: your own host, your private network, and the
// addresses every cloud machine can reach but no customer should make it reach.

import { BlockList, isIP } from "node:net";

const INTERNAL_IPV4: ReadonlyArray<readonly [string, number]> = [
  ["0.0.0.0", 8], // "this network": a connection to 0.0.0.0 reaches the host itself
  ["10.0.0.0", 8],
  ["100.64.0.0", 10], // shared address space, behind a carrier's NAT
  ["127.0.0.0", 8],
  ["169.254.0.0", 16], // link-local, where the cloud metadata address lives
  ["172.16.0.0", 12],
  ["192.168.0.0", 16],
  ["224.0.0.0", 4], // multicast
  ["240.0.0.0", 4], // reserved, and the broadcast address
];

const INTERNAL_IPV6: ReadonlyArray<readonly [string, number]> = [
  ["::", 128],
  ["::1", 128],
  ["fc00::", 7], // unique local
  ["fe80::", 10], // link-local
  ["ff00::", 8], // multicast
];

const internal = new BlockList();
for (const [network, prefix] of INTERNAL_IPV4) {
  internal.addSubnet(network, prefix, "ipv4");
}
for (const [network, prefix] of INTERNAL_IPV6) {
  internal.addSubnet(network, prefix, "ipv6");
}

/**
 * Whether `address` is one a webhook must not reach. A `BlockList` checks an IPv4-mapped IPv6
 * address (`::ffff:127.0.0.1`) against the IPv4 ranges too, as a socket would connect to it. What
 * is not an address cannot be checked, so it is refused.
 */
export function isInternal(address: string): boolean {
  const family = isIP(address);
  if (family === 0) {
    return true;
  }
  return internal.check(address, family === 4 ? "ipv4" : "ipv6");
}
