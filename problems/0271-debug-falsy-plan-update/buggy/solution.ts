// Debug: Falsy Plan Update. Some tests fail: find the bugs and fix them.

export function applyPlanUpdate(bodyJson: string): string {
  const body = JSON.parse(bodyJson);
  const plan = {
    priceCents: body.priceCents || 1900,
    trialDays: body.trialDays || 14,
    label: body.label || "Standard",
    seats: body.seats || 5,
    active: body.active || true,
  };
  if (body.capCents) {
    plan.priceCents = Math.min(plan.priceCents, body.capCents);
  }
  const { priceCents, trialDays, label, seats, active } = plan;
  return `price=${priceCents} trial=${trialDays} label=${label} seats=${seats} active=${active}`;
}
