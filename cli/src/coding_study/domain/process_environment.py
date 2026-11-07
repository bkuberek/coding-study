"""The environment of a process that runs user code, or a tool on it
(docs/specs/runners.md#process-environment, docs/decisions/0019-service-projects.md, P2).

An allowlist: a variable reaches such a process only when this module names it, so a token, a key
or a password in the shell that started `cstudy` does not reach the code of a problem, its tests,
the build tools and package managers that run beside them, or a language server. The adapters hand
in the raw environment; nothing here reads the process's own.

What the list holds is what the toolchains need to find themselves, their caches and the network,
and no more. That is not a sandbox: user code still runs as the user and can read what the user
can read, a credentials file included.
"""

from collections.abc import Mapping

IDENTITY = ("HOME", "USER", "LOGNAME", "SHELL")
SEARCH_PATH = ("PATH",)
LOCALE_AND_TIME = ("LANG", "LANGUAGE", "TZ")
TERMINAL = (
    *("TERM", "COLORTERM", "NO_COLOR", "FORCE_COLOR", "CLICOLOR", "CLICOLOR_FORCE"),
    *("COLUMNS", "LINES", "TERMINFO", "TERMINFO_DIRS"),
)
TEMPORARY_DIRECTORIES = ("TMPDIR", "TMP", "TEMP")
MACOS_DEVELOPER_TOOLS = ("DEVELOPER_DIR",)
"""Where `xcrun` finds the compiler and linker that Rust links with."""

PYTHON = (
    *("VIRTUAL_ENV", "PYTHONIOENCODING", "PYTHONUTF8"),
    *("UV_CACHE_DIR", "UV_PYTHON", "UV_PYTHON_INSTALL_DIR", "UV_PYTHON_PREFERENCE"),
    *("UV_PYTHON_DOWNLOADS", "UV_PROJECT_ENVIRONMENT", "UV_LINK_MODE", "UV_OFFLINE", "UV_NO_SYNC"),
    *("UV_NATIVE_TLS", "UV_SYSTEM_CERTS", "UV_HTTP_TIMEOUT"),
)
"""Where uv finds its cache, its interpreters and the project's environment, and how it reaches
the network. Not `UV_*`: that would pass `UV_PUBLISH_TOKEN`, `UV_GITHUB_TOKEN` and the passwords
of `UV_INDEX_*`."""

NODE = (
    *("NODE_OPTIONS", "NODE_PATH", "NODE_NO_WARNINGS", "NODE_DISABLE_COLORS", "NODE_COMPILE_CACHE"),
    *("PNPM_HOME", "COREPACK_HOME", "COREPACK_ENABLE_AUTO_PIN", "COREPACK_ENABLE_STRICT"),
    "COREPACK_ENABLE_DOWNLOAD_PROMPT",
)
"""Not `NODE_*`: that would pass `NODE_AUTH_TOKEN`, which npm reads for its registry."""
NPM_SETTINGS = ("cache", "store_dir", "cafile", "proxy", "https_proxy", "noproxy", "strict_ssl")
NPM = (
    *(f"npm_config_{setting}" for setting in NPM_SETTINGS),
    *(f"NPM_CONFIG_{setting.upper()}" for setting in NPM_SETTINGS),
)
"""The `npm_config_*` variables pnpm and npm read for their cache and the network, in both
spellings. Not the registry or its credentials."""

JVM = (
    *("JAVA_HOME", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "JAVA_OPTS"),
    *("GRADLE_OPTS", "GRADLE_USER_HOME"),
)
"""`JAVA_HOME` is the selected JDK, which `cstudy` sets for Gradle itself."""

GO = ("GOPATH", "GOCACHE", "GOMODCACHE", "GOROOT", "GOTOOLCHAIN", "GOTMPDIR")
RUST = ("CARGO_HOME", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN")

PROXY_SETTINGS = ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY", "FTP_PROXY")
CERTIFICATES = (
    *("SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"),
    *("NODE_EXTRA_CA_CERTS", "CARGO_HTTP_CAINFO"),
)
NETWORK = (*PROXY_SETTINGS, *(name.lower() for name in PROXY_SETTINGS), *CERTIFICATES)
"""What installs need behind a proxy or a network that inspects TLS. A proxy URL is passed as it
is, so a credential written into one travels with it."""

ALLOWED_NAMES = frozenset(
    (
        *IDENTITY,
        *SEARCH_PATH,
        *LOCALE_AND_TIME,
        *TERMINAL,
        *TEMPORARY_DIRECTORIES,
        *MACOS_DEVELOPER_TOOLS,
        *PYTHON,
        *NODE,
        *NPM,
        *JVM,
        *GO,
        *RUST,
        *NETWORK,
    )
)
ALLOWED_PREFIXES = ("LC_", "XDG_", "SDKMAN_")
"""Locale categories, the XDG base directories and the variables SDKMAN sets and reads."""

CREDENTIAL_MARKERS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
    "PRIVATE",
    "AUTH",
    "KEY",
)
"""A name with one of these in it is not passed on by a prefix, whatever the prefix. A listed
name is passed whatever it holds, and none of them has one of these in it."""


def allowed_environment(raw: Mapping[str, str]) -> dict[str, str]:
    """`raw` without the variables a process running user code may not inherit."""
    return {name: value for name, value in raw.items() if _is_allowed(name)}


def _is_allowed(name: str) -> bool:
    return name in ALLOWED_NAMES or _is_unremarkable_prefixed(name)


def _is_unremarkable_prefixed(name: str) -> bool:
    return name.startswith(ALLOWED_PREFIXES) and not _names_a_credential(name)


def _names_a_credential(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in CREDENTIAL_MARKERS)
