// The identity provider's metadata, read once from its discovery document.

import { ISSUER } from "./config.ts";

export type ProviderMetadata = {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
  revocation_endpoint: string;
  end_session_endpoint: string;
};

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
