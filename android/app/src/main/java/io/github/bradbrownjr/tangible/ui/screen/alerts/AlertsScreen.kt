package io.github.bradbrownjr.tangible.ui.screen.alerts

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.DueAlertDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

// ── ViewModel ─────────────────────────────────────────────────────────────────

data class AlertsUi(
    val alerts: List<DueAlertDto> = emptyList(),
    val loading: Boolean = false,
    val withinDays: Int = 30,
    val selectedKind: String? = null,
)

@HiltViewModel
class AlertsViewModel @Inject constructor(
    private val api: TangibleApi,
) : ViewModel() {
    private val _state = MutableStateFlow(AlertsUi())
    val state: StateFlow<AlertsUi> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        if (_state.value.loading) return
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            val alerts = try {
                api.getAlerts(withinDays = _state.value.withinDays)
            } catch (_: Throwable) { emptyList() }
            _state.value = _state.value.copy(alerts = alerts, loading = false)
        }
    }

    fun setWithinDays(days: Int) {
        _state.value = _state.value.copy(withinDays = days, alerts = emptyList())
        refresh()
    }

    fun setKindFilter(kind: String?) {
        _state.value = _state.value.copy(selectedKind = kind)
    }
}

// ── Screen ────────────────────────────────────────────────────────────────────

private val KIND_LABEL_RES = mapOf(
    "maintenance_due" to R.string.alert_maintenance,
    "chore_due"       to R.string.alert_chore,
    "item_use_by"     to R.string.alert_use_by,
    "item_expires"    to R.string.alert_expires,
    "lot_use_by"      to R.string.alert_package,
    "low_stock"       to R.string.alert_low_stock,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlertsScreen(
    onBack: () -> Unit,
    showBackButton: Boolean = true,
    vm: AlertsViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    val allKinds = s.alerts.map { it.kind }.distinct().sorted()
    val visibleAlerts = (if (s.selectedKind == null) s.alerts
                         else s.alerts.filter { it.kind == s.selectedKind })
        .sortedWith(compareBy({ it.severity != "critical" }, { it.due_at ?: "" }))

    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = { Text(stringResource(R.string.alerts)) },
                    navigationIcon = {
                        if (showBackButton) {
                            IconButton(onClick = onBack) {
                                Icon(
                                    Icons.AutoMirrored.Filled.ArrowBack,
                                    contentDescription = stringResource(R.string.cd_back),
                                )
                            }
                        }
                    },
                    actions = {
                        OutlinedButton(
                            onClick = vm::refresh,
                            enabled = !s.loading,
                            modifier = Modifier.padding(end = 8.dp),
                        ) {
                            if (s.loading) {
                                CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                            } else {
                                Text(stringResource(R.string.refresh))
                            }
                        }
                    },
                )
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                    ) {
                        listOf(7, 14, 30, 60, 90).forEach { days ->
                            FilterChip(
                                selected = s.withinDays == days,
                                onClick = { vm.setWithinDays(days) },
                                label = { Text("${days}d") },
                            )
                        }
                    }
                }
            }
        },
        contentWindowInsets = WindowInsets(0),
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // Kind filter chips
            if (allKinds.isNotEmpty()) {
                item {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        FilterChip(
                            selected = s.selectedKind == null,
                            onClick = { vm.setKindFilter(null) },
                            label = { Text(stringResource(R.string.all)) },
                        )
                        allKinds.forEach { kind ->
                            val label = KIND_LABEL_RES[kind]?.let { stringResource(it) } ?: kind
                            FilterChip(
                                selected = s.selectedKind == kind,
                                onClick = { vm.setKindFilter(if (s.selectedKind == kind) null else kind) },
                                label = { Text(label) },
                            )
                        }
                    }
                }
                item { HorizontalDivider() }
            }

            // Loading / empty / list
            if (s.loading && s.alerts.isEmpty()) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(24.dp),
                        horizontalArrangement = Arrangement.Center,
                    ) { CircularProgressIndicator() }
                }
            } else if (visibleAlerts.isEmpty()) {
                item {
                    Text(
                        stringResource(R.string.no_alerts, s.withinDays),
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(vertical = 24.dp),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                items(visibleAlerts, key = { it.id }) { alert ->
                    AlertCard(alert)
                }
            }
        }
    }
}

@Composable
private fun AlertCard(alert: DueAlertDto) {
    val isOverdue = alert.severity == "critical"
    val kindLabel = KIND_LABEL_RES[alert.kind]?.let { stringResource(it) } ?: alert.kind
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = alert.title,
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = kindLabel,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (!alert.due_at.isNullOrBlank()) {
                Text(
                    text = if (isOverdue) stringResource(R.string.alert_overdue, alert.due_at!!.take(10))
                           else stringResource(R.string.alert_due, alert.due_at!!.take(10)),
                    style = MaterialTheme.typography.bodySmall,
                    color = if (isOverdue) MaterialTheme.colorScheme.error
                            else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (!alert.details.isNullOrBlank()) {
                Text(
                    text = alert.details!!,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
