package io.github.bradbrownjr.covet.ui.screen.collections

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
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
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.repo.CollectionRepository
import javax.inject.Inject

data class CollectionsUi(
    val items: List<CollectionDto> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null,
    val showCreate: Boolean = false,
    val newName: String = "",
)

@HiltViewModel
class CollectionListViewModel @Inject constructor(
    private val repo: CollectionRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CollectionsUi())
    val state: StateFlow<CollectionsUi> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                _state.value = _state.value.copy(items = repo.list(), loading = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message)
            }
        }
    }

    fun showCreate(show: Boolean) { _state.value = _state.value.copy(showCreate = show, newName = "") }
    fun setNewName(v: String) { _state.value = _state.value.copy(newName = v) }
    fun create() {
        val name = _state.value.newName.trim()
        if (name.isEmpty()) return
        viewModelScope.launch {
            try {
                repo.create(name)
                _state.value = _state.value.copy(showCreate = false, newName = "")
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
    onSettings: () -> Unit,
    vm: CollectionListViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Collections") },
                actions = {
                    IconButton(onClick = onSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { vm.showCreate(true) }) {
                Icon(Icons.Default.Add, contentDescription = "New collection")
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                s.loading && s.items.isEmpty() -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                s.error != null && s.items.isEmpty() -> Text(
                    s.error!!,
                    Modifier.align(Alignment.Center).padding(16.dp),
                    color = MaterialTheme.colorScheme.error,
                )
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

        if (s.showCreate) {
            AlertDialog(
                onDismissRequest = { vm.showCreate(false) },
                title = { Text("New collection") },
                text = {
                    OutlinedTextField(
                        value = s.newName,
                        onValueChange = vm::setNewName,
                        label = { Text("Name") },
                        singleLine = true,
                    )
                },
                confirmButton = { TextButton(onClick = { vm.create() }) { Text("Create") } },
                dismissButton = { TextButton(onClick = { vm.showCreate(false) }) { Text("Cancel") } },
            )
        }
    }
}
