// Where the identity provider is, and what it knows this app as. The provider has these two URLs
// registered for the client, exactly, and refuses any other.

export const ISSUER = required("OIDC_ISSUER");
export const CLIENT_ID = required("OIDC_CLIENT_ID");
export const REDIRECT_URI = "http://app:8000/callback";
export const POST_LOGOUT_REDIRECT_URI = "http://app:8000/";
export const PORT = Number(required("PORT"));

function required(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`${name} is not set`);
  }
  return value;
}
