"""A small threat model of a password reset feature, kept as data.

The elements and flows are the data flow diagram. A flow whose two ends sit in different trust
zones crosses a trust boundary, and those flows are where to ask the six STRIDE questions first.
Each threat found gets a likelihood and an impact from 1 to 3, and is ranked by their product.
"""

ZONES = {
    "user's browser": "internet",
    "mail inbox": "internet",
    "web app": "app",
    "mail sender": "app",
    "accounts db": "data",
}
FLOWS = [
    ("user's browser", "web app", "reset request with an email address"),
    ("web app", "accounts db", "look up the account, store the token's hash"),
    ("web app", "mail sender", "reset link to send"),
    ("mail sender", "mail inbox", "email with the reset link"),
    ("user's browser", "web app", "token and new password"),
]
STRIDE = {
    "S": "spoofing: can someone pretend to be another user or component?",
    "T": "tampering: can someone change data in transit or at rest?",
    "R": "repudiation: can someone deny an action because nothing recorded it?",
    "I": "information disclosure: can data reach someone who should not see it?",
    "D": "denial of service: can someone exhaust or block the feature?",
    "E": "elevation of privilege: can someone gain rights they were not given?",
}

print("Flows that cross a trust boundary:")
for source, target, data in FLOWS:
    if ZONES[source] != ZONES[target]:
        print(f"  {source} -> {target}: {data} ({ZONES[source]} to {ZONES[target]})")
print("Questions to ask of each:")
for letter, question in STRIDE.items():
    print(f"  {letter}  {question}")

THREATS = [
    ("I", "the response says whether the email has an account", 3, 2),
    ("D", "a script requests thousands of resets for one victim", 3, 1),
    ("S", "a guessable or reusable token resets someone else's password", 2, 3),
    ("I", "the token leaks from the reset page's URL to other sites", 2, 3),
    ("T", "a forged Host header points the emailed link at an attacker", 1, 3),
    ("R", "nobody can tell later who reset an account and from where", 2, 1),
]
print("Ranked by likelihood x impact:")
for kind, threat, likelihood, impact in sorted(THREATS, key=lambda t: (-t[2] * t[3], t[1])):
    print(f"  {likelihood * impact}  {kind}  {threat}")
