import java.util.*;

/**
 * A request is read in three stages: skip empty lines, find the end of the head (the first CRLF
 * CRLF), then read the body that the framing fields announce. Each stage either finishes, needs
 * more bytes, or fails, and the same code serves the one-shot methods and the connection: {@code
 * feed} keeps the unread bytes and runs the stages again each time more arrive, so a message is
 * reported by the call that completes it.
 */
public class HttpParser {
    private static final String CRLF = "\r\n";
    private static final String END_OF_HEAD = "\r\n\r\n";
    private static final String TOKEN_SYMBOLS = "!#$%&'*+-.^_`|~";
    // A size with more significant digits than this is larger than any limit, so it is never
    // converted into a number: that is how a size such as 10000000000000000 (hex) cannot wrap.
    private static final int MAX_SIGNIFICANT_DIGITS = 12;
    private static final long TOO_MANY_DIGITS = 1L << 62;

    private static final class Failure extends Exception {
        final String code;

        Failure(String code) {
            super(code, null, false, false);
            this.code = code;
        }
    }

    private static final class NeedMore extends Exception {
        NeedMore() {
            super(null, null, false, false);
        }
    }

    private static final class Message {
        final List<List<String>> rows;
        final int end;

        Message(List<List<String>> rows, int end) {
            this.rows = rows;
            this.end = end;
        }
    }

    private Long headLimit = null;
    private Long bodyLimit = null;
    private String buffer = "";
    private boolean closed = false;

    // Level 1
    public List<List<String>> parseHead(String data) {
        try {
            int start = skipEmptyLines(data, 0);
            int end = endOfHead(data, start);
            return headRows(data.substring(start, end - 4));
        } catch (NeedMore needMore) {
            return error("incomplete");
        } catch (Failure failure) {
            return error(failure.code);
        }
    }

    // Level 2
    public List<List<String>> parseMessage(String data) {
        try {
            return message(data, skipEmptyLines(data, 0)).rows;
        } catch (NeedMore needMore) {
            return error("incomplete");
        } catch (Failure failure) {
            return error(failure.code);
        }
    }

    // Level 3
    public List<List<String>> feed(String data) {
        List<List<String>> rows = new ArrayList<>();
        if (closed) {
            return rows;
        }
        buffer += data;
        while (true) {
            buffer = buffer.substring(skipEmptyLines(buffer, 0));
            Message message;
            try {
                message = message(buffer, 0);
            } catch (NeedMore needMore) {
                return rows;
            } catch (Failure failure) {
                closed = true;
                buffer = "";
                rows.add(List.of("error", failure.code));
                return rows;
            }
            rows.addAll(message.rows);
            buffer = buffer.substring(message.end);
        }
    }

    public List<List<String>> close() {
        if (closed) {
            return new ArrayList<>();
        }
        closed = true;
        return buffer.isEmpty() ? new ArrayList<>() : error("incomplete");
    }

    // Level 4
    public void setLimits(int maxHeadBytes, int maxBodyBytes) {
        headLimit = (long) maxHeadBytes;
        bodyLimit = (long) maxBodyBytes;
    }

    // The stages
    private static List<List<String>> error(String code) {
        List<List<String>> rows = new ArrayList<>();
        rows.add(List.of("error", code));
        return rows;
    }

    private static boolean isTokenChar(char c) {
        return c >= '0' && c <= '9' || c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z'
                || TOKEN_SYMBOLS.indexOf(c) >= 0;
    }

    private static boolean isToken(String text) {
        if (text.isEmpty()) {
            return false;
        }
        for (int i = 0; i < text.length(); i++) {
            if (!isTokenChar(text.charAt(i))) {
                return false;
            }
        }
        return true;
    }

    private static boolean isHex(char c) {
        return c >= '0' && c <= '9' || c >= 'a' && c <= 'f' || c >= 'A' && c <= 'F';
    }

    private static boolean allDigits(String text) {
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) < '0' || text.charAt(i) > '9') {
                return false;
            }
        }
        return true;
    }

    private static String trimOws(String text) {
        int start = 0;
        int end = text.length();
        while (start < end && (text.charAt(start) == ' ' || text.charAt(start) == '\t')) {
            start++;
        }
        while (end > start && (text.charAt(end - 1) == ' ' || text.charAt(end - 1) == '\t')) {
            end--;
        }
        return text.substring(start, end);
    }

    private static String stripLeadingZeros(String digits) {
        int start = 0;
        while (start < digits.length() && digits.charAt(start) == '0') {
            start++;
        }
        return digits.substring(start);
    }

    /** The value of a run of digits, or a huge number when it has too many digits to matter. */
    private static long sizeOf(String digits, int radix) {
        String significant = stripLeadingZeros(digits);
        if (significant.isEmpty()) {
            return 0;
        }
        if (significant.length() > MAX_SIGNIFICANT_DIGITS) {
            return TOO_MANY_DIGITS;
        }
        return Long.parseLong(significant, radix);
    }

    private static int skipEmptyLines(String data, int pos) {
        while (data.startsWith(CRLF, pos)) {
            pos += 2;
        }
        return pos;
    }

    private static void checkLineEndings(String text) throws Failure {
        String rest = text.replace(CRLF, "");
        if (rest.indexOf('\r') >= 0 || rest.indexOf('\n') >= 0) {
            throw new Failure("bad-line-ending");
        }
    }

    private static List<String> parseRequestLine(String line) throws Failure {
        String[] parts = line.split(" ", -1);
        if (parts.length != 3) {
            throw new Failure("bad-request-line");
        }
        String method = parts[0];
        String target = parts[1];
        String version = parts[2];
        boolean validTarget = !target.isEmpty() && target.chars().allMatch(c -> c >= '!' && c <= '~');
        boolean validVersion = version.length() == 8 && version.startsWith("HTTP/")
                && Character.isDigit(version.charAt(5)) && version.charAt(6) == '.'
                && Character.isDigit(version.charAt(7));
        if (!isToken(method) || !validTarget || !validVersion) {
            throw new Failure("bad-request-line");
        }
        return List.of("request", method, target, version);
    }

    private static List<String> parseFieldLine(String tag, String line) throws Failure {
        if (line.startsWith(" ") || line.startsWith("\t")) {
            throw new Failure("obs-fold");
        }
        int colon = line.indexOf(':');
        if (colon == -1 || !isToken(line.substring(0, colon))) {
            throw new Failure("bad-field");
        }
        String value = trimOws(line.substring(colon + 1));
        if (!value.chars().allMatch(c -> c == '\t' || c >= ' ' && c <= '~')) {
            throw new Failure("bad-field");
        }
        return List.of(tag, line.substring(0, colon).toLowerCase(Locale.ROOT), value);
    }

    /** A comma-separated list over every field line, with empty elements dropped. */
    private static List<String> listElements(List<String> values) {
        List<String> elements = new ArrayList<>();
        for (String element : String.join(",", values).split(",", -1)) {
            String trimmed = trimOws(element);
            if (!trimmed.isEmpty()) {
                elements.add(trimmed);
            }
        }
        return elements;
    }

    /**
     * The index just after the head's empty line. With a limit, only the first {@code limit}
     * bytes are searched, so a head that cannot fit fails without waiting.
     */
    private int endOfHead(String data, int start) throws Failure, NeedMore {
        int found;
        if (headLimit == null) {
            found = data.indexOf(END_OF_HEAD, start);
        } else {
            int windowEnd = (int) Math.min(data.length(), start + headLimit);
            int inWindow = data.substring(start, windowEnd).indexOf(END_OF_HEAD);
            found = inWindow == -1 ? -1 : start + inWindow;
            if (found == -1 && data.length() - start >= headLimit) {
                throw new Failure("head-too-large");
            }
        }
        if (found == -1) {
            throw new NeedMore();
        }
        return found + 4;
    }

    private List<List<String>> headRows(String text) throws Failure {
        checkLineEndings(text);
        String[] lines = text.split(CRLF, -1);
        List<String> request = parseRequestLine(lines[0]);
        List<List<String>> rows = new ArrayList<>();
        rows.add(request);
        int hosts = 0;
        for (int i = 1; i < lines.length; i++) {
            List<String> row = parseFieldLine("field", lines[i]);
            if (row.get(1).equals("host")) {
                hosts++;
            }
            rows.add(row);
        }
        if (hosts > 1 || hosts == 0 && request.get(3).equals("HTTP/1.1")) {
            throw new Failure("bad-host");
        }
        return rows;
    }

    private Message message(String data, int start) throws Failure, NeedMore {
        int headEnd = endOfHead(data, start);
        List<List<String>> rows = headRows(data.substring(start, headEnd - 4));
        List<String> codings = new ArrayList<>();
        List<String> lengths = new ArrayList<>();
        for (List<String> row : rows.subList(1, rows.size())) {
            if (row.get(1).equals("transfer-encoding")) {
                codings.add(row.get(2));
            } else if (row.get(1).equals("content-length")) {
                lengths.add(row.get(2));
            }
        }
        if (!codings.isEmpty() && !lengths.isEmpty()) {
            throw new Failure("ambiguous-length");
        }
        if (!codings.isEmpty()) {
            List<String> list = listElements(codings);
            if (list.size() != 1 || !list.get(0).equalsIgnoreCase("chunked")) {
                throw new Failure("unsupported-transfer-coding");
            }
            return chunked(data, headEnd, rows);
        }
        long length = lengths.isEmpty() ? 0 : contentLength(lengths);
        if (data.length() - headEnd < length) {
            throw new NeedMore();
        }
        int end = headEnd + (int) length;
        rows.add(List.of("body", data.substring(headEnd, end)));
        return new Message(rows, end);
    }

    private long contentLength(List<String> lines) throws Failure {
        List<String> elements = listElements(lines);
        if (elements.isEmpty() || !elements.stream().allMatch(HttpParser::allDigits)) {
            throw new Failure("bad-content-length");
        }
        String first = stripLeadingZeros(elements.get(0));
        for (String element : elements) {
            if (!stripLeadingZeros(element).equals(first)) {
                throw new Failure("conflicting-content-length");
            }
        }
        long length = sizeOf(elements.get(0), 10);
        if (tooLarge(length, 0)) {
            throw new Failure("body-too-large");
        }
        return length;
    }

    private boolean tooLarge(long size, long used) {
        return bodyLimit != null && used + size > bodyLimit;
    }

    private Message chunked(String data, int pos, List<List<String>> rows) throws Failure, NeedMore {
        StringBuilder content = new StringBuilder();
        long total = 0;
        while (true) {
            int lineEnd = data.indexOf(CRLF, pos);
            if (lineEnd == -1) {
                throw new NeedMore();
            }
            long size = chunkSize(data.substring(pos, lineEnd));
            if (tooLarge(size, total)) {
                throw new Failure("body-too-large");
            }
            pos = lineEnd + 2;
            if (size == 0) {
                break;
            }
            if (data.length() - pos < size + 2) {
                throw new NeedMore();
            }
            int end = pos + (int) size;
            if (!data.startsWith(CRLF, end)) {
                throw new Failure("bad-chunk");
            }
            content.append(data, pos, end);
            total += size;
            pos = end + 2;
        }
        rows.add(List.of("body", content.toString()));
        if (data.startsWith(CRLF, pos)) {
            return new Message(rows, pos + 2);
        }
        int found = data.indexOf(END_OF_HEAD, pos);
        if (found == -1) {
            throw new NeedMore();
        }
        String text = data.substring(pos, found);
        checkLineEndings(text);
        for (String line : text.split(CRLF, -1)) {
            rows.add(parseFieldLine("trailer", line));
        }
        return new Message(rows, found + 4);
    }

    private static long chunkSize(String line) throws Failure {
        if (line.indexOf('\r') >= 0 || line.indexOf('\n') >= 0) {
            throw new Failure("bad-chunk-size");
        }
        int semicolon = line.indexOf(';');
        String digits = line;
        if (semicolon != -1) {
            int end = semicolon;
            while (end > 0 && (line.charAt(end - 1) == ' ' || line.charAt(end - 1) == '\t')) {
                end--;
            }
            digits = line.substring(0, end);
        }
        if (digits.isEmpty() || !digits.chars().allMatch(c -> isHex((char) c))) {
            throw new Failure("bad-chunk-size");
        }
        return sizeOf(digits, 16);
    }
}
