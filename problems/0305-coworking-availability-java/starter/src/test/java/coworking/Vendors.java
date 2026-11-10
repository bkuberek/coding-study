package coworking;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Collections;
import tools.jackson.databind.json.JsonMapper;

/**
 * The vendors, through the mock servers' control interface, whose address and token
 * {@code cstudy test} gives your tests. Only the scenarios in a vendor's API.md are there.
 */
final class Vendors {
    private static final Duration LIMIT = Duration.ofSeconds(30);
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private final HttpClient client = HttpClient.newHttpClient();
    private final URI control = URI.create(System.getenv("CSTUDY_MOCK_CONTROL_URL") + "/");
    private final String authorization = "Bearer " + System.getenv("CSTUDY_MOCK_CONTROL_TOKEN");

    /** Makes {@code vendor} behave as {@code scenario} says, or as usual for null. */
    void setScenario(String vendor, String scenario) throws IOException, InterruptedException {
        String body = JSON.writeValueAsString(Collections.singletonMap("scenario", scenario));
        send(request("mocks/" + vendor + "/scenario")
                .header("Content-Type", "application/json")
                .PUT(BodyPublishers.ofString(body)));
    }

    /** Every vendor back to no scenario. */
    void reset() throws IOException, InterruptedException {
        send(request("reset").POST(BodyPublishers.noBody()));
    }

    private HttpRequest.Builder request(String path) {
        return HttpRequest.newBuilder(control.resolve(path))
                .timeout(LIMIT)
                .header("Authorization", authorization);
    }

    private void send(HttpRequest.Builder request) throws IOException, InterruptedException {
        HttpResponse<String> response = client.send(request.build(), HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 300) {
            throw new IllegalStateException("the mock control answered " + response.statusCode() + ": " + response.body());
        }
    }
}
