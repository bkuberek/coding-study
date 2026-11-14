// The identity provider: its metadata, read once from its discovery document, and the calls this
// app makes to it over the back channel. Each is a form POST that names the client, since a public
// client has no secret. No error raised here holds a token, so any of them can be logged.

import { CLIENT_ID, ISSUER, POST_LOGOUT_REDIRECT_URI, REDIRECT_URI } from "./config.ts";

export type ProviderMetadata = {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
  revocation_endpoint: string;
  end_session_endpoint: string;
};

/** A token endpoint's answer: a refresh may leave out `id_token`, and in principle `refresh_token`. */
export type Tokens = { access_token: string; id_token?: string; refresh_token?: string };

/** The provider answered and refused: a spent or wrong code, or a login that has ended. */
export class TokenRefused extends Error {}

const TIMEOUT_MS = 5000;
let metadata: Promise<ProviderMetadata> | undefined;

/** The provider's endpoints, fetched on first use and kept; a failed fetch is tried again. */
export function providerMetadata(): Promise<ProviderMetadata> {
  metadata ??= fetchMetadata().catch((error: unknown) => {
    metadata = undefined;
    throw error;
  });
  return metadata;
}

async function fetchMetadata(): Promise<ProviderMetadata> {
  const url = `${ISSUER}/.well-known/openid-configuration`;
  const response = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_MS) });
  if (!response.ok) {
    throw new Error(`discovery answered ${response.status}`);
  }
  return (await response.json()) as ProviderMetadata;
}

export async function exchangeCode(code: string, verifier: string): Promise<Tokens> {
  const { token_endpoint } = await providerMetadata();
  return asTokens(
    await postForm(token_endpoint, {
      grant_type: "authorization_code",
      code,
      redirect_uri: REDIRECT_URI,
      client_id: CLIENT_ID,
      code_verifier: verifier,
    }),
  );
}

export async function refreshTokens(refreshToken: string): Promise<Tokens> {
  const { token_endpoint } = await providerMetadata();
  return asTokens(
    await postForm(token_endpoint, {
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: CLIENT_ID,
    }),
  );
}

export async function revoke(refreshToken: string): Promise<void> {
  const { revocation_endpoint } = await providerMetadata();
  await postForm(revocation_endpoint, {
    token: refreshToken,
    token_type_hint: "refresh_token",
    client_id: CLIENT_ID,
  });
}

/** Where the browser goes to end the provider's own session, and comes back from at once. */
export async function endSessionUrl(idToken: string): Promise<string> {
  const { end_session_endpoint } = await providerMetadata();
  const url = new URL(end_session_endpoint);
  url.search = new URLSearchParams({
    id_token_hint: idToken,
    post_logout_redirect_uri: POST_LOGOUT_REDIRECT_URI,
    client_id: CLIENT_ID,
  }).toString();
  return url.href;
}

async function postForm(url: string, fields: Record<string, string>): Promise<unknown> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(fields),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  const text = await response.text();
  const body = parsed(text);
  if (response.status === 400 || response.status === 401) {
    throw new TokenRefused(reasonOf(body) ?? `answered ${response.status}`);
  }
  if (!response.ok) {
    throw new Error(`the provider answered ${response.status}`);
  }
  return body;
}

/** The body as JSON, or null. Never a parse error, whose message would quote the body. */
function parsed(text: string): unknown {
  if (text === "") {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function reasonOf(body: unknown): string | undefined {
  const { error, error_description } = (body ?? {}) as Record<string, unknown>;
  return typeof error === "string" ? `${error}: ${String(error_description ?? "")}` : undefined;
}

function asTokens(body: unknown): Tokens {
  const tokens = body as Partial<Tokens> | null;
  if (typeof tokens?.access_token !== "string") {
    throw new Error("the token endpoint's answer holds no access token");
  }
  return tokens as Tokens;
}
