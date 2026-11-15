# Video Streaming: Reference

## Requirements

Clarify before designing:

- **Three systems in one**: an upload and processing pipeline (throughput, durability), a delivery network (bandwidth, cost, latency) and a counting pipeline (volume, fraud). They share metadata and little else; design them separately.
- **What "playable within 10 minutes" means**: the lowest renditions must be ready first; higher ones and expensive codecs can follow.
- **Cost is a requirement**: delivery bandwidth dominates, so codec choices, cache hit ratio and where caches sit are design decisions, not afterthoughts.
- **View count semantics**: shown counts may lag by minutes and are filtered for fraud; creators' analytics can be corrected later.
- **Out of scope**: live streaming, search, recommendations, ads, DRM details (mention where they plug in).

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Video uploaded | 500,000 x 8 min | 4 M minutes (~67,000 hours) per day |
| Originals | ~10 Mbps x 480 s = ~600 MB per video | ~300 TB/day, ~28 Gbps of upload ingress |
| Renditions (H.264 ladder 240p-1080p) | ladder bitrates sum to ~10 Mbps | another ~300 TB/day; ~220 PB/year with originals |
| Transcoding | ~8 vCPU-seconds per second of video for the whole ladder | ~530,000 vCPU-hours/day, ~22,000 vCPUs busy around the clock |
| Watch time | 1 B views x 6 min | 6 B minutes (100 M hours) per day |
| Concurrent viewers | 6 B min / 1,440 min per day | ~4.2 M average, ~10 M peak |
| Delivery bandwidth | 4.2 M x 3 Mbps | ~12.5 Tbps average, ~31 Tbps peak, ~135 PB/day |
| Segment requests | 4.2 M viewers / 4 s segments | ~1 M/s average at the CDN |
| Player events | heartbeat every 30 s per viewer | ~140,000/s average |

Two conclusions: delivery (about 135 PB/day) is roughly 450 times the upload volume, so every percent of cache hit ratio and codec efficiency is worth more than any processing optimization; and storage grows by hundreds of petabytes a year, so storage tiering is mandatory.

## API

```text
POST /v1/uploads {filename, size_bytes, content_type}
  201 {upload_id, part_size, part_urls: [signed object-storage URLs]}      resumable multipart, direct to storage
POST /v1/uploads/{upload_id}/complete {parts: [{number, etag}], title, visibility}
  202 {video_id, status: "processing"}
GET  /v1/videos/{video_id}
  200 {title, status, duration, thumbnails, manifest_url (signed, expiring), view_count}
POST /v1/playback-events  [{session_id, video_id, event: start|heartbeat|seek|end, position, bitrate, ts}]
GET  /v1/videos/{video_id}/analytics?from=&to=        creators only
```

Clients upload bytes straight to object storage with signed URLs; API servers never proxy video. Playback fetches a master manifest (HLS or DASH) and then segments, all from the CDN.

## Data model

| Data | Store | Key | Fields |
|------|-------|-----|--------|
| Videos | relational or key-value | `video_id` | owner, title, status (`uploading`, `processing`, `ready`, `failed`, `blocked`), visibility, duration, original location, content hash |
| Renditions | same | `(video_id, codec, height)` | bitrate, segment duration, manifest and segment paths, state |
| Processing tasks | workflow engine state | `(video_id, step, rendition, chunk)` | state, attempts, output path |
| Segments | object storage | `/{video_id}/{codec}/{height}/{segment}.m4s` | immutable, cacheable forever |
| View counts | counter store, cached | `video_id` | validated count, updated every few minutes |
| Watch analytics | columnar store | `(video_id, day, country, device)` | views, watch seconds |
| Raw player events | event log, then data lake | `session_id` | as sent |

## High-level design

```text
upload:   creator --> API (create upload) --> signed multipart --> originals bucket
                  --> complete --> workflow engine (durable DAG):
                        probe/validate --> split into GOP-aligned chunks
                        --> transcode tasks (chunk x rendition) on a worker fleet via priority queues
                        --> stitch + package (CMAF segments, HLS and DASH manifests)
                        --> thumbnails, moderation scan --> publish (status ready, metadata cache refreshed)
playback: viewer --> API (metadata + signed manifest URL)
                 --> CDN edge --> regional shield cache --> origin (segments bucket)
                 player ABR picks a rendition per segment from measured throughput and buffer
counting: player events --> collector --> event log --> stream job (dedup, fraud rules, per-minute counts)
                 --> counter store (watch page) + columnar store (creator analytics) + data lake
```

## Deep dives

### Processing pipeline

- **Chunked parallel encoding**: split the original into chunks aligned to keyframes (for example 10 s), encode every chunk of every rendition as an independent task, then stitch. A 10-minute video becomes 60 chunks x 5 renditions = 300 tasks and finishes in minutes, however long the video.
- **Order of work**: lowest renditions first so the video goes live at standard definition quickly; then 720p and 1080p; expensive codecs (VP9, AV1, about 30-50% fewer bytes than H.264 at similar quality) only after a video crosses a view threshold, because the encoding cost only pays back on watched videos.
- **Durable workflow**: the DAG lives in a workflow engine, so a crashed orchestrator resumes where it was. Tasks are idempotent: output paths are deterministic per `(video, rendition, chunk)` and a retry overwrites the same object.
- **Cheap, preemptible workers**: tasks are short, so preemption just means a retry; this cuts compute cost substantially.
- **Poison inputs**: a corrupt file that crashes the encoder is retried a few times, then marked `failed` with a reason for the creator; it never blocks the queue.
- **Priorities**: separate queues for new uploads, re-encodes and backfills, so a re-encode campaign never delays creators.

### Adaptive bitrate and packaging

- Segments of 2-6 seconds: shorter segments adapt faster and start faster, but mean more requests, more manifest entries and slightly worse compression. Four seconds is a common middle.
- CMAF (fragmented MP4) segments can be referenced from both HLS and DASH manifests, so one copy of the media serves every device family.
- The player starts at a conservative rendition for fast startup, then picks each segment's rendition from measured throughput and buffer level; seeks only need the manifest and the target segment.

### Delivery network

- **Tiers**: edge caches near viewers, a regional shield that collapses misses from many edges, and object storage as origin. The shield protects the origin and raises the effective hit ratio for the long tail.
- **Head and tail**: popular videos are pushed ahead of demand, including to caches inside internet providers' networks, which is where the largest cost savings come from. The long tail is served on demand; each tail segment is fetched from the origin once per shield.
- **Request collapsing**: when a new video goes viral, a thousand edge misses for the same segment become one shield request and one origin request.
- **Multiple CDNs** with steering by measured performance and price per region; this is also the failover plan.
- **Access control**: manifests and segment URLs are signed with an expiry (or carry a token checked at the edge), so private videos stay private while segments remain cacheable.

### View counts

- Count a view per playback session once it passes a minimum watch time, deduplicated by session id; heartbeats feed watch time.
- Never increment a database row per view: popular videos would take thousands of writes per second on one key. The stream job aggregates per video per minute and applies idempotent upserts keyed by `(video_id, minute)`, so replays after failures do not double count.
- Fraud filtering (bot patterns, repeated sessions from one source) runs in the stream with a short delay; shown counts may freeze briefly while a video is validated, and later corrections flow to creator analytics.

### Storage lifecycle

- Originals move to an archive tier after processing; they are kept only to re-encode with future codecs.
- Renditions of videos with no views in months move to an infrequent-access tier; for the deep tail, delete the higher renditions and re-encode on demand.
- Deduplicate identical uploads by content hash.
- Deletion removes metadata at once (the video becomes unplayable), then purges CDN caches and deletes objects asynchronously.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| Upload interrupted | Partial file | Multipart upload resumes from the last part; incomplete uploads expire after days |
| Transcode worker preempted or crashes | Task lost | Workflow retries it; idempotent outputs |
| Orchestrator crash | Pipeline stalls | Durable workflow state; resume |
| Corrupt or malicious input | Encoder crash or exploit | Sandboxed workers, bounded retries, `failed` status |
| Partial publish | Manifest points at missing segments | Publish the manifest only after every referenced segment is verified |
| Viral new video | Cache stampede at the origin | Shield tier, request collapsing, pre-warming for big creators |
| CDN outage in a region | Playback errors | Multi-CDN steering moves traffic within minutes |
| Counting pipeline lag | Stale counts | Playback unaffected; counts catch up |

## Trade-offs

- **Eager versus lazy encoding**: encoding every codec for every video wastes compute on videos nobody watches; encoding on demand makes the first viewers wait. Encode a baseline eagerly and premium codecs by popularity.
- **Segment length**: startup and adaptation speed versus request overhead and compression.
- **Push versus pull caching**: pre-positioning the head saves egress and latency; the tail is cheaper to pull.
- **Exact versus validated counts**: fast, cheap and approximate on the watch page; reconciled and exact for creators later.

## Observability and cost

- Viewer quality of experience from player telemetry, broken down by CDN, ISP, device and region: startup time, rebuffer ratio, average bitrate, playback failure rate.
- Pipeline: upload success rate, time from upload to playable (p50/p99), queue depth per priority, task retries, failed videos.
- Delivery: hit ratio by bytes per tier (aim above 95% at the edge for the head), origin egress, cost per hour watched.
- Cost order: delivery bandwidth, then storage, then encoding compute. The biggest levers are cache placement close to viewers, codec efficiency on popular videos and storage tiering.

## Evolution

- Live streaming: real-time ingest, transcoding on the fly and low-latency segment delivery are a separate pipeline sharing the delivery network.
- DRM for licensed content, downloads for offline viewing, multiple audio and subtitle tracks.
- Per-title encoding: choose each video's bitrate ladder from its visual complexity.
