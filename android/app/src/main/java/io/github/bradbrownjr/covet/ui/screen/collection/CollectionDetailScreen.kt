package io.github.bradbrownjr.covet.ui.screen.collection

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.ItemDto
import io.github.bradbrownjr.covet.data.repo.CollectionRepository
import io.github.bradbrownjr.covet.data.repo.ItemRepository
import javax.inject.Inject

data class DetailUi(
    val collection: CollectionDto? = null,
    val items: List<ItemDto> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
    val showCreate: Boolean = false,
    val newType: String = "movie",
    val newTitle: String = "",
)

@HiltViewModel
class CollectionDetailViewModel @Inject constructor(
    private val collections: CollectionRepository,
    private val items: ItemRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val collectionId: String = savedState.get<String>("id").orEmpty()
    private val _state = MutableStateFlow(DetailUi())
    val state: StateFlow<DetailUi> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val c = collections.get(collectionId)
                val list = items.list(collectionId)
                _state.value = _state.value.copy(collection = c, items = list, loading = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message)
            }
        }
    }

    fun showCreate(show: Boolean) { _state.value = _state.value.copy(showCreate = show, newTitle = "") }
    fun setNewType(v: String) { _state.value = _state.value.copy(newType = v) }
    fun setNewTitle(v: String) { _state.value = _state.value.copy(newTitle = v) }
    fun create() {
        val s = _state.value
        if (s.newTitle.isBlank()) return
        viewModelScope.launch {
            try {
                items.create(collectionId, s.newType, s.newTitle.trim())
                _state.value = _state.value.copy(showCreate = false, newTitle = "")
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }
    fun delete(id: String) {
        viewModelScope.launch {
            try { items.delete(id); refresh() } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CollectionDetailScreen(
    collectionId: String,
    onScan: () -> Unit,
    onBack: () -> Unit,
    vm: CollectionDetailViewModel = hiltViewModel(),
) {
    @Suppress("UNUSED_PARAMETER") val cid = collectionId // already in SavedStateHandle
    val s by vm.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(s.collection?.name ?: "Collection") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = onScan) {
                        Icon(Icons.Default.QrCodeScanner, contentDescription = "Scan barcode")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { vm.showCreate(true) }) {
                Icon(Icons.Default.Add, contentDescription = "Add item")
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                s.loading && s.items.isEmpty() -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                s.error != null && s.items.isEmpty() -> Text(
                    s.error!!, Modifier.align(Alignment.Center).padding(16.dp),
                    color = MaterialTheme.colorScheme.error,
                )
                s.items.isEmpty() -> Text(
                    "No items yet.", Modifier.align(Alignment.Center).padding(16.dp),
                )
                else -> LazyColumn(Modifier.fillMaxSize()) {
                    items(s.items, key = { it.id }) { item ->
                        ListItem(
                            headlineContent = { Text(item.title) },
                            supportingContent = { Text(item.type) },
                            trailingContent = {
                                IconButton(onClick = { vm.delete(item.id) }) {
                                    Icon(Icons.Default.Delete, contentDescription = "Delete")
                                }
                            },
                        )
                        HorizontalDivider()
                    }
                }
            }
        }

        if (s.showCreate) {
            AlertDialog(
                onDismissRequest = { vm.showCreate(false) },
                title = { Text("Add item") },
                text = {
                    Column {
                        // Plain text type entry; Phase 5.4 will swap for an exposed dropdown.
                        OutlinedTextField(
                            value = s.newType, onValueChange = vm::setNewType,
                            label = { Text("Type (movie/music/book/comic/game/other)") },
                            singleLine = true,
                        )
                        Spacer(Modifier.height(8.dp))
                        OutlinedTextField(
                            value = s.newTitle, onValueChange = vm::setNewTitle,
                            label = { Text("Title") }, singleLine = true,
                        )
                    }
                },
                confirmButton = { TextButton(onClick = vm::create) { Text("Add") } },
                dismissButton = { TextButton(onClick = { vm.showCreate(false) }) { Text("Cancel") } },
            )
        }
    }
}
