package coworking

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** What the API answers: a status, and its body as JSON. */
class Reply(val status: Int, val body: String)

inline fun <reified T> reply(status: Int, body: T): Reply = Reply(status, Json.encodeToString(body))

fun refusal(status: Int, error: String): Reply = reply(status, Problem(error))

@Serializable
data class Status(val status: String)

@Serializable
data class Problem(val error: String)
