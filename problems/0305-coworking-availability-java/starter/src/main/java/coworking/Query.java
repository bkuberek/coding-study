package coworking;

import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;

/** The query string of a request's target. */
final class Query {
    private Query() {}

    /** The first value of {@code name}, decoded; empty when the target has none. */
    static String value(URI target, String name) {
        String query = target.getRawQuery();
        if (query == null) {
            return "";
        }
        String prefix = name + "=";
        for (String pair : query.split("&")) {
            if (pair.startsWith(prefix)) {
                return URLDecoder.decode(pair.substring(prefix.length()), StandardCharsets.UTF_8);
            }
        }
        return "";
    }
}
