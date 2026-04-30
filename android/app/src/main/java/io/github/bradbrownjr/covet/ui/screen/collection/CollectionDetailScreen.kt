package io.github.bradbrownjr.covet.ui.screen.collection

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ViewList
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
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

enum class ViewMode { LIST, GRID }

data class DetailUi(
    val collection: CollectionDto? = null,
    val items: List<ItemDto> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
    // Pull-to-refresh indicator (separate from initial load spinner).
    val refreshing: Boolean = false,
    // Search
    val searchQuery: String = "",
    // List vs grid view toggle
    val viewMode: ViewMode = ViewMode.LIST,
    // Add-item dialog
    val showCreate: Boolean = false,
    val allCategories: List<CategoryDto> = emptyList(),
    val rootCategories: List<CategoryDto> = emptyList(),
    val leafCategories: List<CategoryDto> = emptyList(),
    val selectedRoot: CategoryDto? = null,
    val selectedLeaf: CategoryDto? = null,
    val newTitle: String = "",
    val scraping: Boolean = false,
    // Active category filter for the items list (null = show all).
    val activeFilter: CategoryDto? = null,
    // Barcode candidate picker
    val showCandidatePicker: Boolean = false,
    val candidates: List<BarcodeCandidateDto> = emptyList(),
    // Collection edit dialog
    val showEdit: Boolean = false,
    val editName: String = "",
    val editDescription: String = "",
    val editSaving: Boolean = false,
    // Collection delete confirmation dialog
    val showDeleteConfirm: Boolean = false,
    val deleted: Boolean = false,
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
                // Only pre-select a category when the collection has an explicit default.
                // Collections without a default get no pre-selection so the user must choose.
                val defaultRoot = c.default_category_slug?.let { slug ->
                    val leaf = cats.firstOrNull { it.slug == slug }
                    cats.firstOrNull { it.id == leaf?.parent_id }
                }
                val leaves = if (defaultRoot != null) cats.filter { it.parent_id == defaultRoot.id } else emptyList()
                val defaultLeaf = c.default_category_slug?.let { slug ->
                    leaves.firstOrNull { it.slug == slug }
                }
                _state.value = _state.value.copy(
                    collection = c,
                    items = list,
                    loading = false,
                    allCategories = cats,
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
        val s = _state.value
        // When opening the dialog, pre-select the active filter category (if any).
        val (root, leaf, leaves) = if (show && s.activeFilter != null) {
            val filter = s.activeFilter
            if (filter.parent_id != null) {
                // Leaf category: resolve parent root and sibling leaves.
                val r = s.rootCategories.firstOrNull { it.id == filter.parent_id }
                val l = s.allCategories.filter { it.parent_id == filter.parent_id }
                Triple(r, filter, l)
            } else {
                // Root category: expand its leaves, no leaf pre-selected.
                val l = s.allCategories.filter { it.parent_id == filter.id }
                Triple(filter, null, l)
            }
        } else {
            Triple(s.selectedRoot, s.selectedLeaf, s.leafCategories)
        }
        _state.value = s.copy(
            showCreate = show,
            newTitle = "",
            scraping = false,
            selectedRoot = root,
            selectedLeaf = leaf,
            leafCategories = leaves,
        )
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

    fun setFilter(cat: CategoryDto?) {
        _state.value = _state.value.copy(activeFilter = cat)
    }

    fun setSearchQuery(query: String) {
        _state.value = _state.value.copy(searchQuery = query)
    }

    fun search() {
        val s = _state.value
        _state.value = s.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val list = items.list(
                    collectionId,
                    search = s.searchQuery.takeIf { it.isNotBlank() },
                )
                _state.value = _state.value.copy(items = list, loading = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message)
            }
        }
    }

    fun clearSearch() {
        _state.value = _state.value.copy(searchQuery = "")
        refresh()
    }

    fun toggleViewMode() {
        val next = if (_state.value.viewMode == ViewMode.LIST) ViewMode.GRID else ViewMode.LIST
        _state.value = _state.value.copy(viewMode = next)
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

    fun startEdit() {
        val c = _state.value.collection ?: return
        _state.value = _state.value.copy(
            showEdit = true,
            editName = c.name,
            editDescription = c.description.orEmpty(),
        )
    }

    fun cancelEdit() { _state.value = _state.value.copy(showEdit = false) }

    fun setEditName(v: String) { _state.value = _state.value.copy(editName = v) }
    fun setEditDescription(v: String) { _state.value = _state.value.copy(editDescription = v) }

    fun saveEdit() {
        val s = _state.value
        if (s.editName.isBlank()) return
        _state.value = s.copy(editSaving = true)
        viewModelScope.launch {
            try {
                collections.update(
                    collectionId,
                    io.github.bradbrownjr.covet.data.remote.CollectionPatch(
                        name = s.editName.trim(),
                        description = s.editDescription.trimEnd().ifEmpty { null },
                    ),
                )
                _state.value = _state.value.copy(showEdit = false, editSaving = false)
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(editSaving = false, error = t.message)
            }
        }
    }

    fun startDeleteCollection() { _state.value = _state.value.copy(showDeleteConfirm = true) }
    fun cancelDeleteCollection() { _state.value = _state.value.copy(showDeleteConfirm = false) }

    fun confirmDeleteCollection() {
        _state.value = _state.value.copy(showDeleteConfirm = false)
        viewModelScope.launch {
            try {
                collections.delete(collectionId)
                _state.value = _state.value.copy(deleted = true)
            } catch (t: Throwable) {
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
    onItem: (String) -> Unit = {},
    scannedBarcode: String? = null,
    vm: CollectionDetailViewModel = hiltViewModel(),
) {
    @Suppress("UNUSED_PARAMETER") val cid = collectionId // already in SavedStateHandle
    val s by vm.state.collectAsState()

    // Navigate back when the collection is successfully deleted.
    LaunchedEffect(s.deleted) {
        if (s.deleted) onBack()
    }

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
                    if (s.collection?.my_role == "owner" || s.collection?.my_role == "editor") {
                        IconButton(onClick = vm::startEdit) {
                            Icon(Icons.Default.Edit, contentDescription = "Edit collection")
                        }
                    }
                    if (s.collection?.my_role == "owner") {
                        IconButton(onClick = vm::startDeleteCollection) {
                            Icon(Icons.Default.Delete, contentDescription = "Delete collection")
                        }
                    }
                    IconButton(onClick = vm::toggleViewMode) {
                        Icon(
                            if (s.viewMode == ViewMode.LIST) Icons.Default.GridView else Icons.AutoMirrored.Filled.ViewList,
                            contentDescription = if (s.viewMode == ViewMode.LIST) "Grid view" else "List view",
                        )
                    }
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
        // Categories present in this collection's items, used for the filter bar.
        val filterCats = remember(s.items, s.allCategories) {
            val slugs = s.items.mapNotNull { it.category_slug }.toSet()
            s.allCategories.filter { it.slug in slugs }
        }
        val displayItems = remember(s.items, s.activeFilter) {
            val filter = s.activeFilter
            if (filter == null) s.items
            else s.items.filter { it.category_slug == filter.slug }
        }

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
                else -> {
                    val headerContent: @Composable () -> Unit = {
                        if (filterCats.size > 1) {
                            CategoryFilterBar(
                                categories = filterCats,
                                allCategories = s.allCategories,
                                activeFilter = s.activeFilter,
                                onFilter = vm::setFilter,
                            )
                        }
                        SearchBar(
                            query = s.searchQuery,
                            onQueryChange = vm::setSearchQuery,
                            onSearch = { vm.search() },
                            onClear = vm::clearSearch,
                        )
                    }
                    if (s.viewMode == ViewMode.GRID) {
                        LazyVerticalGrid(
                            columns = GridCells.Fixed(2),
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(8.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            item(span = { androidx.compose.foundation.lazy.grid.GridItemSpan(maxLineSpan) }) {
                                headerContent()
                            }
                            if (displayItems.isEmpty()) {
                                item(span = { androidx.compose.foundation.lazy.grid.GridItemSpan(maxLineSpan) }) {
                                    Text("No items in this category.", modifier = Modifier.padding(8.dp))
                                }
                            } else {
                                items(displayItems, key = { it.id }) { item ->
                                    ItemCard(
                                        item = item,
                                        onClick = { onItem(item.id) },
                                        onDelete = { vm.delete(item.id) },
                                    )
                                }
                            }
                        }
                    } else {
                        LazyColumn(Modifier.fillMaxSize()) {
                            item { headerContent() }
                            if (displayItems.isEmpty()) {
                                item {
                                    Text(
                                        "No items in this category.",
                                        modifier = Modifier.padding(16.dp),
                                    )
                                }
                            } else {
                                items(displayItems, key = { it.id }) { item ->
                                    ListItem(
                                        headlineContent = { Text(item.title) },
                                        supportingContent = item.category_slug?.let { { Text(it) } },
                                        trailingContent = {
                                            IconButton(onClick = { vm.delete(item.id) }) {
                                                Icon(Icons.Default.Delete, contentDescription = "Delete")
                                            }
                                        },
                                        modifier = Modifier.clickable { onItem(item.id) },
                                    )
                                    HorizontalDivider()
                                }
                            }
                        } // end LazyColumn
                    } // end else (list mode)
                } // end else -> when branch
            } // end when
        } // end PullToRefreshBox
        // Barcode lookup in progress — show a non-blocking overlay before any dialog opens.
        if (s.scraping && !s.showCreate && !s.showCandidatePicker) {
            Box(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center,
            ) {
                Surface(
                    shape = MaterialTheme.shapes.medium,
                    tonalElevation = 8.dp,
                    modifier = Modifier.padding(32.dp),
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 24.dp, vertical = 16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                        Text("Looking up barcode…")
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

        if (s.showEdit) {
            AlertDialog(
                onDismissRequest = vm::cancelEdit,
                title = { Text("Edit collection") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = s.editName,
                            onValueChange = vm::setEditName,
                            label = { Text("Name") },
                            singleLine = true,
                            enabled = !s.editSaving,
                        )
                        OutlinedTextField(
                            value = s.editDescription,
                            onValueChange = vm::setEditDescription,
                            label = { Text("Description") },
                            minLines = 2,
                            enabled = !s.editSaving,
                        )
                    }
                },
                confirmButton = {
                    TextButton(
                        onClick = vm::saveEdit,
                        enabled = !s.editSaving && s.editName.isNotBlank(),
                    ) { Text(if (s.editSaving) "Saving…" else "Save") }
                },
                dismissButton = { TextButton(onClick = vm::cancelEdit) { Text("Cancel") } },
            )
        }

        if (s.showDeleteConfirm) {
            val name = s.collection?.name ?: "this collection"
            val count = s.items.size
            AlertDialog(
                onDismissRequest = vm::cancelDeleteCollection,
                title = { Text("Delete $name?") },
                text = {
                    Text(
                        "This will permanently delete $count item${if (count != 1) "s" else ""} " +
                            "in this collection. This cannot be undone.",
                    )
                },
                confirmButton = {
                    TextButton(
                        onClick = vm::confirmDeleteCollection,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.error,
                        ),
                    ) { Text("Delete") }
                },
                dismissButton = { TextButton(onClick = vm::cancelDeleteCollection) { Text("Cancel") } },
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
                        enabled = !s.scraping && s.newTitle.isNotBlank()
                            && (s.selectedLeaf != null || s.selectedRoot != null),
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
            placeholder = { Text("Select…") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            isError = selected == null,
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

@Composable
private fun ItemCard(
    item: ItemDto,
    onClick: () -> Unit,
    onDelete: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column {
            // Cover photo or placeholder
            Box(
                modifier = Modifier.fillMaxWidth().aspectRatio(1f),
            ) {
                if (item.primary_photo_id != null) {
                    AsyncImage(
                        model = "http://localhost/api/photos/${item.primary_photo_id}/download",
                        contentDescription = item.title,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize(),
                    )
                } else {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            Icons.Default.Image,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                            modifier = Modifier.size(40.dp),
                        )
                    }
                }
            }
            Column(Modifier.padding(horizontal = 8.dp, vertical = 6.dp)) {
                item.category_slug?.let { slug ->
                    Text(
                        slug.substringAfterLast('.'),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                Text(
                    item.title,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                item.subtitle?.takeIf { it.isNotBlank() }?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 0.dp),
                horizontalArrangement = Arrangement.End,
            ) {
                IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Delete, contentDescription = "Delete", modifier = Modifier.size(16.dp))
                }
            }
        }
    }
}

@Composable
private fun CategoryFilterBar(
    categories: List<CategoryDto>,
    allCategories: List<CategoryDto>,
    activeFilter: CategoryDto?,
    onFilter: (CategoryDto?) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 8.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        categories.forEach { cat ->
            val label = if (cat.parent_id != null) {
                val parent = allCategories.firstOrNull { it.id == cat.parent_id }
                if (parent != null) "${parent.name} > ${cat.name}" else cat.name
            } else {
                cat.name
            }
            FilterChip(
                selected = activeFilter?.slug == cat.slug,
                onClick = { onFilter(if (activeFilter?.slug == cat.slug) null else cat) },
                label = { Text(label) },
            )
        }
    }
}

@Composable
private fun SearchBar(
    query: String,
    onQueryChange: (String) -> Unit,
    onSearch: () -> Unit,
    onClear: () -> Unit,
) {
    OutlinedTextField(
        value = query,
        onValueChange = onQueryChange,
        placeholder = { Text("Search items…") },
        leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
        trailingIcon = {
            if (query.isNotEmpty()) {
                IconButton(onClick = onClear) {
                    Icon(Icons.Default.Close, contentDescription = "Clear search")
                }
            }
        },
        singleLine = true,
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
        keyboardActions = KeyboardActions(onSearch = { onSearch() }),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp),
    )
}
