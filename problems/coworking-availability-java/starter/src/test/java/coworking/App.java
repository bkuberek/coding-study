package coworking;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Your app, asked over HTTP as cstudy's cases ask it. */
final class App {
    private static final Duration LIMIT = Duration.ofSeconds(30);
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private final HttpClient client = HttpClient.newHttpClient();
    private final URI base = URI.create("http://127.0.0.1:" + System.getenv("PORT"));

    record Answer(int status, JsonNode body) {}

    /** The status and JSON body your app answers to {@code GET path}, errors included. */
    Answer get(String path) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(base.resolve(path)).timeout(LIMIT).build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return new Answer(response.statusCode(), JSON.readTree(response.body()));
    }

    static JsonNode json(String text) {
        return JSON.readTree(text);
    }
}
