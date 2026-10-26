# Video Streaming

## Question

Design a video platform where creators upload videos and viewers watch them on phones, browsers and smart TVs. Focus on the path from upload to playback, the delivery network and view counts; search and recommendations are out of scope.

## Functional requirements

- Creators upload videos of up to 4 hours and 20 GB; uploads survive dropped connections.
- The platform processes each upload into the formats and quality levels devices need, plus thumbnails.
- Viewers play videos with quality that adapts to their bandwidth, and can seek anywhere.
- The watch page shows a view count; creators see views and watch time per day.
- Creators can make a video private or delete it; private videos are only playable by authorized viewers.

## Non-functional requirements

- A 10-minute video is playable within 10 minutes of upload finishing, at least at standard definition.
- Playback starts in under 2 seconds at p90 and rebuffers less than 0.5% of watch time.
- Playback is 99.99% available; processing may be delayed during incidents but never loses an upload.
- Originals are stored durably and can be reprocessed later.
- Delivery cost per hour watched matters: it is the largest line in the budget.

## Scale

- 500,000 uploads per day, 8 minutes long on average.
- 1 billion views per day, 6 minutes watched per view on average, at about 3 Mbps.
- Peak concurrent viewing is 2.5 times the average.
- Popularity is extremely skewed: a small fraction of videos gets most views, and most videos are watched rarely.
