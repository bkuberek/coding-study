// Sets the model services' behaviour from a test, through the mock server's control interface, and
// reads what they were sent. `cstudy test` gives your tests its address and token. Only the
// scenarios in vendors/embeddings/API.md and vendors/chat/API.md are there.

const control = process.env.CSTUDY_MOCK_CONTROL_URL;
const authorization = { Authorization: `Bearer ${process.env.CSTUDY_MOCK_CONTROL_TOKEN}` };

export type Service = "embeddings" | "chat";

export async function setScenario(service: Service, scenario: string | null): Promise<void> {
  const response = await fetch(`${control}/mocks/${service}/scenario`, {
    method: "PUT",
    headers: { ...authorization, "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!response.ok) {
    throw new Error(`cannot set ${scenario} on ${service}: ${await response.text()}`);
  }
}

// The JSON bodies a service received since the last reset, in the order they came.
export async function sentBodies(service: Service): Promise<unknown[]> {
  const response = await fetch(`${control}/mocks/${service}/log`, { headers: authorization });
  const log = (await response.json()) as { entries: { body: string | null }[] };
  return log.entries.map((entry) => (entry.body === null ? null : JSON.parse(entry.body)));
}

export async function resetProviders(): Promise<void> {
  await fetch(`${control}/reset`, { method: "POST", headers: authorization });
}
