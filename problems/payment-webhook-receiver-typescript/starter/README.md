# Payment Webhook Receiver

An online shop takes card payments through a payment provider, which tells it what happened to each order's payment by signed webhooks. This is the start of the service that receives them and keeps each order's state.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with the provider's events API, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario payment-provider=outage` | The same, with the events API misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready.

## What it reads

| Variable | Holds |
|----------|-------|
| `PORT` | The port to listen on |
| `PAYMENT_PROVIDER_URL` | Where the provider's events API answers |
| `WEBHOOK_SECRET` | The secret the provider signs each delivery with. A fake: nothing here reaches a real provider |
| `CLOCK_NOW` | The sandbox's frozen time, in whole seconds since the Unix epoch, read through `src/clock.ts` |

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/orders.ts` | `OrderBook`: each order's state, in memory |
| `src/events.ts` | `PaymentEvent`: the shape of an event |
| `src/clock.ts` | `nowSeconds()`: the time your app should use |
| `tests/` | Your tests, with `tests/provider.ts` to sign and send a delivery, and to set a scenario on the events API |
| `vendors/payment-provider/API.md` | The provider's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
