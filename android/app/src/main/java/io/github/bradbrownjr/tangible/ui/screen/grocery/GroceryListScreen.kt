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
import androidx.compose.material.icons.filled.Store
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.GroceryAisleDto
import io.github.bradbrownjr.tangible.data.remote.GroceryFeedEntryDto
import io.github.bradbrownjr.tangible.data.remote.GroceryStoreDto
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.GroceryRepository
import javax.inject.Inject

data class GroceryListUi(
    val items: List<GroceryFeedEntryDto> = emptyList(),
    val collections: Map<String, CollectionDto> = emptyMap(),
    val stores: List<GroceryStoreDto> = emptyList(),
    val selectedStoreId: String? = null,
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    val updating: Set<String> = emptySet(),
    val showAddDialog: Boolean = false,
    val showStoreSelector: Boolean = false,
)

@HiltViewModel
class GroceryListViewModel @Inject constructor(
    private val groceryRepo: GroceryRepository,
    private val collectionRepo: CollectionRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(GroceryListUi())
    val state: StateFlow<GroceryListUi> = _state.asStateFlow()

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
                val items = groceryRepo.feed()
                val collections = collectionRepo.list()
                val stores = groceryRepo.listStores()
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
        _state.value = _state.value.copy(showAddDialog = false)
    }

    fun addItem(collectionId: String, name: String, quantity: Int, categorySlug: String?) {
        _state.value = _state.value.copy(showAddDialog = false)
        viewModelScope.launch {
            try {
                groceryRepo.addItem(
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
                    groceryRepo.purchaseItem(entryId)
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
                groceryRepo.deleteItem(entryId)
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
    val items: List<GroceryFeedEntryDto>,
)

private fun groupByAisle(
    items: List<GroceryFeedEntryDto>,
    aisles: List<GroceryAisleDto>,
): List<AisleGroup> {
    val slugToAisle = mutableMapOf<String, GroceryAisleDto>()
    for (aisle in aisles) {
        for (slug in aisle.category_slugs) {
            slugToAisle[slug] = aisle
        }
    }
    val grouped = LinkedHashMap<String?, MutableList<GroceryFeedEntryDto>>()
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
    if (!other.isNullOrEmpty()) result.add(AisleGroup("Other", other))
    return result
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GroceryListScreen(
    viewModel: GroceryListViewModel = hiltViewModel(),
    onBack: () -> Unit,
    onNavigateToCollection: (collectionId: String) -> Unit,
    onManageStores: () -> Unit,
) {
    val ui by viewModel.state.collectAsState()
    val selectedStore = ui.stores.find { it.id == ui.selectedStoreId }
    val aisleGroups = if (selectedStore != null) groupByAisle(ui.items, selectedStore.aisles) else null

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Grocery List")
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
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.toggleStoreSelector() }) {
                        Icon(
                            Icons.Default.Store,
                            contentDescription = "Select store",
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
                Icon(Icons.Default.Add, contentDescription = "Add grocery item")
            }
        },
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
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
                                Text("All stocked! 🎉", style = MaterialTheme.typography.headlineSmall)
                                Text("Everything is in good supply.", style = MaterialTheme.typography.bodySmall)
                                TextButton(onClick = { viewModel.showAddDialog() }) { Text("Add an item") }
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
                                        GroceryEntryCard(
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
                                    GroceryEntryCard(
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
        }
    }

    if (ui.showAddDialog) {
        AddGroceryItemDialog(
            collections = ui.collections.values.toList(),
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
private fun GroceryEntryCard(
    entry: GroceryFeedEntryDto,
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
                            contentDescription = "Remove",
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
                        Icon(Icons.Default.Check, contentDescription = "Got it", Modifier.size(18.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun StoreSelectorDialog(
    stores: List<GroceryStoreDto>,
    selectedStoreId: String?,
    onSelect: (String?) -> Unit,
    onManageStores: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Sort by store aisle") },
        text = {
            Column {
                ListItem(
                    headlineContent = { Text("No store (default order)") },
                    leadingContent = {
                        RadioButton(selected = selectedStoreId == null, onClick = { onSelect(null) })
                    },
                    modifier = Modifier.clickable { onSelect(null) },
                )
                stores.forEach { store ->
                    ListItem(
                        headlineContent = { Text(store.name) },
                        supportingContent = { Text("${store.aisles.size} aisle${if (store.aisles.size == 1) "" else "s"}") },
                        leadingContent = {
                            RadioButton(selected = store.id == selectedStoreId, onClick = { onSelect(store.id) })
                        },
                        modifier = Modifier.clickable { onSelect(store.id) },
                    )
                }
            }
        },
        confirmButton = { TextButton(onClick = onManageStores) { Text("Manage stores") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

@Composable
private fun AddGroceryItemDialog(
    collections: List<CollectionDto>,
    onDismiss: () -> Unit,
    onAdd: (collectionId: String, name: String, quantity: Int, categorySlug: String?) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var quantityText by remember { mutableStateOf("1") }
    var categorySlug by remember { mutableStateOf("") }
    var selectedCollectionId by remember { mutableStateOf(collections.firstOrNull()?.id ?: "") }
    var collectionMenuExpanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Add grocery item") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Item name *") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Box {
                    OutlinedTextField(
                        value = collections.find { it.id == selectedCollectionId }?.name ?: "",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Collection *") },
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
                    label = { Text("Quantity") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = categorySlug,
                    onValueChange = { categorySlug = it },
                    label = { Text("Category slug (optional)") },
                    placeholder = { Text("e.g. food.dairy") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
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
            ) { Text("Add") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}


data class GroceryListUi(
    val items: List<ItemDto> = emptyList(),
    val collections: Map<String, CollectionDto> = emptyMap(),
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    val updating: Set<String> = emptySet(),
)

@HiltViewModel
class GroceryListViewModel @Inject constructor(
    private val itemRepo: ItemRepository,
    private val collectionRepo: CollectionRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(GroceryListUi())
    val state: StateFlow<GroceryListUi> = _state.asStateFlow()

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
                val items = itemRepo.groceryList()
                val collections = collectionRepo.list()
                val collectionMap = collections.associateBy { it.id }
                _state.value = _state.value.copy(
                    items = items,
                    collections = collectionMap,
                    loading = false,
                    refreshing = false,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, refreshing = false, error = t.message)
            }
        }
    }

    fun markPurchased(itemId: String, useByDate: String?) {
        _state.value = _state.value.copy(updating = _state.value.updating + itemId)
        viewModelScope.launch {
            try {
                itemRepo.restock(itemId = itemId, quantity = 1, useByDate = useByDate)
                // Remove from list
                _state.value = _state.value.copy(
                    items = _state.value.items.filter { it.id != itemId },
                    updating = _state.value.updating - itemId,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    error = t.message,
                    updating = _state.value.updating - itemId,
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GroceryListScreen(
    viewModel: GroceryListViewModel = hiltViewModel(),
    onNavigateToCollection: (collectionId: String) -> Unit,
) {
    val ui by viewModel.state.collectAsState()

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
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("All stocked! 🎉", style = MaterialTheme.typography.headlineSmall)
                        Text("Everything is in good supply.", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            else -> {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(vertical = 16.dp),
                ) {
                    items(ui.items, key = { it.id }) { item ->
                        GroceryListItem(
                            item = item,
                            collectionName = ui.collections[item.collection_id]?.name ?: item.collection_id,
                            isUpdating = item.id in ui.updating,
                            onMarkInStock = { viewModel.markPurchased(item.id, item.use_by_date) },
                            onNavigateToCollection = { onNavigateToCollection(item.collection_id) },
                        )
                    }
                }
            }
        }
        if (ui.error != null) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(ui.error!!, color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
private fun GroceryListItem(
    item: ItemDto,
    collectionName: String,
    isUpdating: Boolean,
    onMarkInStock: () -> Unit,
    onNavigateToCollection: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 80.dp),
        shape = RoundedCornerShape(8.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(end = 12.dp),
            ) {
                Text(
                    text = item.title,
                    style = MaterialTheme.typography.bodyLarge,
                    maxLines = 1,
                )
                Text(
                    text = collectionName,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (item.category_slug != null) {
                    Text(
                        text = item.category_slug!!.split(".").last(),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (item.use_by_date != null) {
                    Text(
                        text = "Use by: ${item.use_by_date!!.take(10)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
            Button(
                onClick = onMarkInStock,
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
                    Icon(Icons.Default.Check, contentDescription = "Mark purchased", Modifier.size(18.dp))
                }
            }
        }
    }
}
