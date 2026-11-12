// The receiver keeps the bytes that arrive ahead of the next expected one and releases them once
// the gap before them fills. The sender keeps its segments in order with two marks, the oldest
// unacknowledged byte and the next byte to send; one retransmission timer covers the oldest
// outstanding segment, with its timeout estimated from measured round trips. Every call first
// runs the timer expiries that are due, so the virtual clock moves forward in one place. Sending
// is limited by the smaller of the receiver's window and the congestion window, each of which is
// unlimited until it is set.
const MSS = 1000;
const INITIAL_RTO = 1000;
const MIN_RTO = 1000;
const MAX_RTO = 60000;
const GRANULARITY = 1;
const INITIAL_WINDOW = 4 * MSS;
const DUPLICATE_THRESHOLD = 3;

interface Segment {
  seq: number;
  length: number;
  sent: boolean;
  timedOut: boolean;
}

interface Timed {
  segment: Segment;
  sentAt: number;
}

export class ReliableTransport {
  // Receiver
  private delivered = 0;
  private held = new Map<number, string>();
  // Sender
  private segments: Segment[] = [];
  private una = 0;
  private nxt = 0;
  private rto = INITIAL_RTO;
  private srtt = -1;
  private rttvar = -1;
  private deadline = -1;
  private timed: Timed | null = null;
  private window: number | null = null;
  // Congestion control
  private cwnd: number | null = null;
  private ssthresh = 0;
  private ackedInAvoidance = 0;
  private duplicates = 0;
  private recovering = false;
  private trace: number[][] = [];

  // Level 1
  receive(seq: number, data: string): string {
    for (let offset = 0; offset < data.length; offset++) {
      const position = seq + offset;
      if (position >= this.delivered && !this.held.has(position)) this.held.set(position, data[offset]);
    }
    let released = "";
    while (this.held.has(this.delivered)) {
      released += this.held.get(this.delivered);
      this.held.delete(this.delivered);
      this.delivered++;
    }
    return released;
  }

  buffered(): number {
    return this.held.size;
  }

  ackNumber(): number {
    return this.delivered;
  }

  // Level 2
  send(length: number, now: number): number[][] {
    const sent = this.expire(now);
    let end = this.segments.length > 0 ? ReliableTransport.end(this.segments[this.segments.length - 1]) : 0;
    while (length > 0) {
      const size = Math.min(length, MSS);
      this.segments.push({ seq: end, length: size, sent: false, timedOut: false });
      end += size;
      length -= size;
    }
    return [...sent, ...this.transmitNew(now)];
  }

  ack(ackNo: number, now: number): number[][] {
    return this.acknowledge(ackNo, this.window, now);
  }

  tick(now: number): number[][] {
    return this.expire(now);
  }

  timerState(): number[] {
    return [this.srtt, this.rttvar, this.rto, this.deadline];
  }

  // Level 3
  ackWindow(ackNo: number, window: number, now: number): number[][] {
    return this.acknowledge(ackNo, window, now);
  }

  // Level 4
  enableCongestionControl(ssthresh: number, now: number): void {
    this.expire(now);
    this.cwnd = INITIAL_WINDOW;
    this.ssthresh = ssthresh;
    this.trace.push([now, this.cwnd, this.ssthresh]);
  }

  congestionTrace(): number[][] {
    return this.trace.map((row) => [...row]);
  }

  // The sender
  private static end(segment: Segment): number {
    return segment.seq + segment.length;
  }

  private expire(now: number): number[][] {
    const sent: number[][] = [];
    while (this.deadline !== -1 && this.deadline <= now) sent.push(...this.timeout(this.deadline));
    return sent;
  }

  private timeout(at: number): number[][] {
    const before = this.congestion();
    const oldest = this.oldestUnacked();
    if (this.cwnd !== null) {
      // RFC 5681 holds ssthresh when the timer resends a segment it has resent before.
      if (!oldest.timedOut) this.ssthresh = Math.max(Math.floor((this.nxt - this.una) / 2), 2 * MSS);
      this.cwnd = MSS;
      this.recovering = false;
      this.duplicates = 0;
      this.ackedInAvoidance = 0;
    }
    oldest.timedOut = true;
    const sent = [this.retransmit(oldest)];
    this.rto = Math.min(2 * this.rto, MAX_RTO);
    this.deadline = at + this.rto;
    this.note(at, before);
    return [...sent, ...this.transmitNew(at)];
  }

  private acknowledge(ackNo: number, window: number | null, now: number): number[][] {
    const sent = this.expire(now);
    if (ackNo < this.una || ackNo > this.nxt) return sent;
    const before = this.congestion();
    if (ackNo > this.una) {
      this.newData(ackNo, now);
    } else if (window === this.window && this.nxt > this.una) {
      sent.push(...this.duplicate());
    }
    this.window = window;
    this.note(now, before);
    return [...sent, ...this.transmitNew(now)];
  }

  private newData(ackNo: number, now: number): void {
    const newly = ackNo - this.una;
    this.una = ackNo;
    if (this.timed !== null && ackNo >= ReliableTransport.end(this.timed.segment)) {
      this.measure(now - this.timed.sentAt);
      this.timed = null;
    }
    this.deadline = this.una === this.nxt ? -1 : now + this.rto;
    this.duplicates = 0;
    if (this.cwnd === null) return;
    if (this.recovering) {
      this.cwnd = this.ssthresh;
      this.recovering = false;
    } else if (this.cwnd < this.ssthresh) {
      this.cwnd += Math.min(newly, MSS);
    } else {
      this.ackedInAvoidance += newly;
      if (this.ackedInAvoidance >= this.cwnd) {
        this.ackedInAvoidance -= this.cwnd;
        this.cwnd += MSS;
      }
    }
  }

  private duplicate(): number[][] {
    if (this.cwnd === null) return [];
    this.duplicates++;
    if (this.recovering) {
      this.cwnd += MSS;
      return [];
    }
    if (this.duplicates !== DUPLICATE_THRESHOLD) return [];
    this.ssthresh = Math.max(Math.floor((this.nxt - this.una) / 2), 2 * MSS);
    this.cwnd = this.ssthresh + 3 * MSS;
    this.recovering = true;
    this.ackedInAvoidance = 0;
    return [this.retransmit(this.oldestUnacked())];
  }

  private measure(sample: number): void {
    if (this.srtt === -1) {
      this.srtt = sample;
      this.rttvar = Math.floor(sample / 2);
    } else {
      this.rttvar = Math.floor((3 * this.rttvar + Math.abs(this.srtt - sample)) / 4);
      this.srtt = Math.floor((7 * this.srtt + sample) / 8);
    }
    const rto = this.srtt + Math.max(GRANULARITY, 4 * this.rttvar);
    this.rto = Math.min(Math.max(rto, MIN_RTO), MAX_RTO);
  }

  private oldestUnacked(): Segment {
    return this.segments.find((segment) => ReliableTransport.end(segment) > this.una)!;
  }

  private retransmit(segment: Segment): number[] {
    this.timed = null; // Karn: a retransmitted segment can no longer be timed
    return [segment.seq, segment.length, 1];
  }

  private limit(): number | null {
    const limits = [this.window, this.cwnd].filter((limit): limit is number => limit !== null);
    return limits.length > 0 ? Math.min(...limits) : null;
  }

  private transmitNew(now: number): number[][] {
    const sent: number[][] = [];
    for (const segment of this.segments) {
      if (segment.sent) continue;
      const limit = this.limit();
      if (limit !== null && ReliableTransport.end(segment) > this.una + limit) break;
      segment.sent = true;
      this.nxt = ReliableTransport.end(segment);
      if (this.timed === null) this.timed = { segment, sentAt: now };
      if (this.deadline === -1) this.deadline = now + this.rto;
      sent.push([segment.seq, segment.length, 0]);
    }
    return sent;
  }

  private congestion(): string {
    return `${this.cwnd}/${this.ssthresh}`;
  }

  private note(at: number, before: string): void {
    if (this.cwnd !== null && before !== this.congestion()) {
      this.trace.push([at, this.cwnd, this.ssthresh]);
    }
  }
}
