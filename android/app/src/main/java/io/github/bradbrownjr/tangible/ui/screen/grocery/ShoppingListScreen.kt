package io.github.bradbrownjr.tangible.ui.screen.grocery

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Store
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import io.github.bradbrownjr.tangible.data.remote.BarcodeLookupRequest
import io.github.bradbrownjr.tangible.data.remote.CategoryDto
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingAisleDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingFeedEntryDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingItemPatchRequest
import io.github.bradbrownjr.tangible.data.remote.ShoppingStoreDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ShoppingRepository
import io.github.bradbrownjr.tangible.R
import javax.inject.Inject

private val LIST_TYPES = listOf("groceries", "hardware", "home_goods", "wish_list")

/** Implied collection name that will be auto-created if absent for each list type.
 *  Wish List is intentionally absent — the user picks the target collection in the dialog. */
private val IMPLIED_COLLECTION_NAME = mapOf(
    "groceries"  to "Pantry",
    "hardware"   to "Workshop",
    "home_goods" to "Home",
)

data class ShoppingListUi(
    val listType: String = "groceries",
    val items: List<ShoppingFeedEntryDto> = emptyList(),
    val collections: Map<String, CollectionDto> = emptyMap(),
    val stores: List<ShoppingStoreDto> = emptyList(),
    val selectedStoreId: String? = null,
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    val updating: Set<String> = emptySet(),
    val showAddDialog: Boolean = false,
    val showStoreSelector: Boolean = false,
    val addDialogPreFillName: String = "",
    val addDialogPreFillBrand: String = "",
    val addDialogPreFillNotes: String = "",
    val addDialogPreFillCategorySlug: String = "",
    val impliedCollectionId: String? = null,
    val barcodeLookupLoading: Boolean = false,
    val addDialogBarcodeNotFound: Boolean = false,
    val availableCategories: List<CategoryDto> = emptyList(),
    val editingEntry: ShoppingFeedEntryDto? = null,
)

@HiltViewModel
class ShoppingListViewModel @Inject constructor(
    private val shoppingRepo: ShoppingRepository,
    private val collectionRepo: CollectionRepository,
    private val api: TangibleApi,
) : ViewModel() {
    private val _state = MutableStateFlow(ShoppingListUi())
    val state: StateFlow<ShoppingListUi> = _state.asStateFlow()

    init { refresh() }

    fun refresh() = load(isRefresh = false)
    fun pullRefresh() = load(isRefresh = true)

    private fun load(isRefresh: Boolean) {
        val listType = _state.value.listType
        if (isRefresh) {
            _state.value = _state.value.copy(refreshing = true, error = null)
        } else {
            _state.value = _state.value.copy(loading = true, error = null)
        }
        viewModelScope.launch {
            try {
                val items = shoppingRepo.feed(listType.takeIf { it.isNotBlank() })
                val collections = collectionRepo.list()
                val stores = shoppingRepo.listStores()
                val impliedCollectionId = resolveImpliedCollection(listType, collections)
                val rootCategories = try {
                    api.listCategories().filter { it.parent_id == null }
                } catch (_: Throwable) { emptyList() }
                val checkedIds = _state.value.updating
                _state.value = _state.value.copy(
                    items = items.filter { it.id !in checkedIds },
                    collections = collections.associateBy { it.id },
                    stores = stores,
                    impliedCollectionId = impliedCollectionId,
                    availableCategories = rootCategories,
                    loading = false,
                    refreshing = false,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, refreshing = false, error = t.message)
            }
        }
    }

    fun selectStore(storeId: String?) {
        _state.value = _state.value.copy(selectedStoreId = storeId, showStoreSelector = false)
    }

    fun toggleStoreSelector() {
        _state.value = _state.value.copy(showStoreSelector = !_state.value.showStoreSelector)
    }

    fun dismissStoreSelector() {
        _state.value = _state.value.copy(showStoreSelector = false)
    }

    fun showAddDialog() {
        _state.value = _state.value.copy(showAddDialog = true)
    }

    fun dismissAddDialog() {
        _state.value = _state.value.copy(showAddDialog = false, addDialogPreFillName = "", addDialogPreFillBrand = "", addDialogPreFillNotes = "", addDialogPreFillCategorySlug = "", addDialogBarcodeNotFound = false)
    }

    fun setListType(type: String) {
        if (_state.value.listType == type) return
        _state.value = _state.value.copy(listType = type, items = emptyList())
        load(isRefresh = false)
    }

    /** Returns the ID of the implied collection for [listType], creating it if needed. */
    private suspend fun resolveImpliedCollection(
        listType: String,
        collections: List<CollectionDto>,
    ): String? {
        val impliedName = IMPLIED_COLLECTION_NAME[listType] ?: return collections.firstOrNull()?.id
        val existing = collections.find { it.name.equals(impliedName, ignoreCase = true) }
        if (existing != null) return existing.id
        return try {
            collectionRepo.create(impliedName).id
        } catch (_: Throwable) {
            collections.firstOrNull()?.id
        }
    }

    fun onBarcode(barcode: String) {
        _state.value = _state.value.copy(barcodeLookupLoading = true, showAddDialog = false)
        viewModelScope.launch {
            try {
                val response = api.barcodeLookup(BarcodeLookupRequest(barcode))
                val candidate = response.candidates.firstOrNull()
                val name = candidate?.title.orEmpty()
                val brand = candidate?.brand.orEmpty()
                val categorySlug = response.hint_category_slug
                    ?: candidate?.category.orEmpty()
                _state.value = _state.value.copy(
                    showAddDialog = true,
                    addDialogPreFillName = name,
                    addDialogPreFillBrand = brand,
                    addDialogPreFillNotes = "",
                    addDialogPreFillCategorySlug = categorySlug,
                    addDialogBarcodeNotFound = candidate == null,
                    barcodeLookupLoading = false,
                )
            } catch (_: Throwable) {
                _state.value = _state.value.copy(
                    showAddDialog = true,
                    addDialogPreFillName = "",
                    addDialogPreFillNotes = "",
                    barcodeLookupLoading = false,
                )
            }
        }
    }

    fun addItem(
        name: String,
        quantity: Int,
        brand: String?,
        notes: String?,
        categorySlug: String?,
        collectionId: String? = null,
        newCollectionName: String? = null,
        newCollectionCategorySlug: String? = null,
    ) {
        _state.value = _state.value.copy(showAddDialog = false, addDialogPreFillName = "", addDialogPreFillBrand = "", addDialogPreFillNotes = "", addDialogPreFillCategorySlug = "")
        viewModelScope.launch {
            try {
                val collId = when {
                    collectionId != null -> collectionId
                    newCollectionName != null -> collectionRepo.create(
                        name = newCollectionName,
                        defaultCategorySlug = newCollectionCategorySlug,
                    ).id
                    else -> _state.value.impliedCollectionId ?: return@launch
                }
                shoppingRepo.addItem(
                    collectionId = collId,
                    name = name,
                    quantity = quantity,
                    brand = brand?.takeIf { it.isNotBlank() },
                    notes = notes?.takeIf { it.isNotBlank() },
                    categorySlug = categorySlug?.takeIf { it.isNotBlank() },
                    listType = _state.value.listType,
                )
                load(isRefresh = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun startEdit(entry: ShoppingFeedEntryDto) {
        if (entry.id.startsWith("item:")) return  // depleted-item virtual entries are read-only
        _state.value = _state.value.copy(editingEntry = entry)
    }

    fun dismissEdit() {
        _state.value = _state.value.copy(editingEntry = null)
    }

    fun saveEdit(entry: ShoppingFeedEntryDto, name: String, quantity: Int, brand: String?, notes: String?, categorySlug: String?) {
        _state.value = _state.value.copy(editingEntry = null, updating = _state.value.updating + entry.id)
        viewModelScope.launch {
            try {
                api.patchShoppingItem(
                    entry.id,
                    ShoppingItemPatchRequest(
                        name = name.trim(),
                        quantity = quantity,
                        brand = brand?.takeIf { it.isNotBlank() },
                        notes = notes?.takeIf { it.isNotBlank() },
                        category_slug = categorySlug?.takeIf { it.isNotBlank() },
                    )
                )
                _state.value = _state.value.copy(updating = _state.value.updating - entry.id)
                load(isRefresh = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    error = t.message,
                    updating = _state.value.updating - entry.id,
                )
            }
        }
    }

    /** Marks the entry purchased on the server immediately (web's "Mark purchased" button).
     *  Optimistically removes from the visible list; on failure, restores it and shows an error. */
    fun checkItem(entryId: String) {
        val entry = _state.value.items.find { it.id == entryId } ?: return
        _state.value = _state.value.copy(
            items = _state.value.items.filter { it.id != entryId },
            updating = _state.value.updating + entryId,
        )
        viewModelScope.launch {
            try {
                if (entryId.startsWith("item:")) {
                    shoppingRepo.restockDepletedItem(entryId.removePrefix("item:"), entry.quantity)
                } else {
                    shoppingRepo.purchaseItem(entryId)
                }
                _state.value = _state.value.copy(updating = _state.value.updating - entryId)
            } catch (t: Throwable) {
                // Rollback: re-insert the entry and surface the error.
                _state.value = _state.value.copy(
                    items = listOf(entry) + _state.value.items,
                    updating = _state.value.updating - entryId,
                    error = t.message,
                )
            }
        }
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }

    fun deleteItem(entryId: String) {
        if (entryId.startsWith("item:")) return
        _state.value = _state.value.copy(updating = _state.value.updating + entryId)
        viewModelScope.launch {
            try {
                shoppingRepo.deleteItem(entryId)
                _state.value = _state.value.copy(
                    items = _state.value.items.filter { it.id != entryId },
                    updating = _state.value.updating - entryId,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    error = t.message,
                    updating = _state.value.updating - entryId,
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Aisle-sort helpers
// ---------------------------------------------------------------------------

private data class AisleGroup(
    val name: String,
    val items: List<ShoppingFeedEntryDto>,
)

private fun groupByAisle(
    items: List<ShoppingFeedEntryDto>,
    aisles: List<ShoppingAisleDto>,
    otherLabel: String = "Other",
): List<AisleGroup> {
    val slugToAisle = mutableMapOf<String, ShoppingAisleDto>()
    for (aisle in aisles) {
        for (slug in aisle.category_slugs) {
            slugToAisle[slug] = aisle
        }
    }
    val grouped = LinkedHashMap<String?, MutableList<ShoppingFeedEntryDto>>()
    for (item in items) {
        val aisleName = item.category_slug?.let { slug ->
            slugToAisle[slug]?.name ?: slugToAisle[slug.substringBeforeLast(".", slug)]?.name
        }
        grouped.getOrPut(aisleName) { mutableListOf() }.add(item)
    }
    val result = mutableListOf<AisleGroup>()
    for (aisle in aisles.sortedBy { it.position }) {
        val group = grouped[aisle.name]
        if (!group.isNullOrEmpty()) result.add(AisleGroup(aisle.name, group))
    }
    val other = grouped[null]
    if (!other.isNullOrEmpty()) result.add(AisleGroup(otherLabel, other))
    return result
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShoppingListScreen(
    viewModel: ShoppingListViewModel = hiltViewModel(),
    onBack: () -> Unit,
    showBackButton: Boolean = true,
    onNavigateToCollection: (collectionId: String) -> Unit,
    onManageStores: () -> Unit,
    onNavigateToScanner: () -> Unit = {},
    scannedBarcode: String? = null,
) {
    val ui by viewModel.state.collectAsState()
    val selectedStore = ui.stores.find { it.id == ui.selectedStoreId }
    val otherLabel = stringResource(R.string.other)
    val aisleGroups = if (selectedStore != null) groupByAisle(ui.items, selectedStore.aisles, otherLabel) else null
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()

    // Show errors as snackbars and clear the state so they don't re-fire.
    LaunchedEffect(ui.error) {
        ui.error?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            viewModel.clearError()
        }
    }

    // When a barcode arrives from the scanner, look it up and pre-fill the add dialog.
    LaunchedEffect(scannedBarcode) {
        if (!scannedBarcode.isNullOrBlank()) viewModel.onBarcode(scannedBarcode)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(stringResource(R.string.grocery_list))
                        if (selectedStore != null) {
                            Text(
                                selectedStore.name,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                    }
                },
                navigationIcon = {
                    if (showBackButton) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                        }
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.toggleStoreSelector() }) {
                        Icon(
                            Icons.Default.Store,
                            contentDescription = stringResource(R.string.cd_select_store),
                            tint = if (ui.selectedStoreId != null)
                                MaterialTheme.colorScheme.primary
                            else
                                LocalContentColor.current,
                        )
                    }
                    IconButton(onClick = onNavigateToScanner) {
                        Icon(
                            Icons.Default.QrCodeScanner,
                            contentDescription = stringResource(R.string.cd_scan_barcode),
                        )
                    }
                    IconButton(onClick = { viewModel.showAddDialog() }) {
                        Icon(
                            Icons.Default.Add,
                            contentDescription = stringResource(R.string.cd_add_grocery_item),
                        )
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { innerPadding ->
        val pagerState = rememberPagerState(pageCount = { LIST_TYPES.size })
        // Sync pager → ViewModel when user swipes
        LaunchedEffect(pagerState.currentPage, pagerState.isScrollInProgress) {
            if (!pagerState.isScrollInProgress) {
                viewModel.setListType(LIST_TYPES[pagerState.currentPage])
            }
        }
        // Sync ViewModel → pager when tab is tapped
        LaunchedEffect(ui.listType) {
            val targetPage = LIST_TYPES.indexOf(ui.listType).coerceAtLeast(0)
            if (pagerState.currentPage != targetPage) {
                pagerState.animateScrollToPage(targetPage)
            }
        }
        Column(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            // List type tabs
            ScrollableTabRow(
                selectedTabIndex = pagerState.currentPage,
                edgePadding = 0.dp,
            ) {
            val tabLabels = mapOf(
                "groceries"  to stringResource(R.string.list_type_groceries),
                "hardware"   to stringResource(R.string.list_type_hardware),
                "home_goods" to stringResource(R.string.list_type_home_goods),
                "wish_list"  to stringResource(R.string.list_type_wish_list),
            )
            LIST_TYPES.forEachIndexed { index, type ->
                Tab(
                    selected = pagerState.currentPage == index,
                    onClick = { viewModel.setListType(type) },
                    text = { Text(tabLabels[type] ?: type) },
                )
            }
            }
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.weight(1f),
            beyondViewportPageCount = 0,
        ) {
        PullToRefreshBox(
                isRefreshing = ui.refreshing,
                onRefresh = { viewModel.pullRefresh() },
                modifier = Modifier.fillMaxSize(),
            ) {
                // Empty/loading branches must be inside a LazyColumn so PullToRefreshBox
                // can receive the nested-scroll pull gesture (a plain Box does not dispatch it).
                when {
                    ui.loading -> {
                        LazyColumn(modifier = Modifier.fillMaxSize()) {
                            item {
                                Box(Modifier.fillParentMaxSize(), contentAlignment = Alignment.Center) {
                                    CircularProgressIndicator()
                                }
                            }
                        }
                    }
                    ui.items.isEmpty() && !ui.loading -> {
                        LazyColumn(modifier = Modifier.fillMaxSize()) {
                            item {
                                Box(Modifier.fillParentMaxSize(), contentAlignment = Alignment.Center) {
                                    Column(
                                        horizontalAlignment = Alignment.CenterHorizontally,
                                        verticalArrangement = Arrangement.spacedBy(8.dp),
                                    ) {
                                        Text(stringResource(R.string.all_stocked), style = MaterialTheme.typography.headlineSmall)
                                        Text(stringResource(R.string.all_stocked_subtitle), style = MaterialTheme.typography.bodySmall)
                                        TextButton(onClick = { viewModel.showAddDialog() }) { Text(stringResource(R.string.add_an_item)) }
                                    }
                                }
                            }
                        }
                    }
                    else -> {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            contentPadding = PaddingValues(vertical = 16.dp),
                        ) {
                            if (aisleGroups != null) {
                                aisleGroups.forEach { group ->
                                    item(key = "header-${group.name}") {
                                        AisleHeader(group.name)
                                    }
                                    items(group.items, key = { it.id }) { entry ->
                                        ShoppingEntryCard(
                                            entry = entry,
                                            collectionName = ui.collections[entry.collection_id]?.name ?: entry.collection_id,
                                            isUpdating = entry.id in ui.updating,
                                            onCheck = { viewModel.checkItem(entry.id) },
                                            onDelete = { viewModel.deleteItem(entry.id) },
                                            onNavigateToCollection = { onNavigateToCollection(entry.collection_id) },
                                            onEdit = { viewModel.startEdit(entry) },
                                        )
                                    }
                                }
                            } else {
                                items(ui.items, key = { it.id }) { entry ->
                                    ShoppingEntryCard(
                                        entry = entry,
                                        collectionName = ui.collections[entry.collection_id]?.name ?: entry.collection_id,
                                        isUpdating = entry.id in ui.updating,
                                        onCheck = { viewModel.checkItem(entry.id) },
                                        onDelete = { viewModel.deleteItem(entry.id) },
                                        onNavigateToCollection = { onNavigateToCollection(entry.collection_id) },
                                        onEdit = { viewModel.startEdit(entry) },
                                    )
                                }
                            }
                            // The legacy "Checked" section is gone: tapping the check now syncs
                            // straight to the server (web's "Mark purchased") and removes the row.
                        }
                    }
                }
            } // end PullToRefreshBox

            if (ui.showStoreSelector) {
                StoreSelectorDialog(
                    stores = ui.stores,
                    selectedStoreId = ui.selectedStoreId,
                    onSelect = { viewModel.selectStore(it) },
                    onManageStores = { viewModel.dismissStoreSelector(); onManageStores() },
                    onDismiss = { viewModel.dismissStoreSelector() },
                )
            }
        } // end HorizontalPager
        } // end Column
    }

    // Barcode lookup in-progress overlay
    if (ui.barcodeLookupLoading) {
        androidx.compose.ui.window.Dialog(onDismissRequest = {}) {
            androidx.compose.foundation.layout.Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(32.dp),
                contentAlignment = Alignment.Center,
            ) {
                androidx.compose.material3.Card {
                    Column(
                        modifier = Modifier.padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        CircularProgressIndicator()
                        Text(stringResource(R.string.barcode_looking_up))
                    }
                }
            }
        }
    }

    if (ui.showAddDialog) {
        val allCollections = ui.collections.values.toList()
        AddShoppingItemDialog(
            listType = ui.listType,
            preFillName = ui.addDialogPreFillName,
            preFillBrand = ui.addDialogPreFillBrand,
            preFillNotes = ui.addDialogPreFillNotes,
            preFillCategorySlug = ui.addDialogPreFillCategorySlug,
            barcodeNotFound = ui.addDialogBarcodeNotFound,
            collections = allCollections,
            initialCollectionId = allCollections.find { it.name.equals("Wish List", ignoreCase = true) }?.id
                ?: allCollections.firstOrNull()?.id,
            availableCategories = ui.availableCategories,
            onDismiss = { viewModel.dismissAddDialog() },
            onAdd = { itemName, qty, itemBrand, itemNotes, catSlug, collId, newCollName, newCollCatSlug ->
                viewModel.addItem(itemName, qty, itemBrand, itemNotes, catSlug, collId, newCollName, newCollCatSlug)
            },
        )
    }

    ui.editingEntry?.let { entry ->
        EditShoppingItemDialog(
            entry = entry,
            listType = ui.listType,
            onDismiss = { viewModel.dismissEdit() },
            onSave = { name, qty, brand, notes, catSlug -> viewModel.saveEdit(entry, name, qty, brand, notes, catSlug) },
        )
    }
}

@Composable
private fun AisleHeader(name: String) {
    Text(
        text = name,
        style = MaterialTheme.typography.titleSmall,
        fontWeight = FontWeight.Bold,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 2.dp),
    )
    HorizontalDivider()
}

@Composable
private fun ShoppingEntryCard(
    entry: ShoppingFeedEntryDto,
    collectionName: String,
    isUpdating: Boolean,
    onCheck: () -> Unit,
    onDelete: () -> Unit,
    onNavigateToCollection: () -> Unit,
    onEdit: () -> Unit,
) {
    val isAdHoc = !entry.id.startsWith("item:")
    Card(
        modifier = Modifier.fillMaxWidth().heightIn(min = 72.dp),
        shape = RoundedCornerShape(8.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(
                modifier = Modifier.weight(1f).padding(end = 8.dp)
                    .clickable { if (isAdHoc) onEdit() else onNavigateToCollection() },
            ) {
                Text(
                    text = if (entry.quantity > 1) "${entry.name} \u00d7${entry.quantity}" else entry.name,
                    style = MaterialTheme.typography.bodyLarge,
                    maxLines = 1,
                )
                // Prefer brand (collection is implied by the list type). Fall back to collection
                // name only for depleted-item entries so the user still sees where it lives.
                val secondaryLabel = entry.brand?.takeIf { it.isNotBlank() }
                    ?: collectionName.takeIf { !isAdHoc }
                if (!secondaryLabel.isNullOrBlank()) {
                    Text(
                        text = secondaryLabel,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = if (!isAdHoc) Modifier.clickable { onNavigateToCollection() } else Modifier,
                    )
                }
                if (!entry.category_slug.isNullOrBlank()) {
                    Text(
                        text = entry.category_slug!!.split(".").last(),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (!entry.notes.isNullOrBlank()) {
                    Text(
                        text = entry.notes!!,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                    )
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
                // Depleted-item entries show a navigation arrow so the user knows tapping opens the collection.
                if (!isAdHoc) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowForward,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (isAdHoc) {
                    IconButton(onClick = onDelete, enabled = !isUpdating) {
                        Icon(
                            Icons.Default.Delete,
                            contentDescription = stringResource(R.string.remove),
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(18.dp),
                        )
                    }
                }
                Button(
                    onClick = onCheck,
                    enabled = !isUpdating,
                    modifier = Modifier.heightIn(min = 40.dp),
                ) {
                    if (isUpdating) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary,
                        )
                    } else {
                        Icon(Icons.Default.Check, contentDescription = stringResource(R.string.got_it), Modifier.size(18.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun StoreSelectorDialog(
    stores: List<ShoppingStoreDto>,
    selectedStoreId: String?,
    onSelect: (String?) -> Unit,
    onManageStores: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.sort_by_store_aisle)) },
        text = {
            Column {
                ListItem(
                    headlineContent = { Text(stringResource(R.string.no_store_default_order)) },
                    leadingContent = {
                        RadioButton(selected = selectedStoreId == null, onClick = { onSelect(null) })
                    },
                    modifier = Modifier.clickable { onSelect(null) },
                )
                stores.forEach { store ->
                    ListItem(
                        headlineContent = { Text(store.name) },
                        supportingContent = { Text(pluralStringResource(R.plurals.aisle_count, store.aisles.size, store.aisles.size)) },
                        leadingContent = {
                            RadioButton(selected = store.id == selectedStoreId, onClick = { onSelect(store.id) })
                        },
                        modifier = Modifier.clickable { onSelect(store.id) },
                    )
                }
            }
        },
        confirmButton = { TextButton(onClick = onManageStores) { Text(stringResource(R.string.manage_stores)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddShoppingItemDialog(
    listType: String = "groceries",
    preFillName: String = "",
    preFillBrand: String = "",
    preFillNotes: String = "",
    preFillCategorySlug: String = "",
    barcodeNotFound: Boolean = false,
    collections: List<CollectionDto> = emptyList(),
    initialCollectionId: String? = null,
    availableCategories: List<CategoryDto> = emptyList(),
    onDismiss: () -> Unit,
    onAdd: (name: String, quantity: Int, brand: String?, notes: String?, itemCategorySlug: String?, collectionId: String?, newCollectionName: String?, newCollectionCategorySlug: String?) -> Unit,
) {
    var name by remember { mutableStateOf(preFillName) }
    var quantityText by remember { mutableStateOf("1") }
    var brand by remember { mutableStateOf(preFillBrand) }
    var notes by remember { mutableStateOf(preFillNotes) }
    var categorySlug by remember { mutableStateOf(preFillCategorySlug) }
    // Show category picker for all list types except wish_list (which uses collections for organisation).
    val showCategory = listType != "wish_list"
    // For wish_list: pick from existing collections or create a new one with a category template.
    val isWishList = listType == "wish_list"
    val showCollectionPicker = isWishList && collections.isNotEmpty()
    val showCreateCollection = isWishList && collections.isEmpty()
    var selectedCollectionId by remember { mutableStateOf(initialCollectionId ?: collections.firstOrNull()?.id) }
    // State for the create-new-collection flow.
    var newCollectionName by remember { mutableStateOf("Wish List") }
    var selectedTemplateCategorySlug by remember { mutableStateOf<String?>(null) }
    val categoryPresets = presetsForType(listType)
    val dialogTitle = when (listType) {
        "hardware"   -> stringResource(R.string.list_type_hardware)
        "home_goods" -> stringResource(R.string.list_type_home_goods)
        "wish_list"  -> stringResource(R.string.list_type_wish_list)
        else         -> stringResource(R.string.list_type_groceries)
    }.let { stringResource(R.string.add_item_for_list, it) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(dialogTitle) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                if (barcodeNotFound) {
                    Text(
                        stringResource(R.string.barcode_not_found_hint),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.secondary,
                    )
                }
                OutlinedTextField(
                    value = brand,
                    onValueChange = { brand = it },
                    label = { Text(stringResource(R.string.brand_optional)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.grocery_item_name_required)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                if (showCategory) {
                    var categoryMenuExpanded by remember { mutableStateOf(false) }
                    ExposedDropdownMenuBox(
                        expanded = categoryMenuExpanded,
                        onExpandedChange = { categoryMenuExpanded = it },
                    ) {
                        OutlinedTextField(
                            value = if (categorySlug.isBlank()) stringResource(R.string.no_category)
                                    else categoryPresets.find { it.slug == categorySlug }
                                        ?.let { stringResource(it.labelRes) } ?: categorySlug,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text(stringResource(R.string.category)) },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = categoryMenuExpanded) },
                            modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
                        )
                        ExposedDropdownMenu(
                            expanded = categoryMenuExpanded,
                            onDismissRequest = { categoryMenuExpanded = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text(stringResource(R.string.no_category)) },
                                onClick = { categorySlug = ""; categoryMenuExpanded = false },
                            )
                            categoryPresets.forEach { cat ->
                                DropdownMenuItem(
                                    text = { Text(stringResource(cat.labelRes)) },
                                    onClick = { categorySlug = cat.slug; categoryMenuExpanded = false },
                                )
                            }
                        }
                    }
                }
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text(stringResource(R.string.notes_optional)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = quantityText,
                    onValueChange = { quantityText = it.filter { c -> c.isDigit() } },
                    label = { Text(stringResource(R.string.quantity)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth(),
                )
                if (showCollectionPicker) {
                    var collectionMenuExpanded by remember { mutableStateOf(false) }
                    ExposedDropdownMenuBox(
                        expanded = collectionMenuExpanded,
                        onExpandedChange = { collectionMenuExpanded = it },
                    ) {
                        OutlinedTextField(
                            value = collections.find { it.id == selectedCollectionId }?.name ?: "",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text(stringResource(R.string.collection_default_title)) },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = collectionMenuExpanded) },
                            modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
                        )
                        ExposedDropdownMenu(
                            expanded = collectionMenuExpanded,
                            onDismissRequest = { collectionMenuExpanded = false },
                        ) {
                            collections.forEach { coll ->
                                DropdownMenuItem(
                                    text = { Text(coll.name) },
                                    onClick = { selectedCollectionId = coll.id; collectionMenuExpanded = false },
                                )
                            }
                        }
                    }
                }
                if (showCreateCollection) {
                    HorizontalDivider()
                    Text(
                        stringResource(R.string.wish_list_create_collection_prompt),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    // Category template chips (horizontal scroll)
                    if (availableCategories.isNotEmpty()) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            availableCategories.forEach { cat ->
                                FilterChip(
                                    selected = selectedTemplateCategorySlug == cat.slug,
                                    onClick = {
                                        selectedTemplateCategorySlug =
                                            if (selectedTemplateCategorySlug == cat.slug) null else cat.slug
                                    },
                                    label = { Text(cat.name) },
                                )
                            }
                        }
                    }
                    // Collection name field
                    OutlinedTextField(
                        value = newCollectionName,
                        onValueChange = { newCollectionName = it },
                        label = { Text(stringResource(R.string.collection_name)) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank()) {
                        when {
                            showCreateCollection -> onAdd(
                                name.trim(),
                                quantityText.toIntOrNull() ?: 1,
                                brand.trim().takeIf { it.isNotBlank() },
                                notes.trim().takeIf { it.isNotBlank() },
                                categorySlug.takeIf { it.isNotBlank() },
                                null,
                                newCollectionName.trim().ifBlank { "Wish List" },
                                selectedTemplateCategorySlug,
                            )
                            else -> onAdd(
                                name.trim(),
                                quantityText.toIntOrNull() ?: 1,
                                brand.trim().takeIf { it.isNotBlank() },
                                notes.trim().takeIf { it.isNotBlank() },
                                categorySlug.takeIf { it.isNotBlank() },
                                if (showCollectionPicker) selectedCollectionId else null,
                                null,
                                null,
                            )
                        }
                    }
                },
                enabled = name.isNotBlank(),
            ) { Text(stringResource(R.string.add)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun EditShoppingItemDialog(
    entry: ShoppingFeedEntryDto,
    listType: String = "groceries",
    onDismiss: () -> Unit,
    onSave: (name: String, quantity: Int, brand: String?, notes: String?, categorySlug: String?) -> Unit,
) {
    var name by remember { mutableStateOf(entry.name) }
    var quantityText by remember { mutableStateOf(entry.quantity.toString()) }
    var brand by remember { mutableStateOf(entry.brand.orEmpty()) }
    var notes by remember { mutableStateOf(entry.notes.orEmpty()) }
    val categoryPresets = presetsForType(listType)
    var categorySlug by remember { mutableStateOf(entry.category_slug.orEmpty()) }
    val isWishList = listType == "wish_list"

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.edit_item)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = brand,
                    onValueChange = { brand = it },
                    label = { Text(stringResource(R.string.brand_optional)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.grocery_item_name_required)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                if (!isWishList) {
                    var categoryMenuExpanded by remember { mutableStateOf(false) }
                    ExposedDropdownMenuBox(
                        expanded = categoryMenuExpanded,
                        onExpandedChange = { categoryMenuExpanded = it },
                    ) {
                        OutlinedTextField(
                            value = if (categorySlug.isBlank()) stringResource(R.string.no_category)
                                    else categoryPresets.find { it.slug == categorySlug }
                                        ?.let { stringResource(it.labelRes) } ?: categorySlug,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text(stringResource(R.string.category)) },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = categoryMenuExpanded) },
                            modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
                        )
                        ExposedDropdownMenu(
                            expanded = categoryMenuExpanded,
                            onDismissRequest = { categoryMenuExpanded = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text(stringResource(R.string.no_category)) },
                                onClick = { categorySlug = ""; categoryMenuExpanded = false },
                            )
                            categoryPresets.forEach { cat ->
                                DropdownMenuItem(
                                    text = { Text(stringResource(cat.labelRes)) },
                                    onClick = { categorySlug = cat.slug; categoryMenuExpanded = false },
                                )
                            }
                        }
                    }
                }
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text(stringResource(R.string.notes_optional)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = quantityText,
                    onValueChange = { quantityText = it.filter { c -> c.isDigit() } },
                    label = { Text(stringResource(R.string.quantity)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank()) {
                        onSave(
                            name.trim(),
                            quantityText.toIntOrNull() ?: entry.quantity,
                            brand.trim().takeIf { it.isNotBlank() },
                            notes.trim().takeIf { it.isNotBlank() },
                            categorySlug.takeIf { it.isNotBlank() },
                        )
                    }
                },
                enabled = name.isNotBlank(),
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

