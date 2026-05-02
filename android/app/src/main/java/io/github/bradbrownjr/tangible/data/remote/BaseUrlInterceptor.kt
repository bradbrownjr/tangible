package io.github.bradbrownjr.tangible.data.remote

import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.runBlocking
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.Response
import io.github.bradbrownjr.tangible.data.auth.SessionStore

/**
 * Rewrites each request's scheme, host, and port to the server URL stored in
 * [SessionStore] at request time.
 *
 * [io.github.bradbrownjr.tangible.di.NetworkModule] provides [Retrofit] as a
 * singleton. On a fresh install the URL has not been saved yet, so Retrofit is
 * built with a placeholder base URL (`http://localhost/api/`). This interceptor
 * ensures every network call reaches the user's actual server immediately after
 * login — without requiring an Activity restart.
 */
class BaseUrlInterceptor(private val session: SessionStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val savedBase = runBlocking { session.baseUrl.firstOrNull() }
            ?: return chain.proceed(chain.request())

        val apiBase = "${savedBase.trimEnd('/')}/api/".toHttpUrlOrNull()
            ?: return chain.proceed(chain.request())

        val req = chain.request()
        val newUrl = req.url.newBuilder()
            .scheme(apiBase.scheme)
            .host(apiBase.host)
            .port(apiBase.port)
            .build()

        return chain.proceed(req.newBuilder().url(newUrl).build())
    }
}
