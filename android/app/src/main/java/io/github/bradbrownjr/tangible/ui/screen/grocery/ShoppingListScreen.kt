package io.github.bradbrownjr.tangible.ui.screen.grocery

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
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
import io.github.bradbrownjr.tangible.data.remote.BarcodeLookupRequest
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingAisleDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingFeedEntryDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingStoreDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ShoppingRepository
import io.github.bradbrownjr.tangible.R
import javax.inject.Inject

private val LIST_TYPES = listOf("groceries", "hardware", "home_goods", "wish_list")

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
                _state.value = _state.value.copy(
                    items = items,
                    collections = collections.associateBy { it.id },
                    stores = stores,
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
        _state.value = _state.value.copy(showAddDialog = false, addDialogPreFillName = "")
    }

    fun setListType(type: String) {
        if (_state.value.listType == type) return
        _state.value = _state.value.copy(listType = type, items = emptyList())
        load(isRefresh = false)
    }

    fun onBarcode(barcode: String) {
        viewModelScope.launch {
            try {
                val response = api.barcodeLookup(BarcodeLookupRequest(barcode))
                val name = response.candidates.firstOrNull()?.title.orEmpty()
                _state.value = _state.value.copy(showAddDialog = true, addDialogPreFillName = name)
            } catch (_: Throwable) {
                _state.value = _state.value.copy(showAddDialog = true, addDialogPreFillName = "")
            }
        }
    }

    fun addItem(collectionId: String, name: String, quantity: Int, categorySlug: String?) {
        _state.value = _state.value.copy(showAddDialog = false)
        viewModelScope.launch {
            try {
                shoppingRepo.addItem(
                    collectionId = collectionId,
                    name = name,
                    quantity = quantity,
                    categorySlug = categorySlug?.takeIf { it.isNotBlank() },
                )
                load(isRefresh = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun markPurchased(entryId: String) {
        _state.value = _state.value.copy(updating = _state.value.updating + entryId)
        viewModelScope.launch {
            try {
                if (entryId.startsWith("item:")) {
                    // Virtual depleted-item entry: remove from list only (no grocery_item row).
                    _state.value = _state.value.copy(
                        items = _state.value.items.filter { it.id != entryId },
                        updating = _state.value.updating - entryId,
                    )
                } else {
                    shoppingRepo.purchaseItem(entryId)
                    _state.value = _state.value.copy(
                        items = _state.value.items.filter { it.id != entryId },
                        updating = _state.value.updating - entryId,
                    )
                }
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    error = t.message,
                    updating = _state.value.updating - entryId,
                )
            }
        }
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
    onNavigateToCollection: (collectionId: String) -> Unit,
    onManageStores: () -> Unit,
    onNavigateToScanner: () -> Unit = {},
    scannedBarcode: String? = null,
) {
    val ui by viewModel.state.collectAsState()
    val selectedStore = ui.stores.find { it.id == ui.selectedStoreId }
    val otherLabel = stringResource(R.string.other)
    val aisleGroups = if (selectedStore != null) groupByAisle(ui.items, selectedStore.aisles, otherLabel) else null

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
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                    }
                },
                actions = {
                    IconButton(onClick = onNavigateToScanner) {
                        Icon(Icons.Default.QrCodeScanner, contentDescription = stringResource(R.string.cd_scan_barcode))
                    }
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
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { viewModel.showAddDialog() }) {
                Icon(Icons.Default.Add, contentDescription = stringResource(R.string.cd_add_grocery_item))
            }
        },
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {
            // List type tabs
            ScrollableTabRow(
                selectedTabIndex = LIST_TYPES.indexOf(ui.listType).coerceAtLeast(0),
                edgePadding = 0.dp,
            ) {
                val tabLabels = mapOf(
                    "groceries"  to stringResource(R.string.list_type_groceries),
                    "hardware"   to stringResource(R.string.list_type_hardware),
                    "home_goods" to stringResource(R.string.list_type_home_goods),
                    "wish_list"  to stringResource(R.string.list_type_wish_list),
                )
                LIST_TYPES.forEach { type ->
                    Tab(
                        selected = ui.listType == type,
                        onClick = { viewModel.setListType(type) },
                        text = { Text(tabLabels[type] ?: type) },
                    )
                }
            }
        Box(modifier = Modifier.weight(1f)) {
            PullToRefreshBox(
                isRefreshing = ui.refreshing,
                onRefresh = { viewModel.pullRefresh() },
                modifier = Modifier.fillMaxSize(),
            ) {
                when {
                    ui.loading -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                    }
                    ui.items.isEmpty() && !ui.loading -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
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
                                            onMarkPurchased = { viewModel.markPurchased(entry.id) },
                                            onDelete = { viewModel.deleteItem(entry.id) },
                                            onNavigateToCollection = { onNavigateToCollection(entry.collection_id) },
                                        )
                                    }
                                }
                            } else {
                                items(ui.items, key = { it.id }) { entry ->
                                    ShoppingEntryCard(
                                        entry = entry,
                                        collectionName = ui.collections[entry.collection_id]?.name ?: entry.collection_id,
                                        isUpdating = entry.id in ui.updating,
                                        onMarkPurchased = { viewModel.markPurchased(entry.id) },
                                        onDelete = { viewModel.deleteItem(entry.id) },
                                        onNavigateToCollection = { onNavigateToCollection(entry.collection_id) },
                                    )
                                }
                            }
                        }
                    }
                }
                if (ui.error != null) {
                    Box(
                        modifier = Modifier.fillMaxSize().padding(16.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(ui.error!!, color = MaterialTheme.colorScheme.error)
                    }
                }
            }

            if (ui.showStoreSelector) {
                StoreSelectorDialog(
                    stores = ui.stores,
                    selectedStoreId = ui.selectedStoreId,
                    onSelect = { viewModel.selectStore(it) },
                    onManageStores = { viewModel.dismissStoreSelector(); onManageStores() },
                    onDismiss = { viewModel.dismissStoreSelector() },
                )
            }
        } // end inner Box
        } // end Column
    }

    if (ui.showAddDialog) {
        AddShoppingItemDialog(
            collections = ui.collections.values.toList(),
            listType = ui.listType,
            preFillName = ui.addDialogPreFillName,
            onDismiss = { viewModel.dismissAddDialog() },
            onAdd = { collId, itemName, qty, catSlug ->
                viewModel.addItem(collId, itemName, qty, catSlug)
            },
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
    onMarkPurchased: () -> Unit,
    onDelete: () -> Unit,
    onNavigateToCollection: () -> Unit,
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
                modifier = Modifier.weight(1f).padding(end = 8.dp).clickable { onNavigateToCollection() },
            ) {
                Text(
                    text = if (entry.quantity > 1) "${entry.name} ×${entry.quantity}" else entry.name,
                    style = MaterialTheme.typography.bodyLarge,
                    maxLines = 1,
                )
                Text(
                    text = collectionName,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
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
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
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
                    onClick = onMarkPurchased,
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
    collections: List<CollectionDto>,
    listType: String = "groceries",
    preFillName: String = "",
    onDismiss: () -> Unit,
    onAdd: (collectionId: String, name: String, quantity: Int, categorySlug: String?) -> Unit,
) {
    var name by remember { mutableStateOf(preFillName) }
    var quantityText by remember { mutableStateOf("1") }
    var categorySlug by remember { mutableStateOf("") }
    var selectedCollectionId by remember { mutableStateOf(collections.firstOrNull()?.id ?: "") }
    var collectionMenuExpanded by remember { mutableStateOf(false) }
    // Show category picker only for hardware and home_goods — grocery implies pantry, wish list uses priority.
    val showCategory = listType == "hardware" || listType == "home_goods"
    val categoryPresets = presetsForType(listType)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.add_grocery_item)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text(stringResource(R.string.grocery_item_name_required)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Box {
                    OutlinedTextField(
                        value = collections.find { it.id == selectedCollectionId }?.name ?: "",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text(stringResource(R.string.collection_required)) },
                        modifier = Modifier.fillMaxWidth().clickable { collectionMenuExpanded = true },
                    )
                    DropdownMenu(
                        expanded = collectionMenuExpanded,
                        onDismissRequest = { collectionMenuExpanded = false },
                    ) {
                        collections.forEach { col ->
                            DropdownMenuItem(
                                text = { Text(col.name) },
                                onClick = { selectedCollectionId = col.id; collectionMenuExpanded = false },
                            )
                        }
                    }
                }
                OutlinedTextField(
                    value = quantityText,
                    onValueChange = { quantityText = it.filter { c -> c.isDigit() } },
                    label = { Text(stringResource(R.string.quantity)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
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
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank() && selectedCollectionId.isNotBlank()) {
                        onAdd(selectedCollectionId, name.trim(), quantityText.toIntOrNull() ?: 1, categorySlug.takeIf { it.isNotBlank() })
                    }
                },
                enabled = name.isNotBlank() && selectedCollectionId.isNotBlank(),
            ) { Text(stringResource(R.string.add)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}


