package io.github.bradbrownjr.tangible.ui.screen.maintenance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.CreateTaskBody
import io.github.bradbrownjr.tangible.data.remote.DueAlertDto
import io.github.bradbrownjr.tangible.data.remote.StandaloneTaskDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

private val KIND_LABEL_RES = mapOf(
    "maintenance_due" to R.string.alert_maintenance,
    "chore_due" to R.string.alert_chore,
    "item_use_by" to R.string.alert_use_by,
    "item_expires" to R.string.alert_expires,
    "lot_use_by" to R.string.alert_package,
    "low_stock" to R.string.alert_low_stock,
)

enum class TaskTab { CHORES, MY_TASKS, SCOREBOARD }

data class MaintenanceUi(
    val alerts: List<DueAlertDto> = emptyList(),
    val loading: Boolean = false,
    val withinDays: Int = 30,
    val selectedKind: String? = null,
    // My Tasks tab
    val myTasks: List<StandaloneTaskDto> = emptyList(),
    val taskCollections: List<CollectionDto> = emptyList(),
    val tasksLoading: Boolean = false,
    val tasksError: String? = null,
    val tasksLoaded: Boolean = false,
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

    fun loadTasks() {
        if (_state.value.tasksLoading || _state.value.tasksLoaded) return
        _state.value = _state.value.copy(tasksLoading = true, tasksError = null)
        viewModelScope.launch {
            try {
                val tasks = api.getTasks()
                val cols = if (_state.value.taskCollections.isEmpty()) api.listCollections() else _state.value.taskCollections
                _state.value = _state.value.copy(
                    myTasks = tasks,
                    taskCollections = cols,
                    tasksLoading = false,
                    tasksLoaded = true,
                )
            } catch (e: Throwable) {
                _state.value = _state.value.copy(
                    tasksLoading = false,
                    tasksError = e.message ?: "Error loading tasks",
                )
            }
        }
    }

    fun createTask(collectionId: String, title: String, notes: String?) {
        viewModelScope.launch {
            try {
                val task = api.createTask(collectionId, CreateTaskBody(title, notes))
                _state.value = _state.value.copy(myTasks = _state.value.myTasks + task)
            } catch (e: Throwable) {
                _state.value = _state.value.copy(tasksError = e.message ?: "Error creating task")
            }
        }
    }

    fun completeTask(id: String) {
        viewModelScope.launch {
            try {
                api.completeTask(id)
                _state.value = _state.value.copy(myTasks = _state.value.myTasks.filter { it.id != id })
            } catch (e: Throwable) {
                _state.value = _state.value.copy(tasksError = e.message ?: "Error completing task")
            }
        }
    }

    fun deleteTask(id: String) {
        viewModelScope.launch {
            try {
                api.deleteTask(id)
                _state.value = _state.value.copy(myTasks = _state.value.myTasks.filter { it.id != id })
            } catch (e: Throwable) {
                _state.value = _state.value.copy(tasksError = e.message ?: "Error deleting task")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MaintenanceScreen(
    onBack: () -> Unit,
    showBackButton: Boolean = true,
    onNavigateToChores: (collectionId: String, collectionName: String) -> Unit = { _, _ -> },
    vm: MaintenanceViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    var selectedTabIndex by remember { mutableStateOf(0) }
    val selectedTab = TaskTab.values()[selectedTabIndex]
    var showNewTaskDialog by remember { mutableStateOf(false) }

    LaunchedEffect(selectedTab) {
        if (selectedTab == TaskTab.MY_TASKS) vm.loadTasks()
    }

    val tabs = listOf(
        R.string.tasks_tab_chores    to TaskTab.CHORES,
        R.string.tasks_tab_my_tasks  to TaskTab.MY_TASKS,
        R.string.tasks_tab_scoreboard to TaskTab.SCOREBOARD,
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.tasks)) },
                navigationIcon = {
                    if (showBackButton) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                        }
                    }
                },
                actions = {
                    if (selectedTab == TaskTab.CHORES) {
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
                    }
                },
            )
        },
        floatingActionButton = {
            if (selectedTab == TaskTab.MY_TASKS) {
                FloatingActionButton(onClick = { showNewTaskDialog = true }) {
                    Icon(Icons.Default.Add, contentDescription = stringResource(R.string.tasks_new_task))
                }
            }
        },
        contentWindowInsets = WindowInsets(0),
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            ScrollableTabRow(selectedTabIndex = selectedTabIndex) {
                tabs.forEachIndexed { index, (labelRes, _) ->
                    Tab(
                        selected = selectedTabIndex == index,
                        onClick = { selectedTabIndex = index },
                        text = { Text(stringResource(labelRes)) },
                    )
                }
            }
            when (selectedTab) {
                TaskTab.CHORES     -> ChoresAlertsContent(s, vm, choreOnly = true, onNavigateToChores = onNavigateToChores)
                TaskTab.MY_TASKS   -> MyTasksContent(s, vm)
                TaskTab.SCOREBOARD -> StubTabContent(stringResource(R.string.tasks_scoreboard_empty))
            }
        }
    }

    if (showNewTaskDialog) {
        NewTaskDialog(s, vm, onDismiss = { showNewTaskDialog = false })
    }
}

@Composable
private fun AlertCard(
    alert: DueAlertDto,
    onNavigateToChores: ((collectionId: String, collectionName: String) -> Unit)? = null,
) {
    val isOverdue = alert.severity == "critical"
    val kindLabel = KIND_LABEL_RES[alert.kind]?.let { stringResource(it) } ?: alert.kind
    Card(modifier = Modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
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
                    color = if (isOverdue) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (!alert.details.isNullOrBlank()) {
                Text(
                    text = alert.details!!,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (onNavigateToChores != null && alert.kind == "chore_due") {
                TextButton(
                    onClick = { onNavigateToChores(alert.collection_id, alert.title) },
                    contentPadding = PaddingValues(horizontal = 0.dp, vertical = 4.dp),
                ) {
                    Text(
                        text = stringResource(R.string.tasks_manage_chores),
                        style = MaterialTheme.typography.labelMedium,
                    )
                }
            }
        }
    }
}

@Composable
private fun ChoresAlertsContent(
    s: MaintenanceUi,
    vm: MaintenanceViewModel,
    choreOnly: Boolean,
    onNavigateToChores: (collectionId: String, collectionName: String) -> Unit = { _, _ -> },
) {
    val baseAlerts = if (choreOnly) s.alerts.filter { it.kind == "chore_due" } else s.alerts
    val allKinds = if (choreOnly) emptyList() else s.alerts.map { it.kind }.distinct().sorted()
    val visibleAlerts = (if (choreOnly || s.selectedKind == null) baseAlerts
                         else baseAlerts.filter { it.kind == s.selectedKind })
        .sortedWith(compareBy({ it.severity != "critical" }, { it.due_at ?: "" }))
    val emptyRes = if (choreOnly) R.string.tasks_no_chore_alerts else R.string.no_alerts

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(vertical = 8.dp),
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

        // Kind filter chips (Alerts tab only)
        if (!choreOnly && allKinds.isNotEmpty()) {
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
                    stringResource(emptyRes, s.withinDays),
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(vertical = 24.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        } else {
            items(visibleAlerts, key = { it.id }) { alert ->
                AlertCard(alert, onNavigateToChores = onNavigateToChores.takeIf { choreOnly })
            }
        }
    }
}

@Composable
private fun StubTabContent(message: String) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun MyTasksContent(s: MaintenanceUi, vm: MaintenanceViewModel) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(vertical = 8.dp),
    ) {
        if (!s.tasksError.isNullOrBlank()) {
            item {
                Text(
                    text = s.tasksError!!,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(vertical = 4.dp),
                )
            }
        }
        if (s.tasksLoading && s.myTasks.isEmpty()) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                    horizontalArrangement = Arrangement.Center,
                ) { CircularProgressIndicator() }
            }
        } else if (s.myTasks.isEmpty()) {
            item {
                Text(
                    stringResource(R.string.tasks_my_tasks_empty),
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(vertical = 24.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        } else {
            items(s.myTasks, key = { it.id }) { task ->
                TaskCard(task, onComplete = { vm.completeTask(task.id) }, onDelete = { vm.deleteTask(task.id) })
            }
        }
    }
}

@Composable
private fun TaskCard(
    task: StandaloneTaskDto,
    onComplete: () -> Unit,
    onDelete: () -> Unit,
) {
    val isOverdue = task.due_at != null && task.due_at < java.time.Instant.now().toString().take(10)
    Card(modifier = Modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = task.title,
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.weight(1f),
                )
                Row {
                    IconButton(onClick = onComplete) {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = stringResource(R.string.tasks_complete),
                            tint = MaterialTheme.colorScheme.primary,
                        )
                    }
                    IconButton(onClick = onDelete) {
                        Icon(
                            Icons.Default.Delete,
                            contentDescription = stringResource(R.string.tasks_delete_task),
                            tint = MaterialTheme.colorScheme.error,
                        )
                    }
                }
            }
            if (!task.notes.isNullOrBlank()) {
                Text(
                    text = task.notes!!,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (task.due_at != null) {
                Text(
                    text = if (isOverdue) stringResource(R.string.alert_overdue, task.due_at.take(10))
                           else stringResource(R.string.alert_due, task.due_at.take(10)),
                    style = MaterialTheme.typography.bodySmall,
                    color = if (isOverdue) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NewTaskDialog(
    s: MaintenanceUi,
    vm: MaintenanceViewModel,
    onDismiss: () -> Unit,
) {
    var title by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var selectedCollectionId by remember { mutableStateOf(s.taskCollections.firstOrNull()?.id ?: "") }
    var menuOpen by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.tasks_new_task)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text(stringResource(R.string.tasks_new_task_title_label)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                if (s.taskCollections.isNotEmpty()) {
                    ExposedDropdownMenuBox(expanded = menuOpen, onExpandedChange = { menuOpen = it }) {
                        OutlinedTextField(
                            value = s.taskCollections.firstOrNull { it.id == selectedCollectionId }?.name ?: "",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text(stringResource(R.string.tasks_new_task_collection_label)) },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = menuOpen) },
                            modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
                        )
                        ExposedDropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                            s.taskCollections.forEach { col ->
                                DropdownMenuItem(
                                    text = { Text(col.name) },
                                    onClick = { selectedCollectionId = col.id; menuOpen = false },
                                )
                            }
                        }
                    }
                }
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text(stringResource(R.string.tasks_new_task_notes_label)) },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(0.dp))
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    if (title.isNotBlank() && selectedCollectionId.isNotBlank()) {
                        vm.createTask(selectedCollectionId, title.trim(), notes.trim().ifBlank { null })
                        onDismiss()
                    }
                },
                enabled = title.isNotBlank() && selectedCollectionId.isNotBlank(),
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        },
    )
}
