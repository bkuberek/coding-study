// A user's notes: writing, reading, deleting and searching them.

import { db } from "./db.ts";
import { HttpError, notFound } from "./http.ts";
import type { Answer } from "./http.ts";
import type { User } from "./users.ts";

type Note = { id: number; title: string; body: string };

const maxTitleLength = 200;

function shown(note: Note) {
  return { id: String(note.id), title: note.title, body: note.body };
}

export function createNote(user: User, fields: Record<string, unknown>): Answer {
  const { title, body } = fields;
  if (typeof title !== "string" || title.length < 1 || title.length > maxTitleLength) {
    throw new HttpError(400, "invalid_request", "a title is 1 to 200 characters");
  }
  if (typeof body !== "string") {
    throw new HttpError(400, "invalid_request", "a body is a string");
  }
  const { lastInsertRowid } = db
    .prepare("INSERT INTO notes (owner_id, title, body) VALUES (?, ?, ?)")
    .run(user.id, title, body);
  return { status: 201, body: shown({ id: Number(lastInsertRowid), title, body }) };
}

export function readNote(user: User, id: number): Answer {
  const note = db.prepare("SELECT * FROM notes WHERE id = ?").get(id) as Note | undefined;
  if (note === undefined) {
    throw notFound();
  }
  return { status: 200, body: shown(note) };
}

export function deleteNote(user: User, id: number): Answer {
  const { changes } = db.prepare("DELETE FROM notes WHERE id = ?").run(id);
  if (changes === 0) {
    throw notFound();
  }
  return { status: 204 };
}

export function searchNotes(user: User, text: string): Answer {
  const notes = db
    .prepare(
      `SELECT id, title FROM notes WHERE title LIKE '%${text}%' AND owner_id = ${user.id} ORDER BY id`,
    )
    .all() as Note[];
  return { status: 200, body: notes.map((note) => ({ id: String(note.id), title: note.title })) };
}
