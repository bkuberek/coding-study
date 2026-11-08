"""What the egress probe counts as an IPv6 address on the sandbox network: the kernel's list
(`/proc/net/if_inet6`) read in the container, and parsed by the code the probe itself runs."""

import ipaddress
from collections.abc import Callable

import pytest

from coding_study.domain.sandbox import EGRESS_PROBE, IPV6_ADDRESS_CHECK


def entry(address: str, device: str = "eth0") -> str:
    packed = ipaddress.IPv6Address(address).packed.hex()
    return f"{packed} 02 40 00 80 {device:>8}"


@pytest.fixture
def foreign() -> Callable[[str], list[str]]:
    scope: dict[str, object] = {}
    exec(IPV6_ADDRESS_CHECK, scope)
    return scope["foreign_ipv6"]  # type: ignore[return-value]


def test_loopback_and_link_local_are_no_way_out(foreign):
    text = "\n".join((entry("::1", "lo"), entry("fe80::42:acff:fe11:2"), entry("febf::1")))

    assert foreign(text) == []


def test_a_global_address_counts(foreign):
    assert foreign(entry("2001:db8::2")) == ["2001:db8::2"]


def test_a_unique_local_address_counts(foreign):
    text = "\n".join((entry("::1", "lo"), entry("fd00:c5d::2"), entry("fc00::9")))

    assert foreign(text) == ["fd00:c5d::2", "fc00::9"]


def test_an_empty_or_missing_list_holds_nothing(foreign):
    assert foreign("") == []
    assert foreign("\n") == []


def test_a_line_that_is_not_an_address_is_skipped(foreign):
    assert foreign("not-hex lo\n" + entry("2001:db8::2")) == ["2001:db8::2"]


def test_the_probe_reads_the_list_and_treats_a_missing_file_as_none():
    assert "/proc/net/if_inet6" in EGRESS_PROBE
    assert "except OSError" in EGRESS_PROBE
    compile(EGRESS_PROBE, "egress-probe", "exec")
