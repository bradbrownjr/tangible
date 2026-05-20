package io.github.bradbrownjr.tangible.ui.screen.maintenance

import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.foundation.lazy.itemsIndexed
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
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedCard
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
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.ChoreCompletePayloadDto
import io.github.bradbrownjr.tangible.data.remote.ChoreCreateDto
import io.github.bradbrownjr.tangible.data.remote.ChoreDto
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.CreateTaskBody
import io.github.bradbrownjr.tangible.data.remote.ScoreboardEntryDto
import io.github.bradbrownjr.tangible.data.remote.StandaloneTaskDto
import io.github.bradbrownjr.tangible.data.local.PendingMutationDao
import io.github.bradbrownjr.tangible.data.local.PendingMutationEntity
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.IOException
import java.util.UUID
import javax.inject.Inject
import org.json.JSONObject

enum class TaskTab { CHORES, MY_TASKS, SCOREBOARD }

data class MaintenanceUi(
    // Chores tab
    val chores: List<ChoreDto> = emptyList(),
    val choresLoading: Boolean = false,
    val choresLoaded: Boolean = false,
    val choresError: String? = null,
    // My Tasks tab
    val myTasks: List<StandaloneTaskDto> = emptyList(),
    val taskCollections: List<CollectionDto> = emptyList(),
    val tasksLoading: Boolean = false,
    val tasksError: String? = null,
    val tasksLoaded: Boolean = false,
    // Scoreboard tab
    val scoreboard: List<ScoreboardEntryDto> = emptyList(),
    val scoreboardLoading: Boolean = false,
    val scoreboardError: String? = null,
    val scoreboardLoaded: Boolean = false,
)

@HiltViewModel
class MaintenanceViewModel @Inject constructor(
    private val api: TangibleApi,
    private val mutationDao: PendingMutationDao,
) : ViewModel() {
    private val _state = MutableStateFlow(MaintenanceUi())
    val state: StateFlow<MaintenanceUi> = _state.asStateFlow()

    init {
        // No eager loading — each tab loads lazily on first visit.
    }

    fun loadChores() {
        if (_state.value.choresLoading || _state.value.choresLoaded) return
        _state.value = _state.value.copy(choresLoading = true, choresError = null)
        viewModelScope.launch {
            try {
                val chores = api.listStandaloneChores()
                _state.value = _state.value.copy(chores = chores, choresLoaded = true, choresLoading = false)
            } catch (e: Throwable) {
                _state.value = _state.value.copy(
                    choresLoading = false,
                    choresError = e.message ?: "Couldn't load chores. Pull to retry.",
                )
            }
        }
    }

    fun refreshChores() {
        _state.value = _state.value.copy(choresLoaded = false)
        loadChores()
    }

    fun completeChore(choreId: String) {
        viewModelScope.launch {
            try {
                val updated = api.completeChore(choreId, ChoreCompletePayloadDto())
                _state.value = _state.value.copy(
                    chores = _state.value.chores.map { if (it.id == updated.id) updated else it }
                )
            } catch (e: Throwable) {
                _state.value = _state.value.copy(choresError = e.message ?: "Error completing chore")
            }
        }
    }

    fun deleteChore(choreId: String) {
        viewModelScope.launch {
            try {
                api.deleteChore(choreId)
                _state.value = _state.value.copy(chores = _state.value.chores.filter { it.id != choreId })
            } catch (e: Throwable) {
                _state.value = _state.value.copy(choresError = e.message ?: "Error deleting chore")
            }
        }
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

    fun loadCollections() {
        if (_state.value.taskCollections.isNotEmpty()) return
        viewModelScope.launch {
            try {
                _state.value = _state.value.copy(taskCollections = api.listCollections())
            } catch (_: Throwable) { }
        }
    }

    fun createChore(collectionId: String?, name: String, notes: String?, intervalDays: Int?) {
        viewModelScope.launch {
            try {
                val dto = ChoreCreateDto(name, notes, intervalDays)
                if (collectionId.isNullOrBlank()) {
                    api.createStandaloneChore(dto)
                } else {
                    api.createChore(collectionId, dto)
                }
                _state.value = _state.value.copy(choresError = null)
                if (collectionId.isNullOrBlank()) {
                    _state.value = _state.value.copy(choresLoaded = false)
                    loadChores()
                }
            } catch (e: IOException) {
                val payload = JSONObject().apply {
                    if (!collectionId.isNullOrBlank()) put("collection_id", collectionId) else put("collection_id", JSONObject.NULL)
                    put("name", name)
                    if (notes != null) put("notes", notes) else put("notes", JSONObject.NULL)
                    if (intervalDays != null) put("interval_days", intervalDays) else put("interval_days", JSONObject.NULL)
                }
                mutationDao.insert(
                    PendingMutationEntity(
                        id = UUID.randomUUID().toString(),
                        type = "CREATE_CHORE",
                        payloadJson = payload.toString(),
                    )
                )
                _state.value = _state.value.copy(choresError = "No connection — chore will sync when online")
            } catch (e: Throwable) {
                _state.value = _state.value.copy(choresError = e.message ?: "Error creating chore")
            }
        }
    }

    fun loadScoreboard() {
        if (_state.value.scoreboardLoaded || _state.value.scoreboardLoading) return
        _state.value = _state.value.copy(scoreboardLoading = true, scoreboardError = null)
        viewModelScope.launch {
            try {
                val entries = api.getScoreboard()
                _state.value = _state.value.copy(
                    scoreboard = entries,
                    scoreboardLoaded = true,
                    scoreboardLoading = false,
                )
            } catch (e: Throwable) {
                _state.value = _state.value.copy(
                    scoreboardError = e.message ?: "Error loading scoreboard",
                    scoreboardLoading = false,
                )
            }
        }
    }

    fun refreshTasks() {
        _state.value = _state.value.copy(tasksLoaded = false, tasksLoading = false)
        loadTasks()
    }

    fun refreshScoreboard() {
        _state.value = _state.value.copy(scoreboardLoaded = false, scoreboardLoading = false)
        loadScoreboard()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MaintenanceScreen(
    onBack: () -> Unit,
    showBackButton: Boolean = true,
    onNavigateToChores: (collectionId: String, collectionName: String) -> Unit = { _, _ -> },
    vm: MaintenanceViewModel = hiltViewModel(),
    onSwipeLeft: () -> Unit = {},
    onSwipeRight: () -> Unit = {},
) {
    val s by vm.state.collectAsState()
    val tabs = listOf(
        R.string.tasks_tab_chores    to TaskTab.CHORES,
        R.string.tasks_tab_my_tasks  to TaskTab.MY_TASKS,
        R.string.tasks_tab_scoreboard to TaskTab.SCOREBOARD,
    )
    val pagerState = rememberPagerState(pageCount = { tabs.size })
    val scope = rememberCoroutineScope()
    var showNewTaskDialog by remember { mutableStateOf(false) }
    var showNewChoreDialog by remember { mutableStateOf(false) }

    LaunchedEffect(pagerState.currentPage) {
        when (pagerState.currentPage) {
            0 -> { vm.loadCollections(); vm.loadChores() }
            1 -> vm.loadTasks()
            2 -> vm.loadScoreboard()
        }
    }

    val dragThresholdPx = with(LocalDensity.current) { 80.dp.toPx() }

    Scaffold(
        topBar = {
            var tasksDragAccum by remember { mutableFloatStateOf(0f) }
            Box(
                Modifier.pointerInput(Unit) {
                    detectHorizontalDragGestures(
                        onDragEnd = { tasksDragAccum = 0f },
                        onDragCancel = { tasksDragAccum = 0f },
                        onHorizontalDrag = { _, amount ->
                            tasksDragAccum += amount
                            if (tasksDragAccum < -dragThresholdPx) { tasksDragAccum = 0f; onSwipeLeft() }
                            else if (tasksDragAccum > dragThresholdPx) { tasksDragAccum = 0f; onSwipeRight() }
                        },
                    )
                }
            ) {
            TopAppBar(
                title = { Text(stringResource(R.string.tasks)) },
                navigationIcon = {
                    if (showBackButton) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                        }
                    }
                },
            )
            }
        },
        contentWindowInsets = WindowInsets(0),
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            ScrollableTabRow(selectedTabIndex = pagerState.currentPage) {
                tabs.forEachIndexed { index, (labelRes, _) ->
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
                    0 -> ChoresContent(s, vm, onAddChore = { showNewChoreDialog = true })
                    1 -> MyTasksContent(s, vm, onAddTask = { showNewTaskDialog = true })
                    2 -> ScoreboardContent(s, vm)
                    else -> {}
                }
            }
        }
    }

    if (showNewTaskDialog) {
        NewTaskDialog(s, vm, onDismiss = { showNewTaskDialog = false })
    }
    if (showNewChoreDialog) {
        NewChoreDialog(s, vm, onDismiss = { showNewChoreDialog = false })
    }
}

@Composable
private fun ChoreCard(
    chore: ChoreDto,
    onComplete: () -> Unit,
    onDelete: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(chore.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                if (chore.next_due_at != null) {
                    Text(
                        text = chore.next_due_at.take(10),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (chore.notes != null) {
                    Text(
                        text = chore.notes,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            IconButton(onClick = onComplete) {
                Icon(Icons.Default.Check, contentDescription = stringResource(R.string.chore_complete), tint = MaterialTheme.colorScheme.primary)
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.Delete, contentDescription = stringResource(R.string.cd_delete), tint = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
private fun ChoresContent(
    s: MaintenanceUi,
    vm: MaintenanceViewModel,
    onAddChore: () -> Unit = {},
) {
    PullToRefreshBox(
        isRefreshing = s.choresLoading,
        onRefresh = vm::refreshChores,
        modifier = Modifier.fillMaxSize(),
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(vertical = 8.dp),
        ) {
            if (s.choresError != null) {
                item {
                    Text(
                        text = s.choresError,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                    )
                }
            }
            if (s.chores.isEmpty() && !s.choresLoading) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(32.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = stringResource(R.string.chores_empty),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
            items(s.chores, key = { it.id }) { chore ->
                ChoreCard(
                    chore = chore,
                    onComplete = { vm.completeChore(chore.id) },
                    onDelete = { vm.deleteChore(chore.id) },
                )
            }
            item(key = "new_chore") {
                NewChoreCard(onClick = onAddChore)
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
private fun ScoreboardContent(s: MaintenanceUi, vm: MaintenanceViewModel) {
    PullToRefreshBox(
        isRefreshing = s.scoreboardLoading,
        onRefresh = vm::refreshScoreboard,
        modifier = Modifier.fillMaxSize(),
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            when {
                s.scoreboardError != null -> item {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(32.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = s.scoreboardError,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                }
                s.scoreboard.isEmpty() && !s.scoreboardLoading -> item {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(32.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = stringResource(R.string.tasks_scoreboard_empty),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                else -> itemsIndexed(s.scoreboard, key = { _, e -> e.user_id }) { index, entry ->
                    ScoreboardRow(index = index, entry = entry)
                }
            }
        }
    }
}

@Composable
private fun ScoreboardRow(index: Int, entry: ScoreboardEntryDto) {
    val medal = when (index) {
        0 -> "🥇"
        1 -> "🥈"
        2 -> "🥉"
        else -> "${index + 1}."
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = if (index < 3) 4.dp else 2.dp),
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(text = medal, style = MaterialTheme.typography.titleLarge)
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = entry.display_name,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Bold,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (entry.chore_count > 0) {
                        Text("✨ ${entry.chore_count}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (entry.maintenance_count > 0) {
                        Text("🔧 ${entry.maintenance_count}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (entry.task_count > 0) {
                        Text("✓ ${entry.task_count}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                if (entry.achievements.isNotEmpty()) {
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        entry.achievements.forEach { badge ->
                            val emoji = when (badge) {
                                "first_finish"    -> "🏅"
                                "getting_started" -> "⭐"
                                "on_a_roll"       -> "🔥"
                                "power_user"      -> "💪"
                                "household_hero"  -> "🏆"
                                "legend"          -> "👑"
                                else              -> "🎖️"
                            }
                            Text(emoji, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
            Text(
                text = entry.total.toString(),
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.primary,
            )
        }
    }
}



@Composable
private fun MyTasksContent(s: MaintenanceUi, vm: MaintenanceViewModel, onAddTask: () -> Unit = {}) {
    PullToRefreshBox(
        isRefreshing = s.tasksLoading,
        onRefresh = vm::refreshTasks,
        modifier = Modifier.fillMaxSize(),
    ) {
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
        items(s.myTasks, key = { it.id }) { task ->
                TaskCard(task, onComplete = { vm.completeTask(task.id) }, onDelete = { vm.deleteTask(task.id) })
            }
        item(key = "new_task") {
            NewTaskCard(onClick = onAddTask)
        }
    }
    } // end PullToRefreshBox
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

@Composable
private fun NewChoreCard(onClick: () -> Unit) {
    OutlinedCard(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Icon(Icons.Default.Add, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text(
                    stringResource(R.string.new_chore),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun NewTaskCard(onClick: () -> Unit) {
    OutlinedCard(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Icon(Icons.Default.Add, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text(
                    stringResource(R.string.tasks_new_task),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
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

    LaunchedEffect(s.taskCollections) {
        if (selectedCollectionId.isBlank() && s.taskCollections.isNotEmpty()) {
            selectedCollectionId = s.taskCollections.first().id
        }
    }

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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NewChoreDialog(
    s: MaintenanceUi,
    vm: MaintenanceViewModel,
    onDismiss: () -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var intervalDays by remember { mutableStateOf("") }
    var selectedCollectionId by remember { mutableStateOf("") }
    var menuOpen by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.add_chore)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                if (!s.choresError.isNullOrBlank()) {
                    Text(
                        text = s.choresError!!,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.chore_name_hint)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                ExposedDropdownMenuBox(expanded = menuOpen, onExpandedChange = { menuOpen = it }) {
                    val selectedName = s.taskCollections.firstOrNull { it.id == selectedCollectionId }?.name
                        ?: stringResource(R.string.chore_no_collection)
                    OutlinedTextField(
                        value = selectedName,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text(stringResource(R.string.tasks_new_task_collection_label)) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = menuOpen) },
                        modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
                    )
                    ExposedDropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                        DropdownMenuItem(
                            text = { Text(stringResource(R.string.chore_no_collection)) },
                            onClick = { selectedCollectionId = ""; menuOpen = false },
                        )
                        s.taskCollections.forEach { col ->
                            DropdownMenuItem(
                                text = { Text(col.name) },
                                onClick = { selectedCollectionId = col.id; menuOpen = false },
                            )
                        }
                    }
                }
                OutlinedTextField(
                    value = intervalDays,
                    onValueChange = { if (it.isEmpty() || it.all { c -> c.isDigit() }) intervalDays = it },
                    label = { Text(stringResource(R.string.chore_interval_hint)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                )
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text(stringResource(R.string.chore_notes_hint)) },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(0.dp))
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    if (name.isNotBlank()) {
                        vm.createChore(
                            collectionId = selectedCollectionId.ifBlank { null },
                            name = name.trim(),
                            notes = notes.trim().ifBlank { null },
                            intervalDays = intervalDays.toIntOrNull(),
                        )
                        onDismiss()
                    }
                },
                enabled = name.isNotBlank(),
                ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        },
    )
}
