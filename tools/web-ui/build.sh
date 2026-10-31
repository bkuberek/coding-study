#!/usr/bin/env bash
# Builds the web UI front end (docs/specs/web-ui-proposal.md#shipping-the-bundle-offline) into the
# cstudy package, or into the directory given as the first argument. See README.md.
#
# The build is reproducible: pnpm installs exactly what pnpm-lock.yaml pins, without running any
# package's install scripts, and the pinned esbuild writes the same bytes on every machine. Only the
# install needs the network, and only for packages missing from the pnpm store. The committed
# output is checked against a rebuild by cli/tests/entrypoints/web/test_static_assets.py.
set -euo pipefail

required_node=24
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for tool in node pnpm; do
    if ! command -v "$tool" > /dev/null; then
        echo "build.sh: needs $tool on PATH" >&2
        exit 2
    fi
done
node_version="$(node --version)"
node_major="${node_version#v}"
node_major="${node_major%%.*}"
if (( node_major < required_node )); then
    echo "build.sh: needs node $required_node or later, found: $node_version" >&2
    exit 2
fi

# From this directory, so Corepack runs the pnpm that package.json's packageManager pins.
(
    cd "$here"
    # pnpm 9 calls url.parse(), which Node 24 reports as deprecated on every install.
    NODE_OPTIONS=--no-deprecation pnpm install --frozen-lockfile --ignore-scripts --prefer-offline --reporter=silent
    pnpm run --silent typecheck
    if ! test_output="$(pnpm run --silent test 2>&1)"; then
        printf '%s\n' "$test_output" >&2
        exit 1
    fi
)
node "$here/scripts/build.ts" "$@"
