#!/usr/bin/env bash
# Runs the content half of the release gate: cstudy verify over the whole catalog,
# split into concurrent processes on one workspace.
#
#   static            cstudy verify --static, first and alone
#   ordinary          every problem that is not a service project
#   services-a        service projects with backing services, first half
#   services-b        service projects with backing services, second half
#   services-other    the other service projects
#   conformance       cstudy verify --conformance
#   track-system-design, track-code-review
#                     the two tracks
#
# After static, ordinary, services-a, services-b, services-other and the chain
# conformance, track-system-design, track-code-review run together.
# See tools/gate/README.md.

set -u
set -m

usage() {
  cat <<'EOF'
Usage: tools/gate/verify.sh [options]

Needs a cstudy workspace: set CSTUDY_WORKSPACE or pass --workspace.

Options:
  --workspace DIR   the workspace to verify in (default: $CSTUDY_WORKSPACE)
  --fresh           first run cstudy init DIR --no-ide and cstudy doctor --fix
  --logs DIR        write logs and summary.log under DIR
                    (default: a new timestamped directory under ${TMPDIR:-/tmp})
  --no-stop         run the later stages even when static fails
  --list            print each group with its slug count and exit; runs nothing
  -h, --help        show this help
EOF
}

die() {
  printf 'verify.sh: %s\n' "$*" >&2
  exit 2
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 2
CLI_DIR=$(cd "$SCRIPT_DIR/../../cli" && pwd) || die "cannot find cli/ next to tools/"
PROBLEMS_DIR=$(cd "$SCRIPT_DIR/../../problems" && pwd) || die "cannot find problems/ next to tools/"

WORKSPACE=${CSTUDY_WORKSPACE:-}
FRESH=0
LOGS=""
NO_STOP=0
LIST=0
PIDS=()

while [ $# -gt 0 ]; do
  case $1 in
    -h | --help)
      usage
      exit 0
      ;;
    --workspace)
      [ $# -ge 2 ] || die "--workspace needs a directory"
      WORKSPACE=$2
      shift 2
      ;;
    --workspace=*)
      WORKSPACE=${1#--workspace=}
      shift
      ;;
    --fresh)
      FRESH=1
      shift
      ;;
    --logs)
      [ $# -ge 2 ] || die "--logs needs a directory"
      LOGS=$2
      shift 2
      ;;
    --logs=*)
      LOGS=${1#--logs=}
      shift
      ;;
    --no-stop)
      NO_STOP=1
      shift
      ;;
    --list)
      LIST=1
      shift
      ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
done

# A service project has `grading: http` under `project:` in its meta.yaml; one with
# backing services also has a services/ folder. Plain file checks, no YAML parser.
ORDINARY=()
SERVICES_BACKED=()
SERVICES_OTHER=()
for meta in "$PROBLEMS_DIR"/*/meta.yaml; do
  [ -e "$meta" ] || die "no problems found under $PROBLEMS_DIR"
  dir=$(dirname "$meta")
  slug=$(basename "$dir")
  if grep -qE '^  grading: http[[:space:]]*$' "$meta"; then
    if [ -d "$dir/services" ]; then
      SERVICES_BACKED+=("$slug")
    else
      SERVICES_OTHER+=("$slug")
    fi
  else
    ORDINARY+=("$slug")
  fi
done
HALF=$(((${#SERVICES_BACKED[@]} + 1) / 2))
SERVICES_A=("${SERVICES_BACKED[@]:0:HALF}")
SERVICES_B=("${SERVICES_BACKED[@]:HALF}")

if [ "$LIST" -eq 1 ]; then
  printf '%-16s %5s\n' ordinary "${#ORDINARY[@]}"
  printf '%-16s %5s\n' services-a "${#SERVICES_A[@]}"
  printf '%-16s %5s\n' services-b "${#SERVICES_B[@]}"
  printf '%-16s %5s\n' services-other "${#SERVICES_OTHER[@]}"
  printf '%-16s %5s\n' total $((${#ORDINARY[@]} + ${#SERVICES_BACKED[@]} + ${#SERVICES_OTHER[@]}))
  exit 0
fi

command -v uv >/dev/null 2>&1 || die "uv is not installed"
[ -n "$WORKSPACE" ] || die "set CSTUDY_WORKSPACE or pass --workspace DIR"
if [ "$FRESH" -eq 0 ] && [ ! -d "$WORKSPACE" ]; then
  die "workspace $WORKSPACE does not exist (--fresh creates it)"
fi
mkdir -p "$WORKSPACE" || die "cannot create $WORKSPACE"
WORKSPACE=$(cd "$WORKSPACE" && pwd) || die "cannot enter $WORKSPACE"
export CSTUDY_WORKSPACE=$WORKSPACE

if [ -z "$LOGS" ]; then
  LOGS="${TMPDIR:-/tmp}/cs-verify-logs-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$LOGS" || die "cannot create $LOGS"
LOGS=$(cd "$LOGS" && pwd) || die "cannot enter $LOGS"
SUMMARY=$LOGS/summary.log

cd "$CLI_DIR" || die "cannot enter $CLI_DIR"

on_signal() {
  trap '' INT TERM
  local pid
  for pid in ${PIDS[@]+"${PIDS[@]}"}; do
    kill -TERM -- "-$pid" 2>/dev/null
  done
  wait
  printf '\nverify.sh: interrupted; logs in %s\n' "$LOGS" >&2
  exit 130
}
trap on_signal INT TERM

fmt_time() {
  printf '%d:%02d:%02d' $(($1 / 3600)) $(($1 % 3600 / 60)) $(($1 % 60))
}

# Runs one part: run_part NAME CSTUDY-ARGS... ; the exit status is cstudy's.
run_part() {
  local part=$1 log=$LOGS/$1.log start=$SECONDS rc=0 result line
  shift
  uv run --no-sync cstudy "$@" </dev/null >"$log" 2>&1
  rc=$?
  result=$(grep -E '^ *result ' "$log" | tail -n 1 | sed 's/^ *//')
  [ -n "$result" ] || result="no result line; see $log"
  line=$(printf '%-22s exit=%-3s %8s  %s' "$part" "$rc" "$(fmt_time $((SECONDS - start)))" "$result")
  printf '%s\n' "$line" >>"$SUMMARY"
  printf '%s\n' "$line"
  return "$rc"
}

# Runs the conformance and track parts one after the other; fails when any failed.
run_extras() {
  local rc=0
  run_part conformance verify --conformance --require-ready || rc=1
  run_part track-system-design verify --track system-design --require-ready || rc=1
  run_part track-code-review verify --track code-review --require-ready || rc=1
  return "$rc"
}

printf 'logs: %s\nworkspace: %s\n' "$LOGS" "$WORKSPACE"

if [ "$FRESH" -eq 1 ]; then
  printf 'preparing the workspace (cstudy init, cstudy doctor --fix)\n'
  if ! { uv run --no-sync cstudy init "$WORKSPACE" --no-ide && uv run --no-sync cstudy doctor --fix; } \
    </dev/null >"$LOGS/workspace.log" 2>&1; then
    cat "$LOGS/workspace.log" >&2
    die "workspace preparation failed"
  fi
fi

if ! run_part static verify --static && [ "$NO_STOP" -eq 0 ]; then
  printf 'static failed; the other parts were not run (--no-stop runs them anyway)\n' | tee -a "$SUMMARY"
  printf '\nsummary: %s\n' "$SUMMARY"
  exit 1
fi

FAILED=0
run_part ordinary verify --require-ready "${ORDINARY[@]}" &
PIDS+=("$!")
run_part services-a verify --require-ready "${SERVICES_A[@]}" &
PIDS+=("$!")
run_part services-b verify --require-ready "${SERVICES_B[@]}" &
PIDS+=("$!")
run_part services-other verify --require-ready "${SERVICES_OTHER[@]}" &
PIDS+=("$!")
run_extras &
PIDS+=("$!")
for pid in "${PIDS[@]}"; do
  wait "$pid" || FAILED=$((FAILED + 1))
done
PIDS=()

printf '\nsummary: %s\n' "$SUMMARY"
[ "$FAILED" -eq 0 ] && ! grep -q 'exit=[1-9]' "$SUMMARY"
