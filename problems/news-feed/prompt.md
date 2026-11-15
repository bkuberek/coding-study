# News Feed

## Question

Design the home feed of a social network. Users follow other accounts; when they open the app they see a ranked, endlessly scrollable feed of posts from the accounts they follow.

## Functional requirements

- Publish a post (text plus references to already uploaded media).
- Load the home feed: posts from followed accounts, ranked by relevance with a bias to recency, 20 at a time with infinite scroll.
- Follow and unfollow; an unfollow removes that account's posts from the next feed load.
- Deleted posts and posts from blocked accounts never appear.
- Some accounts are celebrities with tens of millions of followers.

## Non-functional requirements

- Feed load p99 under 300 ms at the server.
- A new post is visible to most followers within 5 seconds and to all followers within 1 minute.
- 99.95% availability for feed reads; a degraded feed (for example unranked) is better than an error.
- Scrolling never shows the same post twice or silently skips one within a session.
- Authors see their own new post in their feed immediately.

## Scale

- 1 billion registered users, 500 million daily active.
- Users follow 300 accounts on average; follower counts follow a power law, up to 100 million.
- 200 million posts per day.
- Each daily active user loads the feed 10 times a day.
- Peak traffic is 3 times the average.
