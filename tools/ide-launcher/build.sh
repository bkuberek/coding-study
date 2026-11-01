#!/usr/bin/env bash
# Builds the IntelliJ open-file launcher (docs/decisions/0010-ide-integration.md) into the cstudy
# package, or into the path given as the first argument.
#
# The build is reproducible: Java 17 bytecode, a fixed manifest (no JDK-specific Created-By) and
# fixed entry timestamps, so the same sources give the same bytes with any javac of the required
# feature release (javac 17 and 21 emit different class files for the same --release). The
# committed jar is checked against a rebuild by cli/tests/adapters/ide/test_launcher_jar.py.
#
# It needs a JDK 21 exactly, though cstudy runs on JDK 21 to 26 (docs/decisions/0016-jdk-range.md):
# the release pins the jar's bytes, not the range the launcher runs on. Like cstudy, this script
# uses the JDK that JAVA_HOME names, else the first javac on PATH, so a maintainer on another JDK
# selects a 21 for the one command, for example with SDKMAN:
#
#   JAVA_HOME="$HOME/.sdkman/candidates/java/<identifier of a 21 from sdk list java>" \
#       tools/ide-launcher/build.sh
set -euo pipefail

required_javac=21
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output="${1:-$here/../../cli/src/coding_study/adapters/ide/cstudy-launcher.jar}"

jdk_bin=""
if [[ -n "${JAVA_HOME:-}" ]]; then
    jdk_bin="$JAVA_HOME/bin/"
fi
select_hint="select a JDK $required_javac with JAVA_HOME, for example \
JAVA_HOME=\"\$HOME/.sdkman/candidates/java/<identifier of a $required_javac>\" tools/ide-launcher/build.sh"
where="on PATH"
if [[ -n "$jdk_bin" ]]; then
    where="in $jdk_bin"
fi
for tool in javac jar; do
    if ! command -v "$jdk_bin$tool" > /dev/null; then
        echo "build.sh: no $tool $where" >&2
        echo "build.sh: $select_hint" >&2
        exit 2
    fi
done

javac_version="$("${jdk_bin}javac" -version 2>&1)"
javac_feature="${javac_version#javac }"
javac_feature="${javac_feature%%.*}"
if [[ "$javac_feature" != "$required_javac" ]]; then
    echo "build.sh: needs javac $required_javac, found: $javac_version" >&2
    echo "build.sh: $select_hint" >&2
    exit 2
fi

classes="$(mktemp -d)"
trap 'rm -rf "$classes"' EXIT

"${jdk_bin}javac" --release 17 -d "$classes" "$here/src/cstudy/launcher/Main.java"
"${jdk_bin}jar" --create --file "$output" --manifest "$here/MANIFEST.MF" --date 2000-01-01T00:00:02Z \
    -C "$classes" .
