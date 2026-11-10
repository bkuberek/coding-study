const NO_MESSAGE = -1;

// Plain string order, as in the other languages; localeCompare would not match it.
function compareIds(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

interface Message {
  readonly text: string;
  readonly words: ReadonlySet<string>;
  readonly sentAt: number;
  deleted: boolean;
}

// Messages stay in place when deleted, so a message's number is its index plus one forever.
class Conversation {
  readonly messages: Message[] = [];
  deleted = false;
  project: string | null = null;

  liveTexts(): string[] {
    return this.messages.filter((message) => !message.deleted).map((message) => message.text);
  }

  // How many live messages share a word with `terms`, and when the latest of them was sent.
  match(terms: readonly string[]): { count: number; latest: number } {
    let count = 0;
    let latest = 0;
    for (const message of this.messages) {
      if (!message.deleted && terms.some((term) => message.words.has(term))) {
        count += 1;
        latest = message.sentAt;
      }
    }
    return { count, latest };
  }
}

export class ChatHistory {
  private readonly users = new Map<string, Map<string, Conversation>>();

  // Level 1
  append(timestamp: number, userId: string, conversationId: string, text: string): number {
    let conversations = this.users.get(userId);
    if (conversations === undefined) {
      conversations = new Map();
      this.users.set(userId, conversations);
    }
    let conversation = conversations.get(conversationId);
    if (conversation === undefined) {
      conversation = new Conversation();
      conversations.set(conversationId, conversation);
    }
    if (conversation.deleted) {
      return NO_MESSAGE;
    }
    const words = new Set(text.split(" "));
    conversation.messages.push({ text, words, sentAt: timestamp, deleted: false });
    return conversation.messages.length;
  }

  getConversation(timestamp: number, userId: string, conversationId: string): string[] {
    return this.live(userId, conversationId)?.liveTexts() ?? [];
  }

  // Level 2
  search(timestamp: number, userId: string, query: string): string[] {
    return this.rank(userId, null, query);
  }

  // Level 3
  deleteMessage(
    timestamp: number,
    userId: string,
    conversationId: string,
    messageNumber: number,
  ): boolean {
    const message = this.live(userId, conversationId)?.messages[messageNumber - 1];
    if (message === undefined || message.deleted) {
      return false;
    }
    message.deleted = true;
    return true;
  }

  deleteConversation(timestamp: number, userId: string, conversationId: string): boolean {
    const conversation = this.live(userId, conversationId);
    if (conversation === null) {
      return false;
    }
    conversation.deleted = true;
    return true;
  }

  // Level 4
  moveToProject(
    timestamp: number,
    userId: string,
    conversationId: string,
    projectId: string,
  ): boolean {
    const conversation = this.live(userId, conversationId);
    if (conversation === null) {
      return false;
    }
    conversation.project = projectId;
    return true;
  }

  searchProject(timestamp: number, userId: string, projectId: string, query: string): string[] {
    return this.rank(userId, projectId, query);
  }

  private live(userId: string, conversationId: string): Conversation | null {
    const conversation = this.users.get(userId)?.get(conversationId);
    return conversation === undefined || conversation.deleted ? null : conversation;
  }

  // Ranks the user's live conversations in `projectId` (null: in no project) for `query`.
  private rank(userId: string, projectId: string | null, query: string): string[] {
    const terms = [...new Set(query.split(" "))];
    const ranked: { id: string; count: number; latest: number }[] = [];
    for (const [id, conversation] of this.users.get(userId) ?? []) {
      if (conversation.deleted || conversation.project !== projectId) {
        continue;
      }
      const { count, latest } = conversation.match(terms);
      if (count > 0) {
        ranked.push({ id, count, latest });
      }
    }
    ranked.sort((a, b) => b.count - a.count || b.latest - a.latest || compareIds(a.id, b.id));
    return ranked.map((entry) => entry.id);
  }
}
