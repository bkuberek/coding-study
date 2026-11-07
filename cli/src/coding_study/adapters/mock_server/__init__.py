"""The mock server: one program for every service project.

Spec: docs/specs/service-projects.md#mock-server.

This folder runs alone, mounted read-only into a pinned Python image: `python -I <this folder>
<config.json>`. Its modules import each other relatively and otherwise only the standard library,
never the rest of cstudy or a third-party package.
"""
