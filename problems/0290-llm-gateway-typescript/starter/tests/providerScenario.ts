// Sets a provider's behaviour from a test, through the mock server's control interface. `cstudy test`
// gives your tests its address and token. Only the scenarios in a provider's API.md are there.

const control = process.env.CSTUDY_MOCK_CONTROL_URL;
const authorization = { Authorization: `Bearer ${process.env.CSTUDY_MOCK_CONTROL_TOKEN}` };

export async function setScenario(provider: string, scenario: string | null): Promise<void> {
  const response = await fetch(`${control}/mocks/${provider}/scenario`, {
    method: "PUT",
    headers: { ...authorization, "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!response.ok) {
    throw new Error(`cannot set ${scenario} on ${provider}: ${await response.text()}`);
  }
}

export async function resetProviders(): Promise<void> {
  await fetch(`${control}/reset`, { method: "POST", headers: authorization });
}
