# Video Streaming: Rubric

## Requirements and scope

- [ ] Splits the problem into processing, delivery and counting, each with its own requirements.
- [ ] Interprets "playable within 10 minutes" as low renditions first.
- [ ] Treats delivery cost as a first-class requirement.
- [ ] Names what is out of scope (live, search, recommendations, ads, DRM).

## Estimates

- [ ] Estimates upload volume (hundreds of terabytes per day) and yearly storage growth.
- [ ] Estimates delivery bandwidth in terabits per second from concurrent viewers and bitrate.
- [ ] Compares delivery volume with upload volume and draws the cost conclusion.
- [ ] Estimates transcoding compute in vCPUs.
- [ ] Estimates player event volume for counting.

## API and data model

- [ ] Uses resumable multipart uploads directly to object storage with signed URLs.
- [ ] Returns a signed manifest URL and serves segments from the CDN.
- [ ] Models videos with a status lifecycle and renditions as separate records.
- [ ] Keeps segments immutable with deterministic paths.

## High-level design

- [ ] Drives processing with a durable workflow (probe, chunk, transcode, package, thumbnails, moderation, publish).
- [ ] Shows a tiered delivery network (edge, shield, origin).
- [ ] Sends player events through a stream pipeline to counters and analytics, not to the database per view.

## Deep dives

- [ ] Explains chunked parallel encoding and why it bounds processing time.
- [ ] Orders work (low renditions first, premium codecs by popularity) and justifies it with cost.
- [ ] Makes tasks idempotent and handles preemption and poison inputs.
- [ ] Explains adaptive bitrate, segment length trade-offs and one packaging format for HLS and DASH.
- [ ] Handles the head (pre-positioning, provider-embedded caches) and the tail (shield, collapsing) differently.
- [ ] Keeps private videos private with signed URLs or tokens while staying cacheable.
- [ ] Counts views per session with deduplication, aggregation and fraud filtering.
- [ ] Plans storage tiering for originals and rarely watched renditions.

## Failure modes and trade-offs

- [ ] Covers interrupted uploads, worker loss, partial publish and viral stampedes.
- [ ] Uses multiple CDNs for failover and cost.
- [ ] Discusses eager versus lazy encoding and exact versus validated counts.

## Operations and evolution

- [ ] Measures quality of experience from the player (startup time, rebuffer ratio, bitrate, failures) by CDN, ISP and device.
- [ ] Tracks time from upload to playable and cache hit ratio by bytes.
- [ ] Ranks cost drivers (delivery, storage, compute) and names the levers.
- [ ] Explains how live streaming would differ.
