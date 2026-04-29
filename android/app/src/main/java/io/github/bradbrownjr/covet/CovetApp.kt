package io.github.bradbrownjr.covet

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import dagger.hilt.android.HiltAndroidApp
import io.github.bradbrownjr.covet.data.sync.SyncWorker
import javax.inject.Inject

@HiltAndroidApp
class CovetApp : Application(), Configuration.Provider {
    @Inject lateinit var workerFactory: HiltWorkerFactory

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()

    override fun onCreate() {
        super.onCreate()
        // Idempotent: ExistingPeriodicWorkPolicy.KEEP keeps any in-flight schedule.
        SyncWorker.schedule(this)
    }
}
