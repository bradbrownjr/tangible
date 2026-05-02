package io.github.bradbrownjr.tangible

import android.Manifest
import android.content.Intent
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
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import io.github.bradbrownjr.tangible.nfc.NfcManager
import io.github.bradbrownjr.tangible.ui.TangibleApp
import io.github.bradbrownjr.tangible.ui.theme.TangibleTheme
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

        // Handle NFC intent that launched (or re-launched) the activity.
        intent?.let { NfcManager.handleIntent(it) }

        setContent {
            val themeMode by sessionStore.themeMode.collectAsState(initial = null)
            val systemDark = isSystemInDarkTheme()
            val dark = when (themeMode) {
                "light" -> false
                "dark"  -> true
                else    -> systemDark
            }
            TangibleTheme(darkTheme = dark) {
                TangibleApp()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        NfcManager.handleIntent(intent)
    }
}
