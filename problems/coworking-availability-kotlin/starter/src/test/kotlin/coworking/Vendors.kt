package coworking

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpRequest.BodyPublishers
import java.net.http.HttpResponse
import java.time.Duration
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/**
 * The vendors, through the mock servers' control interface, whose address and token `cstudy test`
 * gives your tests. Only the scenarios in a vendor's API.md are there.
 */
class Vendors {
    private val client = HttpClient.newHttpClient()
    private val control = System.getenv("CSTUDY_MOCK_CONTROL_URL")
    private val authorization = "Bearer ${System.getenv("CSTUDY_MOCK_CONTROL_TOKEN")}"

    /** Makes [vendor] behave as [scenario] says, or as usual for null. */
    fun setScenario(vendor: String, scenario: String?) {
        val body = buildJsonObject { put("scenario", scenario) }.toString()
        send(
            request("/mocks/$vendor/scenario")
                .header("Content-Type", "application/json")
                .PUT(BodyPublishers.ofString(body)),
        )
    }

    /** Every vendor back to no scenario. */
    fun reset() = send(request("/reset").POST(BodyPublishers.noBody()))

    private fun request(path: String): HttpRequest.Builder =
        HttpRequest.newBuilder(URI.create(control + path))
            .timeout(LIMIT)
            .header("Authorization", authorization)

    private fun send(request: HttpRequest.Builder) {
        val response = client.send(request.build(), HttpResponse.BodyHandlers.ofString())
        check(response.statusCode() < 300) {
            "the mock control answered ${response.statusCode()}: ${response.body()}"
        }
    }

    private companion object {
        val LIMIT: Duration = Duration.ofSeconds(30)
    }
}
