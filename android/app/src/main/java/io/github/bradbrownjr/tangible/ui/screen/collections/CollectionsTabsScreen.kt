package io.github.bradbrownjr.tangible.ui.screen.collections

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ViewList
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.BarcodeLookupRequest
import io.github.bradbrownjr.tangible.data.remote.CategoryDto
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.ItemDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.repo.CategoryRepository
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ItemRepository
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import androidx.compose.foundation.combinedClickable
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Task
import io.github.bradbrownjr.tangible.data.repo.ShoppingRepository

enum class ViewMode { LIST, GRID }

/**
 * Lightweight "Collections as swipeable tabs" home view.
 *
 * Each collection is a tab; the page beneath shows that collection's items as
 * a simple list or grid. Per-tab toolbar exposes edit/delete collection,
 * grid/list toggle, scan barcode (camera + image picker), and add item.
 * Tapping any item opens [io.github.bradbrownjr.tangible.ui.screen.item.ItemDetailScreen].
 */

data class CollectionsTabsUi(
    val collections: List<CollectionDto> = emptyList(),
    val itemsByCollection: Map<String, List<ItemDto>> = emptyMap(),
    val loadingByCollection: Map<String, Boolean> = emptyMap(),
    val searchByCollection: Map<String, String> = emptyMap(),
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    val wizardStep: WizardStep = WizardStep.CLOSED,
    val presets: List<CategoryDto> = emptyList(),
    val selectedPreset: CategoryDto? = null,
    val newName: String = "",
    val newDescription: String = "",
    val pendingDeleteItem: ItemDto? = null,
    val pendingShoppingItem: ItemDto? = null,
    // Per-tab actions
    val editingCollection: CollectionDto? = null,
    val editName: String = "",
    val editDescription: String = "",
    val pendingDeleteCollection: CollectionDto? = null,
    val createItemForCollection: CollectionDto? = null,
    val newItemTitle: String = "",
    val viewMode: ViewMode = ViewMode.LIST,
)

@HiltViewModel
class CollectionsTabsViewModel @Inject constructor(
    private val collectionsRepo: CollectionRepository,
    private val itemsRepo: ItemRepository,
    private val categoryRepo: CategoryRepository,
    private val shoppingRepo: ShoppingRepository,
    private val api: TangibleApi,
) : ViewModel() {
    private val _state = MutableStateFlow(CollectionsTabsUi())
    val state: StateFlow<CollectionsTabsUi> = _state.asStateFlow()

    init { refresh() }

    fun refresh() = load(isRefresh = false)
    fun pullRefresh() = load(isRefresh = true)

    private fun load(isRefresh: Boolean) {
        _state.value = _state.value.copy(
            loading = !isRefresh && _state.value.collections.isEmpty(),
            refreshing = isRefresh,
            error = null,
        )
        viewModelScope.launch {
            try {
                val collections = collectionsRepo.list()
                val cats = try { categoryRepo.load() } catch (_: Throwable) { emptyList() }
                _state.value = _state.value.copy(
                    collections = collections,
                    presets = cats.filter { it.parent_id == null },
                    loading = false,
                    refreshing = false,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    loading = false,
                    refreshing = false,
                    error = t.message,
                )
            }
        }
    }

    fun loadItems(collectionId: String, force: Boolean = false) {
        val cur = _state.value
        if (!force && cur.itemsByCollection.containsKey(collectionId)) return
        if (cur.loadingByCollection[collectionId] == true) return
        _state.value = cur.copy(loadingByCollection = cur.loadingByCollection + (collectionId to true))
        viewModelScope.launch {
            try {
                val items = itemsRepo.list(collectionId = collectionId)
                val s = _state.value
                _state.value = s.copy(
                    itemsByCollection = s.itemsByCollection + (collectionId to items),
                    loadingByCollection = s.loadingByCollection - collectionId,
                )
            } catch (t: Throwable) {
                val s = _state.value
                _state.value = s.copy(
                    loadingByCollection = s.loadingByCollection - collectionId,
                    error = t.message,
                )
            }
        }
    }

    fun openWizard() {
        _state.value = _state.value.copy(
            wizardStep = WizardStep.PICK_PRESET,
            newName = "",
            newDescription = "",
            selectedPreset = null,
        )
    }
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
                collectionsRepo.create(
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

    fun setSearch(collectionId: String, query: String) {
        _state.value = _state.value.copy(
            searchByCollection = _state.value.searchByCollection + (collectionId to query),
        )
    }

    fun confirmDelete(item: ItemDto) {
        _state.value = _state.value.copy(pendingDeleteItem = item)
    }

    fun cancelDelete() {
        _state.value = _state.value.copy(pendingDeleteItem = null)
    }

    fun executeDelete(item: ItemDto) {
        _state.value = _state.value.copy(pendingDeleteItem = null)
        viewModelScope.launch {
            try {
                itemsRepo.delete(item.id)
                loadItems(item.collection_id, force = true)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun confirmAddToList(item: ItemDto) {
        _state.value = _state.value.copy(pendingShoppingItem = item)
    }

    fun cancelAddToList() {
        _state.value = _state.value.copy(pendingShoppingItem = null)
    }

    fun executeAddToList(item: ItemDto) {
        _state.value = _state.value.copy(pendingShoppingItem = null)
        val brand = item.attrs["brand"] as? String
        viewModelScope.launch {
            try {
                shoppingRepo.addItem(
                    collectionId = item.collection_id,
                    name = item.title,
                    quantity = item.quantity,
                    brand = brand,
                    notes = item.notes,
                    categorySlug = item.category_slug,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun executeMoveToList(item: ItemDto) {
        _state.value = _state.value.copy(pendingShoppingItem = null)
        val brand = item.attrs["brand"] as? String
        viewModelScope.launch {
            try {
                shoppingRepo.addItem(
                    collectionId = item.collection_id,
                    name = item.title,
                    quantity = item.quantity,
                    brand = brand,
                    notes = item.notes,
                    categorySlug = item.category_slug,
                )
                // Mark as depleted (restockable) rather than deleting outright.
                itemsRepo.update(item.id, depleted = true)
                loadItems(item.collection_id, force = true)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    // ---- Edit collection ----
    fun startEditCollection(coll: CollectionDto) {
        _state.value = _state.value.copy(
            editingCollection = coll,
            editName = coll.name,
            editDescription = coll.description.orEmpty(),
        )
    }
    fun setEditName(v: String) { _state.value = _state.value.copy(editName = v) }
    fun setEditDescription(v: String) { _state.value = _state.value.copy(editDescription = v) }
    fun cancelEditCollection() { _state.value = _state.value.copy(editingCollection = null) }
    fun saveEditCollection() {
        val coll = _state.value.editingCollection ?: return
        val name = _state.value.editName.trim()
        if (name.isEmpty()) return
        val desc = _state.value.editDescription.trim().takeIf { it.isNotEmpty() }
        viewModelScope.launch {
            try {
                collectionsRepo.update(
                    coll.id,
                    io.github.bradbrownjr.tangible.data.remote.CollectionPatch(
                        name = name,
                        description = desc,
                    ),
                )
                _state.value = _state.value.copy(editingCollection = null)
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    // ---- Delete collection ----
    fun confirmDeleteCollection(coll: CollectionDto) {
        _state.value = _state.value.copy(pendingDeleteCollection = coll)
    }
    fun cancelDeleteCollection() {
        _state.value = _state.value.copy(pendingDeleteCollection = null)
    }
    fun executeDeleteCollection() {
        val coll = _state.value.pendingDeleteCollection ?: return
        _state.value = _state.value.copy(pendingDeleteCollection = null)
        viewModelScope.launch {
            try {
                collectionsRepo.delete(coll.id)
                refresh()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    // ---- Create item ----
    fun showCreateItem(coll: CollectionDto) {
        _state.value = _state.value.copy(createItemForCollection = coll, newItemTitle = "")
    }
    fun dismissCreateItem() {
        _state.value = _state.value.copy(createItemForCollection = null, newItemTitle = "")
    }
    fun setNewItemTitle(v: String) { _state.value = _state.value.copy(newItemTitle = v) }
    fun createItem() {
        val coll = _state.value.createItemForCollection ?: return
        val title = _state.value.newItemTitle.trim()
        if (title.isEmpty()) return
        // Fall back to the collection's default category, then to the first preset, then to "general".
        val slug = coll.default_category_slug
            ?: _state.value.presets.firstOrNull()?.slug
            ?: "general"
        viewModelScope.launch {
            try {
                itemsRepo.create(coll.id, slug, title)
                _state.value = _state.value.copy(createItemForCollection = null, newItemTitle = "")
                loadItems(coll.id, force = true)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    // ---- View mode ----
    fun toggleViewMode() {
        val next = if (_state.value.viewMode == ViewMode.LIST) ViewMode.GRID else ViewMode.LIST
        _state.value = _state.value.copy(viewMode = next)
    }

    // ---- Image-decoded barcode ----
    /** Looks up [code] and opens the create-item dialog for [coll], pre-filling the title. */
    fun onBarcodeForCollection(coll: CollectionDto, code: String) {
        viewModelScope.launch {
            val title = try {
                api.barcodeLookup(BarcodeLookupRequest(code)).candidates.firstOrNull()?.title
            } catch (_: Throwable) { null }
            _state.value = _state.value.copy(
                createItemForCollection = coll,
                newItemTitle = title.orEmpty(),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun CollectionsTabsScreen(
    onOpenItem: (String) -> Unit = {},
    onItemEdit: (String) -> Unit = {},
    onNavigateToScanner: () -> Unit = {},
    onNavigateToChores: (collectionId: String, collectionName: String) -> Unit = { _, _ -> },
    onSwipeLeft: () -> Unit = {},
    onSwipeRight: () -> Unit = {},
    vm: CollectionsTabsViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    val scope = rememberCoroutineScope()
    val dragThresholdPx = with(LocalDensity.current) { 80.dp.toPx() }

    // Empty / loading / error path: no tabs to render. Fall back to the same
    // FAB + wizard as the legacy list screen so users can still create.
    if (s.collections.isEmpty()) {
        Scaffold(
            topBar = {
                var emptyAccum by remember { mutableFloatStateOf(0f) }
                Box(
                    Modifier.pointerInput(Unit) {
                        detectHorizontalDragGestures(
                            onDragEnd = { emptyAccum = 0f },
                            onDragCancel = { emptyAccum = 0f },
                            onHorizontalDrag = { _, amount ->
                                emptyAccum += amount
                                if (emptyAccum < -dragThresholdPx) { emptyAccum = 0f; onSwipeLeft() }
                                else if (emptyAccum > dragThresholdPx) { emptyAccum = 0f; onSwipeRight() }
                            },
                        )
                    }
                ) {
                    TopAppBar(
                        title = { Text(stringResource(R.string.collections)) },
                        actions = {
                            IconButton(onClick = vm::openWizard) {
                                Icon(Icons.Default.Add, contentDescription = stringResource(R.string.cd_new_collection))
                            }
                        },
                    )
                }
            },
        ) { padding ->
            Box(
                Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center,
            ) {
                when {
                    s.loading -> CircularProgressIndicator()
                    s.error != null -> Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text(s.error!!, color = MaterialTheme.colorScheme.error)
                        OutlinedButton(onClick = vm::refresh) { Text(stringResource(R.string.retry)) }
                    }
                    else -> Text(stringResource(R.string.no_collections))
                }
            }
            WizardDialogs(s, vm)
            ConfirmDeleteDialog(s, vm)
            ConfirmAddToListDialog(s, vm)
            EditCollectionDialog(s, vm)
            ConfirmDeleteCollectionDialog(s, vm)
            CreateItemDialog(s, vm)
        }
        return
    }

    val pagerState = rememberPagerState(pageCount = { s.collections.size })
    val currentColl = s.collections.getOrNull(pagerState.currentPage)
    val currentPageLoading = currentColl?.let { s.loadingByCollection[it.id] == true } ?: false

    // ML Kit barcode decoder for the photo-as-barcode picker. Closed in onDispose.
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
        val coll = currentColl ?: return@rememberLauncherForActivityResult
        if (uri == null) return@rememberLauncherForActivityResult
        try {
            val image = InputImage.fromFilePath(context, uri)
            imageScanner.process(image)
                .addOnSuccessListener { results ->
                    val code = results.firstOrNull { !it.rawValue.isNullOrBlank() }?.rawValue
                    if (!code.isNullOrBlank()) vm.onBarcodeForCollection(coll, code)
                    else vm.showCreateItem(coll)
                }
                .addOnFailureListener { vm.showCreateItem(coll) }
        } catch (_: Throwable) {
            vm.showCreateItem(coll)
        }
    }

    // Lazily load items for the current tab.
    LaunchedEffect(pagerState.currentPage, s.collections) {
        s.collections.getOrNull(pagerState.currentPage)?.let { vm.loadItems(it.id) }
    }

    Scaffold(
        topBar = {
            var tabsAccum by remember { mutableFloatStateOf(0f) }
            Box(
                Modifier.pointerInput(Unit) {
                    detectHorizontalDragGestures(
                        onDragEnd = { tabsAccum = 0f },
                        onDragCancel = { tabsAccum = 0f },
                        onHorizontalDrag = { _, amount ->
                            tabsAccum += amount
                            if (tabsAccum < -dragThresholdPx) { tabsAccum = 0f; onSwipeLeft() }
                            else if (tabsAccum > dragThresholdPx) { tabsAccum = 0f; onSwipeRight() }
                        },
                    )
                }
            ) {
                TopAppBar(
                    title = { Text(currentColl?.name ?: stringResource(R.string.collections)) },
                    actions = {
                        currentColl?.let { coll ->
                            if (coll.my_role == "owner" || coll.my_role == "editor") {
                                IconButton(onClick = { vm.startEditCollection(coll) }) {
                                    Icon(
                                        Icons.Default.Edit,
                                        contentDescription = stringResource(R.string.cd_edit_collection),
                                    )
                                }
                            }
                            if (coll.my_role == "owner") {
                                IconButton(onClick = { vm.confirmDeleteCollection(coll) }) {
                                    Icon(
                                        Icons.Default.Delete,
                                        contentDescription = stringResource(R.string.cd_delete_collection),
                                    )
                                }
                            }
                        }
                        IconButton(onClick = vm::toggleViewMode) {
                            Icon(
                                if (s.viewMode == ViewMode.LIST) Icons.Default.GridView
                                else Icons.AutoMirrored.Filled.ViewList,
                                contentDescription = stringResource(
                                    if (s.viewMode == ViewMode.LIST) R.string.cd_grid_view
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
                        currentColl?.let { coll ->
                            IconButton(onClick = { onNavigateToChores(coll.id, coll.name) }) {
                                Icon(
                                    Icons.Default.Task,
                                    contentDescription = stringResource(R.string.cd_chores),
                                )
                            }
                        }
                        if (currentColl != null) {
                            IconButton(onClick = { imagePicker.launch("image/*") }) {
                                Icon(
                                    Icons.Default.Image,
                                    contentDescription = stringResource(R.string.cd_scan_barcode_image),
                                )
                            }
                        }
                        currentColl?.let { coll ->
                            IconButton(onClick = { vm.showCreateItem(coll) }) {
                                Icon(
                                    Icons.Default.Add,
                                    contentDescription = stringResource(R.string.cd_add_item),
                                )
                            }
                        } ?: IconButton(onClick = vm::openWizard) {
                            Icon(Icons.Default.Add, contentDescription = stringResource(R.string.cd_new_collection))
                        }
                    },
                )
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            ScrollableTabRow(
                selectedTabIndex = pagerState.currentPage.coerceAtMost(s.collections.size - 1),
                edgePadding = 0.dp,
            ) {
                s.collections.forEachIndexed { index, c ->
                    Tab(
                        selected = pagerState.currentPage == index,
                        onClick = { scope.launch { pagerState.animateScrollToPage(index) } },
                        text = { Text(c.name) },
                    )
                }
            }
            // PullToRefreshBox wraps the pager (not the other way around) so that the
            // vertical pull gesture is captured before HorizontalPager can intercept it.
            PullToRefreshBox(
                isRefreshing = s.refreshing || currentPageLoading,
                onRefresh = {
                    vm.pullRefresh()
                    currentColl?.let { vm.loadItems(it.id, force = true) }
                },
                modifier = Modifier.weight(1f),
            ) {
                HorizontalPager(
                    state = pagerState,
                    modifier = Modifier.fillMaxSize(),
                    beyondViewportPageCount = 0,
                ) { page ->
                    val coll = s.collections[page]
                    val items = s.itemsByCollection[coll.id] ?: emptyList()
                    val pageLoading = s.loadingByCollection[coll.id] == true
                    // Always use a LazyColumn (even for empty/loading) so the outer
                    // PullToRefreshBox receives the nested-scroll pull gesture.
                    when {
                        pageLoading && items.isEmpty() ->
                            LazyColumn(Modifier.fillMaxSize()) {
                                item {
                                    Box(Modifier.fillParentMaxSize(), contentAlignment = Alignment.Center) {
                                        CircularProgressIndicator()
                                    }
                                }
                            }
                        items.isEmpty() -> LazyColumn(Modifier.fillMaxSize()) {
                            item {
                                Box(Modifier.fillParentMaxSize(), contentAlignment = Alignment.Center) {
                                    Column(
                                        horizontalAlignment = Alignment.CenterHorizontally,
                                        verticalArrangement = Arrangement.spacedBy(8.dp),
                                    ) {
                                        Text(stringResource(R.string.no_items))
                                        OutlinedButton(onClick = { vm.showCreateItem(coll) }) {
                                            Text(stringResource(R.string.add_item))
                                        }
                                    }
                                }
                            }
                        }
                        else -> {
                            val searchQuery = s.searchByCollection[coll.id].orEmpty()
                            val displayItems = remember(items, searchQuery) {
                                if (searchQuery.isBlank()) items
                                else items.filter { it.title.contains(searchQuery, ignoreCase = true) }
                            }
                            if (s.viewMode == ViewMode.LIST) {
                                LazyColumn(Modifier.fillMaxSize()) {
                                    item(key = "search") {
                                        SearchBar(searchQuery) { vm.setSearch(coll.id, it) }
                                    }
                                    if (displayItems.isEmpty()) {
                                        item(key = "no_results") { NoSearchResults() }
                                    } else {
                                        items(displayItems, key = { it.id }) { item ->
                                            ItemRow(
                                                item = item,
                                                onClick = { onItemEdit(item.id) },
                                                onLongClick = { onOpenItem(item.id) },
                                                onEdit = { onItemEdit(item.id) },
                                                onAddToList = { vm.confirmAddToList(item) },
                                                onDelete = { vm.confirmDelete(item) },
                                            )
                                            HorizontalDivider()
                                        }
                                    }
                                }
                            } else {
                                LazyVerticalGrid(
                                    columns = GridCells.Fixed(2),
                                    modifier = Modifier.fillMaxSize(),
                                    contentPadding = PaddingValues(8.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    item(span = { GridItemSpan(maxLineSpan) }) {
                                        SearchBar(searchQuery) { vm.setSearch(coll.id, it) }
                                    }
                                    if (displayItems.isEmpty()) {
                                        item(span = { GridItemSpan(maxLineSpan) }) { NoSearchResults() }
                                    } else {
                                        gridItems(displayItems, key = { it.id }) { item ->
                                            ItemCard(
                                                item = item,
                                                onClick = { onItemEdit(item.id) },
                                                onEdit = { onItemEdit(item.id) },
                                                onAddToList = { vm.confirmAddToList(item) },
                                                onDelete = { vm.confirmDelete(item) },
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        WizardDialogs(s, vm)
        ConfirmDeleteDialog(s, vm)
        ConfirmAddToListDialog(s, vm)
        EditCollectionDialog(s, vm)
        ConfirmDeleteCollectionDialog(s, vm)
        CreateItemDialog(s, vm)
    }
}

@Composable
private fun SearchBar(query: String, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = query,
        onValueChange = onChange,
        placeholder = { Text(stringResource(R.string.search_items)) },
        singleLine = true,
        trailingIcon = {
            if (query.isNotEmpty()) {
                IconButton(onClick = { onChange("") }) {
                    Icon(Icons.Default.Clear, contentDescription = stringResource(R.string.cd_clear_search))
                }
            }
        },
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp),
    )
}

@Composable
private fun NoSearchResults() {
    Box(
        Modifier.fillMaxWidth().padding(32.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(stringResource(R.string.no_search_results))
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
private fun ItemRow(
    item: ItemDto,
    onClick: () -> Unit,
    onLongClick: () -> Unit = {},
    onEdit: () -> Unit = {},
    onAddToList: () -> Unit = {},
    onDelete: () -> Unit = {},
) {
    val brand = (item.attrs["brand"] as? String)?.takeIf { it.isNotBlank() }
    val category = item.category_slug?.takeIf { it.isNotBlank() }?.substringAfterLast('.')
    val secondaryParts = buildList {
        brand?.let { add(it) }
        category?.let { add(it) }
        item.subtitle?.takeIf { it.isNotBlank() }?.let { add(it) }
            ?: item.notes?.takeIf { it.isNotBlank() }?.let { add(it) }
    }
    val supporting: (@Composable () -> Unit)? = if (secondaryParts.isNotEmpty()) {
        { Text(secondaryParts.joinToString(" \u00b7 "), maxLines = 1) }
    } else null
    ListItem(
        headlineContent = { Text(item.title) },
        supportingContent = supporting,
        trailingContent = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (item.quantity > 1) {
                    Text("\u00D7${item.quantity}", style = MaterialTheme.typography.bodyMedium)
                    Spacer(Modifier.width(4.dp))
                }
                IconButton(onClick = onEdit) {
                    Icon(
                        Icons.Default.Edit,
                        contentDescription = stringResource(R.string.edit),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
                IconButton(onClick = onAddToList) {
                    Icon(
                        Icons.Default.ShoppingCart,
                        contentDescription = stringResource(R.string.cd_add_to_list),
                        tint = MaterialTheme.colorScheme.secondary,
                    )
                }
                IconButton(onClick = onDelete) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = stringResource(R.string.cd_delete),
                        tint = MaterialTheme.colorScheme.error,
                    )
                }
            }
        },
        modifier = Modifier.combinedClickable(
            onClick = onClick,
            onLongClick = onLongClick,
        ),
    )
}

@Composable
private fun WizardDialogs(s: CollectionsTabsUi, vm: CollectionsTabsViewModel) {
    if (s.wizardStep == WizardStep.PICK_PRESET) {
        AlertDialog(
            onDismissRequest = vm::closeWizard,
            title = { Text(stringResource(R.string.what_are_you_collecting)) },
            text = {
                val sorted = s.presets.sortedBy { it.name }
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.heightIn(max = 320.dp),
                ) {
                    items(sorted, key = { it.id }) { cat ->
                        OutlinedButton(
                            onClick = { vm.pickPreset(cat) },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text(cat.name) }
                    }
                    item {
                        OutlinedButton(
                            onClick = { vm.pickPreset(null) },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text(stringResource(R.string.custom)) }
                    }
                }
            },
            confirmButton = {},
            dismissButton = { TextButton(onClick = vm::closeWizard) { Text(stringResource(R.string.cancel)) } },
        )
    }
    if (s.wizardStep == WizardStep.CONFIRM) {
        AlertDialog(
            onDismissRequest = vm::closeWizard,
            title = { Text(stringResource(R.string.new_collection)) },
            text = {
                Column {
                    OutlinedTextField(
                        value = s.newName,
                        onValueChange = vm::setNewName,
                        label = { Text(stringResource(R.string.collection_name)) },
                        singleLine = true,
                    )
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = s.newDescription,
                        onValueChange = vm::setNewDescription,
                        label = { Text(stringResource(R.string.collection_description_optional)) },
                        singleLine = true,
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = vm::create,
                    enabled = s.newName.isNotBlank(),
                ) { Text(stringResource(R.string.create)) }
            },
            dismissButton = { TextButton(onClick = vm::closeWizard) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun ConfirmDeleteDialog(s: CollectionsTabsUi, vm: CollectionsTabsViewModel) {
    val item = s.pendingDeleteItem ?: return
    AlertDialog(
        onDismissRequest = vm::cancelDelete,
        title = { Text(stringResource(R.string.delete)) },
        text = { Text(stringResource(R.string.delete_item_confirm, item.title)) },
        confirmButton = {
            TextButton(onClick = { vm.executeDelete(item) }) {
                Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
            }
        },
        dismissButton = { TextButton(onClick = vm::cancelDelete) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
private fun ConfirmAddToListDialog(s: CollectionsTabsUi, vm: CollectionsTabsViewModel) {
    val item = s.pendingShoppingItem ?: return
    AlertDialog(
        onDismissRequest = vm::cancelAddToList,
        title = { Text(stringResource(R.string.cd_add_to_list)) },
        text = { Text(stringResource(R.string.add_to_list_confirm, item.title)) },
        confirmButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = { vm.executeAddToList(item) }) {
                    Text(stringResource(R.string.copy))
                }
                TextButton(onClick = { vm.executeMoveToList(item) }) {
                    Text(stringResource(R.string.move))
                }
            }
        },
        dismissButton = { TextButton(onClick = vm::cancelAddToList) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
private fun EditCollectionDialog(s: CollectionsTabsUi, vm: CollectionsTabsViewModel) {
    s.editingCollection ?: return
    AlertDialog(
        onDismissRequest = vm::cancelEditCollection,
        title = { Text(stringResource(R.string.edit_collection)) },
        text = {
            Column {
                OutlinedTextField(
                    value = s.editName,
                    onValueChange = vm::setEditName,
                    label = { Text(stringResource(R.string.collection_name)) },
                    singleLine = true,
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = s.editDescription,
                    onValueChange = vm::setEditDescription,
                    label = { Text(stringResource(R.string.collection_description_optional)) },
                    singleLine = true,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = vm::saveEditCollection, enabled = s.editName.isNotBlank()) {
                Text(stringResource(R.string.save))
            }
        },
        dismissButton = { TextButton(onClick = vm::cancelEditCollection) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
private fun ConfirmDeleteCollectionDialog(s: CollectionsTabsUi, vm: CollectionsTabsViewModel) {
    val coll = s.pendingDeleteCollection ?: return
    val itemCount = (s.itemsByCollection[coll.id] ?: emptyList()).size
    AlertDialog(
        onDismissRequest = vm::cancelDeleteCollection,
        title = { Text(stringResource(R.string.cd_delete_collection)) },
        text = {
            Text(
                androidx.compose.ui.res.pluralStringResource(
                    R.plurals.delete_collection_confirm,
                    itemCount,
                    itemCount,
                )
            )
        },
        confirmButton = {
            TextButton(onClick = vm::executeDeleteCollection) {
                Text(stringResource(R.string.delete), color = MaterialTheme.colorScheme.error)
            }
        },
        dismissButton = { TextButton(onClick = vm::cancelDeleteCollection) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
private fun CreateItemDialog(s: CollectionsTabsUi, vm: CollectionsTabsViewModel) {
    s.createItemForCollection ?: return
    AlertDialog(
        onDismissRequest = vm::dismissCreateItem,
        title = { Text(stringResource(R.string.add_item)) },
        text = {
            OutlinedTextField(
                value = s.newItemTitle,
                onValueChange = vm::setNewItemTitle,
                label = { Text(stringResource(R.string.title)) },
                singleLine = true,
            )
        },
        confirmButton = {
            TextButton(onClick = vm::createItem, enabled = s.newItemTitle.isNotBlank()) {
                Text(stringResource(R.string.create))
            }
        },
        dismissButton = { TextButton(onClick = vm::dismissCreateItem) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
private fun ItemCard(
    item: ItemDto,
    onClick: () -> Unit,
    onEdit: () -> Unit,
    onAddToList: () -> Unit,
    onDelete: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(Modifier.padding(8.dp)) {
            val brand = (item.attrs["brand"] as? String)?.takeIf { it.isNotBlank() }
            val category = item.category_slug?.takeIf { it.isNotBlank() }?.substringAfterLast('.')
            val secondaryParts = buildList {
                brand?.let { add(it) }
                category?.let { add(it) }
            }
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
                item.title,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            if (item.quantity > 1) {
                Text(
                    "\u00d7${item.quantity}",
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
                IconButton(onClick = onAddToList) {
                    Icon(Icons.Default.ShoppingCart, contentDescription = stringResource(R.string.cd_add_to_list), tint = MaterialTheme.colorScheme.secondary)
                }
                IconButton(onClick = onDelete) {
                    Icon(Icons.Default.Delete, contentDescription = stringResource(R.string.cd_delete), tint = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}
