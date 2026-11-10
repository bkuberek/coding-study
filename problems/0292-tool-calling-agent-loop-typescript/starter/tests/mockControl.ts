// Sets a mock server's scenario from a test, and reads what it received, through the mock server's
// control interface. `cstudy test` gives your tests its address and token. Only the scenarios in a
// mock server's API.md are there.

const control = process.env.CSTUDY_MOCK_CONTROL_URL;
const authorization = { Authorization: `Bearer ${process.env.CSTUDY_MOCK_CONTROL_TOKEN}` };

/** One request a mock server received: header names are lowercase. */
export type ReceivedRequest = {
  route: string | null;
  method: string;
  path: string;
  headers: Record<string, string>;
  body: string | null;
  status: number | null;
};

export async function setScenario(mock: string, scenario: string | null): Promise<void> {
  const response = await fetch(`${control}/mocks/${mock}/scenario`, {
    method: "PUT",
    headers: { ...authorization, "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!response.ok) {
    throw new Error(`cannot set ${scenario} on ${mock}: ${await response.text()}`);
  }
}

/** Clears every mock server's log and scenario. */
export async function resetMocks(): Promise<void> {
  await fetch(`${control}/reset`, { method: "POST", headers: authorization });
}

/** What `mock` received since the last reset, oldest first. */
export async function requestsTo(mock: string): Promise<ReceivedRequest[]> {
  const response = await fetch(`${control}/mocks/${mock}/log`, { headers: authorization });
  if (!response.ok) {
    throw new Error(`cannot read the log of ${mock}: ${await response.text()}`);
  }
  const log = (await response.json()) as { entries: ReceivedRequest[] };
  return log.entries;
}
