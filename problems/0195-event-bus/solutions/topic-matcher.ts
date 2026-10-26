const NO_SUBSCRIBER = "-";

// Dot-separated segments; `*` matches exactly one segment and `#` zero or more.
class TopicPattern {
  private readonly segments: readonly string[];

  constructor(text: string) {
    this.segments = text.split(".");
  }

  matches(topic: string): boolean {
    const words = topic.split(".");
    const memo = new Map<number, boolean>();
    const match = (p: number, w: number): boolean => {
      const key = p * (words.length + 1) + w;
      const known = memo.get(key);
      if (known !== undefined) {
        return known;
      }
      let result: boolean;
      if (p === this.segments.length) {
        result = w === words.length;
      } else if (this.segments[p] === "#") {
        result = match(p + 1, w) || (w < words.length && match(p, w + 1));
      } else {
        result = w < words.length && (this.segments[p] === "*" || this.segments[p] === words[w]) && match(p + 1, w + 1);
      }
      memo.set(key, result);
      return result;
    };
    return match(0, 0);
  }
}

interface Event {
  readonly topic: string;
  readonly payload: string;
}

function render(event: Event): string {
  return `${event.topic}:${event.payload}`;
}

class Subscriber {
  readonly id: string;
  readonly patterns = new Map<string, TopicPattern>(); // subscription order
  private readonly inbox: Event[] = [];
  private head = 0; // index of the oldest event still in the inbox
  limit: number | null = null;

  constructor(id: string) {
    this.id = id;
  }

  get pending(): number {
    return this.inbox.length - this.head;
  }

  wants(topic: string): boolean {
    return [...this.patterns.values()].some((pattern) => pattern.matches(topic));
  }

  // Accept the event unless the inbox is full.
  offer(event: Event): boolean {
    if (this.limit !== null && this.pending >= this.limit) {
      return false;
    }
    this.inbox.push(event);
    return true;
  }

  take(count: number): string[] {
    const taken = this.inbox.slice(this.head, this.head + count).map(render);
    this.head += taken.length;
    return taken;
  }
}

class DeadLetterQueue {
  private readonly letters: string[] = [];
  private head = 0;

  add(subscriberId: string, event: Event): void {
    this.letters.push(`${subscriberId}:${render(event)}`);
  }

  drain(count: number): string[] {
    const drained = this.letters.slice(this.head, this.head + count);
    this.head += drained.length;
    return drained;
  }
}

export class EventBus {
  private readonly subscribers = new Map<string, Subscriber>();
  private readonly deadLetterQueue = new DeadLetterQueue();

  subscribe(subscriberId: string, pattern: string): boolean {
    let subscriber = this.subscribers.get(subscriberId);
    if (subscriber === undefined) {
      subscriber = new Subscriber(subscriberId);
      this.subscribers.set(subscriberId, subscriber);
    }
    if (subscriber.patterns.has(pattern)) {
      return false;
    }
    subscriber.patterns.set(pattern, new TopicPattern(pattern));
    return true;
  }

  unsubscribe(subscriberId: string, pattern: string): boolean {
    return this.subscribers.get(subscriberId)?.patterns.delete(pattern) ?? false;
  }

  publish(topic: string, payload: string): number {
    const event: Event = { topic, payload };
    const interested = [...this.subscribers.values()]
      .filter((subscriber) => subscriber.wants(topic))
      .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    if (interested.length === 0) {
      this.deadLetterQueue.add(NO_SUBSCRIBER, event);
    }
    let delivered = 0;
    for (const subscriber of interested) {
      if (subscriber.offer(event)) {
        delivered++;
      } else {
        this.deadLetterQueue.add(subscriber.id, event);
      }
    }
    return delivered;
  }

  poll(subscriberId: string, maxEvents: number): string[] {
    return this.subscribers.get(subscriberId)?.take(maxEvents) ?? [];
  }

  pending(subscriberId: string): number {
    return this.subscribers.get(subscriberId)?.pending ?? -1;
  }

  setInboxLimit(subscriberId: string, limit: number): boolean {
    const subscriber = this.subscribers.get(subscriberId);
    if (subscriber === undefined) {
      return false;
    }
    subscriber.limit = limit;
    return true;
  }

  deadLetters(maxEvents: number): string[] {
    return this.deadLetterQueue.drain(maxEvents);
  }
}
