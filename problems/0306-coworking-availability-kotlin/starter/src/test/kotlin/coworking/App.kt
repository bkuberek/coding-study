package coworking

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

/** Your app, asked over HTTP as cstudy's cases ask it. */
class App {
    private val client = HttpClient.newHttpClient()
    private val base = URI.create("http://127.0.0.1:${System.getenv("PORT")}")

    data class Answer(val status: Int, val body: JsonElement)

    /** The status and JSON body your app answers to `GET path`, errors included. */
    fun get(path: String): Answer {
        val request = HttpRequest.newBuilder(base.resolve(path)).timeout(LIMIT).build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        return Answer(response.statusCode(), json(response.body()))
    }

    private companion object {
        val LIMIT: Duration = Duration.ofSeconds(30)
    }
}

fun json(text: String): JsonElement = Json.parseToJsonElement(text)
