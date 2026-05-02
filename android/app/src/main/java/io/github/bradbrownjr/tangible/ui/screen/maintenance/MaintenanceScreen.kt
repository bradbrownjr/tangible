package io.github.bradbrownjr.tangible.ui.screen.maintenance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.remote.DueAlertDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

private val KIND_LABELS = mapOf(
    "maintenance_due" to "Maintenance",
    "chore_due" to "Chore",
    "item_use_by" to "Use by",
    "item_expires" to "Expires",
    "lot_use_by" to "Package",
    "low_stock" to "Low stock",
)

data class MaintenanceUi(
    val alerts: List<DueAlertDto> = emptyList(),
    val loading: Boolean = false,
    val withinDays: Int = 30,
    val selectedKind: String? = null,
)

@HiltViewModel
class MaintenanceViewModel @Inject constructor(
    private val api: TangibleApi,
) : ViewModel() {
    private val _state = MutableStateFlow(MaintenanceUi())
    val state: StateFlow<MaintenanceUi> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        if (_state.value.loading) return
        _state.value = _state.value.copy(loading = true)
        viewModelScope.launch {
            val alerts = try {
                api.getAlerts(withinDays = _state.value.withinDays)
            } catch (_: Throwable) {
                emptyList()
            }
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MaintenanceScreen(
    onBack: () -> Unit,
    vm: MaintenanceViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()

    val visibleAlerts = if (s.selectedKind == null) {
        s.alerts
    } else {
        s.alerts.filter { it.kind == s.selectedKind }
    }

    val allKinds = s.alerts.map { it.kind }.distinct().sorted()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Maintenance & alerts") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
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
                            Text("Refresh")
                        }
                    }
                },
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // Time window chips
            item {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.padding(vertical = 8.dp),
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
                            label = { Text("All") },
                        )
                        allKinds.forEach { kind ->
                            FilterChip(
                                selected = s.selectedKind == kind,
                                onClick = { vm.setKindFilter(if (s.selectedKind == kind) null else kind) },
                                label = { Text(KIND_LABELS[kind] ?: kind) },
                            )
                        }
                    }
                }
                item { HorizontalDivider() }
            }

            if (s.loading && s.alerts.isEmpty()) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(24.dp),
                        horizontalArrangement = Arrangement.Center,
                    ) {
                        CircularProgressIndicator()
                    }
                }
            } else if (visibleAlerts.isEmpty()) {
                item {
                    Text(
                        "No alerts in the next ${s.withinDays} days.",
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
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
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
                    text = KIND_LABELS[alert.kind] ?: alert.kind,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (!alert.due_at.isNullOrBlank()) {
                Text(
                    text = if (isOverdue) "Overdue — ${alert.due_at!!.take(10)}" else "Due ${alert.due_at!!.take(10)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (isOverdue) Color(0xFFB00020) else MaterialTheme.colorScheme.onSurfaceVariant,
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
