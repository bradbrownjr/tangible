package io.github.bradbrownjr.tangible.ui.screen.collection

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import io.github.bradbrownjr.tangible.data.remote.CategoryDto
import io.github.bradbrownjr.tangible.data.remote.ContactDto
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.ItemDto
import io.github.bradbrownjr.tangible.data.remote.BarcodeCandidateDto
import io.github.bradbrownjr.tangible.data.remote.BarcodeLookupRequest
import io.github.bradbrownjr.tangible.data.remote.LocationDto
import io.github.bradbrownjr.tangible.data.remote.ScrapeRequest
import io.github.bradbrownjr.tangible.data.remote.TagDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.repo.CategoryRepository
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ItemRepository
import io.github.bradbrownjr.tangible.data.repo.LocationRepository
import io.github.bradbrownjr.tangible.R
import java.text.NumberFormat
import java.util.Currency
import java.util.Locale
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
    val selectedItemIds: Set<String> = emptySet(),
    val tags: List<TagDto> = emptyList(),
    val contacts: List<ContactDto> = emptyList(),
    val selectedBulkTagId: String = "",
    val selectedBulkContactId: String = "",
    val locations: List<LocationDto> = emptyList(),
    val bulkMoveLocationId: String = "",
)

private fun formatItemValue(item: ItemDto): String? {
    val raw = item.rollup_current_value ?: item.current_value ?: return null
    val currencyCode = item.currency ?: "USD"
    return try {
        val fmt = NumberFormat.getCurrencyInstance(Locale.getDefault())
        fmt.currency = Currency.getInstance(currencyCode)
        fmt.format(raw)
    } catch (_: Throwable) {
        String.format(Locale.US, "%s %.2f", currencyCode, raw)
    }
}

/** Flatten a Location tree into (depth, node) pairs in display order. */
internal fun flattenLocations(tree: List<LocationDto>): List<LocationDto> {
    val out = mutableListOf<LocationDto>()
    fun walk(node: LocationDto) {
        out.add(node)
        node.children.forEach(::walk)
    }
    tree.forEach(::walk)
    return out
}

internal fun flattenLocationsWithDepth(tree: List<LocationDto>): List<Pair<Int, LocationDto>> {
    val out = mutableListOf<Pair<Int, LocationDto>>()
    fun walk(node: LocationDto, depth: Int) {
        out.add(depth to node)
        node.children.forEach { walk(it, depth + 1) }
    }
    tree.forEach { walk(it, 0) }
    return out
}

@HiltViewModel
class CollectionDetailViewModel @Inject constructor(
    private val collections: CollectionRepository,
    private val categories: CategoryRepository,
    private val items: ItemRepository,
    private val locations: LocationRepository,
    private val api: TangibleApi,
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
                val tags = items.listTags()
                val contacts = items.listContacts()
                val locs = try { locations.listTree(collectionId) } catch (_: Throwable) { emptyList() }
                val roots = cats.filter { it.parent_id == null }
                // Pre-select a category from the collection's default slug.
                // The slug may name either a leaf (e.g. "groceries.dairy", in
                // which case we resolve and select the root + that leaf) or a
                // root (e.g. "groceries", in which case we select the root and
                // leave the leaf un-chosen so the user picks a sub-category if
                // they want one). Without this branch a root-default like
                // "groceries" produced no pre-selection at all and the Add
                // dialog forced the user to pick a category every time.
                val defaultMatch = c.default_category_slug?.let { slug ->
                    cats.firstOrNull { it.slug == slug }
                }
                val (defaultRoot, defaultLeaf) = when {
                    defaultMatch == null -> null to null
                    defaultMatch.parent_id == null -> defaultMatch to null
                    else -> cats.firstOrNull { it.id == defaultMatch.parent_id } to defaultMatch
                }
                val leaves = if (defaultRoot != null) cats.filter { it.parent_id == defaultRoot.id } else emptyList()
                _state.value = _state.value.copy(
                    collection = c,
                    items = list,
                    loading = false,
                    allCategories = cats,
                    rootCategories = roots,
                    leafCategories = leaves,
                    selectedRoot = defaultRoot,
                    selectedLeaf = defaultLeaf,
                    tags = tags,
                    contacts = contacts,
                    locations = locs,
                    selectedBulkTagId = _state.value.selectedBulkTagId.takeIf { id ->
                        id.isNotBlank() && tags.any { it.id == id }
                    } ?: "",
                    selectedBulkContactId = _state.value.selectedBulkContactId.takeIf { id ->
                        id.isNotBlank() && contacts.any { it.id == id }
                    } ?: "",
                    bulkMoveLocationId = _state.value.bulkMoveLocationId.takeIf { id ->
                        id.isNotBlank() && flattenLocations(locs).any { it.id == id }
                    } ?: "",
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

    fun toggleSelected(itemId: String) {
        val selected = _state.value.selectedItemIds
        _state.value = _state.value.copy(
            selectedItemIds = if (itemId in selected) selected - itemId else selected + itemId,
        )
    }

    fun clearSelection() {
        _state.value = _state.value.copy(selectedItemIds = emptySet())
    }

    fun selectVisible(displayed: List<ItemDto>) {
        _state.value = _state.value.copy(selectedItemIds = displayed.map { it.id }.toSet())
    }

    fun bulkSetDepleted(value: Boolean) {
        val ids = _state.value.selectedItemIds.toList()
        if (ids.isEmpty()) return
        viewModelScope.launch {
            try {
                items.bulkPatch(collectionId, ids, depleted = value)
                _state.value = _state.value.copy(selectedItemIds = emptySet())
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun bulkSetWanted(value: Boolean) {
        val ids = _state.value.selectedItemIds.toList()
        if (ids.isEmpty()) return
        viewModelScope.launch {
            try {
                items.bulkPatch(collectionId, ids, wanted = value)
                _state.value = _state.value.copy(selectedItemIds = emptySet())
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun bulkArchive() {
        val ids = _state.value.selectedItemIds.toList()
        if (ids.isEmpty()) return
        viewModelScope.launch {
            try {
                items.bulkArchive(collectionId, ids)
                _state.value = _state.value.copy(selectedItemIds = emptySet())
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun bulkRestore() {
        val ids = _state.value.selectedItemIds.toList()
        if (ids.isEmpty()) return
        viewModelScope.launch {
            try {
                items.bulkRestore(collectionId, ids)
                _state.value = _state.value.copy(selectedItemIds = emptySet())
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun bulkDelete() {
        val ids = _state.value.selectedItemIds.toList()
        if (ids.isEmpty()) return
        viewModelScope.launch {
            try {
                items.bulkDelete(collectionId, ids)
                _state.value = _state.value.copy(selectedItemIds = emptySet())
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun setBulkTag(tagId: String) {
        _state.value = _state.value.copy(selectedBulkTagId = tagId)
    }

    fun setBulkContact(contactId: String) {
        _state.value = _state.value.copy(selectedBulkContactId = contactId)
    }

    fun setBulkMoveLocation(locationId: String) {
        _state.value = _state.value.copy(bulkMoveLocationId = locationId)
    }

    fun bulkMoveLocation(clear: Boolean = false) {
        val ids = _state.value.selectedItemIds.toList()
        if (ids.isEmpty()) return
        val locationId = if (clear) null else _state.value.bulkMoveLocationId.ifBlank { null }
        if (!clear && locationId == null) return
        viewModelScope.launch {
            try {
                items.bulkMoveLocation(collectionId, ids, locationId)
                _state.value = _state.value.copy(
                    selectedItemIds = emptySet(),
                    bulkMoveLocationId = if (clear) "" else _state.value.bulkMoveLocationId,
                )
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun bulkTag(mode: String) {
        val s = _state.value
        val ids = s.selectedItemIds.toList()
        if (ids.isEmpty() || s.selectedBulkTagId.isBlank()) return
        viewModelScope.launch {
            try {
                items.bulkTag(collectionId, ids, s.selectedBulkTagId, mode)
                _state.value = _state.value.copy(selectedItemIds = emptySet())
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun bulkLend() {
        val s = _state.value
        val ids = s.selectedItemIds.toList()
        if (ids.isEmpty() || s.selectedBulkContactId.isBlank()) return
        viewModelScope.launch {
            try {
                items.bulkLend(collectionId, ids, s.selectedBulkContactId)
                _state.value = _state.value.copy(selectedItemIds = emptySet())
                refresh()
            } catch (t: Throwable) {
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
                    io.github.bradbrownjr.tangible.data.remote.CollectionPatch(
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
    onItemEdit: (String) -> Unit = {},
    scannedBarcode: String? = null,
    vm: CollectionDetailViewModel = hiltViewModel(),
) {
    @Suppress("UNUSED_PARAMETER") val cid = collectionId // already in SavedStateHandle
    val s by vm.state.collectAsState()
    val context = LocalContext.current

    val imageScanner = remember {
        BarcodeScanning.getClient(
            BarcodeScannerOptions.Builder()
                .setBarcodeFormats(
                    Barcode.FORMAT_EAN_13,
                    Barcode.FORMAT_EAN_8,
                    Barcode.FORMAT_UPC_A,
                    Barcode.FORMAT_UPC_E,
                    Barcode.FORMAT_CODE_128,
                    Barcode.FORMAT_QR_CODE,
                )
                .build(),
        )
    }
    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        try {
            val image = InputImage.fromFilePath(context, uri)
            imageScanner.process(image)
                .addOnSuccessListener { results ->
                    val code = results.firstOrNull { !it.rawValue.isNullOrBlank() }?.rawValue
                    if (!code.isNullOrBlank()) vm.onBarcode(code) else vm.showCreate(true)
                }
                .addOnFailureListener {
                    vm.showCreate(true)
                }
        } catch (_: Throwable) {
            vm.showCreate(true)
        }
    }

    DisposableEffect(Unit) {
        onDispose { imageScanner.close() }
    }

    // Navigate back when the collection is successfully deleted.
    LaunchedEffect(s.deleted) {
        if (s.deleted) onBack()
    }

    // Dismiss open dialogs on back press before navigating away.
    BackHandler(enabled = s.showCreate || s.showCandidatePicker) {
        if (s.showCandidatePicker) vm.dismissCandidatePicker()
        else vm.showCreate(false)
    }

    // When a barcode arrives from the scanner, trigger the lookup flow.
    LaunchedEffect(scannedBarcode) {
        if (!scannedBarcode.isNullOrBlank()) vm.onBarcode(scannedBarcode)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(s.collection?.name ?: stringResource(R.string.collection_default_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                    }
                },
                actions = {
                    if (s.collection?.my_role == "owner" || s.collection?.my_role == "editor") {
                        IconButton(onClick = vm::startEdit) {
                            Icon(Icons.Default.Edit, contentDescription = stringResource(R.string.cd_edit_collection))
                        }
                    }
                    if (s.collection?.my_role == "owner") {
                        IconButton(onClick = vm::startDeleteCollection) {
                            Icon(Icons.Default.Delete, contentDescription = stringResource(R.string.cd_delete_collection))
                        }
                    }
                    IconButton(onClick = vm::toggleViewMode) {
                        Icon(
                            if (s.viewMode == ViewMode.LIST) Icons.Default.GridView else Icons.AutoMirrored.Filled.ViewList,
                            contentDescription = if (s.viewMode == ViewMode.LIST) stringResource(R.string.cd_grid_view) else stringResource(R.string.cd_list_view),
                        )
                    }
                    if (onScan != null) {
                        IconButton(onClick = onScan) {
                            Icon(Icons.Default.QrCodeScanner, contentDescription = stringResource(R.string.cd_scan_barcode))
                        }
                        IconButton(onClick = { imagePicker.launch("image/*") }) {
                            Icon(Icons.Default.Image, contentDescription = stringResource(R.string.cd_scan_barcode_image))
                        }
                    }
                    IconButton(onClick = { vm.showCreate(true) }) {
                        Icon(Icons.Default.Add, contentDescription = stringResource(R.string.cd_add_item))
                    }
                },
            )
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
        val selectedCount = s.selectedItemIds.size
        val allVisibleSelected = displayItems.isNotEmpty() && displayItems.all { it.id in s.selectedItemIds }

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
                        OutlinedButton(onClick = vm::refresh) { Text(stringResource(R.string.retry)) }
                    }
                s.items.isEmpty() -> Text(
                    stringResource(R.string.no_items), Modifier.align(Alignment.Center).padding(16.dp),
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
                        BulkActionBar(
                            selectedCount = selectedCount,
                            allVisibleSelected = allVisibleSelected,
                            tags = s.tags,
                            contacts = s.contacts,
                            locations = s.locations,
                            selectedBulkTagId = s.selectedBulkTagId,
                            selectedBulkContactId = s.selectedBulkContactId,
                            bulkMoveLocationId = s.bulkMoveLocationId,
                            onSetBulkTag = vm::setBulkTag,
                            onSetBulkContact = vm::setBulkContact,
                            onSetBulkMoveLocation = vm::setBulkMoveLocation,
                            onSelectVisible = { vm.selectVisible(displayItems) },
                            onClearSelection = vm::clearSelection,
                            onBulkDepleted = { vm.bulkSetDepleted(true) },
                            onBulkInStock = { vm.bulkSetDepleted(false) },
                            onBulkWanted = { vm.bulkSetWanted(true) },
                            onBulkOwned = { vm.bulkSetWanted(false) },
                            onBulkArchive = vm::bulkArchive,
                            onBulkRestore = vm::bulkRestore,
                            onBulkTagAdd = { vm.bulkTag("add") },
                            onBulkTagRemove = { vm.bulkTag("remove") },
                            onBulkMoveLocation = { vm.bulkMoveLocation(false) },
                            onBulkClearLocation = { vm.bulkMoveLocation(true) },
                            onBulkLend = vm::bulkLend,
                            onBulkDelete = vm::bulkDelete,
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
                                    Text(stringResource(R.string.no_items_in_category), modifier = Modifier.padding(8.dp))
                                }
                            } else {
                                items(displayItems, key = { it.id }) { item ->
                                    ItemCard(
                                        item = item,
                                        selected = item.id in s.selectedItemIds,
                                        onToggleSelected = { vm.toggleSelected(item.id) },
                                        onClick = { onItem(item.id) },
                                        onEdit = { onItemEdit(item.id) },
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
                                        stringResource(R.string.no_items_in_category),
                                        modifier = Modifier.padding(16.dp),
                                    )
                                }
                            } else {
                                items(displayItems, key = { it.id }) { item ->
                                    val valueText = formatItemValue(item)
                                    ListItem(
                                        leadingContent = {
                                            Checkbox(
                                                checked = item.id in s.selectedItemIds,
                                                onCheckedChange = { vm.toggleSelected(item.id) },
                                            )
                                        },
                                        headlineContent = { Text(item.title) },
                                        supportingContent = {
                                            val category = item.category_slug
                                            if (category != null && valueText != null) {
                                                Text("$category • $valueText")
                                            } else if (category != null) {
                                                Text(category)
                                            } else if (valueText != null) {
                                                Text(valueText)
                                            }
                                        },
                                        trailingContent = {
                                            IconButton(onClick = { onItemEdit(item.id) }) {
                                                Icon(Icons.Default.Edit, contentDescription = stringResource(R.string.edit))
                                            }
                                            IconButton(onClick = { vm.delete(item.id) }) {
                                                Icon(Icons.Default.Delete, contentDescription = stringResource(R.string.delete))
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
                        Text(stringResource(R.string.looking_up_barcode))
                    }
                }
            }
        }
        if (s.showCandidatePicker) {
            AlertDialog(
                onDismissRequest = vm::dismissCandidatePicker,
                title = { Text(stringResource(R.string.choose_a_match)) },
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
                                headlineContent = { Text(stringResource(R.string.enter_manually)) },
                                modifier = Modifier.clickable { vm.pickManually() },
                            )
                        }
                    }
                },
                confirmButton = {},
                dismissButton = {
                    TextButton(onClick = vm::dismissCandidatePicker) { Text(stringResource(R.string.cancel)) }
                },
            )
        }

        if (s.showEdit) {
            AlertDialog(
                onDismissRequest = vm::cancelEdit,
                title = { Text(stringResource(R.string.edit_collection)) },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = s.editName,
                            onValueChange = vm::setEditName,
                            label = { Text(stringResource(R.string.collection_name)) },
                            singleLine = true,
                            enabled = !s.editSaving,
                        )
                        OutlinedTextField(
                            value = s.editDescription,
                            onValueChange = vm::setEditDescription,
                            label = { Text(stringResource(R.string.collection_description)) },
                            minLines = 2,
                            enabled = !s.editSaving,
                        )
                    }
                },
                confirmButton = {
                    TextButton(
                        onClick = vm::saveEdit,
                        enabled = !s.editSaving && s.editName.isNotBlank(),
                    ) { Text(if (s.editSaving) stringResource(R.string.saving) else stringResource(R.string.save)) }
                },
                dismissButton = { TextButton(onClick = vm::cancelEdit) { Text(stringResource(R.string.cancel)) } },
            )
        }

        if (s.showDeleteConfirm) {
            val name = s.collection?.name ?: stringResource(R.string.this_collection)
            val count = s.items.size
            AlertDialog(
                onDismissRequest = vm::cancelDeleteCollection,
                title = { Text(stringResource(R.string.delete_collection_title, name)) },
                text = {
                    Text(pluralStringResource(R.plurals.delete_collection_confirm, count, count))
                },
                confirmButton = {
                    TextButton(
                        onClick = vm::confirmDeleteCollection,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.error,
                        ),
                    ) { Text(stringResource(R.string.delete)) }
                },
                dismissButton = { TextButton(onClick = vm::cancelDeleteCollection) { Text(stringResource(R.string.cancel)) } },
            )
        }

        if (s.showCreate) {
            AlertDialog(
                onDismissRequest = { vm.showCreate(false) },
                title = { Text(stringResource(R.string.add_item)) },
                text = {
                    if (s.scraping) {
                        Box(Modifier.fillMaxWidth().height(100.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                    } else {
                        Column {
                            // Root category picker
                            CategoryDropdown(
                                label = stringResource(R.string.category),
                                options = s.rootCategories,
                                selected = s.selectedRoot,
                                onSelect = vm::setSelectedRoot,
                            )
                            if (s.leafCategories.isNotEmpty()) {
                                Spacer(Modifier.height(8.dp))
                                CategoryDropdown(
                                    label = stringResource(R.string.sub_category),
                                    options = s.leafCategories,
                                    selected = s.selectedLeaf,
                                    onSelect = vm::setSelectedLeaf,
                                )
                            }
                            Spacer(Modifier.height(8.dp))
                            OutlinedTextField(
                                value = s.newTitle,
                                onValueChange = vm::setNewTitle,
                                label = { Text(stringResource(R.string.title)) },
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
                    ) { Text(stringResource(R.string.add)) }
                },
                dismissButton = { TextButton(onClick = { vm.showCreate(false) }) { Text(stringResource(R.string.cancel)) } },
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
            placeholder = { Text(stringResource(R.string.select_placeholder)) },
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
    selected: Boolean,
    onToggleSelected: () -> Unit,
    onClick: () -> Unit,
    onEdit: () -> Unit,
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
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                ) {
                    Checkbox(
                        checked = selected,
                        onCheckedChange = { onToggleSelected() },
                    )
                }
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
                formatItemValue(item)?.let { value ->
                    Text(
                        value,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
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
                IconButton(onClick = onEdit, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Edit, contentDescription = stringResource(R.string.edit), modifier = Modifier.size(16.dp))
                }
                IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Delete, contentDescription = stringResource(R.string.delete), modifier = Modifier.size(16.dp))
                }
            }
        }
    }
}

@Composable
private fun BulkActionBar(
    selectedCount: Int,
    allVisibleSelected: Boolean,
    tags: List<TagDto>,
    contacts: List<ContactDto>,
    locations: List<LocationDto>,
    selectedBulkTagId: String,
    selectedBulkContactId: String,
    bulkMoveLocationId: String,
    onSetBulkTag: (String) -> Unit,
    onSetBulkContact: (String) -> Unit,
    onSetBulkMoveLocation: (String) -> Unit,
    onSelectVisible: () -> Unit,
    onClearSelection: () -> Unit,
    onBulkDepleted: () -> Unit,
    onBulkInStock: () -> Unit,
    onBulkWanted: () -> Unit,
    onBulkOwned: () -> Unit,
    onBulkArchive: () -> Unit,
    onBulkRestore: () -> Unit,
    onBulkTagAdd: () -> Unit,
    onBulkTagRemove: () -> Unit,
    onBulkMoveLocation: () -> Unit,
    onBulkClearLocation: () -> Unit,
    onBulkLend: () -> Unit,
    onBulkDelete: () -> Unit,
) {
    var tagMenuOpen by remember { mutableStateOf(false) }
    var contactMenuOpen by remember { mutableStateOf(false) }
    var locationMenuOpen by remember { mutableStateOf(false) }
    val tagPlaceholder = stringResource(R.string.tag_placeholder)
    val contactPlaceholder = stringResource(R.string.contact_placeholder)
    val locationPlaceholder = stringResource(R.string.location_placeholder)
    val selectedTagName = tags.firstOrNull { it.id == selectedBulkTagId }?.name ?: tagPlaceholder
    val selectedContactName = contacts.firstOrNull { it.id == selectedBulkContactId }?.name ?: contactPlaceholder
    val flatLocations = remember(locations) { flattenLocationsWithDepth(locations) }
    val selectedLocationName = flatLocations
        .firstOrNull { it.second.id == bulkMoveLocationId }
        ?.second?.name ?: locationPlaceholder

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 8.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AssistChip(onClick = {}, label = { Text(stringResource(R.string.selected_count, selectedCount)) })
        OutlinedButton(onClick = onSelectVisible, enabled = !allVisibleSelected) { Text(stringResource(R.string.select_visible)) }
        OutlinedButton(onClick = onClearSelection, enabled = selectedCount > 0) { Text(stringResource(R.string.clear)) }
        OutlinedButton(onClick = onBulkDepleted, enabled = selectedCount > 0) { Text(stringResource(R.string.depleted)) }
        OutlinedButton(onClick = onBulkInStock, enabled = selectedCount > 0) { Text(stringResource(R.string.in_stock)) }
        OutlinedButton(onClick = onBulkWanted, enabled = selectedCount > 0) { Text(stringResource(R.string.wanted)) }
        OutlinedButton(onClick = onBulkOwned, enabled = selectedCount > 0) { Text(stringResource(R.string.owned)) }
        OutlinedButton(onClick = onBulkArchive, enabled = selectedCount > 0) { Text(stringResource(R.string.archive)) }
        OutlinedButton(onClick = onBulkRestore, enabled = selectedCount > 0) { Text(stringResource(R.string.restore)) }
        Box {
            OutlinedButton(onClick = { tagMenuOpen = true }, enabled = tags.isNotEmpty()) {
                Text(selectedTagName)
            }
            DropdownMenu(expanded = tagMenuOpen, onDismissRequest = { tagMenuOpen = false }) {
                tags.forEach { tag ->
                    DropdownMenuItem(
                        text = { Text(tag.name) },
                        onClick = {
                            onSetBulkTag(tag.id)
                            tagMenuOpen = false
                        },
                    )
                }
            }
        }
        OutlinedButton(
            onClick = onBulkTagAdd,
            enabled = selectedCount > 0 && selectedBulkTagId.isNotBlank(),
        ) { Text(stringResource(R.string.add_tag)) }
        OutlinedButton(
            onClick = onBulkTagRemove,
            enabled = selectedCount > 0 && selectedBulkTagId.isNotBlank(),
        ) { Text(stringResource(R.string.remove_tag)) }
        Box {
            OutlinedButton(onClick = { locationMenuOpen = true }, enabled = flatLocations.isNotEmpty()) {
                Text(selectedLocationName)
            }
            DropdownMenu(expanded = locationMenuOpen, onDismissRequest = { locationMenuOpen = false }) {
                flatLocations.forEach { (depth, loc) ->
                    DropdownMenuItem(
                        text = { Text("${"  ".repeat(depth)}${loc.name}") },
                        onClick = {
                            onSetBulkMoveLocation(loc.id)
                            locationMenuOpen = false
                        },
                    )
                }
            }
        }
        OutlinedButton(
            onClick = onBulkMoveLocation,
            enabled = selectedCount > 0 && bulkMoveLocationId.isNotBlank(),
        ) { Text(stringResource(R.string.move)) }
        OutlinedButton(
            onClick = onBulkClearLocation,
            enabled = selectedCount > 0,
        ) { Text(stringResource(R.string.clear_location)) }
        Box {
            OutlinedButton(onClick = { contactMenuOpen = true }, enabled = contacts.isNotEmpty()) {
                Text(selectedContactName)
            }
            DropdownMenu(expanded = contactMenuOpen, onDismissRequest = { contactMenuOpen = false }) {
                contacts.forEach { contact ->
                    DropdownMenuItem(
                        text = { Text(contact.name) },
                        onClick = {
                            onSetBulkContact(contact.id)
                            contactMenuOpen = false
                        },
                    )
                }
            }
        }
        OutlinedButton(
            onClick = onBulkLend,
            enabled = selectedCount > 0 && selectedBulkContactId.isNotBlank(),
        ) { Text(stringResource(R.string.lend)) }
        Button(
            onClick = onBulkDelete,
            enabled = selectedCount > 0,
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.error,
                contentColor = MaterialTheme.colorScheme.onError,
            ),
        ) {
            Text(stringResource(R.string.delete))
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
        placeholder = { Text(stringResource(R.string.search_items)) },
        leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
        trailingIcon = {
            if (query.isNotEmpty()) {
                IconButton(onClick = onClear) {
                    Icon(Icons.Default.Close, contentDescription = stringResource(R.string.cd_clear_search))
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
