// Who asks the assistant: the role of the staff member, which the support console sets once it has
// signed them in. A role decides which tools a conversation may use, and nothing said in the
// conversation changes it.

export const ROLES = ["trainee", "support", "admin"] as const;

export type Role = (typeof ROLES)[number];

const TOOLS_OF: Record<Role, ReadonlySet<string>> = {
  trainee: new Set(["search_kb"]),
  support: new Set(["search_kb", "lookup_order", "create_ticket"]),
  admin: new Set(["search_kb", "lookup_order", "create_ticket", "issue_refund"]),
};

export function isRole(value: unknown): value is Role {
  return typeof value === "string" && (ROLES as readonly string[]).includes(value);
}

export function mayUse(role: Role, tool: string): boolean {
  return TOOLS_OF[role].has(tool);
}
