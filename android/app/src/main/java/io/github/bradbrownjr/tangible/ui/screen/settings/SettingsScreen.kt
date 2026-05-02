package io.github.bradbrownjr.tangible.ui.screen.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.remote.DueAlertDto
import io.github.bradbrownjr.tangible.data.remote.NotificationPrefDto
import io.github.bradbrownjr.tangible.data.remote.NotificationPrefUpdate
import io.github.bradbrownjr.tangible.data.repo.AuthRepository
import javax.inject.Inject

private val KIND_LABELS = mapOf(
    "maintenance_due" to "Maintenance due",
    "chore_due" to "Chore due",
    "item_use_by" to "Item use-by",
    "item_expires" to "Item expires",
    "lot_use_by" to "Package use-by",
    "low_stock" to "Low stock",
)

data class SettingsUi(
    val baseUrl: String? = null,
    val username: String? = null,
    val testBusy: Boolean = false,
    val testResult: String? = null,
    val testOk: Boolean = false,
    // "system" | "light" | "dark" — null treated as "system"
    val themeMode: String? = null,
    val alerts: List<DueAlertDto> = emptyList(),
    val alertsBusy: Boolean = false,
    val notifPrefs: List<NotificationPrefDto> = emptyList(),
    val notifBusy: Boolean = false,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val session: SessionStore,
    private val auth: AuthRepository,
    private val api: TangibleApi,
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
        refreshAlerts()
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

    fun testConnection() {
        val url = _state.value.baseUrl ?: return
        if (_state.value.testBusy) return
        _state.value = _state.value.copy(testBusy = true, testResult = null)
        viewModelScope.launch {
            val (msg, ok) = try {
                auth.testConnection(url)
                Pair("Connected successfully", true)
            } catch (t: Throwable) {
                Pair(t.message ?: "Connection failed", false)
            }
            _state.value = _state.value.copy(testBusy = false, testResult = msg, testOk = ok)
        }
    }

    fun refreshAlerts() {
        if (_state.value.alertsBusy) return
        _state.value = _state.value.copy(alertsBusy = true)
        viewModelScope.launch {
            val alerts = try {
                api.getAlerts(withinDays = 14)
            } catch (_: Throwable) {
                emptyList()
            }
            _state.value = _state.value.copy(alerts = alerts, alertsBusy = false)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onSignOut: () -> Unit,
    onBack: () -> Unit,
    vm: SettingsViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        }
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item { Text("Server: ${s.baseUrl ?: "—"}") }
            item { Text("Signed in as: ${s.username ?: "—"}") }
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
                            Text("Test connection")
                        }
                    }
                    if (s.testResult != null) {
                        Text(
                            text = s.testResult!!,
                            color = if (s.testOk) Color(0xFF2E7D32) else MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
            item { HorizontalDivider() }
            item {
                Text("Appearance", style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            item {
                @OptIn(ExperimentalMaterial3Api::class)
                SingleChoiceSegmentedButtonRow {
                    val options = listOf("system" to "System", "light" to "Light", "dark" to "Dark")
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
                Text("Notifications", style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (s.notifPrefs.isEmpty() && !s.notifBusy) {
                item { Text("No notification preferences.", style = MaterialTheme.typography.bodySmall) }
            } else {
                items(s.notifPrefs, key = { "notif-${it.kind}" }) { pref ->
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(KIND_LABELS[pref.kind] ?: pref.kind, style = MaterialTheme.typography.bodyMedium)
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
                                Text("App", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
            item { HorizontalDivider() }
            item {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text("Due soon", style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    OutlinedButton(onClick = vm::refreshAlerts, enabled = !s.alertsBusy) {
                        if (s.alertsBusy) {
                            CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                        } else {
                            Text("Refresh")
                        }
                    }
                }
            }
            if (s.alerts.isEmpty()) {
                item { Text("No upcoming alerts in the next 14 days.", style = MaterialTheme.typography.bodySmall) }
            } else {
                items(s.alerts, key = { it.id }) { alert ->
                    ElevatedCard {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(alert.title, style = MaterialTheme.typography.titleSmall)
                            if (!alert.due_at.isNullOrBlank()) {
                                Text(alert.due_at!!, style = MaterialTheme.typography.bodySmall)
                            }
                            if (!alert.details.isNullOrBlank()) {
                                Text(alert.details!!, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
            item { HorizontalDivider() }
            item { Button(onClick = { vm.signOut(onSignOut) }) { Text("Sign out") } }
        }
    }
}
