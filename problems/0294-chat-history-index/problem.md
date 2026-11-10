# Chat History Index

## Statement

Build `ChatHistory`, the service that stores what each user said in their conversations with an assistant and finds old conversations again. A conversation belongs to one user, has an id chosen by the caller and holds messages in the order they were sent. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`. Nothing reads a clock: time is whatever the caller passes.

Aim to finish in 90 minutes. A good split: read the statement and pick the core data structure in the first 5 minutes, then finish level 1 by about minute 20, level 2 by 40, level 3 by 65 and level 4 by 88, keeping the last minutes for a final run.

## Input

- `ChatHistory()`: creates an empty history.
- `timestamp`: the time of the call. Within one test, timestamps never decrease from call to call, and consecutive calls may share a timestamp.
- `userId`: the user a call reads or writes. Users are independent: two users may use the same conversation id for different conversations.
- `conversationId`: a conversation of that user.
- `text`: the content of a message, lowercase words separated by single spaces.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A missing conversation is reported with a sentinel, never with an exception: an empty list for lists, `false` for booleans and `-1` for numbers.

## Level 1: Conversations

- `append(timestamp, userId, conversationId, text)`: adds a message sent at `timestamp` to the end of the conversation, creating the conversation when it does not exist yet. Returns the number of the new message in its conversation: 1 for the first message, 2 for the second, and so on.
- `getConversation(timestamp, userId, conversationId)`: the texts of the conversation's messages, in the order they were appended, or an empty list when the conversation does not exist.

### Example 1

<!-- case: ex1 -->

`c1` of `u1` gets messages 1 and 2, and `c2` starts again at 1. `u2` has a `c1` of its own, which does not mix with the one of `u1`. `c9` was never written.

## Level 2: Keyword search

- `search(timestamp, userId, query)`: the ids of the user's conversations that match `query`, best first. `query` is one or more lowercase words separated by single spaces.
- A message matches when at least one query word is also a word of its text. A word matches only a whole word: `cat` does not match `category`.
- The match count of a conversation is the number of its matching messages. A message counts once, however many query words it holds and however often. A conversation is a result when its match count is at least 1.
- Order the results by match count, highest first; equal counts put first the conversation whose latest matching message was sent later; equal times go in ascending string order of conversation id.

### Example 1

<!-- case: ex2 -->

For `rome pasta`, both messages of `trip` mention `rome`, and both messages of `food` match too, the first one twice over, which still counts once. The counts tie at 2, and the latest match in `food` was sent at 4, after the one in `trip` at 2. Nothing mentions `budget`, and `u2` has no conversations.

## Level 3: Deletion

- `deleteMessage(timestamp, userId, conversationId, messageNumber)`: deletes message number `messageNumber` of the conversation. Returns `false` and changes nothing when the conversation does not exist, has no message with that number, or the message is already deleted.
- `deleteConversation(timestamp, userId, conversationId)`: deletes the conversation with all its messages. Returns `false` when it does not exist or is already deleted.
- Deletions are permanent. A deleted message is left out of `getConversation` and `search`, and never counts as a match. Message numbers never change: the messages after a deleted one keep their numbers, and the next `append` continues after the highest number ever given, deleted or not.
- A deleted conversation behaves like one that does not exist, except that its id is never reused: `append` to it returns `-1` and changes nothing. A conversation whose messages were all deleted still exists and still takes new messages.

### Example 1

<!-- case: ex3 -->

Deleting message 2 twice fails the second time. `getConversation` skips it, but `fourth note` still gets number 4. After `c1` is deleted, it cannot be deleted again, search no longer finds it and `append` to it returns `-1`.

## Level 4: Projects

- `moveToProject(timestamp, userId, conversationId, projectId)`: puts the conversation in the user's project `projectId`, taking it out of the project it was in before. A conversation is in at most one project, and projects need no creating. Returns `false` and changes nothing when the conversation does not exist or was deleted.
- `searchProject(timestamp, userId, projectId, query)`: the same search as `search`, with the same ranking, over only the user's conversations in project `projectId`.
- `search` now covers only the conversations that are in no project.
- A conversation in a project still takes new messages and deletions as before.

### Example 1

<!-- case: ex4 -->

`c1` and `c2` move to `launch`, so a search inside the project finds both, newest match first, while the global search for `launch hiking` sees only `c3`. `c9` does not exist and cannot move, and nothing is in project `travel`.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, never decreasing within a test.
- Ids are 1 to 10 lowercase letters or digits.
- A text is 1 to 20 words, and a word is 1 to 10 lowercase letters.

## Follow-ups

- How would search avoid reading every message of the user once histories hold millions of messages?
- When may the space of a deleted message be reclaimed, given that its number must never be reused?

## Hints

### Hint 1

A map from user to a map from conversation id to conversation covers level 1, with each conversation a list of messages. Store each message's words as a set when it is appended.

### Hint 2

Do not remove a deleted message from its list: mark it deleted. Its number stays its position, and the numbers after it do not move.

### Hint 3

Write one ranking helper that takes the set of conversations to consider. `search` passes the ones in no project, `searchProject` the ones in its project.
