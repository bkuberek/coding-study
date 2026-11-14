# The resolver

The sandbox's DNS. Your app has no network beyond its stack, so the names of this problem are resolved here, at `RESOLVER_URL`. `lookup` in `src/network.ts` asks it for you, and answers an IP address itself without asking.

## `GET /resolve?name=<host name>`

Answers 200 with every address the name has, in the order a resolver would give them:

```json
{"addresses": ["203.0.113.10"]}
```

A name it does not know answers 404 with `{"error": "no such host"}`.

| Name | Addresses |
|------|-----------|
| `localhost` | `127.0.0.1` and `::1` |
| `internal-admin` | `10.20.0.5`, a host on your company's private network |
| `inbox.partner.test` | `198.51.100.20`, the partner server |
| `intranet.attacker.test` | `10.20.0.5`: a name someone outside controls, pointed at your private network |
| `rebind.attacker.test` | `203.0.113.10`, unless a scenario says otherwise |
| `nowhere.test` | None: it answers 404 |

A name this table does not list usually resolves to `203.0.113.10`, the customer server, but not always: the graded cases use names of their own.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `rebinding` | `rebind.attacker.test` answers `203.0.113.10` the first time it is asked, then `10.20.0.5` every time after |
