package io.github.bradbrownjr.tangible.ui.screen.grocery

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ViewList
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Store
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewModelScope
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
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
import io.github.bradbrownjr.tangible.data.remote.PairCreateRequest
import io.github.bradbrownjr.tangible.data.remote.UserListTypeDto
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ItemRepository
import io.github.bradbrownjr.tangible.data.repo.ShoppingRepository
import io.github.bradbrownjr.tangible.data.sync.NetworkMonitor
import io.github.bradbrownjr.tangible.R
import java.io.IOException
import javax.inject.Inject

enum class ListTypeWizardStep { CLOSED, PICK_PRESET, CONFIRM }

data class ShoppingListUi(
    val listType: String = "",
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
    val isOnline: Boolean = true,
    val viewMode: ShoppingViewMode = ShoppingViewMode.LIST,
    val allItems: List<ShoppingFeedEntryDto> = emptyList(),
    val allItemsLoading: Boolean = false,
    val customListTypes: List<UserListTypeDto> = emptyList(),
    val countByType: Map<String, Int> = emptyMap(),
    val listTypeWizardStep: ListTypeWizardStep = ListTypeWizardStep.CLOSED,
    val listTypePresets: List<CategoryDto> = emptyList(),
    val listTypePreset: CategoryDto? = null,
    val listTypeName: String = "",
)

enum class ShoppingViewMode { LIST, GRID }

@HiltViewModel
class ShoppingListViewModel @Inject constructor(
    private val shoppingRepo: ShoppingRepository,
    private val collectionRepo: CollectionRepository,
    private val itemsRepo: ItemRepository,
    private val api: TangibleApi,
    private val networkMonitor: NetworkMonitor,
) : ViewModel() {
    private val _state = MutableStateFlow(ShoppingListUi())
    val state: StateFlow<ShoppingListUi> = _state.asStateFlow()

    init {
        refresh()
        loadCustomTypes()
        viewModelScope.launch {
            networkMonitor.isOnline.collect { online ->
                _state.value = _state.value.copy(isOnline = online)
            }
        }
    }

    fun loadCustomTypes() {
        viewModelScope.launch {
            try {
                val types = api.listUserListTypes()
                val cats = try { api.listCategories().filter { it.parent_id == null } } catch (_: Throwable) { emptyList() }
                _state.value = _state.value.copy(customListTypes = types, listTypePresets = cats)
            } catch (_: Throwable) { /* non-fatal */ }
        }
    }

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

    fun toggleViewMode() {
        val cur = _state.value.viewMode
        _state.value = _state.value.copy(
            viewMode = if (cur == ShoppingViewMode.LIST) ShoppingViewMode.GRID else ShoppingViewMode.LIST,
        )
    }

    fun dismissAddDialog() {
        _state.value = _state.value.copy(showAddDialog = false, addDialogPreFillName = "", addDialogPreFillBrand = "", addDialogPreFillNotes = "", addDialogPreFillCategorySlug = "", addDialogBarcodeNotFound = false)
    }

    fun setListType(type: String) {
        if (_state.value.listType == type) return
        _state.value = _state.value.copy(listType = type, items = emptyList())
        load(isRefresh = false)
    }

    fun loadAllItems() {
        if (_state.value.allItemsLoading) return
        _state.value = _state.value.copy(allItemsLoading = true)
        val allTypes = _state.value.customListTypes.map { it.slug }
        viewModelScope.launch {
            try {
                val results = allTypes.map { type ->
                    async { shoppingRepo.feed(type) }
                }.awaitAll().flatten()
                val countByType = _state.value.customListTypes.associate { lt ->
                    lt.slug to results.count { it.list_type == lt.slug }
                }
                _state.value = _state.value.copy(allItems = results, allItemsLoading = false, countByType = countByType)
            } catch (_: Throwable) {
                _state.value = _state.value.copy(allItemsLoading = false)
            }
        }
    }

    fun openListTypeWizard() {
        _state.value = _state.value.copy(listTypeWizardStep = ListTypeWizardStep.PICK_PRESET, listTypePreset = null, listTypeName = "")
    }
    fun closeListTypeWizard() {
        _state.value = _state.value.copy(listTypeWizardStep = ListTypeWizardStep.CLOSED)
    }
    fun backListTypeWizard() {
        _state.value = _state.value.copy(listTypeWizardStep = ListTypeWizardStep.PICK_PRESET, listTypePreset = null)
    }
    fun pickListTypePreset(cat: CategoryDto?) {
        _state.value = _state.value.copy(listTypePreset = cat, listTypeWizardStep = ListTypeWizardStep.CONFIRM, listTypeName = cat?.name ?: "")
    }
    fun setListTypeName(v: String) {
        _state.value = _state.value.copy(listTypeName = v)
    }

    fun createCustomType(onSuccess: (String) -> Unit) {
        val s = _state.value
        val name = s.listTypeName.trim()
        if (name.isEmpty()) return
        viewModelScope.launch {
            try {
                val result = api.createPair(PairCreateRequest(label = name, category_slug = s.listTypePreset?.slug))
                _state.value = _state.value.copy(
                    customListTypes = _state.value.customListTypes + result.list_type,
                    listTypeWizardStep = ListTypeWizardStep.CLOSED,
                )
                onSuccess(result.list_type.slug)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message, listTypeWizardStep = ListTypeWizardStep.CLOSED)
            }
        }
    }

    fun deleteCustomType(typeId: String) {
        viewModelScope.launch {
            try {
                api.deleteUserListType(typeId)
                val removed = _state.value.customListTypes.find { it.id == typeId }
                _state.value = _state.value.copy(
                    customListTypes = _state.value.customListTypes.filter { it.id != typeId },
                )
                if (removed != null && _state.value.listType == removed.slug) {
                    setListType("")
                }
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    /** Returns the ID of the implied collection for [listType], using the linked collection from the paired list type. */
    private suspend fun resolveImpliedCollection(
        listType: String,
        collections: List<CollectionDto>,
    ): String? {
        if (listType.isEmpty()) return collections.firstOrNull()?.id
        val matched = _state.value.customListTypes.find { it.slug == listType }
        return matched?.linked_collection_id ?: collections.firstOrNull()?.id
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
     *  Optimistically removes from the visible list; on failure, restores it and shows an error.
     *  If offline, the repository queues the mutation — no rollback, no error banner. */
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
            } catch (t: IOException) {
                // The repository already queued the mutation; keep the optimistic removal.
                _state.value = _state.value.copy(updating = _state.value.updating - entryId)
            } catch (t: Throwable) {
                // Real error (auth failure, server rejection, etc.): rollback.
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
        _state.value = _state.value.copy(updating = _state.value.updating + entryId)
        viewModelScope.launch {
            try {
                if (entryId.startsWith("item:")) {
                    // Depleted-item virtual entry: clearing the depleted flag on the
                    // underlying Item removes it from the synthetic feed.
                    itemsRepo.update(entryId.removePrefix("item:"), depleted = false)
                } else {
                    shoppingRepo.deleteItem(entryId)
                }
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

    // Auto-refresh whenever the screen returns to the foreground so items added
    // from other surfaces (e.g. Collections → Add to shopping list) appear without
    // requiring a manual pull-to-refresh.
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) viewModel.refresh()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

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

    // ML Kit barcode decoder for the photo-as-barcode picker. Mirrors the
    // implementation in CollectionsTabsScreen so both surfaces feel the same.
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
    DisposableEffect(Unit) { onDispose { imageScanner.close() } }
    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        try {
            val image = InputImage.fromFilePath(context, uri)
            imageScanner.process(image)
                .addOnSuccessListener { results ->
                    val code = results.firstOrNull { !it.rawValue.isNullOrBlank() }?.rawValue
                    if (!code.isNullOrBlank()) viewModel.onBarcode(code)
                    else viewModel.showAddDialog()
                }
                .addOnFailureListener { viewModel.showAddDialog() }
        } catch (_: Throwable) {
            viewModel.showAddDialog()
        }
    }

    val pagerState = rememberPagerState(pageCount = { 1 + ui.customListTypes.size })

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
                    IconButton(onClick = viewModel::toggleViewMode) {
                        Icon(
                            if (ui.viewMode == ShoppingViewMode.LIST) Icons.Default.GridView
                            else Icons.AutoMirrored.Filled.ViewList,
                            contentDescription = stringResource(
                                if (ui.viewMode == ShoppingViewMode.LIST) R.string.cd_grid_view
                                else R.string.cd_list_view,
                            ),
                        )
                    }
                    IconButton(onClick = onNavigateToScanner) {
                        Icon(
                            Icons.Default.QrCodeScanner,
                            contentDescription = stringResource(R.string.cd_scan_barcode),
                        )
                    }
                    IconButton(onClick = { imagePicker.launch("image/*") }) {
                        Icon(
                            Icons.Default.Image,
                            contentDescription = stringResource(R.string.cd_scan_barcode_image),
                        )
                    }
                    IconButton(onClick = {
                        if (pagerState.currentPage == 0) viewModel.openListTypeWizard()
                        else viewModel.showAddDialog()
                    }) {
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
        // Sync pager → ViewModel when user swipes
        LaunchedEffect(pagerState.currentPage, pagerState.isScrollInProgress) {
            if (!pagerState.isScrollInProgress) {
                when (val page = pagerState.currentPage) {
                    0 -> viewModel.loadAllItems()
                    else -> {
                        val ci = page - 1
                        if (ci < ui.customListTypes.size) viewModel.setListType(ui.customListTypes[ci].slug)
                    }
                }
            }
        }
        // Sync ViewModel → pager when tab is tapped
        LaunchedEffect(ui.listType) {
            val ci = ui.customListTypes.indexOfFirst { it.slug == ui.listType }
            val targetPage = if (ci >= 0) ci + 1 else 0
            if (pagerState.currentPage != targetPage) {
                pagerState.animateScrollToPage(targetPage)
            }
        }
        Column(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            // Offline banner
            if (!ui.isOnline) {
                Surface(
                    color = MaterialTheme.colorScheme.secondaryContainer,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        text = stringResource(R.string.offline_banner),
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                    )
                }
            }
            // List type tabs
            ScrollableTabRow(
                selectedTabIndex = pagerState.currentPage,
                edgePadding = 0.dp,
            ) {
            Tab(
                selected = pagerState.currentPage == 0,
                onClick = {
                    viewModel.loadAllItems()
                    coroutineScope.launch { pagerState.animateScrollToPage(0) }
                },
                text = { Text(stringResource(R.string.tab_all)) },
            )
            ui.customListTypes.forEachIndexed { index, customType ->
                Tab(
                    selected = pagerState.currentPage == 1 + index,
                    onClick = {
                        viewModel.setListType(customType.slug)
                        coroutineScope.launch { pagerState.animateScrollToPage(1 + index) }
                    },
                    text = { Text(customType.label) },
                )
            }
            }
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.weight(1f),
            beyondViewportPageCount = 0,
        ) { page ->
        PullToRefreshBox(
                isRefreshing = if (page == 0) ui.allItemsLoading else ui.refreshing,
                onRefresh = { if (page == 0) viewModel.loadAllItems() else viewModel.pullRefresh() },
                modifier = Modifier.fillMaxSize(),
            ) {
                if (page == 0) {
                    // Home page: card grid of list types
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        items(ui.customListTypes, key = { it.id }) { lt ->
                            ListTypeCard(
                                listType = lt,
                                count = ui.countByType[lt.slug] ?: 0,
                                onClick = {
                                    viewModel.setListType(lt.slug)
                                    val idx = ui.customListTypes.indexOfFirst { it.slug == lt.slug }
                                    if (idx >= 0) coroutineScope.launch { pagerState.animateScrollToPage(idx + 1) }
                                },
                            )
                        }
                    }
                } else {
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
                        if (ui.viewMode == ShoppingViewMode.GRID) {
                            LazyVerticalGrid(
                                columns = GridCells.Fixed(2),
                                modifier = Modifier.fillMaxSize(),
                                contentPadding = PaddingValues(8.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                if (aisleGroups != null) {
                                    aisleGroups.forEach { group ->
                                        item(key = "header-${group.name}", span = { GridItemSpan(maxLineSpan) }) {
                                            AisleHeader(group.name)
                                        }
                                        items(group.items, key = { it.id }) { entry ->
                                            ShoppingEntryCard(
                                                entry = entry,
                                                isUpdating = entry.id in ui.updating,
                                                onCheck = { viewModel.checkItem(entry.id) },
                                                onDelete = { viewModel.deleteItem(entry.id) },
                                                onEdit = { viewModel.startEdit(entry) },
                                            )
                                        }
                                    }
                                } else {
                                    items(ui.items, key = { it.id }) { entry ->
                                        ShoppingEntryCard(
                                            entry = entry,
                                            isUpdating = entry.id in ui.updating,
                                            onCheck = { viewModel.checkItem(entry.id) },
                                            onDelete = { viewModel.deleteItem(entry.id) },
                                            onEdit = { viewModel.startEdit(entry) },
                                        )
                                    }
                                }
                            }
                        } else LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(vertical = 8.dp),
                        ) {
                            if (aisleGroups != null) {
                                aisleGroups.forEach { group ->
                                    item(key = "header-${group.name}") {
                                        AisleHeader(group.name)
                                    }
                                    items(group.items, key = { it.id }) { entry ->
                                        ShoppingEntryRow(
                                            entry = entry,
                                            collectionName = ui.collections[entry.collection_id]?.name ?: entry.collection_id,
                                            isUpdating = entry.id in ui.updating,
                                            onCheck = { viewModel.checkItem(entry.id) },
                                            onDelete = { viewModel.deleteItem(entry.id) },
                                            onEdit = { viewModel.startEdit(entry) },
                                        )
                                        HorizontalDivider()
                                    }
                                }
                            } else {
                                items(ui.items, key = { it.id }) { entry ->
                                    ShoppingEntryRow(
                                        entry = entry,
                                        collectionName = ui.collections[entry.collection_id]?.name ?: entry.collection_id,
                                        isUpdating = entry.id in ui.updating,
                                        onCheck = { viewModel.checkItem(entry.id) },
                                        onDelete = { viewModel.deleteItem(entry.id) },
                                        onEdit = { viewModel.startEdit(entry) },
                                    )
                                    HorizontalDivider()
                                }
                            }
                            // The legacy "Checked" section is gone: tapping the check now syncs
                            // straight to the server (web's "Mark purchased") and removes the row.
                        }
                    }
                }
                } // end else (non-All pages)
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

    if (ui.listTypeWizardStep == ListTypeWizardStep.PICK_PRESET) {
        AlertDialog(
            onDismissRequest = { viewModel.closeListTypeWizard() },
            title = { Text(stringResource(R.string.what_are_you_collecting)) },
            text = {
                val sorted = ui.listTypePresets.sortedBy { it.name }
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.heightIn(max = 320.dp),
                ) {
                    items(sorted, key = { it.id }) { cat ->
                        OutlinedButton(
                            onClick = { viewModel.pickListTypePreset(cat) },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text(cat.name) }
                    }
                    item {
                        OutlinedButton(
                            onClick = { viewModel.pickListTypePreset(null) },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text(stringResource(R.string.custom)) }
                    }
                }
            },
            confirmButton = {},
            dismissButton = { TextButton(onClick = { viewModel.closeListTypeWizard() }) { Text(stringResource(R.string.cancel)) } },
        )
    }
    if (ui.listTypeWizardStep == ListTypeWizardStep.CONFIRM) {
        AlertDialog(
            onDismissRequest = { viewModel.closeListTypeWizard() },
            title = { Text(stringResource(R.string.create_list_type_title)) },
            text = {
                OutlinedTextField(
                    value = ui.listTypeName,
                    onValueChange = { viewModel.setListTypeName(it) },
                    label = { Text(stringResource(R.string.create_list_type_hint)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            },
            confirmButton = {
                TextButton(
                    onClick = { viewModel.createCustomType { slug -> viewModel.setListType(slug) } },
                    enabled = ui.listTypeName.isNotBlank(),
                ) { Text(stringResource(R.string.create)) }
            },
            dismissButton = { TextButton(onClick = { viewModel.backListTypeWizard() }) { Text(stringResource(R.string.cd_back)) } },
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
private fun ListTypeCard(
    listType: UserListTypeDto,
    count: Int,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(listType.label, style = MaterialTheme.typography.titleSmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text("$count items", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
private fun NewListTypeCard(onClick: () -> Unit) {
    OutlinedCard(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Icon(Icons.Default.Add, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text(stringResource(R.string.new_list), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
            }
        }
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
private fun ShoppingEntryRow(
    entry: ShoppingFeedEntryDto,
    collectionName: String,
    isUpdating: Boolean,
    onCheck: () -> Unit,
    onDelete: () -> Unit,
    onEdit: () -> Unit,
) {
    val isAdHoc = !entry.id.startsWith("item:")
    val brand = entry.brand?.takeIf { it.isNotBlank() }
    val category = entry.category_slug?.takeIf { !it.isNullOrBlank() }?.split(".")?.last()
    val secondaryParts = buildList {
        brand?.let { add(it) }
        category?.let { add(it) }
        if (!isAdHoc) add(collectionName)
    }
    val supporting: (@Composable () -> Unit)? = if (secondaryParts.isNotEmpty()) {
        { Text(secondaryParts.joinToString(" \u00b7 "), maxLines = 1) }
    } else null
    // Tap row -> edit (no-op for depleted-link entries; their VM startEdit guards on prefix).
    ListItem(
        headlineContent = { Text(entry.name) },
        supportingContent = supporting,
        trailingContent = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (entry.quantity > 1) {
                    Text("\u00d7${entry.quantity}", style = MaterialTheme.typography.bodyMedium)
                    Spacer(Modifier.width(4.dp))
                }
                IconButton(onClick = onDelete, enabled = !isUpdating) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = stringResource(R.string.remove),
                        tint = MaterialTheme.colorScheme.error,
                    )
                }
                IconButton(onClick = onCheck, enabled = !isUpdating) {
                    if (isUpdating) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    } else {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = stringResource(R.string.got_it),
                            tint = MaterialTheme.colorScheme.primary,
                        )
                    }
                }
            }
        },
        modifier = Modifier.clickable(onClick = onEdit),
    )
}

@Composable
private fun ShoppingEntryCard(
    entry: ShoppingFeedEntryDto,
    isUpdating: Boolean,
    onCheck: () -> Unit,
    onDelete: () -> Unit,
    onEdit: () -> Unit,
) {
    val brand = entry.brand?.takeIf { it.isNotBlank() }
    val category = entry.category_slug?.takeIf { it.isNotBlank() }?.substringAfterLast('.')
    val secondaryParts = buildList {
        brand?.let { add(it) }
        category?.let { add(it) }
    }
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onEdit),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(Modifier.padding(8.dp)) {
            if (secondaryParts.isNotEmpty()) {
                Text(
                    secondaryParts.joinToString(" \u00b7 "),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Text(
                entry.name,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            if (entry.quantity > 1) {
                Text(
                    "\u00d7${entry.quantity}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                IconButton(onClick = onEdit) {
                    Icon(Icons.Default.Edit, contentDescription = stringResource(R.string.edit), tint = MaterialTheme.colorScheme.primary)
                }
                IconButton(onClick = onDelete, enabled = !isUpdating) {
                    Icon(Icons.Default.Delete, contentDescription = stringResource(R.string.remove), tint = MaterialTheme.colorScheme.error)
                }
                IconButton(onClick = onCheck, enabled = !isUpdating) {
                    if (isUpdating) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.primary)
                    } else {
                        Icon(Icons.Default.Check, contentDescription = stringResource(R.string.got_it), tint = MaterialTheme.colorScheme.primary)
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

