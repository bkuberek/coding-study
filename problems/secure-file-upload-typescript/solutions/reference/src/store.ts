// Where files and their records live, under the data directory. A file's bytes sit in quarantine
// until a scan says they are clean, and only then move to where they are served from. Every path
// is built from an id this service made, never from anything the upload carried.

import { randomBytes } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync } from "node:fs";
import { readFile, rename, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";

export type ScanStatus = "pending" | "clean" | "infected";

export type StoredFile = {
  id: string;
  owner: string;
  name: string;
  size: number;
  sha256: string;
  mime: string;
  inline: boolean;
  status: ScanStatus;
};

export type NewFile = Omit<StoredFile, "id" | "status">;

export class FileStore {
  readonly #records: string;
  readonly #quarantine: string;
  readonly #released: string;
  readonly #quota: number;
  readonly #files = new Map<string, StoredFile>();

  constructor(root: string, quota: number) {
    this.#records = join(root, "records");
    this.#quarantine = join(root, "quarantine");
    this.#released = join(root, "files");
    this.#quota = quota;
    for (const folder of [this.#records, this.#quarantine, this.#released]) {
      mkdirSync(folder, { recursive: true });
    }
    for (const entry of readdirSync(this.#records)) {
      const file = JSON.parse(readFileSync(join(this.#records, entry), "utf8")) as StoredFile;
      this.#files.set(file.id, file);
    }
  }

  /** The bytes a user keeps. An infected file's bytes are gone, so it counts for nothing. */
  usage(owner: string): number {
    let used = 0;
    for (const file of this.#files.values()) {
      if (file.owner === owner && file.status !== "infected") {
        used += file.size;
      }
    }
    return used;
  }

  /**
   * Takes the file's room in its owner's quota, as pending, before anything is awaited: two
   * uploads at once cannot both fit in room for one. Null when it does not fit.
   */
  reserve(file: NewFile): StoredFile | null {
    if (this.usage(file.owner) + file.size > this.#quota) {
      return null;
    }
    const stored: StoredFile = { ...file, id: randomBytes(16).toString("hex"), status: "pending" };
    this.#files.set(stored.id, stored);
    return stored;
  }

  /** The owner's file with this id; another user's file is not theirs to know about. */
  find(owner: string, id: string): StoredFile | undefined {
    const file = this.#files.get(id);
    return file?.owner === owner ? file : undefined;
  }

  /** Any user's file, for a link whose signature already proved its owner shared it. */
  findShared(id: string): StoredFile | undefined {
    return this.#files.get(id);
  }

  async quarantine(file: StoredFile, bytes: Buffer): Promise<void> {
    await writeFile(join(this.#quarantine, file.id), bytes);
    await this.#save(file);
  }

  quarantined(file: StoredFile): Promise<Buffer> {
    return readFile(join(this.#quarantine, file.id));
  }

  released(file: StoredFile): Promise<Buffer> {
    return readFile(join(this.#released, file.id));
  }

  /** Moves the bytes out of quarantine first, so the file is never clean where nothing is. */
  async release(file: StoredFile): Promise<void> {
    await rename(join(this.#quarantine, file.id), join(this.#released, file.id));
    file.status = "clean";
    await this.#save(file);
  }

  /** Keeps the record, so its owner can see what happened, and deletes the bytes. */
  async condemn(file: StoredFile): Promise<void> {
    file.status = "infected";
    await rm(join(this.#quarantine, file.id), { force: true });
    await this.#save(file);
  }

  /** Deletes the file and its record, wherever its bytes are. */
  async forget(file: StoredFile): Promise<void> {
    this.#files.delete(file.id);
    await Promise.all([
      rm(join(this.#quarantine, file.id), { force: true }),
      rm(join(this.#released, file.id), { force: true }),
      rm(this.#recordPath(file), { force: true }),
    ]);
  }

  #save(file: StoredFile): Promise<void> {
    return writeFile(this.#recordPath(file), JSON.stringify(file));
  }

  #recordPath(file: StoredFile): string {
    return join(this.#records, `${file.id}.json`);
  }
}
