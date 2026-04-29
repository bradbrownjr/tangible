package io.github.bradbrownjr.covet.data.repo

import com.squareup.moshi.Moshi
import okhttp3.OkHttpClient
import io.github.bradbrownjr.covet.data.auth.SessionStore
import io.github.bradbrownjr.covet.data.auth.normalizedBaseUrl
import io.github.bradbrownjr.covet.data.remote.LoginRequest
import io.github.bradbrownjr.covet.di.NetworkModule
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Login flow:
 *   1. POST /auth/login with username/password against user-supplied base URL
 *   2. Use returned cookie to POST /auth/tokens?name=<device> for a long-lived bearer token
 *   3. Persist (baseUrl, token, username) in [SessionStore]
 *
 * The Hilt-provided [CovetApi] reads its base URL on construction so callers must
 * restart the Activity after login (handled by AuthViewModel emitting a session
 * event the UI observes).
 */
@Singleton
class AuthRepository @Inject constructor(
    private val session: SessionStore,
    private val moshi: Moshi,
    private val client: OkHttpClient,
) {
    suspend fun login(serverUrl: String, username: String, password: String) {
        val base = serverUrl.normalizedBaseUrl()
        // OkHttp doesn't keep cookies across calls without a CookieJar — so we
        // attach one for the login flow only. POST /auth/login sets the session
        // cookie; the very next call (POST /auth/tokens) reuses it to mint a
        // long-lived bearer that we persist for all subsequent requests.
        val jar = okhttp3.JavaNetCookieJar(java.net.CookieManager())
        val authedClient = client.newBuilder().cookieJar(jar).build()
        val authedApi = NetworkModule.apiFor(base, moshi, authedClient)
        authedApi.login(LoginRequest(username, password))
        val deviceName = "android-${android.os.Build.MODEL}".take(64)
        val token = authedApi.createToken(deviceName)
        val raw = token.token ?: error("Server did not return a token value")
        session.save(base, raw, username)
    }

    suspend fun logout() = session.clear()
}
