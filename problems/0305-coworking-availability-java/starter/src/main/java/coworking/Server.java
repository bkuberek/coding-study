package coworking;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.file.Path;
import java.util.Map;
import java.util.OptionalInt;
import java.util.concurrent.Executors;
import tools.jackson.databind.json.JsonMapper;

/** The coworking space's API: what can be booked on a day. */
public final class Server {
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private Server() {}

    public static void main(String[] args) throws IOException {
        DeskInventory desks = DeskInventory.fromFile(Path.of("data/desks.json"));
        int port = Integer.parseInt(System.getenv("PORT"));
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.createContext("/", exchange -> handle(exchange, desks));
        server.start();
        System.out.println("listening on " + port);
    }

    private static void handle(HttpExchange exchange, DeskInventory desks) throws IOException {
        URI target = exchange.getRequestURI();
        switch (target.getPath()) {
            case "/health" -> answer(exchange, 200, Map.of("status", "ok"));
            case "/desks" -> {
                String date = Query.value(target, "date");
                answer(exchange, 200, new DeskCount(date, desks.availableOn(date)));
            }
            default -> answer(exchange, 404, Map.of("error", "not found"));
        }
    }

    record DeskCount(String date, OptionalInt available) {}

    private static void answer(HttpExchange exchange, int status, Object body) throws IOException {
        byte[] json = JSON.writeValueAsBytes(body);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, json.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(json);
        }
    }
}
