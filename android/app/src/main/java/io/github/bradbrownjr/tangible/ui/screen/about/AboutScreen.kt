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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.BuildConfig
import io.github.bradbrownjr.tangible.R
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
    showBackButton: Boolean = true,
    vm: AboutViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    val ctx = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }
    val labelDiagnostics = stringResource(R.string.diagnostics_clipboard_label)
    val labelCopied = stringResource(R.string.diagnostics_copied)

    // Copy diagnostics to clipboard when the ViewModel has them ready.
    LaunchedEffect(s.diagnosticsReady) {
        val text = s.diagnosticsReady ?: return@LaunchedEffect
        val clipboard = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(labelDiagnostics, text))
        snackbarHostState.showSnackbar(labelCopied)
        vm.clearDiagnostics()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.about)) },
                navigationIcon = {
                    if (showBackButton) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                        }
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
                stringResource(R.string.about_description),
                style = MaterialTheme.typography.bodyMedium,
            )
            HorizontalDivider()
            Text(stringResource(R.string.version, BuildConfig.VERSION_NAME), style = MaterialTheme.typography.bodyMedium)
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
                Text(if (s.changelogLoading) stringResource(R.string.loading) else stringResource(R.string.whats_new))
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
                Text(stringResource(R.string.help_user_guide))
            }
            OutlinedButton(
                onClick = vm::prepareDiagnostics,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.copy_diagnostics))
            }
        }
    }

    if (s.showChangelog) {
        AlertDialog(
            onDismissRequest = vm::dismissChangelog,
            title = { Text(stringResource(R.string.whats_new)) },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState()),
                ) {
                    MarkdownContent(s.changelogText)
                }
            },
            confirmButton = {
                TextButton(onClick = vm::dismissChangelog) { Text(stringResource(R.string.close)) }
            },
        )
    }

    if (s.showHelp) {
        val ctx = LocalContext.current
        AlertDialog(
            onDismissRequest = vm::dismissHelp,
            title = { Text(stringResource(R.string.user_guide)) },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState()),
                ) {
                    MarkdownContent(ANDROID_USER_GUIDE)
                    Spacer(Modifier.height(12.dp))
                    TextButton(
                        onClick = {
                            ctx.startActivity(
                                Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/bradbrownjr/tangible/blob/main/docs/android-user-guide.md"))
                            )
                        },
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                    ) {
                        Text(
                            "View full documentation online",
                            textDecoration = TextDecoration.Underline,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = vm::dismissHelp) { Text(stringResource(R.string.close)) }
            },
        )
    }
}

// ---------------------------------------------------------------------------
// Simple Markdown renderer for the changelog and help text.
// ---------------------------------------------------------------------------

private enum class MdBlockStyle { H1, H2, H3, BULLET, NORMAL }
private data class MdBlock(val text: String, val style: MdBlockStyle)

private fun stripBold(text: String): String = text.replace(Regex("\\*\\*(.+?)\\*\\*"), "$1")

private fun parseMarkdown(text: String): List<MdBlock> = text.lines().mapNotNull { line ->
    when {
        line.startsWith("# ")   -> MdBlock(stripBold(line.removePrefix("# ")), MdBlockStyle.H1)
        line.startsWith("## ")  -> MdBlock(stripBold(line.removePrefix("## ")), MdBlockStyle.H2)
        line.startsWith("### ") -> MdBlock(stripBold(line.removePrefix("### ")), MdBlockStyle.H3)
        line.startsWith("- ")   -> MdBlock("\u2022 " + stripBold(line.removePrefix("- ")), MdBlockStyle.BULLET)
        line.isBlank()          -> null
        else                    -> MdBlock(stripBold(line), MdBlockStyle.NORMAL)
    }
}

@Composable
private fun MarkdownContent(text: String) {
    val blocks = remember(text) { parseMarkdown(text) }
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        blocks.forEach { block ->
            when (block.style) {
                MdBlockStyle.H1 -> Text(
                    block.text,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 4.dp, bottom = 4.dp),
                )
                MdBlockStyle.H2 -> Text(
                    block.text,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 10.dp, bottom = 2.dp),
                )
                MdBlockStyle.H3 -> Text(
                    block.text,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(top = 6.dp),
                )
                MdBlockStyle.BULLET -> Text(
                    block.text,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(start = 8.dp),
                )
                MdBlockStyle.NORMAL -> Text(
                    block.text,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

// Embedded user guide — mirrors docs/android-user-guide.md.
private val ANDROID_USER_GUIDE = """
## First launch
- Enter your server URL (e.g. https://tangible.example.com), username, and password, then tap Sign in.

## Collections list
- Pull down to refresh.
- Tap the menu (☰) for Settings, About, and Help.
- Tap + to create a new collection.

## Creating a collection
- Choose a preset category (Books, Music, Games, etc.) or Custom.
- Enter a name and optional description, then tap Create.

## Editing a collection
- Open a collection and tap the pencil icon (visible to editors and owners).
- Change the name or description and tap Save.

## Collection detail
- Tap the grid/list toggle in the toolbar to switch views.
- Pull down to refresh.
- Type in the search bar to filter items.

## Adding items
- Tap + to open the Add item dialog.
- Enter a title directly, type/paste an ISBN, or paste a product URL and tap Look up to pre-fill metadata.
- Use the barcode scanner (QR icon in toolbar) to scan physical items.

## Item detail
- Tap any item to open its detail screen.
- The photo strip at the top shows attached photos — tap to view full-screen, tap trash to delete.
- Tap the pencil icon to edit fields and Save to commit.

## Barcode scanning
- Tap the QR icon in the collection detail toolbar.
- Point at a barcode; the app looks it up and shows matching candidates.
- Choose one to pre-fill the add-item dialog.

## Lists
- Use the Lists tab to manage Groceries, Hardware, Home Goods, and Wish Lists.
- Scan a barcode from the shopping list to look up a product and add it by name.
- Tap the check button on any item to mark it as purchased.

## Settings
- Hamburger menu → Settings.
- Change server URL, test the connection, or sign out.

## Offline
- Collections and items are cached on-device. Browse offline; edits require a live connection.
- The cache refreshes automatically every 15 minutes in the background.
""".trimIndent()
