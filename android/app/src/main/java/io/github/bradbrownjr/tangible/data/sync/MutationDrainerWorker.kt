package io.github.bradbrownjr.tangible.data.sync

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import io.github.bradbrownjr.tangible.data.local.PendingMutationDao
import io.github.bradbrownjr.tangible.data.remote.RestockRequest
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import org.json.JSONObject
import retrofit2.HttpException
import java.io.IOException

/**
 * Drains the pending_mutations queue when the device is back online.
 *
 * Enqueued by NetworkMonitor.onAvailable as a one-shot KEEP job with
 * CONNECTED constraint so WorkManager will also schedule it automatically
 * when the radio comes back.
 */
@HiltWorker
class MutationDrainerWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val api: TangibleApi,
    private val mutationDao: PendingMutationDao,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val pending = mutationDao.getAll()
        for (mutation in pending) {
            try {
                val payload = JSONObject(mutation.payloadJson)
                when (mutation.type) {
                    "PURCHASE_SHOPPING_ITEM" -> {
                        val entryId = payload.getString("entry_id")
                        try {
                            api.purchaseShoppingItem(entryId, idempotencyKey = mutation.id)
                        } catch (e: HttpException) {
                            // 404 = already deleted; 409 = already purchased; both are success.
                            if (e.code() != 404 && e.code() != 409) throw e
                        }
                    }
                    "RESTOCK_DEPLETED_ITEM" -> {
                        val itemId = payload.getString("item_id")
                        val quantity = payload.getInt("quantity")
                        api.restockItem(
                            itemId,
                            RestockRequest(
                                quantity = quantity,
                                purchased_at = java.time.OffsetDateTime.now().toString(),
                                mark_in_stock = true,
                            ),
                            idempotencyKey = mutation.id,
                        )
                    }
                    else -> {
                        // Unknown mutation type — drop it to avoid blocking the queue.
                        mutationDao.delete(mutation.id)
                        continue
                    }
                }
                mutationDao.delete(mutation.id)
            } catch (e: IOException) {
                // Still offline — stop processing and let WorkManager retry when connected.
                break
            } catch (e: Exception) {
                // Permanent error (bad payload, auth failure, etc.) — drop the mutation.
                mutationDao.delete(mutation.id)
            }
        }
        return Result.success()
    }

    companion object {
        const val UNIQUE_NAME = "tangible-mutation-drainer"

        fun enqueue(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = OneTimeWorkRequestBuilder<MutationDrainerWorker>()
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniqueWork(UNIQUE_NAME, ExistingWorkPolicy.KEEP, request)
        }
    }
}
