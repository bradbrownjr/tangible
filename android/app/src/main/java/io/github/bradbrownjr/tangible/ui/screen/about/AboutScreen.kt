package io.github.bradbrownjr.tangible.ui.screen.about

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.BuildConfig
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AboutUi(
    val changelogText: String = "",
    val changelogLoading: Boolean = false,
    val changelogError: String? = null,
    val showChangelog: Boolean = false,
    val helpText: String = "",
    val helpLoading: Boolean = false,
    val showHelp: Boolean = false,
    // Non-null when diagnostics text is ready to be copied by the UI.
    val diagnosticsReady: String? = null,
)

@HiltViewModel
class AboutViewModel @Inject constructor(
    private val api: TangibleApi,
    private val session: SessionStore,
) : ViewModel() {
    private val _state = MutableStateFlow(AboutUi())
    val state: StateFlow<AboutUi> = _state.asStateFlow()

    fun showChangelog() {
        if (_state.value.changelogText.isNotEmpty()) {
            _state.value = _state.value.copy(showChangelog = true)
            return
        }
        _state.value = _state.value.copy(changelogLoading = true, changelogError = null)
        viewModelScope.launch {
            try {
                val text = api.changelog()
                _state.value = _state.value.copy(
                    changelogText = text,
                    changelogLoading = false,
                    showChangelog = true,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    changelogLoading = false,
                    changelogError = t.message ?: "Failed to load changelog",
                )
            }
        }
    }

    fun dismissChangelog() { _state.value = _state.value.copy(showChangelog = false) }

    fun showHelp() { _state.value = _state.value.copy(showHelp = true) }
    fun dismissHelp() { _state.value = _state.value.copy(showHelp = false) }

    fun prepareDiagnostics() {
        viewModelScope.launch {
            val baseUrl = session.baseUrl.first() ?: "—"
            val username = session.username.first() ?: "—"
            val logLines = try {
                val pid = android.os.Process.myPid()
                val proc = Runtime.getRuntime().exec(
                    arrayOf("logcat", "-d", "-t", "100", "--pid=$pid"),
                )
                proc.inputStream.bufferedReader().readText()
            } catch (_: Exception) {
                "(logcat unavailable)"
            }
            val text = buildString {
                appendLine("=== Tangible Diagnostics ===")
                appendLine("App version : ${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})")
                appendLine("Android     : ${Build.VERSION.RELEASE} (SDK ${Build.VERSION.SDK_INT})")
                appendLine("Device      : ${Build.MANUFACTURER} ${Build.MODEL}")
                appendLine("Server      : $baseUrl")
                appendLine("User        : $username")
                appendLine()
                appendLine("--- Recent logs ---")
                append(logLines)
            }
            _state.value = _state.value.copy(diagnosticsReady = text)
        }
    }

    fun clearDiagnostics() { _state.value = _state.value.copy(diagnosticsReady = null) }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AboutScreen(
    onBack: () -> Unit,
    vm: AboutViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    val ctx = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }

    // Copy diagnostics to clipboard when the ViewModel has them ready.
    LaunchedEffect(s.diagnosticsReady) {
        val text = s.diagnosticsReady ?: return@LaunchedEffect
        val clipboard = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Tangible diagnostics", text))
        snackbarHostState.showSnackbar("Diagnostics copied to clipboard")
        vm.clearDiagnostics()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("About") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Tangible", style = MaterialTheme.typography.headlineMedium)
            Text(
                "A personal collection tracker for books, music, games, and more. " +
                    "Self-hosted, open-source, and designed for collectors who want " +
                    "ownership of their data.",
                style = MaterialTheme.typography.bodyMedium,
            )
            HorizontalDivider()
            Text("Version ${BuildConfig.VERSION_NAME}", style = MaterialTheme.typography.bodyMedium)
            TextButton(
                onClick = {
                    ctx.startActivity(
                        Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/bradbrownjr/tangible"))
                    )
                },
                contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
            ) {
                Text(
                    "github.com/bradbrownjr/tangible",
                    textDecoration = TextDecoration.Underline,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            HorizontalDivider()
            OutlinedButton(
                onClick = vm::showChangelog,
                enabled = !s.changelogLoading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (s.changelogLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier
                            .height(16.dp)
                            .padding(end = 8.dp),
                        strokeWidth = 2.dp,
                    )
                }
                Text(if (s.changelogLoading) "Loading…" else "What's new")
            }
            if (s.changelogError != null) {
                Text(
                    s.changelogError!!,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            OutlinedButton(
                onClick = vm::showHelp,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Help / User guide")
            }
            OutlinedButton(
                onClick = vm::prepareDiagnostics,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Copy diagnostics")
            }
        }
    }

    if (s.showChangelog) {
        AlertDialog(
            onDismissRequest = vm::dismissChangelog,
            title = { Text("What's new") },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState()),
                ) {
                    Text(
                        s.changelogText,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = vm::dismissChangelog) { Text("Close") }
            },
        )
    }

    if (s.showHelp) {
        AlertDialog(
            onDismissRequest = vm::dismissHelp,
            title = { Text("User guide") },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState()),
                ) {
                    Text(
                        ANDROID_USER_GUIDE,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = vm::dismissHelp) { Text("Close") }
            },
        )
    }
}

// Embedded user guide — mirrors docs/android-user-guide.md.
private val ANDROID_USER_GUIDE = """
FIRST LAUNCH
Enter your server URL (e.g. https://tangible.example.com), username, and password, then tap Sign in.

COLLECTIONS LIST
Pull down to refresh. Tap the menu (☰) for Settings, About, and Help. Tap + to create a new collection.

CREATING A COLLECTION
Choose a preset category (Books, Music, Games, etc.) or Custom, then enter a name and optional description.

EDITING A COLLECTION
Open a collection and tap the pencil icon (visible to editors and owners). Change the name or description and tap Save.

COLLECTION DETAIL — LIST AND GRID VIEWS
Tap the grid/list toggle in the toolbar to switch views. Pull down to refresh. Type in the search bar to filter items.

ADDING ITEMS
Tap + to open the Add item dialog. You can enter a title directly, type/paste an ISBN, or paste a product URL and tap Look up to pre-fill metadata. Use the barcode scanner (QR icon in toolbar) to scan physical items.

ITEM DETAIL
Tap any item to open its detail screen. The photo strip at the top shows attached photos — tap to view full-screen, tap trash to delete. Tap the pencil icon to edit fields and Save to commit.

BARCODE SCANNING
Tap the QR icon in the collection detail toolbar. Point at a barcode; the app looks it up and shows matching candidates. Choose one to pre-fill the add-item dialog.

SETTINGS
Hamburger menu → Settings. Change server URL, test the connection, or sign out.

OFFLINE
Collections and items are cached on-device. Browse offline; edits require a live connection. The cache refreshes automatically every 15 minutes in the background.
""".trimIndent()
