# Chat History Index: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| tombstoned-conversations | optimal | O(1) per append or deletion; O(n q + c log c) per search | O(n w) | default answer; deletion and projects are flags on the same records |

Here `n` is the number of messages the user has ever appended, `c` the number of the user's conversations, `q` the number of words in the query and `w` the number of words in a message.

## How the design grows level by level

| Level | Change | Structure after the level |
|-------|--------|---------------------------|
| 1 | Append messages and read a conversation | `users: userId -> (conversationId -> Conversation(messages))` |
| 2 | Rank conversations against a query | `Message` gains `words` (a set built at append) and `sentAt` |
| 3 | Delete messages and conversations for good | `Message.deleted` and `Conversation.deleted`: tombstones, never removals |
| 4 | Projects scope the searches | `Conversation.project`, and one ranking helper that filters by it |

The choice that carries the problem is to delete by marking, not by removing. A message's number is its position in its conversation's list, so removing it from the list would renumber every later message, and the next `deleteMessage(3)` would hit what used to be message 4. A tombstone keeps every position stable for free, keeps the next number at the list's length plus one, and lets a deleted conversation remember that its id is taken.

## Approach: tombstoned-conversations (Per-user conversations with tombstones)

### Intuition

Each conversation is a list of messages that only grows, and each message carries what search needs: its word set, its send time and a deleted flag. A search walks the user's conversations, skips the ones it may not see, and for each counts the live messages that share a word with the query, remembering the time of the last of them. Because appends arrive with non-decreasing timestamps, the last matching message in list order is also the latest matching one. Level 4 adds one field per conversation and one filter in the ranking helper: "in no project" for `search`, "in this project" for `searchProject`.

### Algorithm

1. Keep `users`, a map from user id to a map from conversation id to `Conversation`.
2. A `Conversation` holds `messages`, a `deleted` flag and `project` (none at first). A `Message` holds its text, its word set, `sentAt` and a `deleted` flag.
3. Level 1: `append` creates the conversation when needed, returns `-1` when it is deleted, otherwise appends the message and returns the list's length. `getConversation` returns the texts of the live messages of a live conversation.
4. Level 2: `search` builds the set of query words and calls `rank(user, scope, terms)`. For every live conversation in scope, `rank` walks the messages, counting the live ones whose word set shares a word with `terms` and keeping the `sentAt` of the last of them. It keeps conversations with a count of at least 1, sorts them by `(-count, -latest, id)` and returns the ids.
5. Level 3: `deleteMessage` finds the live conversation, checks `1 <= messageNumber <= len(messages)`, fails when that message is already deleted, and otherwise sets its flag. `deleteConversation` sets the conversation's flag when it is live.
6. Level 4: `moveToProject` sets `project` on a live conversation. `search` ranks the conversations whose `project` is none; `searchProject` ranks those whose `project` equals its argument.

### Correctness

Invariant: message number `i` of a conversation is `messages[i - 1]` for as long as the history exists, because messages are only ever appended and deletion only sets a flag. So `append` returns `len(messages)`, the highest number ever given plus one, and `deleteMessage(i)` always reaches the message that `append` numbered `i`. Every reader skips flagged messages and flagged conversations, so a deleted item never reaches `getConversation`, a match count or a search result, and checking the flag before acting makes a second deletion fail without changing anything. For ranking, a conversation's count is the number of live messages sharing a word with the query, which is the definition of the match count; since messages are in non-decreasing `sentAt` order, the last matching message seen has the latest send time. Sorting by `(-count, -latest, id)` applies the three ordering rules in order. Each conversation has exactly one `project` value, so `search` and the `searchProject` calls see disjoint sets that together cover every live conversation.

### Complexity

- Time: O(1) per append or deletion; O(n q + c log c) per search — an append adds one message with a word set bounded by the 20-word limit and a deletion flips one flag; a search tests every message of the user against the `q` query words and sorts the matching conversations.
- Space: O(n w) — every message stays, deleted or not, with its text and its word set.

### Trade-offs

- Removing deleted messages from the list frees memory but breaks numbering. A map from message number to message keeps both, at the cost of a map per conversation; the tombstone list is simpler and gives the same answers.
- An inverted index from word to the messages that hold it would make search proportional to the matching messages instead of all messages. Deletions then have to update it, or the index keeps the tombstoned entries and the search skips them, which is the same tombstone idea one level down.
- Keeping each project's conversations in a set of their own speeds up `searchProject`, but every move must then update two sets. A `project` field read during the scan is enough for these sizes; mention the set when the follow-up asks for scale.

### Pitfalls and edge cases

- Level 1: the message number counts within one conversation, and the same conversation id under another user is a different conversation.
- Level 2: count matching messages, not word hits: `red car red car` is one matching message for the query `red car`. Rank equal counts by the latest matching message, not the latest message of the conversation, then by id in string order (`b10` before `b2`). Match whole words only.
- Level 3: never shift numbers: after deleting message 1 of four, message 4 is still number 4, and the next `append` returns 5. Deleting twice returns `false`, and so does deleting message 0 or a number never given. A deleted conversation must not come back when someone appends to it, while an emptied one still takes messages.
- Level 4: the global search must now leave out project chats, even those that would rank first. Moving a chat to a second project takes it out of the first. A deleted chat cannot move, and a chat deleted inside a project leaves that project's search.

### Language notes

- Python: `isdisjoint` tells whether a message shares a word with the query and stops at the first shared word, where `&` would build a new set for every message. Sorting tuples `(-count, -latest, id)` gives all three tie-breaks in one key. Dataclasses with `slots=True` keep the message records small.
- TypeScript: the reference tests the query words with `some` and `has`, which stops at the first word that matches; `Set.prototype.intersection` would build a new set for every message. Indexing an array out of range returns `undefined` rather than throwing, which the reference uses to reject message number 0 and numbers past the end in one check. Ids compare with `<` and `>`, which match the other language for ASCII; `localeCompare` would not.
