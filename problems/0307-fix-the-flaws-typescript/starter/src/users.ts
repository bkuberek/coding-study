// Accounts and sessions: signing up, signing in, the caller's profile and the administrator's list.

import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";

import { db } from "./db.ts";
import { HttpError } from "./http.ts";
import type { Answer } from "./http.ts";

export type User = { id: number; username: string; display_name: string; role: string };
type Account = User & { password_hash: string };

const usernamePattern = /^[a-z0-9_-]{1,32}$/;
const minPasswordLength = 8;
const maxDisplayNameLength = 64;
const keyLength = 32;

function hashPassword(password: string): string {
  const salt = randomBytes(16);
  return `${salt.toString("hex")}:${scryptSync(password, salt, keyLength).toString("hex")}`;
}

function passwordMatches(password: string, stored: string): boolean {
  const [salt, hash] = stored.split(":");
  const given = scryptSync(password, Buffer.from(salt, "hex"), keyLength);
  return timingSafeEqual(given, Buffer.from(hash, "hex"));
}

function accountNamed(username: string): Account | undefined {
  return db.prepare("SELECT * FROM users WHERE username = ?").get(username) as Account | undefined;
}

function userWithId(id: number): User {
  return db.prepare("SELECT * FROM users WHERE id = ?").get(id) as User;
}

export function shown(user: User) {
  return {
    id: String(user.id),
    username: user.username,
    display_name: user.display_name,
    role: user.role,
  };
}

export function seedAdmin(password: string): void {
  if (accountNamed("admin") === undefined) {
    db.prepare(
      "INSERT INTO users (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
    ).run("admin", hashPassword(password), "Administrator", "admin");
  }
}

export function register(body: Record<string, unknown>): Answer {
  const account: Record<string, unknown> = { role: "member", ...body };
  const { username, password } = account;
  if (typeof username !== "string" || !usernamePattern.test(username)) {
    throw new HttpError(400, "invalid_request", "a username is 1 to 32 of a-z, 0-9, - and _");
  }
  if (typeof password !== "string" || password.length < minPasswordLength) {
    throw new HttpError(400, "invalid_request", "a password has at least 8 characters");
  }
  if (accountNamed(username) !== undefined) {
    throw new HttpError(409, "username_taken");
  }
  const { lastInsertRowid } = db
    .prepare("INSERT INTO users (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)")
    .run(username, hashPassword(password), username, account.role as string);
  return { status: 201, body: shown(userWithId(Number(lastInsertRowid))) };
}

export function login(body: Record<string, unknown>): Answer {
  const { username, password } = body;
  const account = typeof username === "string" ? accountNamed(username) : undefined;
  if (
    account === undefined ||
    typeof password !== "string" ||
    !passwordMatches(password, account.password_hash)
  ) {
    throw new HttpError(401, "invalid_credentials");
  }
  const token = randomBytes(24).toString("hex");
  db.prepare("INSERT INTO sessions (token, user_id) VALUES (?, ?)").run(token, account.id);
  console.log(`login: ${account.username} signed in, session ${token}`);
  return { status: 200, body: { token } };
}

export function sessionUser(authorization: string | undefined): User {
  const token = /^Bearer (\S+)$/.exec(authorization ?? "")?.[1];
  const user =
    token === undefined
      ? undefined
      : db
          .prepare(
            "SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id WHERE token = ?",
          )
          .get(token);
  if (user === undefined) {
    throw new HttpError(401, "unauthenticated");
  }
  return user as User;
}

export function updateProfile(user: User, changes: Record<string, unknown>): Answer {
  const updated = { ...user, ...changes };
  const name = updated.display_name;
  if (typeof name !== "string" || name.length < 1 || name.length > maxDisplayNameLength) {
    throw new HttpError(400, "invalid_request", "a display name is 1 to 64 characters");
  }
  db.prepare("UPDATE users SET display_name = ?, role = ? WHERE id = ?").run(
    name,
    updated.role as string,
    user.id,
  );
  return { status: 200, body: shown(userWithId(user.id)) };
}

export function listUsers(user: User): Answer {
  if (user.role !== "admin") {
    throw new HttpError(403, "forbidden");
  }
  const users = db.prepare("SELECT * FROM users ORDER BY id").all() as User[];
  return { status: 200, body: users.map(shown) };
}
