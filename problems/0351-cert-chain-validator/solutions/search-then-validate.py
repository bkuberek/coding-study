OK = "ok"
KEY_CERT_SIGN = "keyCertSign"
NO_LIMIT = -1
MIN_LABELS_AFTER_WILDCARD = 2


class _Certificate:
    __slots__ = (
        "dns_names",
        "is_ca",
        "issuer",
        "key_usage",
        "not_after",
        "not_before",
        "path_len",
        "subject",
    )

    def __init__(
        self, subject: str, issuer: str, not_before: int, not_after: int, dns_names: list[str]
    ) -> None:
        self.subject = subject
        self.issuer = issuer
        self.not_before = not_before
        self.not_after = not_after
        self.dns_names = list(dns_names)
        # No call to setConstraints: neither basicConstraints nor keyUsage is present.
        self.is_ca = False
        self.path_len = NO_LIMIT
        self.key_usage: list[str] = []

    def self_issued(self) -> bool:
        return self.subject == self.issuer


def name_matches(presented: str, hostname: str) -> bool:
    """RFC 9525 section 6.3, plus this problem's rule of two labels after a wildcard."""
    presented_labels = presented.lower().split(".")
    host_labels = hostname.lower().split(".")
    if "*" not in presented:
        return presented_labels == host_labels
    wildcard, *rest = presented_labels
    if wildcard != "*" or "*" in "".join(rest) or len(rest) < MIN_LABELS_AFTER_WILDCARD:
        return False
    return len(host_labels) == len(rest) + 1 and host_labels[1:] == rest


class ChainValidator:
    def __init__(self) -> None:
        self._certificates: dict[str, _Certificate] = {}
        self._signatures: dict[tuple[str, str], bool] = {}
        self._anchors: set[str] = set()
        self._revoked: set[str] = set()

    # Level 1
    def add_certificate(
        self,
        cert_id: str,
        subject: str,
        issuer: str,
        not_before: int,
        not_after: int,
        dns_names: list[str],
    ) -> bool:
        if cert_id in self._certificates:
            return False
        self._certificates[cert_id] = _Certificate(
            subject, issuer, not_before, not_after, dns_names
        )
        return True

    def matched_name(self, cert_id: str, hostname: str) -> str:
        certificate = self._certificates.get(cert_id)
        if certificate is None:
            return ""
        return next((name for name in certificate.dns_names if name_matches(name, hostname)), "")

    def check_leaf(self, cert_id: str, hostname: str, now: int) -> str:
        certificate = self._certificates.get(cert_id)
        if certificate is None:
            return "unknown-certificate"
        return self._validity(certificate, now) or (
            OK if self.matched_name(cert_id, hostname) else "hostname-mismatch"
        )

    # Level 2
    def add_signature(self, signer_id: str, cert_id: str, valid: bool) -> None:
        self._signatures[(signer_id, cert_id)] = valid

    def add_trust_anchor(self, cert_id: str) -> bool:
        if cert_id not in self._certificates or cert_id in self._anchors:
            return False
        self._anchors.add(cert_id)
        return True

    def build_chain(self, leaf_id: str) -> list[str]:
        candidates = self._candidates(leaf_id)
        return candidates[0] if candidates else []

    # Level 3
    def set_constraints(
        self, cert_id: str, is_ca: bool, path_len: int, key_usage: list[str]
    ) -> bool:
        certificate = self._certificates.get(cert_id)
        if certificate is None:
            return False
        certificate.is_ca = is_ca
        certificate.path_len = path_len
        certificate.key_usage = list(key_usage)
        return True

    def validate_path(self, path: list[str], hostname: str, now: int) -> list[str]:
        problem = self._structure(path) or self._process(path, now)
        if problem is not None:
            return list(problem)
        if not self.matched_name(path[0], hostname):
            return ["hostname-mismatch", path[0]]
        return [OK, ""]

    # Level 4
    def revoke(self, cert_id: str) -> bool:
        if cert_id not in self._certificates or cert_id in self._revoked:
            return False
        self._revoked.add(cert_id)
        return True

    def verify(self, leaf_id: str, hostname: str, now: int) -> list[list[str]]:
        if leaf_id not in self._certificates:
            return [["unknown-certificate", leaf_id]]
        candidates = self._candidates(leaf_id)
        if not candidates:
            return [["no-path", leaf_id]]
        rows = []
        for chain in candidates:
            outcome = self.validate_path(chain, hostname, now)
            rows.append([*outcome, *chain])
            if outcome[0] == OK:
                break
        return rows

    # The search: every chain from the leaf to the first trust anchor, shortest first.
    def _issuers(self, cert_id: str) -> list[str]:
        issuer = self._certificates[cert_id].issuer
        return [
            signer_id
            for signer_id, signer in self._certificates.items()
            if signer.subject == issuer and self._signatures.get((signer_id, cert_id), False)
        ]

    def _candidates(self, leaf_id: str) -> list[list[str]]:
        if leaf_id not in self._certificates:
            return []
        chains: list[list[str]] = []

        def extend(chain: list[str]) -> None:
            if chain[-1] in self._anchors:
                chains.append(list(chain))
                return
            for signer_id in self._issuers(chain[-1]):
                if signer_id not in chain:
                    chain.append(signer_id)
                    extend(chain)
                    chain.pop()

        extend([leaf_id])
        return sorted(chains, key=lambda chain: (len(chain), chain))

    # Validation, in the order of RFC 5280 section 6.1.
    def _structure(self, path: list[str]) -> tuple[str, str] | None:
        for cert_id in path:
            if cert_id not in self._certificates:
                return ("unknown-certificate", cert_id)
        seen: set[str] = set()
        for cert_id in path:
            if cert_id in seen:
                return ("repeated-certificate", cert_id)
            seen.add(cert_id)
        if path[-1] not in self._anchors:
            return ("not-trusted", path[-1])
        return None

    def _validity(self, certificate: _Certificate, now: int) -> str:
        if now < certificate.not_before:
            return "not-yet-valid"
        if now > certificate.not_after:
            return "expired"
        return ""

    def _process(self, path: list[str], now: int) -> tuple[str, str] | None:
        from_anchor = path[::-1]
        max_path_length = len(path) - 1
        for position in range(1, len(from_anchor)):
            signer_id, cert_id = from_anchor[position - 1], from_anchor[position]
            signer, certificate = self._certificates[signer_id], self._certificates[cert_id]
            if not self._signatures.get((signer_id, cert_id), False):
                return ("bad-signature", cert_id)
            reason = self._validity(certificate, now)
            if reason:
                return (reason, cert_id)
            if cert_id in self._revoked:
                return ("revoked", cert_id)
            if certificate.issuer != signer.subject:
                return ("name-mismatch", cert_id)
            if position == len(from_anchor) - 1:
                break
            if not certificate.is_ca:
                return ("not-a-ca", cert_id)
            if not certificate.self_issued():
                if max_path_length <= 0:
                    return ("path-too-long", cert_id)
                max_path_length -= 1
            if certificate.path_len != NO_LIMIT and certificate.path_len < max_path_length:
                max_path_length = certificate.path_len
            if certificate.key_usage and KEY_CERT_SIGN not in certificate.key_usage:
                return ("missing-key-cert-sign", cert_id)
        return None
