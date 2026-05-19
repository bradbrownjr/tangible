package io.github.bradbrownjr.tangible.ui.screen.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.*
import androidx.compose.ui.graphics.Color
import io.github.bradbrownjr.tangible.ui.screen.about.AboutScreen
import io.github.bradbrownjr.tangible.ui.theme.ALL_PALETTES
import io.github.bradbrownjr.tangible.ui.theme.AppPalette
import io.github.bradbrownjr.tangible.ui.theme.DEFAULT_PALETTE_ID
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier

import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import io.github.bradbrownjr.tangible.data.remote.PatchMeRequest
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.remote.NotificationPrefDto
import io.github.bradbrownjr.tangible.data.remote.NotificationPrefUpdate
import io.github.bradbrownjr.tangible.data.repo.AuthRepository
import android.content.Context
import javax.inject.Inject

private val SUPPORTED_LOCALES = listOf(
    "en" to "English",
    "fr" to "Français",
    "de" to "Deutsch",
    "es" to "Español",
    "ja" to "日本語",
    "zh" to "中文",
    "it" to "Italiano",
)

private val KIND_LABEL_RES = mapOf(
    "maintenance_due" to R.string.notif_maintenance_due,
    "chore_due" to R.string.notif_chore_due,
    "item_use_by" to R.string.notif_item_use_by,
    "item_expires" to R.string.notif_item_expires,
    "lot_use_by" to R.string.notif_lot_use_by,
    "low_stock" to R.string.notif_low_stock,
)

data class SettingsUi(
    val baseUrl: String? = null,
    val username: String? = null,
    val testBusy: Boolean = false,
    val testResult: String? = null,
    val testOk: Boolean = false,
    // "system" | "light" | "dark" — null treated as "system"
    val themeMode: String? = null,
    val palette: String = DEFAULT_PALETTE_ID,
    val locale: String? = null,
    val notifPrefs: List<NotificationPrefDto> = emptyList(),
    val notifBusy: Boolean = false,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val session: SessionStore,
    private val auth: AuthRepository,
    private val api: TangibleApi,
    @ApplicationContext private val context: Context,
) : ViewModel() {
    private val _state = MutableStateFlow(SettingsUi())
    val state: StateFlow<SettingsUi> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            session.baseUrl.combine(session.username) { url, name -> url to name }
                .collect { (url, name) ->
                    _state.value = _state.value.copy(baseUrl = url, username = name)
                }
        }
        viewModelScope.launch {
            session.themeMode.collect { mode ->
                _state.value = _state.value.copy(themeMode = mode)
            }
        }
        viewModelScope.launch {
            session.locale.collect { loc ->
                _state.value = _state.value.copy(locale = loc)
            }
        }
        viewModelScope.launch {
            session.palette.collect { pal ->
                _state.value = _state.value.copy(palette = pal ?: DEFAULT_PALETTE_ID)
            }
        }
        loadNotifPrefs()
    }

    fun loadNotifPrefs() {
        if (_state.value.notifBusy) return
        _state.value = _state.value.copy(notifBusy = true)
        viewModelScope.launch {
            val prefs = try {
                api.listNotificationPrefs()
            } catch (_: Throwable) {
                emptyList()
            }
            _state.value = _state.value.copy(notifPrefs = prefs, notifBusy = false)
        }
    }

    fun saveNotifPref(kind: String, pushEnabled: Boolean, emailEnabled: Boolean, browserEnabled: Boolean, leadDays: Int) {
        viewModelScope.launch {
            try {
                val updated = api.updateNotificationPref(
                    kind,
                    NotificationPrefUpdate(
                        email_enabled = emailEnabled,
                        push_enabled = pushEnabled,
                        browser_enabled = browserEnabled,
                        lead_days = leadDays,
                    ),
                )
                _state.value = _state.value.copy(
                    notifPrefs = _state.value.notifPrefs.map { if (it.kind == kind) updated else it }
                )
            } catch (_: Throwable) { /* non-fatal */ }
        }
    }

    fun signOut(after: () -> Unit) {
        viewModelScope.launch { auth.logout(); after() }
    }

    fun setTheme(mode: String) {
        viewModelScope.launch { session.saveTheme(mode) }
    }

    fun setPalette(id: String) {
        viewModelScope.launch { session.savePalette(id) }
    }

    fun setLocale(code: String) {
        _state.value = _state.value.copy(locale = code)
        viewModelScope.launch {
            session.saveLocale(code)
            AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(code))
            try { api.patchMe(PatchMeRequest(locale = code)) } catch (_: Throwable) {}
        }
    }

    fun testConnection() {
        val url = _state.value.baseUrl ?: return
        if (_state.value.testBusy) return
        _state.value = _state.value.copy(testBusy = true, testResult = null)
        viewModelScope.launch {
            val (msg, ok) = try {
                auth.testConnection(url)
                Pair(context.getString(R.string.msg_connected_successfully), true)
            } catch (t: Throwable) {
                Pair(t.message ?: context.getString(R.string.msg_connection_failed), false)
            }
            _state.value = _state.value.copy(testBusy = false, testResult = msg, testOk = ok)
        }
    }

}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onSignOut: () -> Unit,
    onBack: () -> Unit,
    onNavigateToAbout: () -> Unit = {},
    showBackButton: Boolean = true,
    vm: SettingsViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    val pagerState = rememberPagerState(pageCount = { 4 })
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.settings)) },
                navigationIcon = {
                    if (showBackButton) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                        }
                    }
                },
            )
        },
        contentWindowInsets = WindowInsets(0),
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            ScrollableTabRow(selectedTabIndex = pagerState.currentPage) {
                listOf(R.string.appearance, R.string.notifications, R.string.account, R.string.about).forEachIndexed { index, labelRes ->
                    Tab(
                        selected = pagerState.currentPage == index,
                        onClick = { scope.launch { pagerState.animateScrollToPage(index) } },
                        text = { Text(stringResource(labelRes)) },
                    )
                }
            }
            HorizontalPager(
                state = pagerState,
                modifier = Modifier.fillMaxSize(),
            ) { page ->
                when (page) {
                    0 -> SettingsAppearanceTab(s, vm)
                    1 -> SettingsNotificationsTab(s, vm)
                    2 -> SettingsAccountTab(s, vm, onSignOut)
                    3 -> AboutScreen(onBack = {}, showBackButton = false)
                    else -> {}
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingsAppearanceTab(s: SettingsUi, vm: SettingsViewModel) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Text(stringResource(R.string.appearance), style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            SingleChoiceSegmentedButtonRow {
                val options = listOf(
                    "system" to stringResource(R.string.theme_system),
                    "light"  to stringResource(R.string.theme_light),
                    "dark"   to stringResource(R.string.theme_dark),
                )
                options.forEachIndexed { index, (value, label) ->
                    SegmentedButton(
                        selected = (s.themeMode ?: "system") == value,
                        onClick = { vm.setTheme(value) },
                        shape = SegmentedButtonDefaults.itemShape(index = index, count = options.size),
                        label = { Text(label) },
                    )
                }
            }
        }
        item { HorizontalDivider() }
        item {
            Text(stringResource(R.string.palette), style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            val systemDark = isSystemInDarkTheme()
            val swatchDark = when (s.themeMode ?: "system") {
                "light" -> false
                "dark"  -> true
                else    -> systemDark
            }
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ALL_PALETTES.chunked(3).forEach { row ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        row.forEach { pal ->
                            PaletteSwatch(
                                palette = pal,
                                selected = s.palette == pal.id,
                                dark = swatchDark,
                                onClick = { vm.setPalette(pal.id) },
                                modifier = Modifier.weight(1f),
                            )
                        }
                        repeat(3 - row.size) {
                            Spacer(Modifier.weight(1f))
                        }
                    }
                }
            }
        }
        item { HorizontalDivider() }
        item {
            Text(stringResource(R.string.language), style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            var langMenuExpanded by remember { mutableStateOf(false) }
            ExposedDropdownMenuBox(
                expanded = langMenuExpanded,
                onExpandedChange = { langMenuExpanded = it },
            ) {
                OutlinedTextField(
                    value = SUPPORTED_LOCALES.find { it.first == (s.locale ?: "en") }?.second ?: "English",
                    onValueChange = {},
                    readOnly = true,
                    label = { Text(stringResource(R.string.language)) },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = langMenuExpanded) },
                    colors = ExposedDropdownMenuDefaults.outlinedTextFieldColors(),
                    modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
                )
                ExposedDropdownMenu(
                    expanded = langMenuExpanded,
                    onDismissRequest = { langMenuExpanded = false },
                ) {
                    SUPPORTED_LOCALES.forEach { (code, label) ->
                        DropdownMenuItem(
                            text = { Text(label) },
                            onClick = { vm.setLocale(code); langMenuExpanded = false },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsNotificationsTab(s: SettingsUi, vm: SettingsViewModel) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (s.notifPrefs.isEmpty() && !s.notifBusy) {
            item { Text(stringResource(R.string.no_notification_prefs), style = MaterialTheme.typography.bodySmall) }
        } else {
            items(s.notifPrefs, key = { "notif-${it.kind}" }) { pref ->
                val kindLabel = KIND_LABEL_RES[pref.kind]?.let { stringResource(it) } ?: pref.kind
                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(kindLabel, style = MaterialTheme.typography.bodyMedium)
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            Switch(
                                checked = pref.push_enabled,
                                onCheckedChange = { checked ->
                                    vm.saveNotifPref(pref.kind, checked, pref.email_enabled, pref.browser_enabled, pref.lead_days)
                                },
                            )
                            Text(stringResource(R.string.app_label), style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsAccountTab(
    s: SettingsUi,
    vm: SettingsViewModel,
    onSignOut: () -> Unit,
) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Text(stringResource(R.string.server_prefix, s.baseUrl ?: "—")) }
        item { Text(stringResource(R.string.signed_in_as, s.username ?: "—")) }
        item {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                OutlinedButton(
                    onClick = vm::testConnection,
                    enabled = !s.testBusy && s.baseUrl != null,
                ) {
                    if (s.testBusy) {
                        CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Text(stringResource(R.string.test_connection))
                    }
                }
                if (s.testResult != null) {
                    Text(
                        text = s.testResult!!,
                        color = if (s.testOk) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
        item { HorizontalDivider() }
        item { Button(onClick = { vm.signOut(onSignOut) }) { Text(stringResource(R.string.sign_out)) } }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PaletteSwatch(
    palette: AppPalette,
    selected: Boolean,
    dark: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val bg     = if (dark) palette.darkBg     else palette.lightBg
    val accent = if (dark) palette.darkAccent else palette.lightAccent
    val textColor = if (dark) Color.White.copy(alpha = 0.9f) else Color.Black.copy(alpha = 0.75f)
    Surface(
        onClick = onClick,
        modifier = modifier.aspectRatio(1.6f),
        shape = MaterialTheme.shapes.medium,
        border = if (selected)
            BorderStroke(2.dp, MaterialTheme.colorScheme.primary)
        else
            BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Box(modifier = Modifier.fillMaxSize().background(bg)) {
            Text(
                text = palette.name,
                style = MaterialTheme.typography.labelSmall,
                color = textColor,
                modifier = Modifier.align(Alignment.TopStart).padding(6.dp),
            )
            Box(
                modifier = Modifier
                    .padding(6.dp)
                    .size(10.dp)
                    .background(accent, CircleShape)
                    .align(Alignment.BottomEnd),
            )
            if (selected) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription = null,
                    tint = accent,
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .padding(4.dp)
                        .size(14.dp),
                )
            }
        }
    }
}
