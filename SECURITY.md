# Security policy

## Supported versions

Only the latest release of `cstudy` gets security fixes. Upgrade before you report, in case a fix has already shipped.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**. Please don't open a public issue for a security problem.

A useful report includes:

- the `cstudy --version` output and your operating system;
- the steps to reproduce, with the smallest problem, workspace or command that shows it;
- what an attacker could do with it.

You can expect an acknowledgement within a week. Once a fix is released, the advisory is published with credit, unless you prefer to stay anonymous.

## Scope

`cstudy` runs on your own machine, so the issues that matter most are those that break the boundaries it promises:

- code from a problem or a solution escaping the service-project sandbox, or reaching the host or the internet from it ([service projects](docs/specs/service-projects.md));
- problem content, a workspace file or a downloaded tool running code or writing files outside the workspace without your action;
- a downloaded tool or language server installed without its checksum being verified;
- the local web UI (`cstudy serve`) being reachable or controllable from another machine or another website.

Some problems deliberately contain flawed code for you to find and fix. Those planted flaws are teaching material, not vulnerabilities in `cstudy`.
