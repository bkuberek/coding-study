interface Family {
  current: string;
  expiresAt: number;
  lastSpent: string | null;
  graceEndsAt: number;
  revoked: boolean;
}

export class RefreshTokenStore {
  private readonly ttlSeconds: number;
  private readonly graceSeconds: number;
  private readonly families = new Map<string, Family>();
  // Every token ever issued, spent ones included: a spent token must still find its family.
  private readonly familyOfToken = new Map<string, Family>();

  constructor(ttlSeconds: number, graceSeconds: number) {
    this.ttlSeconds = ttlSeconds;
    this.graceSeconds = graceSeconds;
  }

  issue(familyId: string, tokenId: string, now: number): boolean {
    if (this.families.has(familyId) || this.familyOfToken.has(tokenId)) {
      return false;
    }
    const family: Family = {
      current: tokenId,
      expiresAt: now + this.ttlSeconds,
      lastSpent: null,
      graceEndsAt: 0,
      revoked: false,
    };
    this.families.set(familyId, family);
    this.familyOfToken.set(tokenId, family);
    return true;
  }

  rotate(tokenId: string, newTokenId: string, now: number): string {
    const family = this.familyOfToken.get(tokenId);
    if (family === undefined) {
      return "unknown";
    }
    if (family.revoked) {
      return "revoked";
    }
    if (tokenId === family.current) {
      if (now >= family.expiresAt) {
        return "expired";
      }
      family.lastSpent = family.current;
      family.graceEndsAt = now + this.graceSeconds;
      family.current = newTokenId;
      family.expiresAt = now + this.ttlSeconds;
      this.familyOfToken.set(newTokenId, family);
      return "rotated";
    }
    if (tokenId === family.lastSpent && now < family.graceEndsAt) {
      return "grace-retry";
    }
    family.revoked = true;
    return "reuse-detected";
  }

  activeToken(familyId: string, now: number): string {
    const family = this.families.get(familyId);
    if (family === undefined || family.revoked || now >= family.expiresAt) {
      return "";
    }
    return family.current;
  }
}
