"""The environment variables `cstudy` reads or sets, in the three classes of
docs/specs/compatibility.md#environment-variables. The contract tests snapshot the tuples and
fail for a `CSTUDY_*` string literal under `cli/src` that is in none of them."""

WORKSPACE = "CSTUDY_WORKSPACE"
CONTENT = "CSTUDY_CONTENT"
CONFIG = "CSTUDY_CONFIG"

PUBLIC = (WORKSPACE, CONTENT, CONFIG, "NO_COLOR", "VISUAL", "EDITOR", "JAVA_HOME")
"""Set by the user. The last four keep their usual meaning, which `cstudy` reads."""

PROBLEM_FORMAT = (
    "CSTUDY_DATA_DIR",
    "CSTUDY_MOCK_CONTROL_URL",
    "CSTUDY_MOCK_CONTROL_TOKEN",
    "CSTUDY_RESET_PHASE",
    "CSTUDY_PROBLEM_DIR",
    "CSTUDY_GRADED_LEVEL",
)
"""Set by `cstudy` for user code and problem code (docs/specs/service-projects.md#environment)."""

INTERNAL = (
    "CSTUDY_EGRESS_HOSTS",
    "CSTUDY_GO_DEBUG_LISTEN",
    "CSTUDY_GO_DELVE",
    "CSTUDY_GO_DEBUG_PACKAGE",
    "CSTUDY_HIDDEN_DIRECTORIES",
)
"""Between `cstudy` and its own helpers; no promise."""
