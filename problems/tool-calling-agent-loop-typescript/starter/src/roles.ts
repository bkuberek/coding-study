// Who asks the assistant: the role of the staff member, which the support console sets once it has
// signed them in.

export const ROLES = ["trainee", "support", "admin"] as const;

export type Role = (typeof ROLES)[number];

export function isRole(value: unknown): value is Role {
  return typeof value === "string" && (ROLES as readonly string[]).includes(value);
}
