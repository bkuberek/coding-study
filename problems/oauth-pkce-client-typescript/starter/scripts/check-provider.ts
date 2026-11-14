// The stack's bootstrap: the provider imports its own realm as it starts, so there is no data to
// load here. This only checks, before your app starts, that the provider answers your app at
// OIDC_ISSUER with that issuer, and says plainly when it does not.

const issuer = process.env.OIDC_ISSUER;
if (issuer === undefined || issuer === "") {
  console.error("OIDC_ISSUER is not set");
  process.exit(1);
}

const url = `${issuer}/.well-known/openid-configuration`;
try {
  const response = await fetch(url, { signal: AbortSignal.timeout(10_000) });
  const found = response.ok ? ((await response.json()) as { issuer?: unknown }).issuer : undefined;
  if (found !== issuer) {
    console.error(`${url} answered ${response.status} without the issuer ${issuer}`);
    process.exit(1);
  }
  console.log(`the identity provider answers as ${issuer}`);
} catch (error) {
  console.error(`${url} did not answer: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
