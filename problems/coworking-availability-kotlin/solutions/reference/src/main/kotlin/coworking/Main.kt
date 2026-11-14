package coworking

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import coworking.vendors.AnnexVendor
import coworking.vendors.RoomVendor
import java.lang.System.Logger.Level
import java.net.InetSocketAddress
import java.net.URI
import java.nio.file.Path
import java.util.concurrent.Executors
import kotlinx.coroutines.runBlocking

private val log = System.getLogger("coworking")

fun main() {
    val api = CoworkingApi(
        DeskInventory.fromFile(Path.of("data/desks.json")),
        listOf(
            RoomVendor(URI.create(System.getenv("ROOM_VENDOR_URL"))),
            AnnexVendor(URI.create(System.getenv("ANNEX_VENDOR_URL"))),
        ),
    )
    val port = System.getenv("PORT").toInt()
    val server = HttpServer.create(InetSocketAddress(port), 0)
    server.executor = Executors.newVirtualThreadPerTaskExecutor()
    server.createContext("/") { exchange -> exchange.reply(api) }
    server.start()
    println("listening on $port")
}

/**
 * HTTP in and out; every method goes to the API, which refuses all but GET. Each request runs on a
 * virtual thread of its own, and its coroutines on that thread.
 */
private fun HttpExchange.reply(api: CoworkingApi) {
    val reply = try {
        runBlocking { api.answer(requestMethod, requestURI) }
    } catch (failure: Exception) {
        log.log(Level.ERROR, "no answer to $requestURI", failure)
        refusal(500, "internal error")
    }
    val body = reply.body.toByteArray()
    responseHeaders["Content-Type"] = "application/json"
    sendResponseHeaders(reply.status, body.size.toLong())
    responseBody.use { it.write(body) }
}
