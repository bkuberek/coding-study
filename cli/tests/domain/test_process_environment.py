import pytest

from coding_study.domain.process_environment import (
    ALLOWED_NAMES,
    CREDENTIAL_MARKERS,
    allowed_environment,
)

NEEDED_BY = {
    "every toolchain": (
        *("PATH", "HOME", "USER", "LOGNAME", "SHELL", "TZ", "TMPDIR"),
        *("LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "LC_MESSAGES"),
        *("TERM", "COLORTERM", "NO_COLOR", "FORCE_COLOR", "COLUMNS", "LINES"),
        *("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"),
    ),
    "Python": (
        *("VIRTUAL_ENV", "PYTHONIOENCODING", "UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR"),
        *("UV_PYTHON", "UV_PROJECT_ENVIRONMENT", "UV_NO_SYNC", "UV_OFFLINE", "UV_NATIVE_TLS"),
    ),
    "TypeScript": (
        *("NODE_OPTIONS", "NODE_PATH", "NODE_EXTRA_CA_CERTS", "PNPM_HOME", "COREPACK_HOME"),
        *(
            "npm_config_cache",
            "NPM_CONFIG_CAFILE",
            "npm_config_https_proxy",
            "npm_config_store_dir",
        ),
    ),
    "Java and Kotlin": (
        *("JAVA_HOME", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GRADLE_OPTS", "GRADLE_USER_HOME"),
        *("SDKMAN_DIR", "SDKMAN_CANDIDATES_DIR", "SDKMAN_PLATFORM"),
    ),
    "Go": ("GOPATH", "GOCACHE", "GOMODCACHE", "GOROOT", "GOTOOLCHAIN", "GOTMPDIR"),
    "Rust": ("CARGO_HOME", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN", "DEVELOPER_DIR"),
    "an install behind a proxy": (
        *("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY", "FTP_PROXY"),
        *("http_proxy", "https_proxy", "no_proxy", "all_proxy", "ftp_proxy"),
        *("SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"),
        "CARGO_HTTP_CAINFO",
    ),
}
CREDENTIALS = (
    *("CSTUDY_TEST_SECRET_TOKEN", "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID"),
    *("AWS_SESSION_TOKEN", "AWS_PROFILE", "GOOGLE_APPLICATION_CREDENTIALS", "AZURE_CLIENT_SECRET"),
    *("GITHUB_TOKEN", "GH_TOKEN", "NPM_TOKEN", "NODE_AUTH_TOKEN", "PYPI_TOKEN"),
    *("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "STRIPE_SECRET_KEY", "DB_PASSWORD", "DATABASE_URL"),
    *("UV_PUBLISH_TOKEN", "UV_GITHUB_TOKEN", "UV_INDEX_PRIVATE_PASSWORD"),
    *("CARGO_REGISTRY_TOKEN", "CARGO_REGISTRIES_PRIVATE_TOKEN", "COREPACK_NPM_TOKEN"),
    *("ORG_GRADLE_PROJECT_signingPassword", "GRADLE_ENTERPRISE_ACCESS_KEY"),
    *("SSH_AUTH_SOCK", "GPG_AGENT_INFO", "KUBECONFIG", "DOCKER_CONFIG"),
)
OTHER_VARIABLES = ("MY_SETTING", "EDITOR", "PAGER", "PYTHONPATH", "LD_PRELOAD", "NODE_ENV", "CI")
PREFIXED_CREDENTIALS = (
    *("LC_TOKEN", "LC_SECRET", "XDG_RUNTIME_PASSWORD", "XDG_API_KEY"),
    *("SDKMAN_API_KEY", "SDKMAN_AUTH", "SDKMAN_PRIVATE_THING"),
)


def environment_of(names: tuple[str, ...]) -> dict[str, str]:
    return {name: f"value of {name}" for name in names}


@pytest.mark.parametrize("names", NEEDED_BY.values(), ids=NEEDED_BY)
def test_what_a_toolchain_needs_is_passed_on(names):
    assert allowed_environment(environment_of(names)) == environment_of(names)


@pytest.mark.parametrize("name", CREDENTIALS)
def test_a_credential_is_dropped(name):
    assert allowed_environment({"PATH": "/bin", name: "secret"}) == {"PATH": "/bin"}


@pytest.mark.parametrize("name", OTHER_VARIABLES)
def test_a_variable_that_is_not_listed_is_dropped(name):
    assert name not in allowed_environment({"PATH": "/bin", name: "x"})


@pytest.mark.parametrize("name", PREFIXED_CREDENTIALS)
def test_a_prefix_does_not_pass_on_a_credential(name):
    assert name not in allowed_environment({name: "secret"})


def test_a_value_is_passed_on_as_it_is():
    proxy = "http://user:pass@proxy.example.test:3128"
    assert allowed_environment({"HTTPS_PROXY": proxy}) == {"HTTPS_PROXY": proxy}


def test_an_empty_environment_stays_empty():
    assert allowed_environment({}) == {}


def test_the_environment_it_is_given_is_left_as_it_was():
    raw = {"PATH": "/bin", "CSTUDY_TEST_SECRET_TOKEN": "secret"}
    allowed_environment(raw)
    assert raw == {"PATH": "/bin", "CSTUDY_TEST_SECRET_TOKEN": "secret"}


def test_no_listed_name_looks_like_a_credential():
    assert [
        name for name in sorted(ALLOWED_NAMES) if any(m in name.upper() for m in CREDENTIAL_MARKERS)
    ] == []
