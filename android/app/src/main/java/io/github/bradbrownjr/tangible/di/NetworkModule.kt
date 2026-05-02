package io.github.bradbrownjr.tangible.di

import android.content.Context
import coil.ImageLoader
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.converter.scalars.ScalarsConverterFactory
import io.github.bradbrownjr.tangible.BuildConfig
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import io.github.bradbrownjr.tangible.data.remote.AuthInterceptor
import io.github.bradbrownjr.tangible.data.remote.BaseUrlInterceptor
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
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
            .addInterceptor(BaseUrlInterceptor(session))
            .addInterceptor(AuthInterceptor(session))
            .addInterceptor(log)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    /**
     * The base URL is a placeholder; [BaseUrlInterceptor] rewrites the scheme,
     * host, and port on every request from the URL stored in [SessionStore].
     * This lets the singleton survive from app start through login without
     * needing an Activity restart.
     */
    @Provides @Singleton
    fun retrofit(client: OkHttpClient, moshi: Moshi): Retrofit {
        return Retrofit.Builder()
            .baseUrl("http://localhost/api/")
            .client(client)
            .addConverterFactory(ScalarsConverterFactory.create())
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
    }

    @Provides @Singleton
    fun api(retrofit: Retrofit): TangibleApi = retrofit.create(TangibleApi::class.java)

    @Provides @Singleton
    fun imageLoader(@ApplicationContext ctx: Context, client: OkHttpClient): ImageLoader =
        ImageLoader.Builder(ctx).okHttpClient(client).build()

    /**
     * Build a one-off [TangibleApi] for an arbitrary base URL.
     * Used during login (before the user has saved a base URL).
     */
    fun apiFor(baseUrl: String, moshi: Moshi, client: OkHttpClient): TangibleApi =
        Retrofit.Builder()
            .baseUrl("${baseUrl.trimEnd('/')}/api/")
            .client(client)
            .addConverterFactory(ScalarsConverterFactory.create())
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(TangibleApi::class.java)
}
