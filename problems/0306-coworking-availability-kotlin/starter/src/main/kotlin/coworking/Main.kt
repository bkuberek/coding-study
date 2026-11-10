package coworking

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import java.nio.file.Path
import java.util.concurrent.Executors
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** The coworking space's API: what can be booked on a day. */
fun main() {
    val desks = DeskInventory.fromFile(Path.of("data/desks.json"))
    val port = System.getenv("PORT").toInt()
    val server = HttpServer.create(InetSocketAddress(port), 0)
    server.executor = Executors.newVirtualThreadPerTaskExecutor()
    server.createContext("/") { exchange -> exchange.handle(desks) }
    server.start()
    println("listening on $port")
}

@Serializable
data class Status(val status: String)

@Serializable
data class DeskCount(val date: String, val available: Int?)

@Serializable
data class Problem(val error: String)

private fun HttpExchange.handle(desks: DeskInventory) {
    when (requestURI.path) {
        "/health" -> answer(200, Json.encodeToString(Status("ok")))
        "/desks" -> {
            val date = requestURI.queryValue("date")
            answer(200, Json.encodeToString(DeskCount(date, desks.availableOn(date))))
        }
        else -> answer(404, Json.encodeToString(Problem("not found")))
    }
}

private fun HttpExchange.answer(status: Int, json: String) {
    val body = json.toByteArray()
    responseHeaders["Content-Type"] = "application/json"
    sendResponseHeaders(status, body.size.toLong())
    responseBody.use { it.write(body) }
}
