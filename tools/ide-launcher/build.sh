#!/usr/bin/env bash
# Builds the IntelliJ open-file launcher (docs/decisions/0010-ide-integration.md) into the cstudy
# package, or into the path given as the first argument.
#
# The build is reproducible: Java 17 bytecode, a fixed manifest (no JDK-specific Created-By) and
# fixed entry timestamps, so the same sources give the same bytes with any javac of the required
# feature release (javac 17 and 21 emit different class files for the same --release). The
# committed jar is checked against a rebuild by cli/tests/adapters/ide/test_launcher_jar.py.
set -euo pipefail

required_javac=21
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output="${1:-$here/../../cli/src/coding_study/adapters/ide/cstudy-launcher.jar}"

javac_version="$(javac -version 2>&1)"
javac_feature="${javac_version#javac }"
javac_feature="${javac_feature%%.*}"
if [[ "$javac_feature" != "$required_javac" ]]; then
    echo "build.sh: needs javac $required_javac, found: $javac_version" >&2
    exit 2
fi

classes="$(mktemp -d)"
trap 'rm -rf "$classes"' EXIT

javac --release 17 -d "$classes" "$here/src/cstudy/launcher/Main.java"
jar --create --file "$output" --manifest "$here/MANIFEST.MF" --date 2000-01-01T00:00:02Z \
    -C "$classes" .
