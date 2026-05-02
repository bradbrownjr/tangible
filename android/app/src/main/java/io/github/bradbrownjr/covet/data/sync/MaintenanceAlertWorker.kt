package io.github.bradbrownjr.covet.data.sync

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
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
import io.github.bradbrownjr.covet.MainActivity
import io.github.bradbrownjr.covet.R
import io.github.bradbrownjr.covet.data.auth.SessionStore
import io.github.bradbrownjr.covet.data.remote.CovetApi
import java.util.concurrent.TimeUnit

/**
 * Runs once a day when the device has network.
 * Fetches overdue + due-within-7-days alerts from the server and posts a
 * single grouped local notification so the user doesn't miss anything.
 *
 * No Firebase project required — this is pure WorkManager + NotificationCompat.
 * Admins deploying their own server never need to recompile the APK.
 */
@HiltWorker
class MaintenanceAlertWorker @AssistedInject constructor(
    @Assisted private val appContext: Context,
    @Assisted params: WorkerParameters,
    private val api: CovetApi,
    private val session: SessionStore,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        // Skip silently when the user has not logged in yet.
        if (!session.isLoggedIn()) return Result.success()

        return try {
            val alerts = api.getAlerts(withinDays = 7)
            if (alerts.isEmpty()) return Result.success()

            val overdue = alerts.filter { a ->
                a.due_at != null && a.due_at < nowIso()
            }
            val upcoming = alerts.filter { a ->
                a.due_at == null || a.due_at >= nowIso()
            }

            // Build a concise summary line.
            val parts = buildList {
                if (overdue.isNotEmpty()) add("${overdue.size} overdue")
                if (upcoming.isNotEmpty()) add("${upcoming.size} due soon")
            }
            if (parts.isEmpty()) return Result.success()

            val summary = parts.joinToString(", ")
            val lines = (overdue + upcoming).take(5).map { it.title }

            postNotification(appContext, summary, lines)
            Result.success()
        } catch (_: Throwable) {
            // Network failures — retry with backoff rather than crashing.
            Result.retry()
        }
    }

    private fun nowIso(): String {
        val now = java.time.Instant.now()
        return now.toString() // e.g. "2026-05-02T12:00:00Z"
    }

    companion object {
        const val UNIQUE_NAME = "covet-maintenance-alerts"
        const val CHANNEL_ID = "covet_maintenance"
        const val NOTIFICATION_ID = 1001

        fun ensureChannel(context: Context) {
            val mgr = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (mgr.getNotificationChannel(CHANNEL_ID) != null) return
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Maintenance & alerts",
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = "Daily summary of overdue and upcoming maintenance tasks, chores, and expiry alerts."
            }
            mgr.createNotificationChannel(channel)
        }

        fun schedule(context: Context) {
            ensureChannel(context)
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = PeriodicWorkRequestBuilder<MaintenanceAlertWorker>(1, TimeUnit.DAYS)
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(UNIQUE_NAME, ExistingPeriodicWorkPolicy.KEEP, request)
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(UNIQUE_NAME)
        }

        private fun postNotification(context: Context, summary: String, lines: List<String>) {
            val mgr = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

            val tapIntent = PendingIntent.getActivity(
                context,
                0,
                Intent(context, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    putExtra("navigate_to", "maintenance")
                },
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

            val style = NotificationCompat.InboxStyle()
            lines.forEach { style.addLine(it) }

            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentTitle("Covet — maintenance alert")
                .setContentText(summary)
                .setStyle(style)
                .setContentIntent(tapIntent)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .build()

            mgr.notify(NOTIFICATION_ID, notification)
        }
    }
}
