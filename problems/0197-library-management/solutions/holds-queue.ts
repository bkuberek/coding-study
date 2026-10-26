class FinePolicy {
  private readonly perDay: number;

  constructor(perDay: number) {
    this.perDay = perDay;
  }

  fine(due: number, returned: number): number {
    return Math.max(0, returned - due) * this.perDay;
  }
}

// All copies of one ISBN, with the members waiting for one.
class Title {
  copies = 0;
  onLoan = 0;
  readonly reserved = new Set<string>(); // members with a copy set aside for them
  readonly waiting: string[] = [];

  get free(): number {
    return this.copies - this.onLoan - this.reserved.size;
  }

  // Invariant: a free copy never sits on the shelf while someone is waiting.
  assignFreeCopies(): void {
    while (this.free > 0) {
      const next = this.waiting.shift();
      if (next === undefined) {
        return;
      }
      this.reserved.add(next);
    }
  }
}

class Member {
  readonly maxLoans: number;
  readonly loans = new Map<string, number>(); // isbn -> due day
  fines = 0;

  constructor(maxLoans: number) {
    this.maxLoans = maxLoans;
  }

  canBorrow(isbn: string): boolean {
    return this.fines === 0 && !this.loans.has(isbn) && this.loans.size < this.maxLoans;
  }
}

export class Library {
  private readonly loanDays: number;
  private readonly finePolicy: FinePolicy;
  private readonly titles = new Map<string, Title>();
  private readonly members = new Map<string, Member>();

  constructor(loanDays: number, finePerDay: number) {
    this.loanDays = loanDays;
    this.finePolicy = new FinePolicy(finePerDay);
  }

  addBook(isbn: string, copies: number): number {
    let title = this.titles.get(isbn);
    if (title === undefined) {
      title = new Title();
      this.titles.set(isbn, title);
    }
    title.copies += copies;
    title.assignFreeCopies();
    return title.copies;
  }

  addMember(memberId: string, maxLoans: number): boolean {
    if (this.members.has(memberId)) {
      return false;
    }
    this.members.set(memberId, new Member(maxLoans));
    return true;
  }

  checkout(day: number, memberId: string, isbn: string): number {
    const member = this.members.get(memberId);
    const title = this.titles.get(isbn);
    if (member === undefined || title === undefined || !member.canBorrow(isbn)) {
      return -1;
    }
    if (!title.reserved.delete(memberId) && title.free === 0) {
      return -1;
    }
    title.onLoan++;
    const due = day + this.loanDays;
    member.loans.set(isbn, due);
    return due;
  }

  returnBook(day: number, memberId: string, isbn: string): number {
    const member = this.members.get(memberId);
    const due = member?.loans.get(isbn);
    const title = this.titles.get(isbn);
    if (member === undefined || due === undefined || title === undefined) {
      return -1;
    }
    member.loans.delete(isbn);
    const fine = this.finePolicy.fine(due, day);
    member.fines += fine;
    title.onLoan--;
    title.assignFreeCopies();
    return fine;
  }

  placeHold(day: number, memberId: string, isbn: string): number {
    const member = this.members.get(memberId);
    const title = this.titles.get(isbn);
    if (member === undefined || title === undefined || title.free > 0) {
      return -1;
    }
    if (member.loans.has(isbn) || title.reserved.has(memberId) || title.waiting.includes(memberId)) {
      return -1;
    }
    title.waiting.push(memberId);
    return title.waiting.length;
  }

  cancelHold(day: number, memberId: string, isbn: string): boolean {
    const title = this.titles.get(isbn);
    if (title === undefined) {
      return false;
    }
    const position = title.waiting.indexOf(memberId);
    if (position >= 0) {
      title.waiting.splice(position, 1);
      return true;
    }
    if (title.reserved.delete(memberId)) {
      title.assignFreeCopies();
      return true;
    }
    return false;
  }

  renew(day: number, memberId: string, isbn: string): number {
    const member = this.members.get(memberId);
    const due = member?.loans.get(isbn);
    if (member === undefined || due === undefined) {
      return -1;
    }
    if (day > due || (this.titles.get(isbn)?.waiting.length ?? 0) > 0) {
      return -1;
    }
    member.loans.set(isbn, due + this.loanDays);
    return due + this.loanDays;
  }

  fines(day: number, memberId: string): number {
    return this.members.get(memberId)?.fines ?? -1;
  }

  payFine(day: number, memberId: string, amount: number): number {
    const member = this.members.get(memberId);
    if (member === undefined) {
      return -1;
    }
    member.fines = Math.max(0, member.fines - amount);
    return member.fines;
  }

  available(day: number, isbn: string): number {
    return this.titles.get(isbn)?.free ?? -1;
  }
}
