#!/usr/bin/env python3
"""Retakes the screenshots and animations that show `cstudy serve`, from a released wheel.

Run it under `uv run` from `cli/`, which already has Playwright; see README.md in this folder:

    cd cli
    uv run python ../tools/showcase/showcase.py --wheel PATH/coding_study-X.Y.Z-py3-none-any.whl \
        --work /tmp/showcase --out ../docs/images

It builds a throwaway virtual environment and workspace in `--work`, seeds some practice history,
serves the workspace on localhost and drives one Chromium at a time. It never touches an installed
`cstudy`. Stages, in the order they run: prepare, seed, videos, shots, mock. The mock stage comes
last because a running mock shows a banner in every view.
"""

import argparse
import contextlib
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

STAGES = ("prepare", "seed", "videos", "shots", "mock")
DESKTOP = (1440, 900)
PHONE = (390, 844)
PHONE_SCALE = 2
THEMES = ("light", "dark")
SHOTS = (
    "code-intelligence-hover",
    "code-intelligence-error",
    "autocomplete-list",
    "code-intelligence-java-hover",
    "code-intelligence-kotlin-hover",
    "code-intelligence-go-hover",
    "code-intelligence-rust-hover",
    "web-ui-problems",
    "web-ui-attempt",
    "web-ui-project",
    "web-ui-results",
    "web-ui-history",
    "web-ui-health",
    "web-ui-settings",
)
"""The screenshots of the `shots` stage, in the order they are taken; `--shots` picks some."""
WAIT_MS = 60_000
TYPING_MS = 75
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
DENOISE = "hqdn3d=4:4:20:20"
"""Playwright's video is noisy. Without this every GIF frame differs from the last one."""
GIF_LIMIT = 3_000_000
MP4_LIMIT = 2_000_000
PREFERENCES = {
    "format": 1,
    "vim": False,
    "run_on_save": False,
    "typecheck": True,
    "theme": "system",
    "code_intelligence": True,
    "autocomplete": True,
}

TWO_SUM = '''def two_sum(nums: list[int], target: int) -> list[int]:
    by_value = sorted(range(len(nums)), key=lambda i: nums[i])
    low, high = 0, len(nums) - 1
    while low < high:
        total = nums[by_value[low]] + nums[by_value[high]]
        if total == target:
            return sorted([by_value[low], by_value[high]])
        if total < target:
            low += 1
        else:
            high -= 1
    return []
'''
TOP_K_JAVA = """public class Solution {
    public int[] topKFrequent(int[] nums, int k) {
        Map<Integer, Integer> counts = new HashMap<>();
        for (int num : nums) {
            counts.put(num, counts.getOrDefault(num, 0) + 1);
        }
        PriorityQueue<Integer> heap = new PriorityQueue<>(Comparator.comparingInt(counts::get));
        for (int value : counts.keySet()) {
            heap.offer(value);
            if (heap.size() > k) {
                heap.poll();
            }
        }
        int[] answer = new int[k];
        for (int i = k - 1; i >= 0; i--) {
            answer[i] = heap.poll();
        }
        return answer;
    }
}
"""
JAVA_SLUG = "top-k-frequent-elements"
MAJORITY_KOTLIN = """class Solution {
    fun majorityElement(nums: IntArray): Int {
        val counts = nums.asList().groupingBy { it }.eachCount()
        val half = nums.size / 2
        return counts.entries.first { (_, count) -> count > half }.key
    }
}
"""
KOTLIN_SLUG = "majority-element"
GROUP_ANAGRAMS_GO = """import (
	"slices"
	"strings"
)

func groupAnagrams(strs []string) [][]string {
	groups := map[string][]string{}
	for _, word := range strs {
		letters := strings.Split(word, "")
		slices.Sort(letters)
		key := strings.Join(letters, "")
		groups[key] = append(groups[key], word)
	}
	answer := make([][]string, 0, len(groups))
	for _, group := range groups {
		answer = append(answer, group)
	}
	return answer
}
"""
GO_SLUG = "group-anagrams"
PRODUCT_RUST = """pub fn product_except_self(nums: Vec<i32>) -> Vec<i32> {
    let mut answer = vec![1; nums.len()];
    let mut prefix = 1;
    for i in 0..nums.len() {
        answer[i] = prefix;
        prefix *= nums[i];
    }
    let mut suffix = 1;
    for i in (0..nums.len()).rev() {
        answer[i] *= suffix;
        suffix *= nums[i];
    }
    answer
}
"""
RUST_SLUG = "product-except-self"
TWO_SUM_WITH_TYPO = TWO_SUM.replace("high = 0, len(nums) - 1", "high = 0, len(num) - 1")
TWO_SUM_WITH_ROOM = TWO_SUM + "\n\n"
MOVE_ZEROES = (
    "def move_zeroes(nums: list[int]) -> None:\n"
    "    write = 0\n"
    "    for read in range(len(nums)):\n"
    "        if nums[read] != 0:\n"
    "            nums[write], nums[read] = nums[read], nums[write]\n"
    "            write += 1\n"
)
FIRST_ANAGRAM = """    if len(s) != len(t):
        return False
    seen = set(s)
    for letter in t:
        if letter not in seen:
            return False
    return True
"""
SECOND_ANAGRAM = """    from collections import Counter

    return Counter(s) == Counter(t)
"""
LEDGER = '''"""The ledger: a record of every transfer the bank has made."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class Ledger:
    entries: list[tuple[int, str, str, int]] = field(default_factory=list)

    def record(self, timestamp: int, source_id: str, target_id: str, amount: int) -> None:
        self.entries.append((timestamp, source_id, target_id, amount))
'''
BANK = '''"""The bank: the class that `cstudy submit` and the tests drive."""

from bank.ledger import Ledger
from bank.models import Account


class Bank:
    """Bank accounts that hold whole amounts of money and send money to one another."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}
        self._ledger = Ledger()

    def create_account(self, timestamp: int, account_id: str) -> bool:
        if account_id in self._accounts:
            return False
        self._accounts[account_id] = Account(account_id)
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int:
        account = self._accounts.get(account_id)
        if account is None:
            return -1
        account.balance += amount
        return account.balance

    def transfer(
        self, timestamp: int, source_id: str, target_id: str, amount: int
    ) -> int:
        source = self._accounts.get(source_id)
        target = self._accounts.get(target_id)
        if source is None or target is None or source_id == target_id:
            return -1
        source.balance -= amount
        target.balance += amount
        self._ledger.record(timestamp, source_id, target_id, amount)
        return source.balance
'''


@dataclass(frozen=True)
class Variant:
    theme: str
    phone: bool

    @property
    def size(self) -> tuple[int, int]:
        return PHONE if self.phone else DESKTOP

    @property
    def suffix(self) -> str:
        return f"{self.theme}-phone" if self.phone else self.theme


VARIANTS = [Variant(theme, phone) for phone in (False, True) for theme in THEMES]


def say(message: str) -> None:
    print(message, flush=True)


def run(command: list[str | Path], cwd: Path | None = None, env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    done = subprocess.run(
        [str(part) for part in command], cwd=cwd, env=env, text=True, capture_output=True
    )
    if check and done.returncode != 0:
        sys.exit(f"{' '.join(map(str, command))} failed:\n{done.stdout}\n{done.stderr}")
    return done


DAEMONS = ("GradleDaemon", "KotlinCompileDaemon")
"""What a Gradle build may leave running after it ends: its daemon, and Kotlin's compile daemon."""


def processes() -> dict[int, tuple[int, str]]:
    """Every process, as its parent's PID and its command."""
    listing = run(["ps", "-Aww", "-o", "pid=,ppid=,command="], check=False).stdout
    table: dict[int, tuple[int, str]] = {}
    for line in listing.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            table[int(parts[0])] = (int(parts[1]), parts[2])
    return table


def descendants(root: int, table: dict[int, tuple[int, str]]) -> dict[int, str]:
    """The processes below `root`, by PID, with their commands."""
    children: dict[int, list[int]] = {}
    for pid, (parent, _command) in table.items():
        children.setdefault(parent, []).append(pid)
    found: dict[int, str] = {}
    waiting = [root]
    while waiting:
        for child in children.get(waiting.pop(), []):
            found[child] = table[child][1]
            waiting.append(child)
    return found


class DaemonWatch:
    """Notes the Gradle and Kotlin daemons that this script's own processes start, so that only
    those are stopped. A daemon runs below the build that started it until that build ends, then
    belongs to no one, so a look every half second while the script runs finds it. A daemon that
    was running before, or that other work starts meanwhile, is never below this script, and
    stays."""

    def __init__(self) -> None:
        self.started: dict[int, str] = {}
        self.done = threading.Event()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def watch(self) -> None:
        while not self.done.wait(0.5):
            self.look()

    def look(self) -> None:
        for pid, command in descendants(os.getpid(), processes()).items():
            if any(name in command for name in DAEMONS):
                self.started[pid] = command

    def stop(self) -> None:
        """Stops the noted daemons by PID, each only while it still runs the command it ran when
        it was noted, so a PID reused since is left alone."""
        self.done.set()
        self.thread.join()
        self.look()
        table = processes()
        for pid, command in self.started.items():
            if pid in table and table[pid][1] == command:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGTERM)
                name = next(name for name in DAEMONS if name in command)
                say(f"stopped {name} {pid}, started by this run")


class Showcase:
    """The throwaway install, workspace and server that every stage works with."""

    def __init__(self, work: Path, out: Path, shots: tuple[str, ...] = SHOTS) -> None:
        self.work = work.resolve()
        self.out = out.resolve()
        self.shots = shots
        self.venv = self.work / "venv"
        self.workspace = self.work / "ws"
        self.toolbin = self.work / "toolbin"
        self.clips = self.work / "clips"
        self.cstudy = self.venv / "bin" / "cstudy"
        self.daemons = DaemonWatch()
        self.server_pid = 0
        self.base = ""
        self.token_url = ""
        self.attempts: dict[str, str] = {}

    def cs(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return run([self.cstudy, *args], cwd=self.workspace, env=self.environment(), check=check)

    def environment(self) -> dict[str, str]:
        """PATH without any other `cstudy`, so the Health view lists the one install that runs."""
        entries = os.environ.get("PATH", "").split(os.pathsep)
        others = [e for e in entries if e and (Path(e) / "cstudy").exists()]
        kept = [e for e in entries if e not in others]
        self.toolbin.mkdir(parents=True, exist_ok=True)
        link = self.toolbin / "cstudy"
        if not link.exists():
            link.symlink_to(self.cstudy)
        for tool in ("uv", "node", "pnpm", "java", "gradle", "go", "rustc", "cargo", "dlv", "git"):
            found = shutil.which(tool)
            target = self.toolbin / tool
            if found and any(found.startswith(o + os.sep) for o in others) and not target.exists():
                target.symlink_to(found)
        return {**os.environ, "PATH": os.pathsep.join([str(self.toolbin), *kept])}

    def write_preferences(self, **changes: object) -> None:
        folder = self.workspace / ".cs" / "serve"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "preferences.json").write_text(json.dumps({**PREFERENCES, **changes}) + "\n")

    def prepare(self, wheel: Path, licenses: tuple[str, ...] = ()) -> None:
        """`licenses` are the keys of the server licenses that you have read and accept for this
        throwaway workspace, such as `kotlin-lsp`; `cstudy doctor --fix` skips such a server
        without them."""
        say("prepare: virtual environment, workspace, language servers")
        if self.work.exists() and any(self.work.iterdir()):
            sys.exit(f"{self.work} is not empty; give --work an empty or new folder")
        self.work.mkdir(parents=True, exist_ok=True)
        run(["uv", "venv", "--python", "3.13", "--quiet", self.venv])
        run(["uv", "pip", "install", "--quiet", "--python", self.venv / "bin" / "python", wheel])
        self.workspace.mkdir()
        self.cs("init", "--no-ide")
        self.write_preferences()
        accepted = [part for key in licenses for part in ("--accept-license", key)]
        say(self.cs("doctor", "--fix", *accepted).stdout.rstrip())
        self.cs("--version")

    def seed(self) -> None:
        say("seed: practice history")
        edit = self.edit_stub
        self.cs("start", "valid-anagram", "--lang", "python", "--no-open")
        edit("valid-anagram", FIRST_ANAGRAM)
        self.cs("test", "valid-anagram", check=False)
        self.cs("done", "valid-anagram", "--gave-up", "--notes", "Letters, not counts")
        self.cs("start", "valid-anagram", "--lang", "python", "--no-open")
        edit("valid-anagram", SECOND_ANAGRAM)
        self.finish("valid-anagram", "ok")
        for slug, body, rating in (
            ("contains-duplicate", "    return len(set(nums)) < len(nums)\n", "easy"),
            (
                "valid-palindrome",
                "    kept = [c.lower() for c in s if c.isalnum()]\n    return kept == kept[::-1]\n",
                "hard",
            ),
        ):
            self.cs("start", slug, "--lang", "python", "--no-open")
            edit(slug, body)
            self.finish(slug, rating)
        self.cs("start", "two-sum", "--lang", "python", "--no-open")
        self.write_stub("two-sum", TWO_SUM)
        self.cs("start", "move-zeroes", "--lang", "python", "--no-open")
        self.cs("start", JAVA_SLUG, "--lang", "java", "--no-open")
        self.write_java_stub(JAVA_SLUG, TOP_K_JAVA)
        self.cs("start", KOTLIN_SLUG, "--lang", "kotlin", "--no-open")
        self.write_code_after(self.kotlin_stub(KOTLIN_SLUG), "\nclass ", MAJORITY_KOTLIN)
        self.cs("start", GO_SLUG, "--lang", "go", "--no-open")
        self.write_code_after(self.go_stub(GO_SLUG), "\nfunc ", GROUP_ANAGRAMS_GO)
        self.cs("start", RUST_SLUG, "--lang", "rust", "--no-open")
        self.write_code_after(self.rust_stub(RUST_SLUG), "\npub fn ", PRODUCT_RUST)
        self.cs("start", "bank-project-python", "--no-open")
        project = self.workspace / "projects" / "bank-project-python"
        (project / "bank" / "ledger.py").write_text(LEDGER)
        (project / "bank" / "bank.py").write_text(BANK)
        (project / "README.md").unlink()

    def finish(self, slug: str, rating: str) -> None:
        self.cs("test", slug)
        self.cs("done", slug, "--rating", rating)

    def stub(self, slug: str) -> Path:
        return self.workspace / "python" / "practice" / f"{slug.replace('-', '_')}.py"

    def write_stub(self, slug: str, code: str) -> None:
        """Replaces the stub's code and keeps the header `cstudy start` wrote above it, so the
        media show the header of the release they come from."""
        text = self.stub(slug).read_text()
        self.stub(slug).write_text(text[: text.index("\ndef ") + 1] + code)

    def java_stub(self, slug: str) -> Path:
        practice = self.workspace / "jvm" / "java" / "src" / "main" / "java" / "practice"
        return practice / slug.replace("-", "_") / "Solution.java"

    def write_java_stub(self, slug: str, code: str) -> None:
        """Replaces the class and keeps the header, package and imports `cstudy start` wrote."""
        text = self.java_stub(slug).read_text()
        self.java_stub(slug).write_text(text[: text.index("\npublic class ") + 1] + code)

    def kotlin_stub(self, slug: str) -> Path:
        practice = self.workspace / "jvm" / "kotlin" / "src" / "main" / "kotlin" / "practice"
        return practice / slug.replace("-", "_") / "Solution.kt"

    def go_stub(self, slug: str) -> Path:
        name = slug.replace("-", "_")
        return self.workspace / "go" / "practice" / name / f"{name}.go"

    def rust_stub(self, slug: str) -> Path:
        return self.workspace / "rust" / "practice" / f"{slug.replace('-', '_')}.rs"

    @staticmethod
    def write_code_after(path: Path, start: str, code: str) -> None:
        """Replaces the stub's code from the line that begins with `start`, and keeps the header
        and the package line `cstudy start` wrote above it."""
        text = path.read_text()
        path.write_text(text[: text.index(start) + 1] + code)

    def wants(self, name: str) -> bool:
        return name in self.shots

    def edit_stub(self, slug: str, body: str) -> None:
        """Replaces the stub's `raise NotImplementedError` line with `body`."""
        path = self.stub(slug)
        path.write_text(path.read_text().replace("    raise NotImplementedError\n", body))

    @contextlib.contextmanager
    def serving(self) -> Iterator[None]:
        say("serve: cstudy serve on a free port")
        server = subprocess.Popen(
            [self.cstudy, "serve", "--port", "0"], cwd=self.workspace, env=self.environment(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.server_pid = server.pid
        try:
            assert server.stdout is not None
            for line in server.stdout:
                found = re.match(r"open\s+(\S+)", line)
                if found:
                    self.token_url = found.group(1)
                    self.base = self.token_url.split("?")[0]
                    break
            if not self.token_url:
                sys.exit("cstudy serve did not print its address")
            yield
        finally:
            server.send_signal(signal.SIGINT)
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    def wait_for_server_to_stop(self, name: str) -> None:
        """Waits, up to 30 s, until no process of the server's runs `name` (a language server, or
        what it started, such as rust-analyzer's `cargo check`), so that two servers never run at
        once and JDT LS's next session reuses its data directory."""
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            below = descendants(self.server_pid, processes()).values()
            if not any(name in command for command in below):
                return
            time.sleep(0.5)

    def stop_gradle(self) -> None:
        """Stops the Gradle and Kotlin daemons that this script's processes started, by PID."""
        self.daemons.stop()

    # Browser helpers -----------------------------------------------------------------------

    def context(self, browser: Browser, variant: Variant, video: bool = False) -> BrowserContext:
        width, height = variant.size
        options: dict[str, Any] = {
            "viewport": {"width": width, "height": height},
            "color_scheme": variant.theme,
            "bypass_csp": True,
            "device_scale_factor": PHONE_SCALE if variant.phone else 1,
        }
        if video:
            self.clips.mkdir(parents=True, exist_ok=True)
            options["record_video_dir"] = str(self.clips)
            options["record_video_size"] = {"width": width, "height": height}
        context = browser.new_context(**options)
        context.set_default_timeout(WAIT_MS)
        context.add_init_script(HIDE_VENDORS_SCRIPT)
        if video:
            context.add_init_script(POINTER_SCRIPT)
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(self.token_url)
        page.wait_for_selector("nav, header")
        page.close()
        return context

    def page(self, context: BrowserContext, route: str) -> Page:
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(f"{self.base}#{route}")
        page.wait_for_selector("header")
        return page

    def attempt(self, context: BrowserContext, slug: str) -> Page:
        """The attempt view of `slug`, found through the in-progress menu."""
        page = self.page(context, "/")
        link = page.locator("a[href^='#/attempts/']", has_text=slug).first
        link.wait_for(state="attached")
        route = (link.get_attribute("href") or "").removeprefix("#")
        page.goto(f"{self.base}#{route}")
        page.get_by_role("button", name=re.compile("Run tests")).wait_for()
        return page

    def screenshot(self, page: Page, name: str, variant: Variant, redact: bool = False) -> None:
        if redact:
            self.redact(page)
        path = self.out / f"{name}-{variant.suffix}.png"
        page.screenshot(path=path)
        shrink(path)
        say(f"  {path.name}")

    def redact(self, page: Page) -> None:
        """Shows `~` paths in place of this machine's temporary folders."""
        home = str(Path.home())
        pairs = [
            [str(self.toolbin / "cstudy"), "~/.local/bin/cstudy"],
            [str(self.venv), "~/.local/share/uv/tools/coding-study"],
            [str(self.workspace), "~/cstudy-workspace"],
            [home, "~"],
        ]
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            pairs.insert(0, [str(Path(config_home).resolve()), "~/.config"])
            pairs.insert(0, [config_home, "~/.config"])
        page.evaluate(REDACT_SCRIPT, pairs)


HIDE_VENDORS_SCRIPT = """
addEventListener('DOMContentLoaded', () => {
  const hide = () => document.querySelectorAll('p').forEach(p => {
    if (/^\\s*Reference:/.test(p.textContent)) p.style.display = 'none';
  });
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; hide(); });
  }).observe(document.body, {childList: true, subtree: true});
  hide();
});
"""
"""The statements credit the problem they reword; the media do not name any assessment vendor."""

POINTER_SCRIPT = """
addEventListener('DOMContentLoaded', () => {
  const pointer = document.createElement('div');
  pointer.style.cssText = 'position:fixed;left:0;top:0;width:24px;height:24px;z-index:2147483647;'
    + 'pointer-events:none;transform:translate(-100px,-100px);'
    + 'filter:drop-shadow(0 1px 2px rgba(0,0,0,.45));'
    + 'background:url("data:image/svg+xml;utf8,' + encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
      + '<path d="M3 2l15 9-6.5 1.6L8.6 19z" fill="white" stroke="black" stroke-width="1.5" '
      + 'stroke-linejoin="round"/></svg>') + '") no-repeat';
  document.documentElement.appendChild(pointer);
  const ring = document.createElement('div');
  ring.style.cssText = 'position:fixed;left:0;top:0;width:34px;height:34px;border-radius:50%;'
    + 'border:2px solid #e2572b;z-index:2147483646;pointer-events:none;opacity:0;'
    + 'margin:-17px 0 0 -17px;';
  document.documentElement.appendChild(ring);
  addEventListener('mousemove', e => {
    pointer.style.transform = 'translate(' + (e.clientX - 3) + 'px,' + (e.clientY - 2) + 'px)';
  }, true);
  addEventListener('mousedown', e => {
    ring.style.left = e.clientX + 'px';
    ring.style.top = e.clientY + 'px';
    ring.animate([{opacity: .9, transform: 'scale(.4)'}, {opacity: 0, transform: 'scale(1.4)'}],
      {duration: 450});
  }, true);
});
"""

REDACT_SCRIPT = """
(pairs) => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    let value = node.nodeValue;
    for (const [from, to] of pairs) value = value.split(from).join(to);
    if (value !== node.nodeValue) node.nodeValue = value;
  }
}
"""

TOKEN_SCRIPT = """
([selector, lineText, token]) => {
  const line = [...document.querySelectorAll(selector)].find(l => l.textContent.includes(lineText));
  if (!line) return null;
  const start = line.textContent.indexOf(lineText) + lineText.indexOf(token);
  const end = start + token.length;
  const walker = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let seen = 0, from = false;
  while (walker.nextNode()) {
    const node = walker.currentNode, length = node.nodeValue.length;
    if (!from && start < seen + length) { range.setStart(node, start - seen); from = true; }
    if (from && end <= seen + length) { range.setEnd(node, end - seen); break; }
    seen += length;
  }
  const box = range.getBoundingClientRect();
  return {x: box.x + box.width / 2, y: box.y + box.height / 2, left: box.x, top: box.y,
          height: box.height};
}
"""

SHOW_LINE_SCRIPT = """
(text) => {
  const line = [...document.querySelectorAll('.cm-line')].find(l => l.textContent.includes(text));
  if (!line) return;
  const box = line.getBoundingClientRect();
  const shown = document.elementFromPoint(box.left + 8, box.top + box.height / 2);
  if (!line.contains(shown)) line.scrollIntoView({block: 'center'});
  document.querySelectorAll('.cm-scroller').forEach(scroller => { scroller.scrollLeft = 0; });
}
"""
"""Scrolls an editor line to the middle only when it is out of sight, in the window or in the
editor, and never leaves the editor scrolled sideways."""


def shrink(path: Path) -> None:
    """Quantises a PNG to 256 colours, as the first screenshots in docs/images are."""
    if shutil.which("pngquant"):
        run(["pngquant", "--quality", "80-100", "--speed", "1", "--force", "--strip",
             "--output", path, path], check=False)


class Pointer:
    """Moves the (injected) pointer in steps so that a recording shows where it goes."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.rng = random.Random(7)

    def to(self, x: float, y: float, steps: int = 28) -> None:
        self.page.mouse.move(x, y, steps=steps)

    def token(self, line_text: str, token: str, selector: str = ".cm-line") -> dict[str, float]:
        box = self.page.evaluate(TOKEN_SCRIPT, [selector, line_text, token])
        if box is None:
            raise RuntimeError(f"no editor line with {line_text!r}")
        return box

    def to_token(self, line_text: str, token: str) -> dict[str, float]:
        box = self.token(line_text, token)
        self.to(box["x"], box["y"])
        return box

    def type(self, text: str, base_ms: int = TYPING_MS) -> None:
        for character in text:
            self.page.keyboard.type(character)
            self.page.wait_for_timeout(int(base_ms * self.rng.uniform(0.6, 1.5)))


def open_file(page: Page, name: str) -> None:
    page.get_by_text(name, exact=True).first.click()
    page.wait_for_selector(".cm-content")


def wait_ready(page: Page, server: str = "basedpyright", timeout_ms: float = WAIT_MS) -> None:
    page.wait_for_function(
        f"document.body.innerText.includes('{server} · ready')", timeout=timeout_ms
    )


def hover_until(page: Page, pointer: Pointer, line_text: str, token: str, text: str,
                limit_s: float = 180) -> None:
    """Hovers `token` again until its tooltip shows `text`. JDT LS says ready before its first
    Gradle import ends, and answers hover with nothing until then. A line out of sight is scrolled
    to the middle first, and the pointer rests near the start of `token`, since on a phone its
    middle can lie past the window's edge."""
    page.evaluate(SHOW_LINE_SCRIPT, line_text)
    page.wait_for_timeout(300)
    deadline = time.monotonic() + limit_s
    while True:
        pointer.to(5, 5, steps=4)
        box = pointer.token(line_text, token)
        pointer.to(box["left"] + 8, box["y"])
        try:
            page.wait_for_selector(f".cm-tooltip:has-text('{text}')", timeout=5_000)
            return
        except PlaywrightTimeoutError:
            if time.monotonic() > deadline:
                raise


def run_tests(page: Page) -> None:
    """Runs the tests and waits until the run has ended, not just until old results show. While a
    run is active the toolbar is `is-running` and Run tests itself reads Cancel."""
    page.get_by_role("button", name=re.compile("Run tests")).click()
    with contextlib.suppress(PlaywrightTimeoutError):
        page.wait_for_selector(".run-toolbar.is-running", timeout=5_000)
    page.wait_for_selector(".run-toolbar:not(.is-running)")
    page.wait_for_timeout(500)


def click_end_of_file(page: Page, pointer: Pointer) -> None:
    last = page.locator(".cm-line").last.bounding_box()
    assert last is not None
    pointer.to(last["x"] + 60, last["y"] + last["height"] / 2)
    page.mouse.click(last["x"] + 60, last["y"] + last["height"] / 2)


# Screenshots ---------------------------------------------------------------------------------


def feature_shots(app: Showcase, context: BrowserContext, variant: Variant) -> None:
    say(f"feature shots {variant.suffix}")

    if app.wants("code-intelligence-hover"):
        app.write_stub("two-sum", TWO_SUM)
        page = app.attempt(context, "two-sum")
        open_file(page, "two_sum.py")
        wait_ready(page)
        pointer = Pointer(page)
        pointer.to_token("return sorted", "sorted")
        page.wait_for_selector(".cm-tooltip:has-text('Return a new list')")
        page.wait_for_timeout(400)
        app.screenshot(page, "code-intelligence-hover", variant)
        page.close()

    if app.wants("code-intelligence-error"):
        app.write_stub("two-sum", TWO_SUM_WITH_TYPO)
        page = app.attempt(context, "two-sum")
        open_file(page, "two_sum.py")
        wait_ready(page)
        page.wait_for_selector(".cm-lintRange-error")
        pointer = Pointer(page)
        pointer.to_token("len(num)", "num")
        page.wait_for_selector(".cm-tooltip:has-text('is not defined')")
        page.wait_for_timeout(400)
        app.screenshot(page, "code-intelligence-error", variant)
        page.close()

    if app.wants("autocomplete-list"):
        app.write_stub("two-sum", TWO_SUM_WITH_ROOM)
        page = app.attempt(context, "two-sum")
        open_file(page, "two_sum.py")
        wait_ready(page)
        pointer = Pointer(page)
        click_end_of_file(page, pointer)
        page.keyboard.type("answer = sor", delay=60)
        page.wait_for_selector(".cm-tooltip-autocomplete")
        page.wait_for_selector(".cm-completionInfo")
        page.wait_for_timeout(600)
        pointer.to(5, 5, steps=1)
        app.screenshot(page, "autocomplete-list", variant)
        page.close()
    app.write_stub("two-sum", TWO_SUM)

    if app.wants("code-intelligence-java-hover"):
        page = app.attempt(context, JAVA_SLUG)
        open_file(page, "Solution.java")
        wait_ready(page, "jdtls")
        pointer = Pointer(page)
        hover_until(page, pointer, "counts.getOrDefault", "getOrDefault",
                    "Returns the value to which")
        page.wait_for_timeout(400)
        app.screenshot(page, "code-intelligence-java-hover", variant)
        page.close()
        app.wait_for_server_to_stop("jdtls")

    if app.wants("code-intelligence-kotlin-hover"):
        page = app.attempt(context, KOTLIN_SLUG)
        open_file(page, "Solution.kt")
        wait_ready(page, "kotlin-lsp", timeout_ms=180_000)
        pointer = Pointer(page)
        hover_until(page, pointer, "groupingBy { it }", "groupingBy", "group-and-fold",
                    limit_s=300)
        page.wait_for_timeout(400)
        app.screenshot(page, "code-intelligence-kotlin-hover", variant)
        page.close()
        app.wait_for_server_to_stop("kotlin-lsp")

    if app.wants("code-intelligence-go-hover"):
        page = app.attempt(context, GO_SLUG)
        open_file(page, "group_anagrams.go")
        wait_ready(page, "gopls")
        pointer = Pointer(page)
        hover_until(page, pointer, "strings.Split", "Split", "Split slices s into all substrings")
        page.wait_for_timeout(400)
        app.screenshot(page, "code-intelligence-go-hover", variant)
        page.close()
        app.wait_for_server_to_stop("gopls")

    if app.wants("code-intelligence-rust-hover"):
        page = app.attempt(context, RUST_SLUG)
        open_file(page, "product_except_self.rs")
        wait_ready(page, "rust-analyzer")
        pointer = Pointer(page)
        hover_until(page, pointer, "nums: Vec<i32>", "Vec", "A contiguous growable array type")
        page.wait_for_timeout(400)
        app.screenshot(page, "code-intelligence-rust-hover", variant)
        page.close()
        app.wait_for_server_to_stop("rust-analyzer")


def app_shots(app: Showcase, context: BrowserContext, variant: Variant) -> None:
    say(f"app shots {variant.suffix}")

    if app.wants("web-ui-problems"):
        page = app.page(context, "/")
        page.wait_for_selector("tbody tr")
        page.wait_for_timeout(400)
        app.screenshot(page, "web-ui-problems", variant)
        page.close()

    if app.wants("web-ui-attempt") or app.wants("web-ui-project"):
        page = app.attempt(context, "bank-project-python")
        open_file(page, "bank.py")
        wait_ready(page)
        run_tests(page)
        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.wait_for_timeout(300)
        if app.wants("web-ui-attempt"):
            app.screenshot(page, "web-ui-attempt", variant)
        if app.wants("web-ui-project"):
            for name in ("models.py", "ledger.py", "test_level_1.py"):
                page.get_by_text(name, exact=False).first.click()
                page.wait_for_timeout(500)
            page.get_by_text("ledger.py", exact=True).first.click()
            page.wait_for_timeout(600)
            app.screenshot(page, "web-ui-project", variant)
        page.close()

    if app.wants("web-ui-results"):
        app.write_stub("move-zeroes", MOVE_ZEROES)
        page = app.attempt(context, "move-zeroes")
        open_file(page, "move_zeroes.py")
        wait_ready(page)
        run_tests(page)
        if variant.phone:
            page.locator("text=RESULTS").first.evaluate(
                "e => { e.scrollIntoView({block: 'start'}); window.scrollBy(0, -70); }"
            )
        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.wait_for_timeout(400)
        app.screenshot(page, "web-ui-results", variant)
        page.close()

    if app.wants("web-ui-history"):
        page = app.page(context, "/problems/valid-anagram")
        page.locator("summary", has_text="failed").click()
        page.get_by_role("button", name=re.compile("View valid_anagram")).last.click()
        page.wait_for_selector(".cm-content[aria-readonly='true']")
        page.wait_for_timeout(600)
        app.screenshot(page, "web-ui-history", variant)
        page.close()

    if app.wants("web-ui-health"):
        page = app.page(context, "/health")
        page.wait_for_selector("text=code intelligence typescript")
        tall(page, variant)
        app.screenshot(page, "web-ui-health", variant, redact=True)
        page.close()

    if app.wants("web-ui-settings"):
        page = app.page(context, "/settings")
        page.wait_for_selector("text=basedpyright 1.")
        page.wait_for_selector("text=typescript-language-server")
        page.wait_for_selector("text=jdtls 1.")
        page.wait_for_selector("text=/kotlin-lsp \\d/")
        page.wait_for_selector("text=gopls 0.")
        page.wait_for_selector("text=rust-analyzer 1.")
        page.wait_for_timeout(300)
        app.screenshot(page, "web-ui-settings", variant, redact=True)
        page.close()


def tall(page: Page, variant: Variant) -> None:
    """Grows the window to the whole page, up to a limit, for the long Health table."""
    width, height = variant.size
    full = page.evaluate(
        "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
    )
    page.set_viewport_size({"width": width, "height": min(max(height, int(full)), 2600)})
    page.wait_for_timeout(500)


def mock_shots(app: Showcase, browser: Browser) -> None:
    say("mock shots")
    context = app.context(browser, VARIANTS[0])
    try:
        page = app.page(context, "/mock")
        page.get_by_role("button", name=re.compile("Start the mock")).click()
        page.get_by_role("button", name=re.compile("Start the mock")).wait_for(state="detached")
        page.wait_for_timeout(1500)
        page.close()
    finally:
        context.close()
    for variant in VARIANTS:
        context = app.context(browser, variant)
        try:
            page = app.page(context, "/mock")
            page.wait_for_timeout(1500)
            app.screenshot(page, "web-ui-mock", variant)
            page.close()
        finally:
            context.close()


# Animations ----------------------------------------------------------------------------------


def code_intelligence_scene(app: Showcase, page: Page) -> None:
    pointer = Pointer(page)
    pointer.to(1100, 420, steps=1)
    page.wait_for_timeout(700)
    click_end_of_file(page, pointer)
    page.wait_for_timeout(300)
    pointer.type("print(two_sum(numbers, 9))")
    page.wait_for_selector(".cm-lintRange-error")
    page.wait_for_timeout(500)
    pointer.to_token("print(two_sum(numbers", "numbers")
    page.wait_for_selector(".cm-tooltip:has-text('is not defined')")
    page.wait_for_timeout(1800)
    box = pointer.token("print(two_sum(numbers", "numbers")
    page.mouse.dblclick(box["x"], box["y"])
    page.wait_for_timeout(500)
    page.keyboard.press("Backspace")
    pointer.type("[2, 7, 11, 15]")
    page.wait_for_function("document.querySelectorAll('.cm-lintRange-error').length === 0")
    page.wait_for_timeout(1000)
    pointer.to_token("return sorted", "sorted")
    page.wait_for_selector(".cm-tooltip:has-text('Return a new list')")
    page.wait_for_timeout(2400)
    box = pointer.token("return sorted", "sorted")
    page.keyboard.down("Meta")
    page.mouse.click(box["x"], box["y"])
    page.keyboard.up("Meta")
    page.wait_for_selector(".cm-content[aria-readonly='true']")
    page.mouse.move(box["x"] + 300, box["y"] + 200, steps=20)
    page.wait_for_timeout(2400)
    page.keyboard.press("Control+Minus")
    page.wait_for_selector("text=two_sum.py")
    page.wait_for_timeout(1500)


def autocomplete_scene(app: Showcase, page: Page) -> None:
    pointer = Pointer(page)
    pointer.to(1100, 420, steps=1)
    page.wait_for_timeout(1000)
    click_end_of_file(page, pointer)
    page.wait_for_timeout(300)
    pointer.type("answer = sor")
    page.wait_for_selector(".cm-completionInfo")
    page.wait_for_timeout(3000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(700)
    pointer.type("(")
    page.wait_for_selector(".cs-signature")
    page.wait_for_timeout(3000)
    pointer.type("[3, 1, 2], reverse=True")
    page.wait_for_timeout(2500)


@dataclass(frozen=True)
class Animation:
    name: str
    autocomplete: bool
    scene: Callable[[Showcase, Page], None]


ANIMATIONS = (
    Animation("code-intelligence-demo", False, code_intelligence_scene),
    Animation("autocomplete-demo", True, autocomplete_scene),
)


def record(app: Showcase, browser: Browser, animation: Animation, theme: str) -> None:
    say(f"video {animation.name} ({theme})")
    variant = Variant(theme, False)
    app.write_preferences(autocomplete=animation.autocomplete)
    app.write_stub("two-sum", TWO_SUM_WITH_ROOM)
    context = app.context(browser, variant, video=True)
    started = time.monotonic()
    page = app.attempt(context, "two-sum")
    video = page.video
    open_file(page, "two_sum.py")
    wait_ready(page)
    page.mouse.move(1100, 420)
    page.wait_for_timeout(500)
    trim_from = time.monotonic() - started
    scene_started = time.monotonic()
    try:
        animation.scene(app, page)
    finally:
        length = time.monotonic() - scene_started
        page.close()
        context.close()
    assert video is not None
    raw = app.work / f"{animation.name}.webm"
    video.save_as(raw)
    app.write_stub("two-sum", TWO_SUM)
    app.write_preferences()
    encode(raw, app.out, animation.name, trim_from, length)


def ffmpeg(*args: str | Path) -> None:
    run([FFMPEG, "-v", "error", "-y", *args])


def encode(raw: Path, out: Path, name: str, start: float, length: float) -> None:
    """GIF by a two-pass palette, MP4 for the web and the first frame as a poster."""
    say(f"  encode {name}: starts at {start:.1f}s, runs {length:.1f}s")
    trim = ["-ss", f"{start:.2f}", "-t", f"{length:.2f}", "-i", raw]
    ffmpeg(*trim, "-frames:v", "1", out / f"{name}-poster.png")
    shrink(out / f"{name}-poster.png")
    mp4 = out / f"{name}.mp4"
    for crf in (24, 27, 30, 33):
        ffmpeg(*trim, "-an", "-vf", "scale=1200:-2:flags=lanczos,fps=25", "-c:v", "libx264",
               "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", mp4)
        if mp4.stat().st_size < MP4_LIMIT:
            break
    gif = out / f"{name}.gif"
    palette = raw.with_suffix(".palette.png")
    for width, fps in ((1100, 15), (1100, 12), (1000, 12), (900, 12), (800, 10)):
        scaled = f"fps={fps},scale={width}:-1:flags=lanczos,{DENOISE}"
        ffmpeg(*trim, "-vf", f"{scaled},palettegen=max_colors=128:stats_mode=diff",
               "-frames:v", "1", "-update", "1", palette)
        ffmpeg(*trim, "-i", palette, "-lavfi",
               f"{scaled}[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle",
               gif)
        if gif.stat().st_size < GIF_LIMIT:
            break
    palette.unlink(missing_ok=True)
    for produced in (gif, mp4, out / f"{name}-poster.png"):
        say(f"  {produced.name} {produced.stat().st_size / 1000:.0f} kB")


# Entry point ---------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--wheel", type=Path, help="the released wheel, for the prepare stage")
    parser.add_argument("--work", type=Path, required=True, help="a new or empty working folder")
    parser.add_argument("--out", type=Path, required=True, help="where the media go (docs/images)")
    parser.add_argument(
        "--stages", default=",".join(STAGES), help=f"comma list of {', '.join(STAGES)}"
    )
    parser.add_argument(
        "--shots", default=",".join(SHOTS), help="comma list of the screenshots to take"
    )
    parser.add_argument(
        "--video-theme", choices=THEMES, default="light", help="the theme the animations show"
    )
    parser.add_argument(
        "--variants", default=",".join(v.suffix for v in VARIANTS),
        help="comma list of the screenshots' theme and width: light, dark, light-phone, dark-phone",
    )
    parser.add_argument(
        "--accept-license", action="append", default=[], metavar="KEY",
        help="with prepare: accept this server's license in the throwaway workspace, such as "
        "kotlin-lsp, once you have read it; repeat for more",
    )
    args = parser.parse_args()
    stages = [stage for stage in args.stages.split(",") if stage]
    unknown = set(stages) - set(STAGES)
    if unknown:
        sys.exit(f"unknown stages: {', '.join(sorted(unknown))}")
    shots = tuple(shot for shot in args.shots.split(",") if shot)
    unknown = set(shots) - set(SHOTS)
    if unknown:
        sys.exit(f"unknown shots: {', '.join(sorted(unknown))}")
    wanted = {name for name in args.variants.split(",") if name}
    unknown = wanted - {v.suffix for v in VARIANTS}
    if unknown:
        sys.exit(f"unknown variants: {', '.join(sorted(unknown))}")
    variants = [v for v in VARIANTS if v.suffix in wanted]
    app = Showcase(args.work, args.out, shots)
    app.out.mkdir(parents=True, exist_ok=True)
    try:
        if "prepare" in stages:
            if not args.wheel:
                sys.exit("--wheel is needed to prepare")
            app.prepare(args.wheel.resolve(), tuple(args.accept_license))
        if "seed" in stages:
            app.seed()
        if {"videos", "shots", "mock"} & set(stages):
            with app.serving(), sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    if "videos" in stages:
                        for animation in ANIMATIONS:
                            record(app, browser, animation, args.video_theme)
                    if "shots" in stages:
                        for variant in variants:
                            context = app.context(browser, variant)
                            try:
                                feature_shots(app, context, variant)
                                app_shots(app, context, variant)
                            finally:
                                context.close()
                    if "mock" in stages:
                        mock_shots(app, browser)
                finally:
                    browser.close()
    finally:
        app.stop_gradle()


if __name__ == "__main__":
    main()
