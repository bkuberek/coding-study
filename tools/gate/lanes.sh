#!/usr/bin/env bash
# Runs the whole pytest suite as four disjoint lanes, each test exactly once.
#
#   fast       -m "not slow"
#   slow-core  -m "slow and not docker", without the browser test files
#   browser    the browser test files, on the Playwright engines that are installed
#   docker     -m docker, without the browser test files
#
# fast runs first and alone; slow-core, browser and docker then run together.
# See tools/gate/README.md.

set -u
set -m

usage() {
  cat <<'EOF'
Usage: tools/gate/lanes.sh [options] [lane ...] [-- pytest-args ...]

Lanes: fast, slow-core, browser, docker. Without lane names, all four run.

Options:
  --logs DIR        write logs, JUnit XML and summary.log under DIR
                    (default: a new timestamped directory under ${TMPDIR:-/tmp})
  --no-stop         run slow-core, browser and docker even when fast fails
  --collect-check   collect every lane and the full suite, and check that the lanes
                    are pairwise disjoint and together cover the suite; runs no tests
  -h, --help        show this help

Arguments after -- go to every lane's pytest command. A lane's own arguments
come first, so a passed -k replaces the browser lane's engine filter.
CS_LANE_ARGS_<LANE> (FAST, SLOW_CORE, BROWSER, DOCKER) adds arguments to one lane.
EOF
}

die() {
  printf 'lanes.sh: %s\n' "$*" >&2
  exit 2
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 2
CLI_DIR=$(cd "$SCRIPT_DIR/../../cli" && pwd) || die "cannot find cli/ next to tools/"

ALL_LANES=(fast slow-core browser docker)
FAST_BASETEMP=/dev/shm/cs-fast
FAST_MIN_FREE_KB=$((4 * 1024 * 1024))
BROWSER_GLOB='tests/entrypoints/web/test_browser_*.py'

LOGS=""
NO_STOP=0
COLLECT_CHECK=0
SELECTED=()
PASS_ARGS=()
PIDS=()

while [ $# -gt 0 ]; do
  case $1 in
    -h | --help)
      usage
      exit 0
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
    --collect-check)
      COLLECT_CHECK=1
      shift
      ;;
    --)
      shift
      PASS_ARGS=("$@")
      break
      ;;
    fast | slow-core | browser | docker)
      SELECTED+=("$1")
      shift
      ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
done

LANES=()
for lane in "${ALL_LANES[@]}"; do
  if [ ${#SELECTED[@]} -eq 0 ]; then
    LANES+=("$lane")
    continue
  fi
  for chosen in "${SELECTED[@]}"; do
    [ "$chosen" = "$lane" ] && LANES+=("$lane")
  done
done

command -v uv >/dev/null 2>&1 || die "uv is not installed"

if [ -z "$LOGS" ]; then
  LOGS="${TMPDIR:-/tmp}/cs-gate-logs-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$LOGS" || die "cannot create $LOGS"
LOGS=$(cd "$LOGS" && pwd) || die "cannot enter $LOGS"
RUN_TMP=$(mktemp -d "${TMPDIR:-/tmp}/cs-gate-tmp.XXXXXX") || die "cannot create a temporary directory"
SUMMARY=$LOGS/summary.log

cd "$CLI_DIR" || die "cannot enter $CLI_DIR"

on_exit() {
  rmdir "$RUN_TMP" 2>/dev/null
}
trap on_exit EXIT

on_signal() {
  trap '' INT TERM
  local pid
  for pid in ${PIDS[@]+"${PIDS[@]}"}; do
    kill -TERM -- "-$pid" 2>/dev/null
  done
  wait
  printf '\nlanes.sh: interrupted; logs in %s, temporary directories under %s\n' "$LOGS" "$RUN_TMP" >&2
  exit 130
}
trap on_signal INT TERM

fmt_time() {
  printf '%d:%02d:%02d' $(($1 / 3600)) $(($1 % 3600 / 60)) $(($1 % 60))
}

# Sets LANE_ARGS to the pytest selector arguments of a lane.
lane_selector() {
  local files
  case $1 in
    fast) LANE_ARGS=(-m "not slow") ;;
    slow-core) LANE_ARGS=(-m "slow and not docker" "--ignore-glob=$BROWSER_GLOB") ;;
    docker) LANE_ARGS=(-m docker -rs "--ignore-glob=$BROWSER_GLOB") ;;
    browser)
      # shellcheck disable=SC2206  # the glob is meant to expand
      files=($BROWSER_GLOB)
      [ -e "${files[0]}" ] || die "no browser test files match $BROWSER_GLOB"
      LANE_ARGS=(-rs "${files[@]}")
      ;;
    *) die "unknown lane: $1" ;;
  esac
}

# Prints the installed Playwright engines, one per line.
installed_engines() {
  local root engine
  for root in "${PLAYWRIGHT_BROWSERS_PATH:-}" "$HOME/.cache/ms-playwright" "$HOME/Library/Caches/ms-playwright"; do
    if [ -z "$root" ] || [ ! -d "$root" ]; then continue; fi
    for engine in chromium firefox webkit; do
      compgen -G "$root/$engine-*" >/dev/null && printf '%s\n' "$engine"
    done
    return
  done
}

# Sets ENGINE_ARGS to a -k filter for the installed engines, and ENGINE_NOTE to a description.
browser_engines() {
  local present="" skipped="" engine expr=""
  ENGINE_ARGS=()
  present=$(installed_engines | sort -u | tr '\n' ' ')
  for engine in chromium firefox webkit; do
    case " $present " in
      *" $engine "*) expr="${expr:+$expr or }$engine" ;;
      *) skipped="$skipped $engine" ;;
    esac
  done
  if [ -z "$present" ]; then
    ENGINE_NOTE="no Playwright engine installed; the browser tests will skip"
  elif [ -z "$skipped" ]; then
    ENGINE_NOTE="engines: ${present% }"
  else
    ENGINE_ARGS=(-k "$expr")
    ENGINE_NOTE="engines: ${present% }; skipped (not installed):$skipped"
  fi
}

# Runs one lane to completion; the exit status is 0 when the lane passed.
run_lane() {
  local lane=$1 log=$LOGS/$1.log
  local start=$SECONDS basetemp rc=0 var result avail extra=() engine_args=()
  lane_selector "$lane"

  if [ "$lane" = fast ]; then
    basetemp=$FAST_BASETEMP
    if [ -d /dev/shm ]; then
      avail=$(df --output=avail -k /dev/shm 2>/dev/null | tail -n 1 | tr -d ' ')
      case $avail in
        '' | *[!0-9]*) basetemp=$RUN_TMP/fast ;;
        *)
          if [ "$avail" -lt "$FAST_MIN_FREE_KB" ]; then
            printf 'refused: /dev/shm has %s MB free, the fast lane needs 4096 MB\n' $((avail / 1024)) >"$log"
            finish_lane "$lane" 2 $((SECONDS - start)) "refused: /dev/shm has under 4 GB free" ""
            return 2
          fi
          ;;
      esac
    else
      basetemp=$RUN_TMP/fast
    fi
  else
    basetemp=$RUN_TMP/$lane
  fi

  if [ "$lane" = browser ]; then
    browser_engines
    engine_args=(${ENGINE_ARGS[@]+"${ENGINE_ARGS[@]}"})
    printf 'browser lane %s\n' "$ENGINE_NOTE" >"$log"
  else
    : >"$log"
  fi

  var=CS_LANE_ARGS_$(printf '%s' "$lane" | tr 'a-z-' 'A-Z_')
  # shellcheck disable=SC2229  # $var names the variable on purpose
  read -r -a extra <<<"${!var:-}"

  uv run --no-sync pytest -q "${LANE_ARGS[@]}" \
    --basetemp="$basetemp" \
    -o "cache_dir=.pytest_cache/$lane" \
    --durations=50 --durations-min=5 \
    --junitxml="$LOGS/$lane.xml" \
    ${engine_args[@]+"${engine_args[@]}"} \
    ${extra[@]+"${extra[@]}"} \
    ${PASS_ARGS[@]+"${PASS_ARGS[@]}"} \
    </dev/null >>"$log" 2>&1
  rc=$?

  result=$(grep -E '^(=+ )?([0-9]+ [a-z]|no tests ran).* in [0-9.]+s' "$log" | tail -n 1)
  if [ "$rc" -eq 5 ] && [ ${#PASS_ARGS[@]} -gt 0 ]; then
    rc=0
    result="no tests selected"
  fi
  [ -n "$result" ] || result="no pytest result line; see $log"

  if [ "$rc" -eq 0 ]; then
    rm -rf -- "$basetemp"
    finish_lane "$lane" "$rc" $((SECONDS - start)) "$result" ""
  else
    if [ -d "$basetemp" ]; then
      finish_lane "$lane" "$rc" $((SECONDS - start)) "$result" "kept: $basetemp"
    else
      finish_lane "$lane" "$rc" $((SECONDS - start)) "$result" ""
    fi
  fi
  return "$rc"
}

finish_lane() {
  local line
  line=$(printf '%-10s exit=%-3s %8s  %s' "$1" "$2" "$(fmt_time "$3")" "$4")
  [ -n "$5" ] && line="$line ($5)"
  printf '%s\n' "$line" >>"$SUMMARY"
  printf '%s\n' "$line"
}

FAILED=0

# Runs the given lanes concurrently and counts the failures in FAILED.
run_group() {
  local lane i
  PIDS=()
  for lane in "$@"; do
    run_lane "$lane" &
    PIDS+=("$!")
  done
  for i in "${!PIDS[@]}"; do
    wait "${PIDS[$i]}" || FAILED=$((FAILED + 1))
  done
  PIDS=()
}

sync_environment() {
  printf 'syncing the environment (uv sync --locked --group browser)\n'
  if ! uv sync --locked --group browser >"$LOGS/sync.log" 2>&1; then
    cat "$LOGS/sync.log" >&2
    die "uv sync failed"
  fi
}

count_lines() {
  wc -l <"$1" | tr -d ' '
}

# Prints up to 20 lines of a file, and how many more there are.
show_some() {
  head -n 20 "$1" | sed 's/^/    /'
  local total
  total=$(count_lines "$1")
  if [ "$total" -gt 20 ]; then
    printf '    ... %s more, all in %s\n' $((total - 20)) "$1"
  fi
}

collect_check() {
  local dir=$LOGS/collect lane i other ok=1 total=0 n
  local names=("full" "${LANES[@]}")
  mkdir -p "$dir"
  PIDS=()
  for lane in "${names[@]}"; do
    (
      if [ "$lane" = full ]; then
        LANE_ARGS=()
      else
        lane_selector "$lane"
      fi
      uv run --no-sync pytest -q --collect-only "${LANE_ARGS[@]+"${LANE_ARGS[@]}"}" \
        -o "cache_dir=.pytest_cache/collect-$lane" </dev/null >"$dir/$lane.raw" 2>&1
    ) &
    PIDS+=("$!")
  done
  printf 'collecting %s in parallel\n' "${names[*]}"
  for i in "${!names[@]}"; do
    lane=${names[$i]}
    if ! wait "${PIDS[$i]}"; then
      printf 'collection of %s failed; see %s\n' "$lane" "$dir/$lane.raw" >&2
      ok=0
    fi
  done
  PIDS=()
  [ "$ok" -eq 1 ] || return 1

  for lane in "${names[@]}"; do
    grep -E '^tests/.*::' "$dir/$lane.raw" | LC_ALL=C sort >"$dir/$lane.ids"
  done

  printf '\n%-10s %8s\n' lane tests
  for lane in "${LANES[@]}"; do
    n=$(count_lines "$dir/$lane.ids")
    total=$((total + n))
    printf '%-10s %8s\n' "$lane" "$n"
  done
  printf '%-10s %8s\n' "sum" "$total"
  printf '%-10s %8s\n\n' "full" "$(count_lines "$dir/full.ids")"

  for lane in "${LANES[@]}"; do
    for other in "${LANES[@]}"; do
      [ "$lane" \< "$other" ] || continue
      LC_ALL=C comm -12 "$dir/$lane.ids" "$dir/$other.ids" >"$dir/overlap-$lane-$other.ids"
      if [ -s "$dir/overlap-$lane-$other.ids" ]; then
        ok=0
        printf 'in both %s and %s: %s tests\n' "$lane" "$other" "$(count_lines "$dir/overlap-$lane-$other.ids")"
        show_some "$dir/overlap-$lane-$other.ids"
      fi
    done
  done

  for lane in "${LANES[@]}"; do
    uniq -d "$dir/$lane.ids" >"$dir/repeated-$lane.ids"
    if [ -s "$dir/repeated-$lane.ids" ]; then
      ok=0
      printf 'collected twice in %s:\n' "$lane"
      show_some "$dir/repeated-$lane.ids"
    fi
  done

  for lane in "${LANES[@]}"; do cat "$dir/$lane.ids"; done | LC_ALL=C sort -u >"$dir/union.ids"
  LC_ALL=C sort -u "$dir/full.ids" >"$dir/full.unique.ids"
  LC_ALL=C comm -13 "$dir/union.ids" "$dir/full.unique.ids" >"$dir/missing.ids"
  LC_ALL=C comm -23 "$dir/union.ids" "$dir/full.unique.ids" >"$dir/extra.ids"
  if [ -s "$dir/missing.ids" ]; then
    ok=0
    printf 'in the suite but in no lane: %s tests\n' "$(count_lines "$dir/missing.ids")"
    show_some "$dir/missing.ids"
  fi
  if [ -s "$dir/extra.ids" ]; then
    ok=0
    printf 'in a lane but not in the suite: %s tests\n' "$(count_lines "$dir/extra.ids")"
    show_some "$dir/extra.ids"
  fi

  if [ "$ok" -eq 1 ]; then
    printf 'collection check passed: the lanes are disjoint and cover the suite\n'
    return 0
  fi
  printf 'collection check FAILED; id lists are in %s\n' "$dir"
  return 1
}

sync_environment

if [ "$COLLECT_CHECK" -eq 1 ]; then
  LANES=("${ALL_LANES[@]}")
  collect_check
  exit $?
fi

printf 'logs: %s\n' "$LOGS"
case " ${LANES[*]} " in
  *" browser "*)
    browser_engines
    printf 'browser lane %s\n' "$ENGINE_NOTE"
    printf 'browser    %s\n' "$ENGINE_NOTE" >>"$SUMMARY"
    ;;
esac

REST=()
for lane in "${LANES[@]}"; do
  if [ "$lane" = fast ]; then
    run_group fast
  else
    REST+=("$lane")
  fi
done

if [ ${#REST[@]} -gt 0 ]; then
  if [ "$FAILED" -gt 0 ] && [ "$NO_STOP" -eq 0 ]; then
    for lane in "${REST[@]}"; do
      line=$(printf '%-10s skipped: fast failed (--no-stop runs it anyway)' "$lane")
      printf '%s\n' "$line" | tee -a "$SUMMARY"
    done
  else
    run_group "${REST[@]}"
  fi
fi

printf '\nsummary: %s\n' "$SUMMARY"
[ "$FAILED" -eq 0 ]
