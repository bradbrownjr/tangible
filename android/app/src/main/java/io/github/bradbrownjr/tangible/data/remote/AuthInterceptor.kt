package io.github.bradbrownjr.tangible.data.remote

import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import io.github.bradbrownjr.tangible.data.auth.SessionStore

/**
 * Adds `Authorization: Bearer <token>` if one is stored.
 *
 * `runBlocking` is used inside the OkHttp interceptor because OkHttp's API is
 * synchronous; the DataStore read is sub-millisecond after the first hit.
 */
class AuthInterceptor(private val session: SessionStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = runBlocking { session.token.firstOrNull() }
        val req = chain.request()
        val out = if (token.isNullOrBlank()) req
        else req.newBuilder().addHeader("Authorization", "Bearer $token").build()
        val response = chain.proceed(out)
        // An expired or invalid token produces a 401. Clear the stored token so
        // RootViewModel.loggedIn emits false and TangibleApp re-routes to Login.
        if (response.code == 401) {
            runBlocking { session.clear() }
        }
        return response
    }
}
