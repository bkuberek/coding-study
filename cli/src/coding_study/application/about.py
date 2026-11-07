"""`cstudy about` and the About view: the same version, license, links and credits for both
(docs/specs/cli.md#cstudy-about, docs/specs/web-ui.md#about-view)."""

from coding_study.application.ports import InstalledPackages
from coding_study.domain.about import (
    AUTHOR_LINK,
    AUTHOR_NAME,
    LICENSE_NAME,
    NOTICE_RULE_WIDTH,
    PROJECT_LINKS,
    SPONSOR_LINKS,
    TOOLCHAINS,
    WEBSITE_LINK,
    About,
    Author,
    Credit,
    CreditSection,
    web_ui_credits,
)
from coding_study.domain.code_intelligence import LANGUAGE_SERVERS

NO_LICENSE_TEXT = "The package ships no license text; see its project page."
_RULE = "-" * NOTICE_RULE_WIDTH


def read_about(version: str, packages: InstalledPackages) -> About:
    return About(
        author=Author(AUTHOR_NAME, AUTHOR_LINK),
        version=version,
        license=LICENSE_NAME,
        website=WEBSITE_LINK,
        links=PROJECT_LINKS,
        sponsor=SPONSOR_LINKS,
        credits=_credits(packages),
    )


def read_license_texts(packages: InstalledPackages) -> str:
    """The full text of cstudy's license, then that of each Python package, then the notice of
    the web page's packages as the build wrote it."""
    texts = packages.python_license_texts()
    parts = [_titled(f"cstudy ({LICENSE_NAME})", packages.own_license_text())]
    parts.extend(
        _titled(_heading(credit), texts.get(credit.name, NO_LICENSE_TEXT))
        for credit in packages.python_packages()
    )
    notice = packages.web_ui_notice()
    if notice is not None:
        parts.append(notice.strip())
    return "\n\n".join(parts) + "\n"


def _credits(packages: InstalledPackages) -> tuple[CreditSection, ...]:
    notice = packages.web_ui_notice()
    sections = [
        CreditSection("Python packages", packages.python_packages()),
        CreditSection("Web page", web_ui_credits(notice) if notice is not None else ()),
        CreditSection(
            "Language servers",
            tuple(Credit(server.name, server.version, "") for server in LANGUAGE_SERVERS),
        ),
        CreditSection("Toolchains", tuple(Credit(name, "", "") for name in TOOLCHAINS)),
    ]
    return tuple(section for section in sections if section.credits)


def _heading(credit: Credit) -> str:
    return f"{credit.name} {credit.version} ({credit.license or 'license not declared'})"


def _titled(title: str, text: str) -> str:
    return "\n".join((_RULE, title, _RULE, "", text.strip()))
