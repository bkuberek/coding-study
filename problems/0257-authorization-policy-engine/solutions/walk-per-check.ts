const EVERY = "*";
const SEPARATOR = "/";

interface Rule {
  effect: string;
  action: string;
  resource: string;
}

function coveringResources(resource: string): Set<string> {
  const covering = new Set([EVERY, resource]);
  let end = resource.lastIndexOf(SEPARATOR);
  while (end !== -1) {
    covering.add(resource.slice(0, end));
    end = resource.lastIndexOf(SEPARATOR, end - 1);
  }
  return covering;
}

function addTo<V>(map: Map<string, V[]>, key: string, value: V): void {
  const values = map.get(key);
  if (values === undefined) {
    map.set(key, [value]);
  } else {
    values.push(value);
  }
}

export class PolicyEngine {
  private readonly parents = new Map<string, string[]>();
  private readonly rolesOf = new Map<string, string[]>();
  private readonly rulesOf = new Map<string, Rule[]>();

  inherit(role: string, parentRole: string): void {
    addTo(this.parents, role, parentRole);
  }

  assignRole(principal: string, role: string): void {
    addTo(this.rolesOf, principal, role);
  }

  addRule(role: string, effect: string, action: string, resource: string): void {
    addTo(this.rulesOf, role, { effect, action, resource });
  }

  check(principal: string, action: string, resource: string): string {
    const covering = coveringResources(resource);
    let decision = "default-deny";
    for (const role of this.effectiveRoles(principal)) {
      for (const rule of this.rulesOf.get(role) ?? []) {
        if ((rule.action === action || rule.action === EVERY) && covering.has(rule.resource)) {
          if (rule.effect === "deny") {
            return "deny";
          }
          decision = "allow";
        }
      }
    }
    return decision;
  }

  // One visited set for the whole walk: a cycle ends, and a diamond is walked once.
  private effectiveRoles(principal: string): Set<string> {
    const seen = new Set<string>();
    const pending = [...(this.rolesOf.get(principal) ?? [])];
    while (pending.length > 0) {
      const role = pending.pop()!;
      if (!seen.has(role)) {
        seen.add(role);
        pending.push(...(this.parents.get(role) ?? []));
      }
    }
    return seen;
  }
}
