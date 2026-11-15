# Chat System

## Question

Design the backend of a mobile and web messaging app with one-to-one conversations and group chats. Users are often on flaky mobile networks and use the app on several devices.

## Functional requirements

- Send text messages in one-to-one conversations and in groups of up to 500 members. Attachments are uploaded separately and referenced by id.
- Delivery receipts: the sender sees sent (the server has it), delivered (reached at least one device of each recipient) and read.
- Offline sync: a device that was offline, or a newly added device, catches up on every conversation it missed.
- Push notifications to devices that are not connected.
- History is kept for one year and is available on every device of a member.

## Non-functional requirements

- When sender and recipient are both online in the same region, delivery takes under 500 ms at p99.
- Once the sender sees "sent", the message is never lost.
- Every member sees a conversation's messages in the same order, and never sees a message twice, even when clients retry.
- Sending is 99.99% available.
- A user has up to 5 devices.

## Scale

- 300 million daily active users, each sending 50 messages per day.
- Up to 100 million connected devices at peak.
- 80% of messages are one-to-one; group messages go to 30 members on average.
- Average message size is 100 bytes of text.
- Peak traffic is 3 times the average.
