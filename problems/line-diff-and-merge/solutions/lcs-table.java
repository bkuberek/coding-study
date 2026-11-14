import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class LineDiff {
    private static final char KEEP = ' ';
    private static final char REMOVE = '-';
    private static final char ADD = '+';
    private static final Pattern HEADER = Pattern.compile("^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@$");
    private static final String OURS = "<<<<<<< ours";
    private static final String BASE = "||||||| base";
    private static final String SEPARATOR = "=======";
    private static final String THEIRS = ">>>>>>> theirs";

    private record Step(char kind, String line) {}

    private record Hunk(int start, List<String> old, List<String> fresh) {}

    private List<String> last = new ArrayList<>();

    // Level 1
    public List<String> lcs(List<String> before, List<String> after) {
        List<String> kept = new ArrayList<>();
        for (Step step : script(before, after)) {
            if (step.kind() == KEEP) {
                kept.add(step.line());
            }
        }
        return kept;
    }

    public List<String> diff(List<String> before, List<String> after) {
        List<String> lines = new ArrayList<>();
        for (Step step : script(before, after)) {
            lines.add(step.kind() + step.line());
        }
        return lines;
    }

    // Level 2
    public List<String> unified(List<String> before, List<String> after, int context) {
        List<Step> steps = script(before, after);
        List<Integer> changed = new ArrayList<>();
        for (int index = 0; index < steps.size(); index++) {
            if (steps.get(index).kind() != KEEP) {
                changed.add(index);
            }
        }
        List<String> lines = new ArrayList<>();
        if (changed.isEmpty()) {
            return lines;
        }
        List<int[]> groups = new ArrayList<>();
        int first = changed.get(0);
        int previous = first;
        for (int index : changed.subList(1, changed.size())) {
            if (index - previous - 1 > 2 * context) {
                groups.add(new int[] {first, previous});
                first = index;
            }
            previous = index;
        }
        groups.add(new int[] {first, previous});
        for (int[] group : groups) {
            int start = Math.max(0, group[0] - context);
            int end = Math.min(steps.size(), group[1] + context + 1);
            List<Step> prior = steps.subList(0, start);
            List<Step> hunk = steps.subList(start, end);
            String oldRange = range(count(prior, ADD), count(hunk, ADD));
            String newRange = range(count(prior, REMOVE), count(hunk, REMOVE));
            lines.add("@@ -" + oldRange + " +" + newRange + " @@");
            for (Step step : hunk) {
                lines.add(step.kind() + step.line());
            }
        }
        return lines;
    }

    // Level 3
    public List<String> applyPatch(List<String> lines, List<String> patch, int maxOffset) {
        List<String> result = new ArrayList<>(lines);
        List<String> statuses = new ArrayList<>();
        int added = 0;
        int shift = 0;
        int floor = 0;
        for (Hunk hunk : parseHunks(patch)) {
            int base = hunk.start() + added;
            int found = findHunk(result, hunk.old(), base + shift, floor, maxOffset);
            if (found < 0) {
                statuses.add("rejected");
                continue;
            }
            List<String> replaced = result.subList(found, found + hunk.old().size());
            replaced.clear();
            replaced.addAll(hunk.fresh());
            shift = found - base;
            added += hunk.fresh().size() - hunk.old().size();
            floor = found + hunk.fresh().size();
            statuses.add("applied " + shift);
        }
        last = result;
        return statuses;
    }

    public List<String> patched() {
        return new ArrayList<>(last);
    }

    // Level 4
    public List<String> merge(List<String> base, List<String> ours, List<String> theirs) {
        Map<Integer, Integer> toOurs = keptAt(base, ours);
        Map<Integer, Integer> toTheirs = keptAt(base, theirs);
        List<String> merged = new ArrayList<>();
        int o = 0;
        int a = 0;
        int b = 0;
        for (int index = 0; index < base.size(); index++) {
            Integer j = toOurs.get(index);
            Integer k = toTheirs.get(index);
            if (j != null && k != null) {
                merged.addAll(resolve(base.subList(o, index), ours.subList(a, j), theirs.subList(b, k)));
                merged.add(base.get(index));
                o = index + 1;
                a = j + 1;
                b = k + 1;
            }
        }
        merged.addAll(resolve(base.subList(o, base.size()), ours.subList(a, ours.size()), theirs.subList(b, theirs.size())));
        return merged;
    }

    /**
     * The diff with the most kept lines that, read from the top, keeps rather than removes and
     * removes rather than adds wherever both stay optimal.
     */
    private static List<Step> script(List<String> before, List<String> after) {
        int n = before.size();
        int m = after.size();
        // longest[i][j]: the length of a longest common subsequence of before[i:] and after[j:].
        int[][] longest = new int[n + 1][m + 1];
        for (int i = n - 1; i >= 0; i--) {
            for (int j = m - 1; j >= 0; j--) {
                longest[i][j] = before.get(i).equals(after.get(j))
                        ? longest[i + 1][j + 1] + 1
                        : Math.max(longest[i + 1][j], longest[i][j + 1]);
            }
        }
        List<Step> steps = new ArrayList<>();
        int i = 0;
        int j = 0;
        while (i < n || j < m) {
            if (i < n && j < m && before.get(i).equals(after.get(j))) {
                steps.add(new Step(KEEP, before.get(i)));
                i++;
                j++;
            } else if (i < n && (j == m || longest[i + 1][j] >= longest[i][j + 1])) {
                steps.add(new Step(REMOVE, before.get(i)));
                i++;
            } else {
                steps.add(new Step(ADD, after.get(j)));
                j++;
            }
        }
        return steps;
    }

    /** The number of steps that are not of the given kind. */
    private static int count(List<Step> steps, char skipped) {
        int total = 0;
        for (Step step : steps) {
            if (step.kind() != skipped) {
                total++;
            }
        }
        return total;
    }

    private static String range(int linesBefore, int size) {
        if (size == 0) {
            return linesBefore + ",0";
        }
        return size == 1 ? Integer.toString(linesBefore + 1) : (linesBefore + 1) + "," + size;
    }

    /** Each hunk with the index where its old lines start, its old lines and its new lines. */
    private static List<Hunk> parseHunks(List<String> patch) {
        List<Hunk> hunks = new ArrayList<>();
        for (String line : patch) {
            Matcher header = HEADER.matcher(line);
            if (header.matches()) {
                int oldStart = Integer.parseInt(header.group(1));
                int oldCount = header.group(2) == null ? 1 : Integer.parseInt(header.group(2));
                hunks.add(new Hunk(oldCount > 0 ? oldStart - 1 : oldStart, new ArrayList<>(), new ArrayList<>()));
                continue;
            }
            if (line.isEmpty()) {
                continue;
            }
            Hunk hunk = hunks.get(hunks.size() - 1);
            String text = line.substring(1);
            char kind = line.charAt(0);
            if (kind != ADD) {
                hunk.old().add(text);
            }
            if (kind != REMOVE) {
                hunk.fresh().add(text);
            }
        }
        return hunks;
    }

    /** The nearest position to {@code expected} where {@code old} matches, the earlier one first, or -1. */
    private static int findHunk(List<String> result, List<String> old, int expected, int floor, int maxOffset) {
        for (int distance = 0; distance <= maxOffset; distance++) {
            for (int position : new int[] {expected - distance, expected + distance}) {
                boolean fits = floor <= position && position + old.size() <= result.size();
                if (fits && result.subList(position, position + old.size()).equals(old)) {
                    return position;
                }
            }
        }
        return -1;
    }

    /** For each line of {@code base} that the diff to {@code other} keeps, the index it keeps it at. */
    private static Map<Integer, Integer> keptAt(List<String> base, List<String> other) {
        Map<Integer, Integer> kept = new HashMap<>();
        int i = 0;
        int j = 0;
        for (Step step : script(base, other)) {
            if (step.kind() == KEEP) {
                kept.put(i, j);
            }
            if (step.kind() != ADD) {
                i++;
            }
            if (step.kind() != REMOVE) {
                j++;
            }
        }
        return kept;
    }

    private static List<String> resolve(List<String> base, List<String> ours, List<String> theirs) {
        if (ours.equals(theirs)) {
            return ours;
        }
        if (ours.equals(base)) {
            return theirs;
        }
        if (theirs.equals(base)) {
            return ours;
        }
        List<String> conflict = new ArrayList<>();
        conflict.add(OURS);
        conflict.addAll(ours);
        conflict.add(BASE);
        conflict.addAll(base);
        conflict.add(SEPARATOR);
        conflict.addAll(theirs);
        conflict.add(THEIRS);
        return conflict;
    }
}
