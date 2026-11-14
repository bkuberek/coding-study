package coworking;

import java.util.Map;

/** What the API answers: a status, and a body that becomes JSON. */
public record Reply(int status, Object body) {
    static Reply error(int status, String error) {
        return new Reply(status, Map.of("error", error));
    }
}
