package rooms;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.regex.Pattern;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

public final class Server {
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Path STOCK = Path.of(System.getenv("CSTUDY_DATA_DIR"), "stock.json");
    private static final URI VENDOR = URI.create(System.getenv("ROOM_VENDOR_URL") + "/v1/rooms");
    private static final Pattern DATE = Pattern.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}");
    private static final Duration VENDOR_LIMIT = Duration.ofSeconds(1);
    private static final HttpClient VENDORS = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(VENDOR_LIMIT)
            .build();
    private static final Map<String, Object> DEGRADED = Map.of("rooms", List.of(), "degraded", true);
    private static final int TOO_MANY_REQUESTS = 429;

    private Server() {}

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(System.getenv("PORT"));
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.createContext("/", Server::handle);
        server.start();
        System.out.println("listening on " + port);
    }

    private static void handle(HttpExchange exchange) throws IOException {
        URI target = exchange.getRequestURI();
        switch (exchange.getRequestMethod() + " " + target.getPath()) {
            case "GET /health" -> answer(exchange, 200, Map.of("status", "ok"));
            case "GET /desks" -> desks(exchange, dateOf(target));
            case "POST /desks/book" -> book(exchange);
            case "GET /rooms" -> answer(exchange, 200, rooms());
            default -> answer(exchange, 404, Map.of("error", "not found"));
        }
    }

    private static void desks(HttpExchange exchange, String date) throws IOException {
        if (DATE.matcher(date).matches()) {
            answer(exchange, 200, Map.of("date", date, "available", available()));
        } else {
            answer(exchange, 400, Map.of("error", "date is required"));
        }
    }

    private static void book(HttpExchange exchange) throws IOException {
        int left = available() - 1;
        Files.writeString(STOCK, JSON.writeValueAsString(Map.of("available", left)));
        answer(exchange, 201, Map.of("available", left));
    }

    private static int available() throws IOException {
        return JSON.readTree(Files.readString(STOCK)).get("available").asInt();
    }

    private static Object rooms() {
        try {
            HttpResponse<byte[]> answer = vendorCall();
            if (answer.statusCode() == TOO_MANY_REQUESTS) {
                long seconds = Long.parseLong(answer.headers().firstValue("Retry-After").orElse("1"));
                Thread.sleep(Duration.ofSeconds(seconds));
                answer = vendorCall();
            }
            JsonNode rooms = answer.statusCode() == 200 ? JSON.readTree(answer.body()).get("rooms") : null;
            return rooms != null && rooms.isArray() ? Map.of("rooms", rooms, "degraded", false) : DEGRADED;
        } catch (IOException | JacksonException | NumberFormatException failed) {
            return DEGRADED;
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            return DEGRADED;
        }
    }

    private static HttpResponse<byte[]> vendorCall() throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(VENDOR).timeout(VENDOR_LIMIT).build();
        return VENDORS.send(request, HttpResponse.BodyHandlers.ofByteArray());
    }

    private static String dateOf(URI target) {
        String query = target.getRawQuery() == null ? "" : target.getRawQuery();
        for (String pair : query.split("&")) {
            if (pair.startsWith("date=")) {
                return URLDecoder.decode(pair.substring("date=".length()), StandardCharsets.UTF_8);
            }
        }
        return "";
    }

    private static void answer(HttpExchange exchange, int status, Object body) throws IOException {
        byte[] json = JSON.writeValueAsBytes(body);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, json.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(json);
        }
    }
}
