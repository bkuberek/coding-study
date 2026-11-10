from dataclasses import dataclass, field

NO_MESSAGE = -1


@dataclass(slots=True)
class _Message:
    text: str
    words: frozenset[str]
    sent_at: int
    deleted: bool = False


@dataclass(slots=True)
class _Conversation:
    """Messages stay in place when deleted, so a message's number is its index plus one forever."""

    messages: list[_Message] = field(default_factory=list)
    deleted: bool = False
    project: str | None = None

    def live_messages(self) -> list[_Message]:
        return [message for message in self.messages if not message.deleted]

    def match(self, terms: frozenset[str]) -> tuple[int, int]:
        """How many live messages share a word with `terms`, and when the latest was sent."""
        count = latest = 0
        for message in self.messages:
            if not message.deleted and not terms.isdisjoint(message.words):
                count += 1
                latest = message.sent_at
        return count, latest


class ChatHistory:
    def __init__(self) -> None:
        self._users: dict[str, dict[str, _Conversation]] = {}

    # Level 1
    def append(self, timestamp: int, user_id: str, conversation_id: str, text: str) -> int:
        conversations = self._users.setdefault(user_id, {})
        conversation = conversations.setdefault(conversation_id, _Conversation())
        if conversation.deleted:
            return NO_MESSAGE
        conversation.messages.append(_Message(text, frozenset(text.split()), timestamp))
        return len(conversation.messages)

    def get_conversation(self, timestamp: int, user_id: str, conversation_id: str) -> list[str]:
        conversation = self._live(user_id, conversation_id)
        return [message.text for message in conversation.live_messages()] if conversation else []

    # Level 2
    def search(self, timestamp: int, user_id: str, query: str) -> list[str]:
        return self._search(user_id, None, query)

    # Level 3
    def delete_message(
        self, timestamp: int, user_id: str, conversation_id: str, message_number: int
    ) -> bool:
        conversation = self._live(user_id, conversation_id)
        if conversation is None or not 1 <= message_number <= len(conversation.messages):
            return False
        message = conversation.messages[message_number - 1]
        if message.deleted:
            return False
        message.deleted = True
        return True

    def delete_conversation(self, timestamp: int, user_id: str, conversation_id: str) -> bool:
        conversation = self._live(user_id, conversation_id)
        if conversation is None:
            return False
        conversation.deleted = True
        return True

    # Level 4
    def move_to_project(
        self, timestamp: int, user_id: str, conversation_id: str, project_id: str
    ) -> bool:
        conversation = self._live(user_id, conversation_id)
        if conversation is None:
            return False
        conversation.project = project_id
        return True

    def search_project(
        self, timestamp: int, user_id: str, project_id: str, query: str
    ) -> list[str]:
        return self._search(user_id, project_id, query)

    def _live(self, user_id: str, conversation_id: str) -> _Conversation | None:
        conversation = self._users.get(user_id, {}).get(conversation_id)
        return None if conversation is None or conversation.deleted else conversation

    def _search(self, user_id: str, project_id: str | None, query: str) -> list[str]:
        """Ranks the user's live conversations in `project_id` (None: in no project) for `query`."""
        terms = frozenset(query.split())
        ranked = []
        for conversation_id, conversation in self._users.get(user_id, {}).items():
            if conversation.deleted or conversation.project != project_id:
                continue
            count, latest = conversation.match(terms)
            if count:
                ranked.append((-count, -latest, conversation_id))
        ranked.sort()
        return [conversation_id for _, _, conversation_id in ranked]
