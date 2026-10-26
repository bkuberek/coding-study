# Chat System: Rubric

## Requirements and scope

- [ ] Scopes ordering to a single conversation and uses that to shard by conversation.
- [ ] States at-least-once delivery with deduplication instead of claiming exactly-once delivery.
- [ ] Defines "sent" as persisted on a quorum before acknowledging the sender.
- [ ] Clarifies the history model (durable for a year versus delete after delivery) and its consequences.
- [ ] Names out-of-scope features (presence, typing, end-to-end encryption, broadcast channels).

## Estimates

- [ ] Derives about 175,000 messages/s average and over 500,000/s peak.
- [ ] Computes delivery fan-out including group members and multiple devices.
- [ ] Sizes storage at terabytes per day and about a petabyte per year.
- [ ] Sizes the gateway fleet from connections per server and plans headroom for zone loss and deploys.

## API and data model

- [ ] Uses a persistent connection for real-time frames and HTTPS for sync and history.
- [ ] Includes a client-generated message id for idempotent retries.
- [ ] Keys messages by conversation and seq, with bucketing to bound partition size.
- [ ] Models receipts as per-member watermarks rather than per-message rows.
- [ ] Has a structure that makes sync efficient (membership index or per-user inbox) and explains its write cost.

## High-level design

- [ ] Separates stateful connection gateways from the chat service.
- [ ] Uses a session registry to route messages to the gateways of online devices.
- [ ] Sends push notifications for offline devices through a queue.
- [ ] Explains the end-to-end send flow: dedup, seq, persist, ack, route.

## Deep dives

- [ ] Assigns seq with a single writer per conversation and fences stale owners (lease epochs).
- [ ] Has clients detect gaps and fetch missing ranges.
- [ ] Handles reconnect storms (gradual drains, jittered backoff) and slow consumers (bounded queues).
- [ ] Coalesces receipts and computes group read status from watermarks.
- [ ] Designs offline and new-device sync with tokens and per-conversation cursors.
- [ ] Writes group messages once and fans out only notifications and index updates.

## Failure modes and trade-offs

- [ ] Walks through a lost ack and shows the retry does not duplicate.
- [ ] Covers a crash between persisting and routing (outbox or sync as the safety net).
- [ ] Covers gateway loss and region loss, stating the recovery point for region failover.
- [ ] Discusses durable history versus store-and-forward, and per-conversation storage versus per-recipient copies.

## Operations and evolution

- [ ] Names key metrics: send-to-delivered latency, retry and gap-fetch rates, reconnect rate, push success.
- [ ] Identifies message storage as the dominant cost and proposes tiering or compression.
- [ ] Explains what end-to-end encryption would change (no server-side search, per-device keys, contentless push).
