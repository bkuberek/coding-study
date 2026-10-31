import re

from tests.helpers import REPOSITORY_ROOT

TEMPLATE = REPOSITORY_ROOT / "packaging" / "homebrew" / "cstudy.rb.template"
LINUX_GCC = re.compile(r'^  on_linux do\n    depends_on "gcc"\n  end$', re.MULTILINE)


def test_the_formula_depends_on_gcc_on_linux_only():
    """The prebuilt `rpds` and `watchfiles` extensions link `libgcc_s`, which `brew linkage`
    finds only in Homebrew's gcc."""
    assert LINUX_GCC.search(TEMPLATE.read_text(encoding="utf-8"))

