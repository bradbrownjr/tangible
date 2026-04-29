package io.github.bradbrownjr.covet.di

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import io.github.bradbrownjr.covet.BuildConfig
import io.github.bradbrownjr.covet.data.auth.SessionStore
import io.github.bradbrownjr.covet.data.remote.AuthInterceptor
import io.github.bradbrownjr.covet.data.remote.CovetApi
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides @Singleton
    fun moshi(): Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    @Provides @Singleton
    fun okHttp(session: SessionStore): OkHttpClient {
        val log = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BASIC
                    else HttpLoggingInterceptor.Level.NONE
        }
        return OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor(session))
            .addInterceptor(log)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    /**
     * The bound base URL is read once at injection time. After login or sign-out
     * the user must restart the activity (or we rebuild via [retrofitFor]).
     */
    @Provides @Singleton
    fun retrofit(client: OkHttpClient, moshi: Moshi, session: SessionStore): Retrofit {
        val base = runBlocking { session.baseUrl.firstOrNull() } ?: "https://covet.invalid/"
        val apiBase = "${base.trimEnd('/')}/api/"
        return Retrofit.Builder()
            .baseUrl(apiBase)
            .client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
    }

    @Provides @Singleton
    fun api(retrofit: Retrofit): CovetApi = retrofit.create(CovetApi::class.java)

    /**
     * Build a one-off [CovetApi] for an arbitrary base URL.
     * Used during login (before the user has saved a base URL).
     */
    fun apiFor(baseUrl: String, moshi: Moshi, client: OkHttpClient): CovetApi =
        Retrofit.Builder()
            .baseUrl("${baseUrl.trimEnd('/')}/api/")
            .client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(CovetApi::class.java)
}
