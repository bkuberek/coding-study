package coworking.vendors

import java.io.IOException
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpHeaders
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.toJavaDuration
import kotlinx.coroutines.delay
import kotlinx.coroutines.future.await
import kotlinx.serialization.DeserializationStrategy
import kotlinx.serialization.json.Json

/** How long a vendor gets to answer. */
internal val REQUEST_LIMIT = 1500.milliseconds

private val client = HttpClient.newBuilder()
    .version(HttpClient.Version.HTTP_1_1)
    .connectTimeout(REQUEST_LIMIT.toJavaDuration())
    .build()

/** Vendors add fields; a client reads the ones their API documents. */
private val vendorJson = Json { ignoreUnknownKeys = true }

/** What a vendor answered, whatever its status. */
internal class Answer(val status: Int, val headers: HttpHeaders, val body: ByteArray) {
    val ok: Boolean get() = status in 200..299

    /** The body as [shape], what the vendor documents; anything else throws [VendorUnavailable]. */
    fun <T> decode(shape: DeserializationStrategy<T>, vendor: String): T =
        try {
            vendorJson.decodeFromString(shape, body.decodeToString())
        } catch (broken: IllegalArgumentException) {
            throw VendorUnavailable("$vendor sent what it does not document: ${broken.message}", broken)
        }
}

/** One request, whatever its status; throws [VendorUnavailable] when no answer comes in time. */
internal suspend fun fetch(uri: URI): Answer {
    val request = HttpRequest.newBuilder(uri).timeout(REQUEST_LIMIT.toJavaDuration()).build()
    val response = try {
        client.sendAsync(request, HttpResponse.BodyHandlers.ofByteArray()).await()
    } catch (noAnswer: IOException) {
        throw VendorUnavailable("no answer from $uri: $noAnswer", noAnswer)
    }
    return Answer(response.statusCode(), response.headers(), response.body())
}

/**
 * Asks until asking again will not help, or [maxRequests] are spent. [waitBeforeRetry] reads an
 * answer and gives the wait before asking again, or null when asking again will not help; the wait
 * starts once the answer has arrived.
 */
internal suspend fun <T> askWithRetries(
    maxRequests: Int,
    waitBeforeRetry: (T) -> Duration?,
    ask: suspend () -> T,
): T {
    var answer = ask()
    repeat(maxRequests - 1) {
        val wait = waitBeforeRetry(answer) ?: return answer
        delay(wait)
        answer = ask()
    }
    return answer
}
