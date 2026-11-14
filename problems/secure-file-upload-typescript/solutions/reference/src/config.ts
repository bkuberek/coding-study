// What the service reads from its environment.

function setting(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`${name} is not set`);
  }
  return value;
}

export const PORT = Number(setting("PORT"));
export const DATA_DIR = setting("CSTUDY_DATA_DIR");
/** The most an upload's request body may hold, the JSON around the file included. */
export const MAX_BODY_BYTES = Number(setting("MAX_BODY_BYTES"));
/** The most a user may keep, counted in the bytes of their pending and clean files. */
export const QUOTA_BYTES = Number(setting("QUOTA_BYTES"));
export const SCANNER_URL = setting("SCANNER_URL");
export const SCANNER_API_KEY = setting("SCANNER_API_KEY");
export const LINK_SIGNING_KEY = setting("LINK_SIGNING_KEY");
