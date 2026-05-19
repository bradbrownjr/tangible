package io.github.bradbrownjr.tangible.ui.screen.grocery

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
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
import io.github.bradbrownjr.tangible.data.remote.ShoppingAisleDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingStoreDto
import io.github.bradbrownjr.tangible.data.repo.ShoppingRepository
import io.github.bradbrownjr.tangible.R
import javax.inject.Inject

data class ShoppingStoreListUi(
    val stores: List<ShoppingStoreDto> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ShoppingStoreListViewModel @Inject constructor(
    private val shoppingRepo: ShoppingRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ShoppingStoreListUi())
    val state: StateFlow<ShoppingStoreListUi> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val stores = shoppingRepo.listStores()
                _state.value = _state.value.copy(stores = stores, loading = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message)
            }
        }
    }

    fun createStore(name: String) {
        viewModelScope.launch {
            try {
                shoppingRepo.createStore(name)
                load()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun deleteStore(id: String) {
        viewModelScope.launch {
            try {
                shoppingRepo.deleteStore(id)
                _state.value = _state.value.copy(stores = _state.value.stores.filter { it.id != id })
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShoppingStoreListScreen(
    viewModel: ShoppingStoreListViewModel = hiltViewModel(),
    onBack: () -> Unit,
    showBackButton: Boolean = true,
    onOpenStore: (storeId: String) -> Unit,
) {
    val ui by viewModel.state.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }
    var confirmDeleteStore by remember { mutableStateOf<ShoppingStoreDto?>(null) }

    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = { Text(stringResource(R.string.my_stores)) },
                    navigationIcon = {
                        if (showBackButton) {
                            IconButton(onClick = onBack) {
                                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                            }
                        }
                    },
                    actions = {
                        IconButton(onClick = { showCreateDialog = true }) {
                            Icon(Icons.Default.Add, contentDescription = stringResource(R.string.cd_add_store))
                        }
                    },
                )
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                ) {}
            }
        },
    ) { innerPadding ->
        Box(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            when {
                ui.loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                else -> {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        gridItems(ui.stores, key = { it.id }) { store ->
                            StoreCard(
                                store = store,
                                onClick = { onOpenStore(store.id) },
                                onDelete = { confirmDeleteStore = store },
                            )
                        }
                        item(key = "new_store") {
                            NewStoreCard(onClick = { showCreateDialog = true })
                        }
                    }
                }
            }
            if (ui.error != null) {
                Snackbar(modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp)) {
                    Text(ui.error!!)
                }
            }
        }
    }

    if (showCreateDialog) {
        NameInputDialog(
            title = stringResource(R.string.new_store),
            label = stringResource(R.string.store_name),
            onDismiss = { showCreateDialog = false },
            onConfirm = { name -> viewModel.createStore(name); showCreateDialog = false },
        )
    }

    confirmDeleteStore?.let { store ->
        AlertDialog(
            onDismissRequest = { confirmDeleteStore = null },
            title = { Text(stringResource(R.string.delete_store_title)) },
            text = { Text(stringResource(R.string.delete_store_body, store.name)) },
            confirmButton = {
                Button(
                    onClick = { viewModel.deleteStore(store.id); confirmDeleteStore = null },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                ) { Text(stringResource(R.string.delete)) }
            },
            dismissButton = { TextButton(onClick = { confirmDeleteStore = null }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun StoreCard(
    store: ShoppingStoreDto,
    onClick: () -> Unit,
    onDelete: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(
                store.name,
                style = MaterialTheme.typography.titleSmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(4.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    pluralStringResource(R.plurals.aisle_count, store.aisles.size, store.aisles.size),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                IconButton(
                    onClick = onDelete,
                    modifier = Modifier.size(24.dp),
                ) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = stringResource(R.string.cd_delete_store),
                        tint = MaterialTheme.colorScheme.error,
                        modifier = Modifier.size(16.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun NewStoreCard(onClick: () -> Unit) {
    OutlinedCard(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Icon(Icons.Default.Add, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text(
                    stringResource(R.string.new_store),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Aisle editor screen
// ---------------------------------------------------------------------------

data class ShoppingAisleEditorUi(
    val store: ShoppingStoreDto? = null,
    val loading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ShoppingAisleEditorViewModel @Inject constructor(
    private val shoppingRepo: ShoppingRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val storeId: String = checkNotNull(savedState["storeId"])
    private val _state = MutableStateFlow(ShoppingAisleEditorUi())
    val state: StateFlow<ShoppingAisleEditorUi> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val stores = shoppingRepo.listStores()
                _state.value = _state.value.copy(
                    store = stores.find { it.id == storeId },
                    loading = false,
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message)
            }
        }
    }

    fun createAisle(name: String, categorySlugs: List<String>) {
        viewModelScope.launch {
            try {
                val position = (_state.value.store?.aisles?.maxOfOrNull { it.position } ?: -1) + 1
                shoppingRepo.createAisle(storeId, name, position, categorySlugs)
                load()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun updateAisle(aisleId: String, name: String, categorySlugs: List<String>) {
        viewModelScope.launch {
            try {
                shoppingRepo.updateAisle(storeId, aisleId, name = name, categorySlugs = categorySlugs)
                load()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun deleteAisle(aisleId: String) {
        viewModelScope.launch {
            try {
                shoppingRepo.deleteAisle(storeId, aisleId)
                _state.value = _state.value.copy(
                    store = _state.value.store?.copy(
                        aisles = _state.value.store!!.aisles.filter { it.id != aisleId }
                    )
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun moveAisleUp(aisleId: String) {
        val aisles = _state.value.store?.aisles?.sortedBy { it.position } ?: return
        val idx = aisles.indexOfFirst { it.id == aisleId }.takeIf { it > 0 } ?: return
        val reordered = aisles.toMutableList().also { list ->
            val tmp = list[idx]; list[idx] = list[idx - 1]; list[idx - 1] = tmp
        }
        viewModelScope.launch {
            try {
                shoppingRepo.reorderAisles(storeId, reordered.map { it.id })
                load()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun moveAisleDown(aisleId: String) {
        val aisles = _state.value.store?.aisles?.sortedBy { it.position } ?: return
        val idx = aisles.indexOfFirst { it.id == aisleId }.takeIf { it < aisles.lastIndex } ?: return
        val reordered = aisles.toMutableList().also { list ->
            val tmp = list[idx]; list[idx] = list[idx + 1]; list[idx + 1] = tmp
        }
        viewModelScope.launch {
            try {
                shoppingRepo.reorderAisles(storeId, reordered.map { it.id })
                load()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShoppingAisleEditorScreen(
    viewModel: ShoppingAisleEditorViewModel = hiltViewModel(),
    onBack: () -> Unit,
) {
    val ui by viewModel.state.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }
    var editAisle by remember { mutableStateOf<ShoppingAisleDto?>(null) }
    var confirmDeleteAisle by remember { mutableStateOf<ShoppingAisleDto?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(ui.store?.name ?: stringResource(R.string.aisles_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = stringResource(R.string.cd_add_aisle))
            }
        },
    ) { innerPadding ->
        Box(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            when {
                ui.loading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                else -> {
                    val aisles = ui.store?.aisles?.sortedBy { it.position } ?: emptyList()
                    if (aisles.isEmpty()) {
                        Column(
                            modifier = Modifier.align(Alignment.Center).padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Text(stringResource(R.string.no_aisles), style = MaterialTheme.typography.bodyLarge)
                            Text(
                                stringResource(R.string.no_aisles_hint),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    } else {
                        LazyColumn(contentPadding = PaddingValues(vertical = 8.dp)) {
                            itemsIndexed(aisles, key = { _, a -> a.id }) { idx, aisle ->
                                ListItem(
                                    headlineContent = { Text(aisle.name) },
                                    supportingContent = {
                                        if (aisle.category_slugs.isNotEmpty()) {
                                            Text(aisle.category_slugs.joinToString(", "))
                                        }
                                    },
                                    overlineContent = { Text(stringResource(R.string.position, idx + 1)) },
                                    trailingContent = {
                                        Row {
                                            IconButton(onClick = { editAisle = aisle }) {
                                                Icon(Icons.Default.Edit, contentDescription = stringResource(R.string.edit))
                                            }
                                            IconButton(onClick = { confirmDeleteAisle = aisle }) {
                                                Icon(
                                                    Icons.Default.Delete,
                                                    contentDescription = stringResource(R.string.delete),
                                                    tint = MaterialTheme.colorScheme.error,
                                                )
                                            }
                                        }
                                    },
                                    modifier = Modifier.clickable { editAisle = aisle },
                                )
                                HorizontalDivider()
                            }
                        }
                    }
                }
            }
            if (ui.error != null) {
                Snackbar(modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp)) {
                    Text(ui.error!!)
                }
            }
        }
    }

    if (showCreateDialog) {
        AisleInputDialog(
            title = stringResource(R.string.new_aisle),
            initialName = "",
            initialSlugs = emptyList(),
            onDismiss = { showCreateDialog = false },
            onConfirm = { name, slugs ->
                viewModel.createAisle(name, slugs)
                showCreateDialog = false
            },
        )
    }

    editAisle?.let { aisle ->
        AisleInputDialog(
            title = stringResource(R.string.edit_aisle),
            initialName = aisle.name,
            initialSlugs = aisle.category_slugs,
            onDismiss = { editAisle = null },
            onConfirm = { name, slugs ->
                viewModel.updateAisle(aisle.id, name, slugs)
                editAisle = null
            },
        )
    }

    confirmDeleteAisle?.let { aisle ->
        AlertDialog(
            onDismissRequest = { confirmDeleteAisle = null },
            title = { Text(stringResource(R.string.delete_aisle_title)) },
            text = { Text(stringResource(R.string.delete_aisle_body, aisle.name)) },
            confirmButton = {
                Button(
                    onClick = { viewModel.deleteAisle(aisle.id); confirmDeleteAisle = null },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                ) { Text(stringResource(R.string.delete)) }
            },
            dismissButton = { TextButton(onClick = { confirmDeleteAisle = null }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

private fun String.parseSlugs(): List<String> =
    split(",", "\n").map { it.trim() }.filter { it.isNotBlank() }

// ---------------------------------------------------------------------------
// Shared dialogs
// ---------------------------------------------------------------------------

@Composable
private fun NameInputDialog(
    title: String,
    label: String,
    initialValue: String = "",
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var value by remember { mutableStateOf(initialValue) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            OutlinedTextField(
                value = value,
                onValueChange = { value = it },
                label = { Text(label) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        },
        confirmButton = {
            Button(onClick = { if (value.isNotBlank()) onConfirm(value.trim()) }, enabled = value.isNotBlank()) {
                Text(stringResource(R.string.save))
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun AisleInputDialog(
    title: String,
    initialName: String,
    initialSlugs: List<String>,
    onDismiss: () -> Unit,
    onConfirm: (name: String, slugs: List<String>) -> Unit,
) {
    var name by remember { mutableStateOf(initialName) }
    val selectedSlugs = remember {
        mutableStateOf(initialSlugs.filter { it in PRESET_SLUGS }.toSet())
    }
    var customText by remember {
        mutableStateOf(
            initialSlugs.filter { it !in PRESET_SLUGS }.joinToString(", ")
        )
    }

    fun buildSlugs(): List<String> {
        val result = selectedSlugs.value.toMutableList()
        customText.split(",").map { it.trim().lowercase().replace(" ", "-") }
            .filter { it.isNotBlank() && it !in result }
            .forEach { result.add(it) }
        return result
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                label = { Text(stringResource(R.string.aisle_name_required)) },
                    placeholder = { Text(stringResource(R.string.aisle_name_placeholder)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(stringResource(R.string.categories), style = MaterialTheme.typography.labelMedium)
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    SHOPPING_CATEGORY_PRESETS.forEach { cat ->
                        FilterChip(
                            selected = cat.slug in selectedSlugs.value,
                            onClick = {
                                selectedSlugs.value = if (cat.slug in selectedSlugs.value)
                                    selectedSlugs.value - cat.slug
                                else
                                    selectedSlugs.value + cat.slug
                            },
                            label = { Text(stringResource(cat.labelRes)) },
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
                OutlinedTextField(
                    value = customText,
                    onValueChange = { customText = it },
                    label = { Text(stringResource(R.string.custom_categories_optional)) },
                    placeholder = { Text(stringResource(R.string.custom_categories_placeholder)) },
                    supportingText = { Text(stringResource(R.string.custom_categories_hint)) },
                    maxLines = 3,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { if (name.isNotBlank()) onConfirm(name.trim(), buildSlugs()) },
                enabled = name.isNotBlank(),
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
