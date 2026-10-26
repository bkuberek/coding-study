const CHANNEL_ORDER = ["EMAIL", "SMS", "PUSH"] as const;
const MAX_RETRIES = 3;
const BASE_RETRY_DELAY = 1000;

interface Channel {
  format(address: string, text: string): string;
}

class EmailChannel implements Channel {
  format(address: string, text: string): string {
    return `${address}: ${text}`;
  }
}

// A channel with a length limit: a longer text is cut so that it ends in `...` and fits.
class TruncatingChannel implements Channel {
  private readonly limit: number;

  constructor(limit: number) {
    this.limit = limit;
  }

  format(address: string, text: string): string {
    const fitted = text.length > this.limit ? `${text.slice(0, this.limit - 3)}...` : text;
    return `${address}: ${fitted}`;
  }
}

class Template {
  private readonly body: string;

  constructor(body: string) {
    this.body = body;
  }

  render(params: readonly string[]): string {
    const values = new Map<string, string>();
    for (const param of params) {
      const split = param.indexOf("=");
      if (split >= 0) {
        values.set(param.slice(0, split), param.slice(split + 1));
      }
    }
    return this.body.replace(/\{([^{}]*)\}/g, (_match, key: string) => values.get(key) ?? "");
  }
}

// At most `limit` accepted notifications per user in any `window` milliseconds.
class SlidingWindowLimiter {
  private readonly limit: number;
  private readonly window: number;
  private readonly accepted = new Map<string, number[]>();

  constructor(limit: number, window: number) {
    this.limit = limit;
    this.window = window;
  }

  tryAcquire(userId: string, now: number): boolean {
    const recent = (this.accepted.get(userId) ?? []).filter((time) => time > now - this.window);
    this.accepted.set(userId, recent);
    if (recent.length >= this.limit) {
      return false;
    }
    recent.push(now);
    return true;
  }
}

class ChannelState {
  readonly channel: Channel;
  limiter: SlidingWindowLimiter | null = null;
  outage: readonly [number, number] | null = null;
  delivered = 0;
  retries = 0;
  dropped = 0;
  rateLimited = 0;

  constructor(channel: Channel) {
    this.channel = channel;
  }

  isDown(now: number): boolean {
    return this.outage !== null && this.outage[0] <= now && now < this.outage[1];
  }

  stats(): number[] {
    return [this.delivered, this.retries, this.dropped, this.rateLimited];
  }
}

interface Contact {
  address: string;
  enabled: boolean;
}

interface Attempt {
  readonly due: number;
  readonly sequence: number;
  readonly userId: string;
  readonly channel: string;
  readonly payload: string;
  readonly retriesLeft: number;
}

function key(userId: string, channel: string): string {
  return `${userId} ${channel}`;
}

export class NotificationService {
  private readonly channels = new Map<string, ChannelState>([
    ["EMAIL", new ChannelState(new EmailChannel())],
    ["SMS", new ChannelState(new TruncatingChannel(20))],
    ["PUSH", new ChannelState(new TruncatingChannel(30))],
  ]);
  private readonly contacts = new Map<string, Contact>();
  private readonly templates = new Map<string, Template>();
  private readonly retries: Attempt[] = []; // sorted by (due, sequence)
  private sequence = 0;
  private readonly inbox = new Map<string, string[]>();

  addContact(userId: string, channel: string, address: string): boolean {
    if (!this.channels.has(channel)) {
      return false;
    }
    this.contacts.set(key(userId, channel), { address, enabled: true });
    return true;
  }

  setPreference(userId: string, channel: string, enabled: boolean): boolean {
    const contact = this.contacts.get(key(userId, channel));
    if (contact === undefined) {
      return false;
    }
    contact.enabled = enabled;
    return true;
  }

  addTemplate(templateId: string, body: string): boolean {
    if (this.templates.has(templateId)) {
      return false;
    }
    this.templates.set(templateId, new Template(body));
    return true;
  }

  setRateLimit(channel: string, limit: number, windowMs: number): boolean {
    const state = this.channels.get(channel);
    if (state === undefined) {
      return false;
    }
    state.limiter = new SlidingWindowLimiter(limit, windowMs);
    return true;
  }

  setOutage(channel: string, start: number, end: number): boolean {
    const state = this.channels.get(channel);
    if (state === undefined) {
      return false;
    }
    state.outage = [start, end];
    return true;
  }

  send(timestamp: number, userId: string, templateId: string, params: string[]): number {
    this.processRetries(timestamp);
    const template = this.templates.get(templateId);
    if (template === undefined) {
      return -1;
    }
    const text = template.render(params);
    let accepted = 0;
    for (const name of CHANNEL_ORDER) {
      const contact = this.contacts.get(key(userId, name));
      const state = this.channels.get(name);
      if (contact === undefined || !contact.enabled || state === undefined) {
        continue;
      }
      if (state.limiter !== null && !state.limiter.tryAcquire(userId, timestamp)) {
        state.rateLimited++;
        continue;
      }
      accepted++;
      const payload = state.channel.format(contact.address, text);
      this.attempt(this.newAttempt(timestamp, userId, name, payload, MAX_RETRIES));
    }
    return accepted;
  }

  delivered(timestamp: number, userId: string, channel: string): string[] {
    this.processRetries(timestamp);
    return [...(this.inbox.get(key(userId, channel)) ?? [])];
  }

  stats(timestamp: number, channel: string): number[] {
    this.processRetries(timestamp);
    return this.channels.get(channel)?.stats() ?? [];
  }

  private newAttempt(due: number, userId: string, channel: string, payload: string, retriesLeft: number): Attempt {
    this.sequence++;
    return { due, sequence: this.sequence, userId, channel, payload, retriesLeft };
  }

  // Deliver now, or schedule the next retry with an exponentially growing delay.
  private attempt(attempt: Attempt): void {
    const state = this.channels.get(attempt.channel);
    if (state === undefined) {
      return;
    }
    if (!state.isDown(attempt.due)) {
      state.delivered++;
      const messages = this.inbox.get(key(attempt.userId, attempt.channel)) ?? [];
      messages.push(attempt.payload);
      this.inbox.set(key(attempt.userId, attempt.channel), messages);
    } else if (attempt.retriesLeft === 0) {
      state.dropped++;
    } else {
      const retryNumber = MAX_RETRIES - attempt.retriesLeft + 1;
      const due = attempt.due + BASE_RETRY_DELAY * 2 ** (retryNumber - 1);
      this.schedule(this.newAttempt(due, attempt.userId, attempt.channel, attempt.payload, attempt.retriesLeft - 1));
    }
  }

  private schedule(retry: Attempt): void {
    let low = 0;
    let high = this.retries.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      const other = this.retries[middle];
      if (other.due < retry.due || (other.due === retry.due && other.sequence < retry.sequence)) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    this.retries.splice(low, 0, retry);
  }

  private processRetries(now: number): void {
    while (this.retries.length > 0 && this.retries[0].due <= now) {
      const retry = this.retries.shift();
      if (retry === undefined) {
        return;
      }
      const state = this.channels.get(retry.channel);
      if (state !== undefined) {
        state.retries++;
      }
      this.attempt(retry);
    }
  }
}
