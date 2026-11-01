/**
 * The stylesheets of the page's chunks (`scripts/build.ts`): a module fetched on first use, such as
 * a view, a dialog or the run session, links its own stylesheet as it loads, and its chunk resolves
 * only once the stylesheet applies, so nothing it draws shows unstyled. The page's other styles are
 * app.css, which `page.html` links.
 */

const ASSETS = "/assets/";
const NONCE_META = 'meta[name="cstudy-csp-nonce"]';

/** Links `/assets/<path>`, with the page's CSP nonce; resolves once it applies. */
export function linkStylesheet(path: string): Promise<void> {
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = `${ASSETS}${path}`;
  link.nonce = document.querySelector<HTMLMetaElement>(NONCE_META)?.content ?? "";
  return new Promise((resolve, reject) => {
    link.addEventListener("load", () => resolve(), { once: true });
    link.addEventListener("error", () => reject(new Error(`could not load the stylesheet ${path}`)), { once: true });
    document.head.append(link);
  });
}
