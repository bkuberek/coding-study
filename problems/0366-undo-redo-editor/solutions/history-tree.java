import java.util.*;

public class Editor {
    private static final long GROUP_GAP_MS = 1000;
    private static final int ROOT = 0;

    /**
     * One recorded edit, kept as a command that can be applied and reverted: at {@code position},
     * {@code removed} was replaced by {@code inserted}. The step is also the history state it leads to.
     */
    private static final class Step {
        final int number;
        final Step parent;
        final int position;
        String removed = "";
        StringBuilder inserted = new StringBuilder();
        final List<Step> children = new ArrayList<>();
        Step currentChild;

        Step(int number, Step parent, int position) {
            this.number = number;
            this.parent = parent;
            this.position = position;
        }

        String apply(String text) {
            return text.substring(0, position) + inserted + text.substring(position + removed.length());
        }

        String revert(String text) {
            return text.substring(0, position) + removed + text.substring(position + inserted.length());
        }

        /** This step and every step above it, up to the root. */
        List<Step> ancestors() {
            List<Step> chain = new ArrayList<>();
            for (Step step = this; step != null; step = step.parent) {
                chain.add(step);
            }
            return chain;
        }
    }

    private String content;
    private final List<Step> steps = new ArrayList<>();
    private Step current;
    private final Map<String, String> checkpoints = new HashMap<>();
    private boolean groupOpen = false;
    private long lastTypedAt = 0;

    public Editor(String initial) {
        content = initial;
        current = new Step(ROOT, null, 0);
        steps.add(current);
    }

    // Level 1
    public void insert(int position, String text) {
        groupOpen = false;
        record(Math.min(position, content.length()), "", text);
    }

    public void erase(int position, int count) {
        groupOpen = false;
        int start = Math.min(position, content.length());
        int end = (int) Math.min(content.length(), (long) start + count);
        record(start, content.substring(start, end), "");
    }

    public boolean undo() {
        groupOpen = false;
        if (current.parent == null) {
            return false;
        }
        content = current.revert(content);
        current = current.parent;
        return true;
    }

    public boolean redo() {
        groupOpen = false;
        Step child = current.currentChild;
        if (child == null) {
            return false;
        }
        content = child.apply(content);
        current = child;
        return true;
    }

    public String text() {
        return content;
    }

    // Level 2
    public void typeText(long timestamp, int position, String text) {
        int at = Math.min(position, content.length());
        if (joinsGroup(timestamp, at)) {
            content = content.substring(0, at) + text + content.substring(at);
            current.inserted.append(text);
        } else {
            record(at, "", text);
        }
        groupOpen = true;
        lastTypedAt = timestamp;
    }

    private boolean joinsGroup(long timestamp, int position) {
        Step group = current;
        int length = group.inserted.length();
        return groupOpen
                && position == group.position + length
                && timestamp - lastTypedAt <= GROUP_GAP_MS
                && (length == 0 || group.inserted.charAt(length - 1) != ' ');
    }

    // Level 3
    public void checkpoint(String name) {
        groupOpen = false;
        checkpoints.put(name, content);
    }

    public boolean restore(String name) {
        groupOpen = false;
        String saved = checkpoints.get(name);
        if (saved == null) {
            return false;
        }
        record(0, content, saved);
        return true;
    }

    // Level 4
    public int state() {
        return current.number;
    }

    public List<Integer> branches() {
        List<Integer> numbers = new ArrayList<>();
        for (Step child : current.children) {
            numbers.add(child.number);
        }
        return numbers;
    }

    public boolean jump(int state) {
        groupOpen = false;
        if (state < 0 || state >= steps.size()) {
            return false;
        }
        Step target = steps.get(state);
        List<Step> pathDown = target.ancestors();
        Set<Step> onTargetPath = new HashSet<>(pathDown);
        while (!onTargetPath.contains(current)) {
            content = current.revert(content);
            current = current.parent;
        }
        int common = pathDown.indexOf(current);
        for (int index = common - 1; index >= 0; index--) {
            content = pathDown.get(index).apply(content);
        }
        for (int index = 1; index < pathDown.size(); index++) {
            pathDown.get(index).currentChild = pathDown.get(index - 1);
        }
        current = target;
        return true;
    }

    /** Records one step, unless it would leave the text as it is. */
    private void record(int position, String removed, String inserted) {
        if (removed.equals(inserted)) {
            return;
        }
        Step step = new Step(steps.size(), current, position);
        step.removed = removed;
        step.inserted.append(inserted);
        steps.add(step);
        current.children.add(step);
        current.currentChild = step;
        content = step.apply(content);
        current = step;
    }
}
