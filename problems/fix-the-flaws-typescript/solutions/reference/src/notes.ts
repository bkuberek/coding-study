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

// Every query that finds a note by its id also asks for its owner, so another user's note is
// exactly as absent as one that never existed.
export function readNote(user: User, id: number): Answer {
  const note = db.prepare("SELECT * FROM notes WHERE id = ? AND owner_id = ?").get(id, user.id) as
    | Note
    | undefined;
  if (note === undefined) {
    throw notFound();
  }
  return { status: 200, body: shown(note) };
}

export function deleteNote(user: User, id: number): Answer {
  const { changes } = db.prepare("DELETE FROM notes WHERE id = ? AND owner_id = ?").run(id, user.id);
  if (changes === 0) {
    throw notFound();
  }
  return { status: 204 };
}

// The text is a value bound to the query, never part of its SQL, so no character of it can change
// what the query means.
export function searchNotes(user: User, text: string): Answer {
  const notes = db
    .prepare(
      "SELECT id, title FROM notes WHERE owner_id = ? AND title LIKE '%' || ? || '%' ORDER BY id",
    )
    .all(user.id, text) as Note[];
  return { status: 200, body: notes.map((note) => ({ id: String(note.id), title: note.title })) };
}
