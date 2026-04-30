package io.github.bradbrownjr.covet.ui.screen.collections

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import io.github.bradbrownjr.covet.data.remote.CategoryDto
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.repo.CategoryRepository
import io.github.bradbrownjr.covet.data.repo.CollectionRepository
import javax.inject.Inject

enum class WizardStep { CLOSED, PICK_PRESET, CONFIRM }

data class CollectionsUi(
    val items: List<CollectionDto> = emptyList(),
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    val wizardStep: WizardStep = WizardStep.CLOSED,
    val presets: List<CategoryDto> = emptyList(),
    val selectedPreset: CategoryDto? = null,
    val newName: String = "",
    val newDescription: String = "",
)

@HiltViewModel
class CollectionListViewModel @Inject constructor(
    private val repo: CollectionRepository,
    private val categoryRepo: CategoryRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CollectionsUi())
    val state: StateFlow<CollectionsUi> = _state.asStateFlow()

    init { refresh() }

    fun refresh() = load(isRefresh = false)
    fun pullRefresh() = load(isRefresh = true)

    private fun load(isRefresh: Boolean) {
        if (isRefresh) {
            _state.value = _state.value.copy(refreshing = true, error = null)
        } else {
            _state.value = _state.value.copy(loading = true, error = null)
        }
        viewModelScope.launch {
            try {
                val collections = repo.list()
                val cats = try { categoryRepo.load() } catch (_: Throwable) { emptyList() }
                _state.value = _state.value.copy(
                    items = collections,
                    loading = false,
                    refreshing = false,
                    presets = cats.filter { it.parent_id == null },
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, refreshing = false, error = t.message)
            }
        }
    }

    fun openWizard() { _state.value = _state.value.copy(wizardStep = WizardStep.PICK_PRESET, newName = "", newDescription = "", selectedPreset = null) }
    fun closeWizard() { _state.value = _state.value.copy(wizardStep = WizardStep.CLOSED) }

    fun pickPreset(cat: CategoryDto?) {
        _state.value = _state.value.copy(
            selectedPreset = cat,
            wizardStep = WizardStep.CONFIRM,
            newName = cat?.name ?: "",
        )
    }

    fun setNewName(v: String) { _state.value = _state.value.copy(newName = v) }
    fun setNewDescription(v: String) { _state.value = _state.value.copy(newDescription = v) }

    fun create() {
        val s = _state.value
        val name = s.newName.trim()
        if (name.isEmpty()) return
        viewModelScope.launch {
            try {
                repo.create(
                    name = name,
                    description = s.newDescription.takeIf { it.isNotBlank() },
                    defaultCategorySlug = s.selectedPreset?.slug,
                )
                _state.value = _state.value.copy(wizardStep = WizardStep.CLOSED)
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CollectionListScreen(
    onOpen: (String) -> Unit,
    onGroceryList: () -> Unit,
    onSettings: () -> Unit,
    onAbout: () -> Unit,
    vm: CollectionListViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    var menuExpanded by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Collections") },
                actions = {
                    Box {
                        IconButton(onClick = { menuExpanded = true }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menu")
                        }
                        DropdownMenu(
                            expanded = menuExpanded,
                            onDismissRequest = { menuExpanded = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text("Grocery List") },
                                onClick = { menuExpanded = false; onGroceryList() },
                            )
                            DropdownMenuItem(
                                text = { Text("Settings") },
                                onClick = { menuExpanded = false; onSettings() },
                            )
                            DropdownMenuItem(
                                text = { Text("About") },
                                onClick = { menuExpanded = false; onAbout() },
                            )
                        }
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = vm::openWizard) {
                Icon(Icons.Default.Add, contentDescription = "New collection")
            }
        },
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = s.refreshing,
            onRefresh = vm::pullRefresh,
            modifier = Modifier.fillMaxSize().padding(padding),
        ) {
            when {
                s.loading && s.items.isEmpty() -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                s.error != null && s.items.isEmpty() -> Column(
                    Modifier.align(Alignment.Center).padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(s.error!!, color = MaterialTheme.colorScheme.error)
                    OutlinedButton(onClick = vm::refresh) { Text("Retry") }
                }
                s.items.isEmpty() -> Text(
                    "No collections yet. Tap + to create one.",
                    Modifier.align(Alignment.Center).padding(16.dp),
                )
                else -> LazyColumn(Modifier.fillMaxSize()) {
                    items(s.items, key = { it.id }) { c ->
                        ListItem(
                            headlineContent = { Text(c.name) },
                            supportingContent = c.description?.let { { Text(it) } },
                            modifier = Modifier.clickable { onOpen(c.id) },
                        )
                        HorizontalDivider()
                    }
                }
            }
        }

        // Step 1: pick a preset category
        if (s.wizardStep == WizardStep.PICK_PRESET) {
            AlertDialog(
                onDismissRequest = vm::closeWizard,
                title = { Text("What are you collecting?") },
                text = {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.heightIn(max = 320.dp),
                    ) {
                        items(s.presets, key = { it.id }) { cat ->
                            OutlinedButton(
                                onClick = { vm.pickPreset(cat) },
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text(cat.name) }
                        }
                        item {
                            OutlinedButton(
                                onClick = { vm.pickPreset(null) },
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text("Custom") }
                        }
                    }
                },
                confirmButton = {},
                dismissButton = { TextButton(onClick = vm::closeWizard) { Text("Cancel") } },
            )
        }

        // Step 2: confirm name and optional description
        if (s.wizardStep == WizardStep.CONFIRM) {
            AlertDialog(
                onDismissRequest = vm::closeWizard,
                title = { Text("New collection") },
                text = {
                    Column {
                        OutlinedTextField(
                            value = s.newName,
                            onValueChange = vm::setNewName,
                            label = { Text("Name") },
                            singleLine = true,
                        )
                        Spacer(Modifier.height(8.dp))
                        OutlinedTextField(
                            value = s.newDescription,
                            onValueChange = vm::setNewDescription,
                            label = { Text("Description (optional)") },
                            singleLine = true,
                        )
                    }
                },
                confirmButton = {
                    TextButton(
                        onClick = vm::create,
                        enabled = s.newName.isNotBlank(),
                    ) { Text("Create") }
                },
                dismissButton = { TextButton(onClick = vm::closeWizard) { Text("Cancel") } },
            )
        }
    }
}

