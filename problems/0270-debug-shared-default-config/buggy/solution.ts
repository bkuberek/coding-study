// Debug: Shared Default Config. Some tests fail: find the bug and fix it.

interface Settings {
  retries: number;
  limits: {
    requestsPerMinute: number;
    perRoute: Record<string, number>;
  };
  notifyChannels: string[];
}

const DEFAULT_SETTINGS: Settings = {
  retries: 3,
  limits: { requestsPerMinute: 60, perRoute: { "/search": 10 } },
  notifyChannels: ["email"],
};

export class TenantSettings {
  readonly #tenants = new Map<string, Settings>();

  #settingsOf(tenant: string): Settings {
    let settings = this.#tenants.get(tenant);
    if (settings === undefined) {
      settings = { ...DEFAULT_SETTINGS };
      this.#tenants.set(tenant, settings);
    }
    return settings;
  }

  setRetries(tenant: string, retries: number): void {
    this.#settingsOf(tenant).retries = retries;
  }

  setRequestsPerMinute(tenant: string, requestsPerMinute: number): void {
    this.#settingsOf(tenant).limits.requestsPerMinute = requestsPerMinute;
  }

  setRouteLimit(tenant: string, route: string, limit: number): void {
    this.#settingsOf(tenant).limits.perRoute[route] = limit;
  }

  addChannel(tenant: string, channel: string): void {
    this.#settingsOf(tenant).notifyChannels.push(channel);
  }

  reset(tenant: string): void {
    this.#tenants.delete(tenant);
  }

  retries(tenant: string): number {
    return this.#settingsOf(tenant).retries;
  }

  requestsPerMinute(tenant: string): number {
    return this.#settingsOf(tenant).limits.requestsPerMinute;
  }

  routeLimit(tenant: string, route: string): number {
    return this.#settingsOf(tenant).limits.perRoute[route] ?? -1;
  }

  channels(tenant: string): string[] {
    return this.#settingsOf(tenant).notifyChannels;
  }
}
