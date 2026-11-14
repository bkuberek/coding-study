// The primary provider's client. It knows whole answers only, so far.

const url = process.env.PRIMARY_LLM_URL;
const key = process.env.PRIMARY_LLM_KEY;

export type Usage = { prompt_tokens: number; completion_tokens: number };
export type Answer = { content: string; usage: Usage };

/** The provider gave no usable answer. */
export class ProviderError extends Error {}

type Completion = {
  choices: { message: { content: string } }[];
  usage: Usage;
};

export async function askPrimary(messages: unknown, maxTokens: number): Promise<Answer> {
  const response = await fetch(`${url}/v1/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "brisk-1", messages, max_tokens: maxTokens, stream: false }),
  });
  if (!response.ok) {
    throw new ProviderError(`the primary answered ${response.status}`);
  }
  const completion = (await response.json()) as Completion;
  const { prompt_tokens, completion_tokens } = completion.usage;
  return { content: completion.choices[0].message.content, usage: { prompt_tokens, completion_tokens } };
}
