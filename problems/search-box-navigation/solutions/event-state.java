import java.util.*;

/** The list is empty exactly when nothing is highlighted: {@code show} keeps the two in step. */
public class SearchBox {
    private static final String ARROW_DOWN = "ArrowDown";
    private static final String ARROW_UP = "ArrowUp";
    private static final String ENTER = "Enter";
    private static final int NOTHING = -1;
    private static final int NO_REQUEST = 0;

    private final List<String> names;
    private final List<String> loweredNames = new ArrayList<>();
    private List<String> shown = new ArrayList<>();
    private int highlight = NOTHING;
    private String text = "";
    private int requestsSent = 0;
    private int awaitedRequest = NO_REQUEST;
    private final List<String> selected = new ArrayList<>();

    public SearchBox(List<String> names) {
        this.names = List.copyOf(names);
        for (String name : names) {
            // Locale.ROOT: in a Turkish locale, toLowerCase() turns "I" into a dotless "ı".
            loweredNames.add(name.toLowerCase(Locale.ROOT));
        }
    }

    // Level 1
    public void keydown(long timestamp, String key) {
        switch (key) {
            case ARROW_DOWN -> move(1);
            case ARROW_UP -> move(-1);
            case ENTER -> selectHighlighted();
            default -> { }
        }
    }

    /** Releasing a key changes nothing: every action happens when the key goes down. */
    public void keyup(long timestamp, String key) {
    }

    public void resultsArrived(long timestamp, List<String> items) {
        show(items);
    }

    public List<String> results(long timestamp) {
        return new ArrayList<>(shown);
    }

    public int highlighted(long timestamp) {
        return highlight;
    }

    public String highlightedText(long timestamp) {
        return highlight == NOTHING ? "" : shown.get(highlight);
    }

    // Level 2
    public void search(long timestamp, String query) {
        String needle = query.strip().toLowerCase(Locale.ROOT);
        List<String> matches = new ArrayList<>();
        if (!needle.isEmpty()) {
            for (int index = 0; index < names.size(); index++) {
                if (loweredNames.get(index).contains(needle)) {
                    matches.add(names.get(index));
                }
            }
        }
        show(matches);
    }

    // Level 3
    public int inputChanged(long timestamp, String text) {
        this.text = text;
        if (text.isBlank()) {
            stopAwaiting();
            return NOTHING;
        }
        requestsSent += 1;
        awaitedRequest = requestsSent;
        return requestsSent;
    }

    public void responseArrived(long timestamp, int requestId, List<String> items) {
        if (requestId == awaitedRequest) {
            show(items);
        }
    }

    public String inputText(long timestamp) {
        return text;
    }

    // Level 4
    public List<String> selections(long timestamp) {
        return new ArrayList<>(selected);
    }

    /** {@code %} keeps the sign of the dividend, and Math.floorMod does not. */
    private void move(int step) {
        int count = shown.size();
        if (count > 0) {
            highlight = Math.floorMod(highlight + step, count);
        }
    }

    private void selectHighlighted() {
        if (highlight == NOTHING) {
            return;
        }
        String choice = shown.get(highlight);
        selected.add(choice);
        text = choice;
        stopAwaiting();
    }

    /** The input changed without a request: no response sent so far may be shown, and the list closes. */
    private void stopAwaiting() {
        awaitedRequest = NO_REQUEST;
        show(List.of());
    }

    private void show(List<String> items) {
        shown = new ArrayList<>(items);
        highlight = items.isEmpty() ? NOTHING : 0;
    }
}
