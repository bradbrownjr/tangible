package io.github.bradbrownjr.tangible

import android.app.Application
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import coil.ImageLoader
import coil.ImageLoaderFactory
import dagger.hilt.android.HiltAndroidApp
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import io.github.bradbrownjr.tangible.data.sync.MaintenanceAlertWorker
import io.github.bradbrownjr.tangible.data.sync.NetworkMonitor
import io.github.bradbrownjr.tangible.data.sync.SyncWorker
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.runBlocking
import javax.inject.Inject

@HiltAndroidApp
class TangibleApp : Application(), Configuration.Provider, ImageLoaderFactory {
    @Inject lateinit var workerFactory: HiltWorkerFactory
    @Inject lateinit var imageLoader: ImageLoader
    @Inject lateinit var sessionStore: SessionStore
    @Inject lateinit var networkMonitor: NetworkMonitor

    override fun newImageLoader(): ImageLoader = imageLoader

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()

    override fun onCreate() {
        super.onCreate()
        // Restore user's saved locale preference (if any) into the Android locale system.
        // AppCompatDelegate persists the choice across restarts once set; this ensures
        // the locale from the DataStore (e.g. set via the web profile) is applied on first launch.
        val savedLocale = runBlocking { sessionStore.locale.firstOrNull() }
        if (!savedLocale.isNullOrBlank()) {
            AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(savedLocale))
        }
        // Idempotent: ExistingPeriodicWorkPolicy.KEEP keeps any in-flight schedule.
        SyncWorker.schedule(this)
        MaintenanceAlertWorker.schedule(this)
        // Force init of the singleton so the ConnectivityManager callback is registered.
        // The networkMonitor field is unused beyond this — the @Singleton init block does the work.
        @Suppress("UNUSED_EXPRESSION")
        networkMonitor
    }
}
