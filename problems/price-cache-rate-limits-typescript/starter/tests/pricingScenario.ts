// Sets the pricing engine's behaviour from a test, through the mock server's control interface.
// `cstudy test` gives your tests its address and token. Only the scenarios in vendors/pricing/API.md
// are there.

const control = process.env.CSTUDY_MOCK_CONTROL_URL;
const authorization = { Authorization: `Bearer ${process.env.CSTUDY_MOCK_CONTROL_TOKEN}` };

export async function setScenario(scenario: string | null): Promise<void> {
  const response = await fetch(`${control}/mocks/pricing/scenario`, {
    method: "PUT",
    headers: { ...authorization, "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!response.ok) {
    throw new Error(`cannot set ${scenario} on the engine: ${await response.text()}`);
  }
}

// How many requests the engine received for one route of its config, since the last reset.
export async function engineCalls(route: string): Promise<number> {
  const response = await fetch(`${control}/mocks/pricing/log`, { headers: authorization });
  const log = (await response.json()) as { entries: { route: string | null }[] };
  return log.entries.filter((entry) => entry.route === route).length;
}

export async function resetEngine(): Promise<void> {
  await fetch(`${control}/reset`, { method: "POST", headers: authorization });
}
