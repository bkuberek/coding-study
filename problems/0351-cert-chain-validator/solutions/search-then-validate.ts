const OK = "ok";
const KEY_CERT_SIGN = "keyCertSign";
const NO_LIMIT = -1;
const MIN_LABELS_AFTER_WILDCARD = 2;

class Certificate {
  readonly subject: string;
  readonly issuer: string;
  readonly notBefore: number;
  readonly notAfter: number;
  readonly dnsNames: string[];
  // No call to setConstraints: neither basicConstraints nor keyUsage is present.
  isCa = false;
  pathLen = NO_LIMIT;
  keyUsage: string[] = [];

  constructor(subject: string, issuer: string, notBefore: number, notAfter: number, dnsNames: string[]) {
    this.subject = subject;
    this.issuer = issuer;
    this.notBefore = notBefore;
    this.notAfter = notAfter;
    this.dnsNames = [...dnsNames];
  }

  isSelfIssued(): boolean {
    return this.subject === this.issuer;
  }
}

/** RFC 9525 section 6.3, plus this problem's rule of two labels after a wildcard. */
function nameMatches(presented: string, hostname: string): boolean {
  const presentedLabels = presented.toLowerCase().split(".");
  const hostLabels = hostname.toLowerCase().split(".");
  if (!presented.includes("*")) {
    return presentedLabels.join(".") === hostLabels.join(".");
  }
  const [wildcard, ...rest] = presentedLabels;
  if (wildcard !== "*" || rest.some((label) => label.includes("*")) || rest.length < MIN_LABELS_AFTER_WILDCARD) {
    return false;
  }
  return hostLabels.length === rest.length + 1 && hostLabels.slice(1).join(".") === rest.join(".");
}

function compareChains(a: string[], b: string[]): number {
  if (a.length !== b.length) {
    return a.length - b.length;
  }
  for (let index = 0; index < a.length; index++) {
    if (a[index] !== b[index]) {
      return a[index] < b[index] ? -1 : 1;
    }
  }
  return 0;
}

export class ChainValidator {
  private readonly certificates = new Map<string, Certificate>();
  private readonly signatures = new Map<string, boolean>();
  private readonly anchors = new Set<string>();
  private readonly revoked = new Set<string>();

  // Level 1
  addCertificate(
    certId: string,
    subject: string,
    issuer: string,
    notBefore: number,
    notAfter: number,
    dnsNames: string[],
  ): boolean {
    if (this.certificates.has(certId)) {
      return false;
    }
    this.certificates.set(certId, new Certificate(subject, issuer, notBefore, notAfter, dnsNames));
    return true;
  }

  matchedName(certId: string, hostname: string): string {
    const certificate = this.certificates.get(certId);
    return certificate?.dnsNames.find((name) => nameMatches(name, hostname)) ?? "";
  }

  checkLeaf(certId: string, hostname: string, now: number): string {
    const certificate = this.certificates.get(certId);
    if (certificate === undefined) {
      return "unknown-certificate";
    }
    const reason = validity(certificate, now);
    if (reason !== "") {
      return reason;
    }
    return this.matchedName(certId, hostname) === "" ? "hostname-mismatch" : OK;
  }

  // Level 2
  addSignature(signerId: string, certId: string, valid: boolean): void {
    this.signatures.set(signatureKey(signerId, certId), valid);
  }

  addTrustAnchor(certId: string): boolean {
    if (!this.certificates.has(certId) || this.anchors.has(certId)) {
      return false;
    }
    this.anchors.add(certId);
    return true;
  }

  buildChain(leafId: string): string[] {
    return this.candidates(leafId)[0] ?? [];
  }

  // Level 3
  setConstraints(certId: string, isCa: boolean, pathLen: number, keyUsage: string[]): boolean {
    const certificate = this.certificates.get(certId);
    if (certificate === undefined) {
      return false;
    }
    certificate.isCa = isCa;
    certificate.pathLen = pathLen;
    certificate.keyUsage = [...keyUsage];
    return true;
  }

  validatePath(path: string[], hostname: string, now: number): string[] {
    const problem = this.structure(path) ?? this.process(path, now);
    if (problem !== null) {
      return problem;
    }
    if (this.matchedName(path[0], hostname) === "") {
      return ["hostname-mismatch", path[0]];
    }
    return [OK, ""];
  }

  // Level 4
  revoke(certId: string): boolean {
    if (!this.certificates.has(certId) || this.revoked.has(certId)) {
      return false;
    }
    this.revoked.add(certId);
    return true;
  }

  verify(leafId: string, hostname: string, now: number): string[][] {
    if (!this.certificates.has(leafId)) {
      return [["unknown-certificate", leafId]];
    }
    const candidates = this.candidates(leafId);
    if (candidates.length === 0) {
      return [["no-path", leafId]];
    }
    const rows: string[][] = [];
    for (const chain of candidates) {
      const outcome = this.validatePath(chain, hostname, now);
      rows.push([...outcome, ...chain]);
      if (outcome[0] === OK) {
        break;
      }
    }
    return rows;
  }

  // The search: every chain from the leaf to the first trust anchor, shortest first.
  private issuersOf(certId: string): string[] {
    const issuer = this.certificates.get(certId)!.issuer;
    const signers: string[] = [];
    for (const [signerId, signer] of this.certificates) {
      if (signer.subject === issuer && this.signatures.get(signatureKey(signerId, certId)) === true) {
        signers.push(signerId);
      }
    }
    return signers;
  }

  private candidates(leafId: string): string[][] {
    if (!this.certificates.has(leafId)) {
      return [];
    }
    const chains: string[][] = [];
    const extend = (chain: string[]): void => {
      const last = chain[chain.length - 1];
      if (this.anchors.has(last)) {
        chains.push([...chain]);
        return;
      }
      for (const signerId of this.issuersOf(last)) {
        if (!chain.includes(signerId)) {
          chain.push(signerId);
          extend(chain);
          chain.pop();
        }
      }
    };
    extend([leafId]);
    return chains.sort(compareChains);
  }

  // Validation, in the order of RFC 5280 section 6.1.
  private structure(path: string[]): string[] | null {
    const unknown = path.find((certId) => !this.certificates.has(certId));
    if (unknown !== undefined) {
      return ["unknown-certificate", unknown];
    }
    const seen = new Set<string>();
    for (const certId of path) {
      if (seen.has(certId)) {
        return ["repeated-certificate", certId];
      }
      seen.add(certId);
    }
    const anchor = path[path.length - 1];
    return this.anchors.has(anchor) ? null : ["not-trusted", anchor];
  }

  private process(path: string[], now: number): string[] | null {
    const fromAnchor = [...path].reverse();
    let maxPathLength = path.length - 1;
    for (let position = 1; position < fromAnchor.length; position++) {
      const signerId = fromAnchor[position - 1];
      const certId = fromAnchor[position];
      const signer = this.certificates.get(signerId)!;
      const certificate = this.certificates.get(certId)!;
      if (this.signatures.get(signatureKey(signerId, certId)) !== true) {
        return ["bad-signature", certId];
      }
      const reason = validity(certificate, now);
      if (reason !== "") {
        return [reason, certId];
      }
      if (this.revoked.has(certId)) {
        return ["revoked", certId];
      }
      if (certificate.issuer !== signer.subject) {
        return ["name-mismatch", certId];
      }
      if (position === fromAnchor.length - 1) {
        break;
      }
      if (!certificate.isCa) {
        return ["not-a-ca", certId];
      }
      if (!certificate.isSelfIssued()) {
        if (maxPathLength <= 0) {
          return ["path-too-long", certId];
        }
        maxPathLength -= 1;
      }
      if (certificate.pathLen !== NO_LIMIT && certificate.pathLen < maxPathLength) {
        maxPathLength = certificate.pathLen;
      }
      if (certificate.keyUsage.length > 0 && !certificate.keyUsage.includes(KEY_CERT_SIGN)) {
        return ["missing-key-cert-sign", certId];
      }
    }
    return null;
  }
}

function validity(certificate: Certificate, now: number): string {
  if (now < certificate.notBefore) {
    return "not-yet-valid";
  }
  if (now > certificate.notAfter) {
    return "expired";
  }
  return "";
}

function signatureKey(signerId: string, certId: string): string {
  return JSON.stringify([signerId, certId]);
}
