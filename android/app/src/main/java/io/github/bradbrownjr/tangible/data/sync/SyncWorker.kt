package io.github.bradbrownjr.tangible.data.sync

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ItemRepository
import java.util.concurrent.TimeUnit

/**
 * Periodic sync: refresh the local cache with the latest server state.
 *
 * Phase 5.5 scope: pull-only mirror so the UI has fresh data the next time
 * the user opens the app while offline. Push of pending writes (CRDT change
 * blobs) lands in Phase 5.6.
 */
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val collections: CollectionRepository,
    private val items: ItemRepository,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result = try {
        val cs = collections.list()
        for (c in cs) {
            // Best-effort per-collection refresh; one failure shouldn't abort the rest.
            runCatching { items.list(c.id) }
        }
        Result.success()
    } catch (t: Throwable) {
        // Transient (network) failures should retry with backoff.
        Result.retry()
    }

    companion object {
        const val UNIQUE_NAME = "tangible-sync"

        fun schedule(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(UNIQUE_NAME, ExistingPeriodicWorkPolicy.KEEP, request)
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(UNIQUE_NAME)
        }
    }
}
