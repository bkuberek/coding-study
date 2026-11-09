// The campus portal: its users sign in with the campus identity provider, and the app keeps a
// session of its own for each of them, behind a cookie. The browser only ever holds random ids:
// the tokens stay here, and none of them is ever printed.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { CLIENT_ID, ISSUER, PORT, REDIRECT_URI } from "./config.ts";
import { clearedCookie, cookie, readCookies } from "./cookies.ts";
import { InvalidToken, verifyIdToken } from "./idToken.ts";
import type { IdClaims } from "./idToken.ts";
import { RemoteKeySet } from "./jwks.ts";
import { challengeOf, randomValue } from "./pkce.ts";
import {
  TokenRefused,
  endSessionUrl,
  exchangeCode,
  providerMetadata,
  refreshTokens,
  revoke,
} from "./provider.ts";
import { MemoryStore } from "./store.ts";

/** Who is signed in, from the claims of their ID token. */
export type User = { sub: string; username: string; email: string };
type Session = { user: User; refreshToken: string; idToken: string };
/** One login in progress: what the callback must see again, and the verifier only this app knows. */
type LoginAttempt = { state: string; nonce: string; verifier: string; expiresAt: number };

/** What a route answers: a status, and a JSON body, a redirect or cookies to set. */
type Answer = { status: number; body?: unknown; location?: string; cookies?: string[] };
type Route = { method: string; handle: (request: IncomingMessage, url: URL) => Promise<Answer> };

const SESSION_COOKIE = "session";
const SESSION_TTL_S = 8 * 3600;
const LOGIN_COOKIE = "login";
const LOGIN_TTL_S = 600;
const NOT_SIGNED_IN: Answer = { status: 401, body: { error: "not signed in" } };
const sessions = new MemoryStore<Session>();
const attempts = new MemoryStore<LoginAttempt>();
const keys = new RemoteKeySet(async () => (await providerMetadata()).jwks_uri);

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

function sessionIdOf(request: IncomingMessage): string | undefined {
  return readCookies(request.headers.cookie).get(SESSION_COOKIE);
}

function sessionOf(request: IncomingMessage): Session | undefined {
  return sessions.get(sessionIdOf(request));
}

function userOf(claims: IdClaims): User {
  return {
    sub: claims.sub,
    username: String(claims.preferred_username ?? ""),
    email: String(claims.email ?? ""),
  };
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function home(request: IncomingMessage): Promise<Answer> {
  return { status: 200, body: { app: "campus portal", signed_in: sessionOf(request) !== undefined } };
}

async function login(): Promise<Answer> {
  const { authorization_endpoint } = await providerMetadata();
  const attempt: LoginAttempt = {
    state: randomValue(),
    nonce: randomValue(),
    verifier: randomValue(),
    expiresAt: nowSeconds() + LOGIN_TTL_S,
  };
  const url = new URL(authorization_endpoint);
  url.search = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    redirect_uri: REDIRECT_URI,
    scope: "openid",
    state: attempt.state,
    nonce: attempt.nonce,
    code_challenge: challengeOf(attempt.verifier),
    code_challenge_method: "S256",
  }).toString();
  const loginCookie = cookie(LOGIN_COOKIE, attempts.put(attempt), LOGIN_TTL_S);
  return { status: 302, location: url.href, cookies: [loginCookie] };
}

/** The browser back from the provider. The login attempt is taken whatever happens, so a callback
 * works once; the state is checked before the code is spent; the ID token before it is believed. */
async function callback(request: IncomingMessage, url: URL): Promise<Answer> {
  const attempt = attempts.take(readCookies(request.headers.cookie).get(LOGIN_COOKIE));
  const forgetAttempt = clearedCookie(LOGIN_COOKIE);
  const refuse = (status: number, error: string): Answer => {
    console.warn(`login refused: ${error}`);
    return { status, body: { error }, cookies: [forgetAttempt] };
  };
  if (attempt === undefined || attempt.expiresAt < nowSeconds()) {
    return refuse(400, "no login in progress");
  }
  if (url.searchParams.get("state") !== attempt.state) {
    return refuse(400, "the state is not this login's");
  }
  const code = url.searchParams.get("code");
  if (code === null) {
    return refuse(400, "the provider sent no code");
  }
  let tokens;
  try {
    tokens = await exchangeCode(code, attempt.verifier);
  } catch (error) {
    if (error instanceof TokenRefused) {
      return refuse(400, `the provider refused the code (${error.message})`);
    }
    throw error;
  }
  if (tokens.id_token === undefined || tokens.refresh_token === undefined) {
    return refuse(502, "the provider sent no ID token or refresh token");
  }
  let claims;
  try {
    claims = await verifyIdToken(tokens.id_token, keys, {
      issuer: ISSUER,
      clientId: CLIENT_ID,
      nonce: attempt.nonce,
      nowSeconds: nowSeconds(),
    });
  } catch (error) {
    if (error instanceof InvalidToken) {
      return refuse(401, `the ID token is not valid: ${error.message}`);
    }
    throw error;
  }
  const session: Session = {
    user: userOf(claims),
    refreshToken: tokens.refresh_token,
    idToken: tokens.id_token,
  };
  const sessionCookie = cookie(SESSION_COOKIE, sessions.put(session), SESSION_TTL_S);
  return { status: 302, location: "/", cookies: [forgetAttempt, sessionCookie] };
}

async function me(request: IncomingMessage): Promise<Answer> {
  const session = sessionOf(request);
  return session === undefined ? NOT_SIGNED_IN : { status: 200, body: session.user };
}

/** Each refresh spends the refresh token it sends, so the session keeps the one that comes back. */
async function refresh(request: IncomingMessage): Promise<Answer> {
  const id = sessionIdOf(request);
  const session = sessions.get(id);
  if (id === undefined || session === undefined) {
    return NOT_SIGNED_IN;
  }
  try {
    const tokens = await refreshTokens(session.refreshToken);
    sessions.set(id, { ...session, refreshToken: tokens.refresh_token ?? session.refreshToken });
    return { status: 204 };
  } catch (error) {
    if (error instanceof TokenRefused) {
      sessions.delete(id);
      console.warn(`session ended by the provider: ${error.message}`);
      return {
        status: 401,
        body: { error: "session ended" },
        cookies: [clearedCookie(SESSION_COOKIE)],
      };
    }
    throw error;
  }
}

/** Ends the session here, revokes it at the provider, and sends the browser to end the provider's
 * own session too, which would otherwise sign the next login in without asking. */
async function logout(request: IncomingMessage): Promise<Answer> {
  const session = sessions.take(sessionIdOf(request));
  if (session === undefined) {
    return NOT_SIGNED_IN;
  }
  await revoke(session.refreshToken).catch((error: unknown) => {
    console.warn(`revocation failed: ${messageOf(error)}`);
  });
  const location = await endSessionUrl(session.idToken);
  return { status: 302, location, cookies: [clearedCookie(SESSION_COOKIE)] };
}

const ROUTES: Record<string, Route> = {
  "/health": { method: "GET", handle: async () => ({ status: 200, body: { status: "ok" } }) },
  "/": { method: "GET", handle: home },
  "/login": { method: "GET", handle: login },
  "/callback": { method: "GET", handle: callback },
  "/me": { method: "GET", handle: me },
  "/refresh": { method: "POST", handle: refresh },
  "/logout": { method: "POST", handle: logout },
};

async function route(request: IncomingMessage): Promise<Answer> {
  const url = new URL(request.url ?? "/", "http://app");
  const found = Object.hasOwn(ROUTES, url.pathname) ? ROUTES[url.pathname] : undefined;
  if (found === undefined) {
    return { status: 404, body: { error: "not found" } };
  }
  if (request.method !== found.method) {
    return { status: 405, body: { error: "method not allowed" } };
  }
  return found.handle(request, url);
}

function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  if (answer.location !== undefined) {
    response.setHeader("Location", answer.location);
  }
  if (answer.cookies !== undefined) {
    response.setHeader("Set-Cookie", answer.cookies);
  }
  if (answer.body === undefined) {
    response.end();
    return;
  }
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  route(request).then(
    (answer) => send(response, answer),
    (error: unknown) => {
      console.error(`internal error: ${messageOf(error)}`);
      send(response, { status: 500, body: { error: "internal error" } });
    },
  );
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`listening on ${PORT}`);
});
