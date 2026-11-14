interface StoredFile {
  readonly name: string;
  readonly size: number;
  readonly owner: string | null;
}

class User {
  capacity: number;
  used = 0;
  readonly files = new Set<string>();

  constructor(capacity: number) {
    this.capacity = capacity;
  }

  fits(size: number): boolean {
    return this.used + size <= this.capacity;
  }
}

function compareNames(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function largestFirst(a: StoredFile, b: StoredFile): number {
  return b.size - a.size || compareNames(a.name, b.name);
}

export class CloudStorage {
  private readonly files = new Map<string, StoredFile>();
  private readonly users = new Map<string, User>();
  private readonly backups = new Map<string, StoredFile[]>();

  // Level 1
  addFile(timestamp: number, name: string, size: number): boolean {
    if (this.files.has(name)) {
      return false;
    }
    this.store({ name, size, owner: null });
    return true;
  }

  getFileSize(timestamp: number, name: string): number {
    return this.files.get(name)?.size ?? -1;
  }

  deleteFile(timestamp: number, name: string): number {
    const file = this.files.get(name);
    if (file === undefined) {
      return -1;
    }
    this.discard(file);
    return file.size;
  }

  // Level 2
  listLargest(timestamp: number, prefix: string, limit: number): string[] {
    return [...this.files.values()]
      .filter((file) => file.name.startsWith(prefix))
      .sort(largestFirst)
      .slice(0, limit)
      .map((file) => `${file.name}(${file.size})`);
  }

  // Level 3
  addUser(timestamp: number, userId: string, capacity: number): boolean {
    if (this.users.has(userId)) {
      return false;
    }
    this.users.set(userId, new User(capacity));
    return true;
  }

  addFileBy(timestamp: number, userId: string, name: string, size: number): number {
    const user = this.users.get(userId);
    if (user === undefined || this.files.has(name) || !user.fits(size)) {
      return -1;
    }
    this.store({ name, size, owner: userId });
    return user.capacity - user.used;
  }

  updateCapacity(timestamp: number, userId: string, capacity: number): number {
    const user = this.users.get(userId);
    if (user === undefined) {
      return -1;
    }
    user.capacity = capacity;
    let removed = 0;
    for (const file of this.ownedBy(user).sort(largestFirst)) {
      if (user.used <= capacity) {
        break;
      }
      this.discard(file);
      removed++;
    }
    return removed;
  }

  // Level 4
  backupUser(timestamp: number, userId: string): number {
    const user = this.users.get(userId);
    if (user === undefined) {
      return -1;
    }
    const saved = this.ownedBy(user);
    this.backups.set(userId, saved);
    return saved.length;
  }

  restoreUser(timestamp: number, userId: string): number {
    const user = this.users.get(userId);
    if (user === undefined) {
      return -1;
    }
    for (const file of this.ownedBy(user)) {
      this.discard(file);
    }
    let restored = 0;
    const saved = [...(this.backups.get(userId) ?? [])].sort((a, b) => compareNames(a.name, b.name));
    for (const file of saved) {
      if (!this.files.has(file.name) && user.fits(file.size)) {
        this.store(file);
        restored++;
      }
    }
    return restored;
  }

  private ownedBy(user: User): StoredFile[] {
    const owned: StoredFile[] = [];
    for (const name of user.files) {
      const file = this.files.get(name);
      if (file !== undefined) {
        owned.push(file);
      }
    }
    return owned;
  }

  private store(file: StoredFile): void {
    this.files.set(file.name, file);
    const user = file.owner === null ? undefined : this.users.get(file.owner);
    if (user !== undefined) {
      user.used += file.size;
      user.files.add(file.name);
    }
  }

  private discard(file: StoredFile): void {
    this.files.delete(file.name);
    const user = file.owner === null ? undefined : this.users.get(file.owner);
    if (user !== undefined) {
      user.used -= file.size;
      user.files.delete(file.name);
    }
  }
}
