package rooms;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.Map;
import java.util.concurrent.Executors;
import tools.jackson.databind.json.JsonMapper;

public final class Server {
    private static final JsonMapper JSON = JsonMapper.builder().build();

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
        if (exchange.getRequestURI().getPath().equals("/health")) {
            answer(exchange, 200, Map.of("status", "ok"));
        } else {
            answer(exchange, 404, Map.of("error", "not found"));
        }
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
