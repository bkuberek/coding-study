// Reading the browser's cookies and writing the ones this app sets. Every cookie here is for this
// app alone: HttpOnly, so a page's script cannot read it, and SameSite=Lax, so another site cannot
// send it with a form it posts. The sandbox has no TLS, so none is Secure; a real app's would be.

export function readCookies(header: string | undefined): Map<string, string> {
  const cookies = new Map<string, string>();
  for (const pair of (header ?? "").split(";")) {
    const separator = pair.indexOf("=");
    if (separator > 0) {
      cookies.set(pair.slice(0, separator).trim(), pair.slice(separator + 1).trim());
    }
  }
  return cookies;
}

/** A `Set-Cookie` value that keeps `name` for `maxAgeSeconds`. */
export function cookie(name: string, value: string, maxAgeSeconds: number): string {
  return `${name}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAgeSeconds}`;
}

/** A `Set-Cookie` value that makes the browser forget `name`. */
export function clearedCookie(name: string): string {
  return cookie(name, "", 0);
}
