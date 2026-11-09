# Your company's private network

Your app must never reach this server. It plays every address of the sandbox that is not one of the public hosts in `src/network.ts`: loopback, the private ranges, link-local, the cloud metadata address `169.254.169.254`, and the rest. A request here is a request a customer's URL tricked your dispatcher into sending, so the graded cases count them and expect none.

## `POST /admin` and `POST /metadata/credentials`

Answer 200 with something no customer should ever see. Any other path answers 404, and every request counts, whatever its path.
