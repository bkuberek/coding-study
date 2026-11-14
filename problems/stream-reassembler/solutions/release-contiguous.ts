export class StreamReassembler {
  // released[i] is fragment i, so the next sequence to release is released.length.
  private readonly released: string[] = [];
  private readonly held = new Map<number, string>();
  private highestArrived = -1;
  private lastSequence: number | null = null;
  private closed = false;

  delta(sequence: number, fragment: string): string {
    if (this.closed || this.isPastTheEnd(sequence) || this.hasArrived(sequence)) {
      return "";
    }
    this.held.set(sequence, fragment);
    this.highestArrived = Math.max(this.highestArrived, sequence);
    let newlyReleased = "";
    while (this.held.has(this.released.length)) {
      const piece = this.held.get(this.released.length)!;
      this.held.delete(this.released.length);
      this.released.push(piece);
      newlyReleased += piece;
    }
    return newlyReleased;
  }

  finish(lastSequence: number): boolean {
    if (this.closed || this.lastSequence !== null || lastSequence < this.highestArrived) {
      return false;
    }
    this.lastSequence = lastSequence;
    return true;
  }

  close(): void {
    this.closed = true;
  }

  status(): string {
    if (this.lastSequence !== null && this.released.length === this.lastSequence + 1) {
      return "complete";
    }
    return this.closed ? "truncated" : "streaming";
  }

  text(): string {
    return this.released.join("");
  }

  missing(): number[] {
    const end = this.lastSequence ?? this.highestArrived;
    const absent: number[] = [];
    for (let sequence = this.released.length; sequence <= end; sequence += 1) {
      if (!this.held.has(sequence)) {
        absent.push(sequence);
      }
    }
    return absent;
  }

  private isPastTheEnd(sequence: number): boolean {
    return this.lastSequence !== null && sequence > this.lastSequence;
  }

  private hasArrived(sequence: number): boolean {
    return sequence < this.released.length || this.held.has(sequence);
  }
}
