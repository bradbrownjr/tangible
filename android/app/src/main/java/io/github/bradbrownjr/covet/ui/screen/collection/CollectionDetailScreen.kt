package io.github.bradbrownjr.covet.ui.screen.collection

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
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
import io.github.bradbrownjr.covet.data.remote.CategoryDto
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.ItemDto
import io.github.bradbrownjr.covet.data.remote.BarcodeCandidateDto
import io.github.bradbrownjr.covet.data.remote.BarcodeLookupRequest
import io.github.bradbrownjr.covet.data.remote.ScrapeRequest
import io.github.bradbrownjr.covet.data.remote.CovetApi
import io.github.bradbrownjr.covet.data.repo.CategoryRepository
import io.github.bradbrownjr.covet.data.repo.CollectionRepository
import io.github.bradbrownjr.covet.data.repo.ItemRepository
import javax.inject.Inject

data class DetailUi(
    val collection: CollectionDto? = null,
    val items: List<ItemDto> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
    // Pull-to-refresh indicator (separate from initial load spinner).
    val refreshing: Boolean = false,
    // Add-item dialog
    val showCreate: Boolean = false,
    val rootCategories: List<CategoryDto> = emptyList(),
    val leafCategories: List<CategoryDto> = emptyList(),
    val selectedRoot: CategoryDto? = null,
    val selectedLeaf: CategoryDto? = null,
    val newTitle: String = "",
    val scraping: Boolean = false,
    // Barcode candidate picker
    val showCandidatePicker: Boolean = false,
    val candidates: List<BarcodeCandidateDto> = emptyList(),
)

@HiltViewModel
class CollectionDetailViewModel @Inject constructor(
    private val collections: CollectionRepository,
    private val categories: CategoryRepository,
    private val items: ItemRepository,
    private val api: CovetApi,
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
                val cats = categories.load()
                val roots = cats.filter { it.parent_id == null }
                // Pre-select root matching the collection's default category.
                val defaultRoot = c.default_category_slug?.let { slug ->
                    // Find the leaf with that slug, then its root parent.
                    val leaf = cats.firstOrNull { it.slug == slug }
                    cats.firstOrNull { it.id == leaf?.parent_id } ?: roots.firstOrNull()
                } ?: roots.firstOrNull()
                val leaves = if (defaultRoot != null) cats.filter { it.parent_id == defaultRoot.id } else emptyList()
                val defaultLeaf = c.default_category_slug?.let { slug ->
                    leaves.firstOrNull { it.slug == slug }
                } ?: leaves.firstOrNull()
                _state.value = _state.value.copy(
                    collection = c,
                    items = list,
                    loading = false,
                    rootCategories = roots,
                    leafCategories = leaves,
                    selectedRoot = defaultRoot,
                    selectedLeaf = defaultLeaf,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message)
            }
        }
    }

    fun showCreate(show: Boolean) {
        _state.value = _state.value.copy(showCreate = show, newTitle = "", scraping = false)
    }

    fun setSelectedRoot(root: CategoryDto) {
        val s = _state.value
        val allCats = s.rootCategories + s.leafCategories
        // Rebuild leaf list from known categories via parentId match.
        val leaves = allCats.filter { it.parent_id == root.id }
        _state.value = s.copy(
            selectedRoot = root,
            leafCategories = leaves,
            selectedLeaf = leaves.firstOrNull(),
        )
    }

    fun setSelectedLeaf(leaf: CategoryDto) {
        _state.value = _state.value.copy(selectedLeaf = leaf)
    }

    fun setNewTitle(v: String) { _state.value = _state.value.copy(newTitle = v) }

    /** Called when a barcode is scanned. Fans out to all barcode adapters via the server. */
    fun onBarcode(barcode: String) {
        _state.value = _state.value.copy(scraping = true)
        viewModelScope.launch {
            try {
                val response = api.barcodeLookup(BarcodeLookupRequest(barcode))
                val candidates = response.candidates
                when {
                    candidates.isEmpty() -> {
                        // Nothing found — open blank create dialog.
                        _state.value = _state.value.copy(showCreate = true, scraping = false, newTitle = "")
                    }
                    candidates.size == 1 -> {
                        // Single match — auto-fill and open create dialog.
                        _applyCandidate(candidates.first())
                    }
                    else -> {
                        // Multiple matches — show picker.
                        _state.value = _state.value.copy(
                            scraping = false,
                            showCandidatePicker = true,
                            candidates = candidates,
                        )
                    }
                }
            } catch (t: Throwable) {
                // Lookup failed — still open the dialog with an empty title.
                _state.value = _state.value.copy(showCreate = true, scraping = false, newTitle = "")
            }
        }
    }

    fun pickCandidate(candidate: BarcodeCandidateDto) {
        _state.value = _state.value.copy(showCandidatePicker = false, candidates = emptyList())
        _applyCandidate(candidate)
    }

    fun pickManually() {
        _state.value = _state.value.copy(
            showCandidatePicker = false,
            candidates = emptyList(),
            showCreate = true,
            newTitle = "",
        )
    }

    fun dismissCandidatePicker() {
        _state.value = _state.value.copy(showCandidatePicker = false, candidates = emptyList())
    }

    private fun _applyCandidate(candidate: BarcodeCandidateDto) {
        val s = _state.value
        val allCats = s.rootCategories + s.leafCategories
        val matchedLeaf = candidate.category?.let { slug -> allCats.firstOrNull { it.slug == slug } }
        val newRoot = if (matchedLeaf != null)
            s.rootCategories.firstOrNull { it.id == matchedLeaf.parent_id } ?: s.selectedRoot
        else s.selectedRoot
        val newLeaves = if (newRoot != null) allCats.filter { it.parent_id == newRoot.id } else s.leafCategories
        _state.value = s.copy(
            showCreate = true,
            newTitle = candidate.title.orEmpty(),
            selectedRoot = newRoot,
            leafCategories = newLeaves,
            selectedLeaf = matchedLeaf ?: newLeaves.firstOrNull() ?: s.selectedLeaf,
            scraping = false,
        )
    }

    fun create() {
        val s = _state.value
        if (s.newTitle.isBlank()) return
        val slug = s.selectedLeaf?.slug ?: s.selectedRoot?.slug ?: return
        viewModelScope.launch {
            try {
                items.create(collectionId, slug, s.newTitle.trim())
                _state.value = _state.value.copy(showCreate = false, newTitle = "")
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun pullRefresh() {
        _state.value = _state.value.copy(refreshing = true, error = null)
        viewModelScope.launch {
            try {
                val c = collections.get(collectionId)
                val list = items.list(collectionId)
                _state.value = _state.value.copy(
                    collection = c,
                    items = list,
                    refreshing = false,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(refreshing = false, error = t.message)
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
    onScan: (() -> Unit)? = null,
    onBack: () -> Unit,
    scannedBarcode: String? = null,
    vm: CollectionDetailViewModel = hiltViewModel(),
) {
    @Suppress("UNUSED_PARAMETER") val cid = collectionId // already in SavedStateHandle
    val s by vm.state.collectAsState()

    // When a barcode arrives from the scanner, trigger the lookup flow.
    LaunchedEffect(scannedBarcode) {
        if (!scannedBarcode.isNullOrBlank()) vm.onBarcode(scannedBarcode)
    }

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
                    if (onScan != null) {
                        IconButton(onClick = onScan) {
                            Icon(Icons.Default.QrCodeScanner, contentDescription = "Scan barcode")
                        }
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
                    "No items yet.", Modifier.align(Alignment.Center).padding(16.dp),
                )
                else -> LazyColumn(Modifier.fillMaxSize()) {
                    items(s.items, key = { it.id }) { item ->
                        ListItem(
                            headlineContent = { Text(item.title) },
                            supportingContent = item.category_slug?.let { { Text(it) } },
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

        if (s.showCandidatePicker) {
            AlertDialog(
                onDismissRequest = vm::dismissCandidatePicker,
                title = { Text("Choose a match") },
                text = {
                    LazyColumn {
                        items(s.candidates) { c ->
                            ListItem(
                                headlineContent = { Text(c.title ?: "(untitled)") },
                                supportingContent = c.description?.let {
                                    { Text(it, maxLines = 1, style = MaterialTheme.typography.bodySmall) }
                                },
                                trailingContent = {
                                    Text(c.provider, style = MaterialTheme.typography.labelSmall)
                                },
                                modifier = Modifier.clickable { vm.pickCandidate(c) },
                            )
                            HorizontalDivider()
                        }
                        item {
                            ListItem(
                                headlineContent = { Text("Enter manually") },
                                modifier = Modifier.clickable { vm.pickManually() },
                            )
                        }
                    }
                },
                confirmButton = {},
                dismissButton = {
                    TextButton(onClick = vm::dismissCandidatePicker) { Text("Cancel") }
                },
            )
        }

        if (s.showCreate) {
            AlertDialog(
                onDismissRequest = { vm.showCreate(false) },
                title = { Text("Add item") },
                text = {
                    if (s.scraping) {
                        Box(Modifier.fillMaxWidth().height(100.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                    } else {
                        Column {
                            // Root category picker
                            CategoryDropdown(
                                label = "Category",
                                options = s.rootCategories,
                                selected = s.selectedRoot,
                                onSelect = vm::setSelectedRoot,
                            )
                            if (s.leafCategories.isNotEmpty()) {
                                Spacer(Modifier.height(8.dp))
                                CategoryDropdown(
                                    label = "Sub-category",
                                    options = s.leafCategories,
                                    selected = s.selectedLeaf,
                                    onSelect = vm::setSelectedLeaf,
                                )
                            }
                            Spacer(Modifier.height(8.dp))
                            OutlinedTextField(
                                value = s.newTitle,
                                onValueChange = vm::setNewTitle,
                                label = { Text("Title") },
                                singleLine = true,
                            )
                        }
                    }
                },
                confirmButton = {
                    TextButton(
                        onClick = vm::create,
                        enabled = !s.scraping && s.newTitle.isNotBlank(),
                    ) { Text("Add") }
                },
                dismissButton = { TextButton(onClick = { vm.showCreate(false) }) { Text("Cancel") } },
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CategoryDropdown(
    label: String,
    options: List<CategoryDto>,
    selected: CategoryDto?,
    onSelect: (CategoryDto) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
    ) {
        OutlinedTextField(
            value = selected?.name ?: "",
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable).fillMaxWidth(),
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            options.forEach { cat ->
                DropdownMenuItem(
                    text = { Text(cat.name) },
                    onClick = { onSelect(cat); expanded = false },
                )
            }
        }
    }
}

