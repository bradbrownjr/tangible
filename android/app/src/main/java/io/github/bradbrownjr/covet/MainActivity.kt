package io.github.bradbrownjr.covet

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.content.ContextCompat
import dagger.hilt.android.AndroidEntryPoint
import io.github.bradbrownjr.covet.data.auth.SessionStore
import io.github.bradbrownjr.covet.ui.CovetApp
import io.github.bradbrownjr.covet.ui.theme.CovetTheme
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject lateinit var sessionStore: SessionStore

    private val requestNotificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* no-op */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Android 13+ requires POST_NOTIFICATIONS at runtime.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
        ) {
            requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            val themeMode by sessionStore.themeMode.collectAsState(initial = null)
            val systemDark = isSystemInDarkTheme()
            val dark = when (themeMode) {
                "light" -> false
                "dark"  -> true
                else    -> systemDark
            }
            CovetTheme(darkTheme = dark) {
                CovetApp()
            }
        }
    }
}
