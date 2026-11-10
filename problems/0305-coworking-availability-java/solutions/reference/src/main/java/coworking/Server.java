package coworking;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import coworking.vendors.AnnexVendor;
import coworking.vendors.RoomVendor;
import java.io.IOException;
import java.io.OutputStream;
import java.lang.System.Logger.Level;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.Executors;
import tools.jackson.databind.json.JsonMapper;

/** HTTP in and out, and where the server starts; every answer comes from {@link CoworkingApi}. */
public final class Server {
    private static final System.Logger LOG = System.getLogger(Server.class.getName());
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private Server() {}

    public static void main(String[] args) throws IOException {
        CoworkingApi api = new CoworkingApi(
                DeskInventory.fromFile(Path.of("data/desks.json")),
                List.of(
                        new RoomVendor(URI.create(System.getenv("ROOM_VENDOR_URL"))),
                        new AnnexVendor(URI.create(System.getenv("ANNEX_VENDOR_URL")))));
        int port = Integer.parseInt(System.getenv("PORT"));
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.createContext("/", exchange -> reply(exchange, api));
        server.start();
        System.out.println("listening on " + port);
    }

    /** Every method goes to the API, which refuses all but GET. */
    private static void reply(HttpExchange exchange, CoworkingApi api) throws IOException {
        Reply reply;
        try {
            reply = api.answer(exchange.getRequestMethod(), exchange.getRequestURI());
        } catch (RuntimeException failure) {
            LOG.log(Level.ERROR, "no answer to " + exchange.getRequestURI(), failure);
            reply = Reply.error(500, "internal error");
        }
        byte[] body = JSON.writeValueAsBytes(reply.body());
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(reply.status(), body.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(body);
        }
    }
}
