# Chat System: Reference

## Requirements

Clarify before designing:

- **Ordering scope**: a total order per conversation, identical for every member. No order across conversations; that is what makes the system shardable by conversation.
- **Delivery semantics**: networks drop acks, so delivery is at least once; "never twice" is achieved by idempotent sends and deduplication, giving effectively-once display.
- **"Sent" is a durability promise**: acknowledge the sender only after the message is persisted on a quorum of replicas.
- **History model**: messages are stored durably for a year (needed for new devices), not deleted after delivery. That decides storage cost and the sync design.
- **Out of scope unless asked**: presence ("online now"), typing indicators, end-to-end encryption, very large broadcast channels. Each changes a specific part of the design; mention where.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Messages | 300 M x 50 | 15 B/day, ~175,000/s average, ~520,000/s peak |
| Recipients per message | 0.8 x 1 + 0.2 x 29 | ~6.6 |
| Deliveries | 175,000 x 6.6, x ~1.5 devices | ~1.2 M users/s, ~1.7 M device deliveries/s average, ~5 M/s peak |
| Message storage | 15 B x ~200 B (text plus ids, timestamps) | ~3 TB/day, ~1.1 PB/year before replication |
| Gateways | 100 M connections / ~500,000 per gateway (~10-20 KB each) | 200 minimum, ~400 with headroom for zone loss and deploys |
| Heartbeats | 100 M / 45 s | ~2 M/s, absorbed by gateways and never forwarded |

Group fan-out, not sending, dominates delivery work; storage, not compute, dominates cost.

## API

A persistent connection per device (WebSocket or MQTT over TLS); frames:

```text
client -> server
  send    {client_msg_id, conversation_id, body, attachment_ids}
  ack     {conversation_id, seq}                 delivered up to seq on this device
  read    {conversation_id, seq}                 read up to seq
server -> client
  sent    {client_msg_id, conversation_id, seq, server_ts}
  message {conversation_id, seq, msg_id, sender_id, body, server_ts}
  receipt {conversation_id, user_id, delivered_seq, read_seq}
```

HTTPS for everything that is not latency critical:

```text
GET  /v1/sync?token=<opaque>                       conversations changed since token, new token
GET  /v1/conversations/{id}/messages?after_seq=&limit=200
POST /v1/conversations {members: [...], title}     create a group
POST /v1/devices {push_token, platform}            register for push
```

## Data model

| Data | Store | Key | Notes |
|------|-------|-----|-------|
| Messages | wide-column, RF 3 | partition `(conversation_id, bucket)`, clustering `seq` | bucket = seq / 10,000 keeps busy groups from building huge partitions; 1-year TTL |
| Dedup | same store, TTL 7 days | `(conversation_id, client_msg_id)` | maps a retry to its original seq |
| Conversations | relational or key-value | `conversation_id` | type, title, member list (groups), `last_seq` |
| Membership index | key-value | `user_id -> conversation_id -> (last_seq, updated_at)` | drives sync; one upsert per member per message |
| Receipts | key-value | `(conversation_id, user_id)` | `delivered_seq`, `read_seq`: watermarks, not one row per message |
| Device cursors | key-value | `(user_id, device_id)` | last sync token, push token |
| Session registry | replicated in-memory, TTL refreshed by heartbeat | `user_id -> [(device_id, gateway_id)]` | where each connected device is |

## High-level design

```text
device <--TLS--> L4 load balancer <--> connection gateway (stateful: sockets, heartbeats)
                                          | register device in session registry
                                          v
                               chat service, sharded by conversation_id
                                 1. dedup (conversation_id, client_msg_id)
                                 2. assign seq (single writer per conversation)
                                 3. persist message on quorum --> ack "sent" to sender
                                 4. upsert membership index for each member
                                 5. route: session registry --> recipient gateways (online devices)
                                                            --> push queue --> APNs / FCM (offline devices)
devices --> ack/read frames --> receipt service --> watermarks --> receipt frames to sender
```

- **Gateways** are dumb pipes with state: they terminate connections, authenticate, track heartbeats and forward frames. Business logic lives in the stateless-per-request chat service, so gateways rarely need redeploying.
- **Chat service** instances own ranges of conversations through leases (consistent hashing plus a lease with an epoch number). The owner is the only writer of seq for its conversations.
- **Routing to recipients**: the owner looks up each member's devices in the session registry and sends the frame to those gateways; anything not acknowledged by a device within a timeout is left for sync, never retried forever.

## Deep dives

### Ordering and idempotency

- The client creates `client_msg_id` once per message and reuses it on every retry. The conversation owner checks the dedup table first, so a retry returns the original seq and is never stored twice.
- Seq is assigned by the single owner: an in-memory counter initialized from the highest persisted seq when the lease is acquired. Every member orders by seq, so the order is identical everywhere regardless of arrival order.
- Clients detect gaps (they hold 41 and receive 43) and fetch the missing range; they deduplicate by `(conversation_id, seq)`.
- Split brain: an old owner whose lease expired could keep assigning seqs. Writes carry the lease epoch and the store rejects writes from an older epoch for that conversation range (fencing).

### Connection gateways

- 500,000 mostly idle connections per gateway is feasible with an event-driven server; memory per connection (TLS state, buffers) is the limit.
- Deploys and failures cause reconnect storms: drain gateways a few percent at a time, send clients a reconnect hint with a random delay, and have clients reconnect with exponential backoff and jitter.
- Slow consumers: bounded per-connection send queues; when a queue fills, drop the connection and let the device resync rather than buffering unboundedly.

### Receipts as watermarks

- Store `delivered_seq` and `read_seq` per member per conversation; one row update acknowledges everything up to that seq. Per-message receipt rows would multiply writes by members and messages.
- Coalesce: a device reading 50 messages sends one read frame with the highest seq; the receipt service batches updates for a few hundred milliseconds before fanning them out.
- Groups: "read by all" is `min(read_seq)` over members; for large groups show counts ("read by 37") computed on demand.

### Offline sync and multiple devices

- Each device keeps a sync token. On reconnect it calls `/v1/sync`: the server reads the membership index for conversations updated after the token, returns them with their `last_seq`, and the device fetches messages after its local seq per conversation, newest conversations first.
- A new device has no local seqs and pages history lazily, starting with recent conversations.
- Delivered status counts a recipient as delivered when any of their devices acks; each device still syncs independently.

### Group fan-out

- Write the message once in the conversation partition; fan out only notifications and membership-index upserts (at most 500 per message).
- For 500-member groups at peak, batch registry lookups and group sends by gateway, so one frame per gateway carries all of that gateway's recipients.
- Broadcast channels with tens of thousands of members would switch to pull: no per-member upserts, clients poll or subscribe to the channel.

## Failure modes

| Failure | What happens | Recovery |
|---------|--------------|----------|
| Sender loses the "sent" ack | Client retries with the same `client_msg_id` | Dedup returns the original seq; no duplicate |
| Chat service owner crashes after persisting, before routing | Recipients not notified | Recipients get it on next sync; push queue fed from an outbox written with the message |
| Gateway crashes | Its devices disconnect | Devices reconnect elsewhere with jittered backoff and sync; unacked messages are redelivered by sync |
| Session registry stale | Frames sent to a dead gateway | No device ack within timeout; message stays for sync; push sent if the device is offline |
| Message store replica down | Writes continue on quorum | Hinted handoff and repair |
| Region outage | Users homed there disconnect | Fail over to another region with replicated data; asynchronous cross-region replication can lose the last seconds (state the RPO), or use synchronous replication for "sent" at a latency cost |
| Lease expiry during a pause (garbage collection) | Two owners | Epoch fencing rejects the stale owner's writes |

## Trade-offs

- **Durable history versus store-and-forward**: keeping messages a year enables new devices and server-side history at petabyte-scale storage cost; deleting after delivery is cheaper and more private but makes multi-device sync much harder.
- **Write once per conversation versus per-recipient inbox copies**: one write keeps storage proportional to messages; the membership index adds small per-member upserts so sync does not scan every conversation.
- **Single writer per conversation versus a distributed counter**: simple, ordered and fast, but the owner is a hot spot for a very busy conversation; acceptable at 500 members.
- **Push versus pull**: push to online devices for latency; pull (sync) for correctness. Every delivery path can fail, and sync is the safety net.
- **Consistency**: per-conversation linearizable seq assignment; everything else (receipts, membership index, push) is eventually consistent.

## Observability and cost

- Send-to-sent latency, send-to-delivered latency p50/p99, dedup hit rate (retry volume), gap-fetch rate from clients (lost real-time deliveries), connections per gateway, reconnect rate, push delivery success per platform, sync payload size, lease handovers.
- Cost: message storage (about 1 PB per year before replication, about 3 PB with RF 3) dominates; compress, tier messages older than 30 days to cheaper storage, and enforce the one-year TTL. Gateways are the second line item.

## Evolution

- End-to-end encryption: the server stores ciphertext, cannot search or moderate content, and must manage per-device keys; push notifications carry no content.
- Presence and typing indicators: ephemeral, high-volume, never persisted; publish through gateways with aggressive coalescing.
- Edits and deletes as new events with their own seq that clients apply to earlier messages.
- Server-side search (not possible with end-to-end encryption) and large broadcast channels with a pull model.
