interface PlanUpdate {
  readonly priceCents?: number | null;
  readonly trialDays?: number | null;
  readonly label?: string | null;
  readonly seats?: number | null;
  readonly active?: boolean | null;
  readonly capCents?: number | null;
}

export function applyPlanUpdate(bodyJson: string): string {
  const body = JSON.parse(bodyJson) as PlanUpdate;
  const plan = {
    priceCents: body.priceCents ?? 1900,
    trialDays: body.trialDays ?? 14,
    label: body.label ?? "Standard",
    seats: body.seats ?? 5,
    active: body.active ?? true,
  };
  if (body.capCents !== undefined && body.capCents !== null) {
    plan.priceCents = Math.min(plan.priceCents, body.capCents);
  }
  const { priceCents, trialDays, label, seats, active } = plan;
  return `price=${priceCents} trial=${trialDays} label=${label} seats=${seats} active=${active}`;
}
