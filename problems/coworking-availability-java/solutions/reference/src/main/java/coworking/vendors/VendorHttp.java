package coworking.vendors;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpHeaders;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.json.JsonMapper;

/** One request to a vendor, with the limit every vendor gets, and its answer whatever its status. */
final class VendorHttp {
    static final Duration REQUEST_LIMIT = Duration.ofMillis(1500);
    private static final JsonMapper JSON = JsonMapper.builder()
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .build();
    private static final HttpClient CLIENT = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(REQUEST_LIMIT)
            .build();

    private VendorHttp() {}

    /** What a vendor answered. */
    record Answer(int status, HttpHeaders headers, byte[] body) {
        boolean ok() {
            return status >= 200 && status < 300;
        }

        /**
         * The body as {@code shape}, a record of what the vendor documents, whose constructor
         * refuses a part that is missing; fields it does not document are left out.
         */
        <T> T as(Class<T> shape, String vendor) throws VendorUnavailableException {
            try {
                return JSON.readValue(body, shape);
            } catch (JacksonException broken) {
                throw new VendorUnavailableException(vendor + " sent what it does not document", broken);
            }
        }
    }

    /**
     * One request, whatever its status.
     *
     * @throws VendorUnavailableException when no answer comes within the limit
     */
    static Answer get(URI uri) throws VendorUnavailableException {
        HttpRequest request = HttpRequest.newBuilder(uri).timeout(REQUEST_LIMIT).build();
        try {
            HttpResponse<byte[]> response = CLIENT.send(request, HttpResponse.BodyHandlers.ofByteArray());
            return new Answer(response.statusCode(), response.headers(), response.body());
        } catch (IOException noAnswer) {
            throw new VendorUnavailableException("no answer from " + uri + ": " + noAnswer, noAnswer);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new VendorUnavailableException("stopped while asking " + uri, interrupted);
        }
    }
}
