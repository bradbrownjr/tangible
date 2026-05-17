package io.github.bradbrownjr.tangible.ui.screen.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.AssignmentTurnedIn
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Store
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.ItemCreate
import io.github.bradbrownjr.tangible.data.remote.ItemDto
import io.github.bradbrownjr.tangible.data.remote.ItemPatch
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ItemRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class HomeSearchField(val wire: String, val labelRes: Int) {
    ALL("all", R.string.home_search_field_all),
    TITLE("title", R.string.home_search_field_title),
    BRAND("brand", R.string.home_search_field_brand),
    CATEGORY("category", R.string.home_search_field_category),
    NOTES("notes", R.string.home_search_field_notes),
    BARCODE("barcode", R.string.home_search_field_barcode),
    SERIAL("serial", R.string.home_search_field_serial),
}

data class HomeUi(
    val q: String = "",
    val field: HomeSearchField = HomeSearchField.ALL,
    val includeArchived: Boolean = true,
    val results: List<ItemDto> = emptyList(),
    val collections: List<CollectionDto> = emptyList(),
    val loading: Boolean = false,
    val searched: Boolean = false,
    val error: String? = null,
    val alertCount: Int = 0,
)

@HiltViewModel
class HomeTabViewModel @Inject constructor(
    private val api: TangibleApi,
    private val items: ItemRepository,
    private val collectionsRepo: CollectionRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(HomeUi())
    val state: StateFlow<HomeUi> = _state.asStateFlow()

    private var searchJob: Job? = null

    init {
        viewModelScope.launch {
            try {
                val cols = collectionsRepo.list()
                _state.value = _state.value.copy(collections = cols)
            } catch (_: Throwable) {
                // surfaced lazily when user tries to add
            }
        }
        viewModelScope.launch {
            try {
                val count = api.getAlerts(withinDays = 30).size
                _state.value = _state.value.copy(alertCount = count)
            } catch (_: Throwable) { /* non-fatal */ }
        }
    }

    fun onQueryChange(value: String) {
        _state.value = _state.value.copy(q = value)
        scheduleSearch()
    }

    fun setField(field: HomeSearchField) {
        _state.value = _state.value.copy(field = field)
        if (_state.value.q.isNotBlank()) runSearch()
    }

    fun setIncludeArchived(value: Boolean) {
        _state.value = _state.value.copy(includeArchived = value)
        if (_state.value.q.isNotBlank()) runSearch()
    }

    private fun scheduleSearch() {
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(250)
            runSearch()
        }
    }

    fun runSearch() {
        val q = _state.value.q.trim()
        if (q.isEmpty()) {
            _state.value = _state.value.copy(results = emptyList(), searched = false, error = null)
            return
        }
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val r = items.search(
                    q = q,
                    field = _state.value.field.wire,
                    includeArchived = _state.value.includeArchived,
                    limit = 50,
                )
                _state.value = _state.value.copy(results = r, loading = false, searched = true)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(
                    results = emptyList(),
                    loading = false,
                    searched = true,
                    error = t.message,
                )
            }
        }
    }

    suspend fun quickAdd(collectionId: String, asWishlist: Boolean): ItemDto? {
        val title = _state.value.q.trim()
        if (title.isEmpty()) return null
        val col = _state.value.collections.firstOrNull { it.id == collectionId }
        val slug = col?.default_category_slug ?: "general"
        val created = api.createItem(
            ItemCreate(
                collection_id = collectionId,
                category = slug,
                title = title,
            ),
        )
        if (asWishlist) {
            try {
                api.patchItem(created.id, ItemPatch(wanted = true))
            } catch (_: Throwable) {
                // best-effort; item still landed in collection
            }
        }
        return created
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeTabScreen(
    onItemEdit: (String) -> Unit,
    onJumpTo: (Int) -> Unit = {},
    vm: HomeTabViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    var fieldMenuOpen by remember { mutableStateOf(false) }
    var addOpen by remember { mutableStateOf(false) }
    var addCollectionId by remember { mutableStateOf("") }
    var addAsWishlist by remember { mutableStateOf(true) }
    val scope = androidx.compose.runtime.rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.home_tab)) },
                actions = {
                    BadgedBox(
                        badge = {
                            if (s.alertCount > 0) {
                                Badge { Text(s.alertCount.toString()) }
                            }
                        },
                    ) {
                        IconButton(onClick = { onJumpTo(5) }) {
                            Icon(
                                Icons.Default.Notifications,
                                contentDescription = stringResource(R.string.tasks_tab_alerts),
                            )
                        }
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = s.q,
                onValueChange = vm::onQueryChange,
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text(stringResource(R.string.home_search_placeholder)) },
                singleLine = true,
                trailingIcon = {
                    if (s.q.isNotEmpty()) {
                        IconButton(onClick = { vm.onQueryChange("") }) {
                            Icon(
                                Icons.Default.Close,
                                contentDescription = stringResource(R.string.cd_clear_search),
                            )
                        }
                    }
                },
            )
            // Filter row: [Archived checkbox] [spacer] [field dropdown]
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Checkbox(
                    checked = s.includeArchived,
                    onCheckedChange = { vm.setIncludeArchived(it) },
                )
                Text(
                    stringResource(R.string.home_include_archived),
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.clickable { vm.setIncludeArchived(!s.includeArchived) },
                )
                Spacer(Modifier.weight(1f))
                Box {
                    AssistChip(
                        onClick = { fieldMenuOpen = true },
                        label = { Text(stringResource(s.field.labelRes)) },
                        trailingIcon = {
                            Icon(Icons.Default.ArrowDropDown, contentDescription = null)
                        },
                        colors = AssistChipDefaults.assistChipColors(),
                    )
                    DropdownMenu(
                        expanded = fieldMenuOpen,
                        onDismissRequest = { fieldMenuOpen = false },
                    ) {
                        HomeSearchField.values().forEach { f ->
                            DropdownMenuItem(
                                text = { Text(stringResource(f.labelRes)) },
                                onClick = {
                                    fieldMenuOpen = false
                                    vm.setField(f)
                                },
                            )
                        }
                    }
                }
            }

            s.error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }

            when {
                s.loading -> {
                    Text(stringResource(R.string.loading))
                }
                s.searched && s.q.isNotBlank() && s.results.isEmpty() -> {
                    Card(modifier = Modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                stringResource(R.string.home_empty_title, s.q.trim()),
                                style = MaterialTheme.typography.titleMedium,
                            )
                            Spacer(Modifier.height(4.dp))
                            Text(
                                stringResource(R.string.home_empty_subtitle),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Spacer(Modifier.height(12.dp))
                            Button(
                                onClick = {
                                    if (s.collections.isNotEmpty()) {
                                        addCollectionId = s.collections.first().id
                                        addAsWishlist = true
                                        addOpen = true
                                    }
                                },
                                enabled = s.collections.isNotEmpty(),
                            ) {
                                Text(stringResource(R.string.home_empty_add))
                            }
                        }
                    }
                }
                s.results.isNotEmpty() -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        items(s.results, key = { it.id }) { item ->
                            ResultRow(
                                item = item,
                                collections = s.collections,
                                onClick = {
                                    if (item.list_type != null) onJumpTo(2)
                                    else onItemEdit(item.id)
                                },
                            )
                        }
                    }
                }
            }

            // Jump-to tiles — hidden while search is active.
            if (!s.searched && s.q.isBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(
                    stringResource(R.string.home_shortcuts_heading),
                    style = MaterialTheme.typography.labelLarge,
                )
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        JumpToTile(
                            icon = Icons.Default.Folder,
                            label = stringResource(R.string.collections),
                            onClick = { onJumpTo(1) },
                            modifier = Modifier.weight(1f),
                        )
                        JumpToTile(
                            icon = Icons.AutoMirrored.Filled.List,
                            label = stringResource(R.string.grocery_list),
                            onClick = { onJumpTo(2) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        JumpToTile(
                            icon = Icons.Default.Store,
                            label = stringResource(R.string.stores),
                            onClick = { onJumpTo(3) },
                            modifier = Modifier.weight(1f),
                        )
                        JumpToTile(
                            icon = Icons.Default.AssignmentTurnedIn,
                            label = stringResource(R.string.tasks),
                            onClick = { onJumpTo(4) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        JumpToTile(
                            icon = Icons.Default.Notifications,
                            label = stringResource(R.string.alerts),
                            onClick = { onJumpTo(5) },
                            modifier = Modifier.weight(1f),
                        )
                        JumpToTile(
                            icon = Icons.Default.Settings,
                            label = stringResource(R.string.settings),
                            onClick = { onJumpTo(6) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        }
    }

    if (addOpen) {
        var menuOpen by remember { mutableStateOf(false) }
        val selectedCol = s.collections.firstOrNull { it.id == addCollectionId }
        AlertDialog(
            onDismissRequest = { addOpen = false },
            confirmButton = {
                TextButton(
                    onClick = {
                        scope.launch {
                            val created = vm.quickAdd(addCollectionId, addAsWishlist)
                            addOpen = false
                            if (created != null) onItemEdit(created.id)
                        }
                    },
                    enabled = addCollectionId.isNotBlank(),
                ) { Text(stringResource(R.string.home_add_dialog_add)) }
            },
            dismissButton = {
                TextButton(onClick = { addOpen = false }) { Text(stringResource(R.string.cancel)) }
            },
            title = { Text(stringResource(R.string.home_add_dialog_title, s.q.trim())) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        stringResource(R.string.home_add_dialog_collection),
                        style = MaterialTheme.typography.bodySmall,
                    )
                    OutlinedButton(onClick = { menuOpen = true }, modifier = Modifier.fillMaxWidth()) {
                        Text(selectedCol?.name ?: "—")
                        Icon(Icons.Default.ArrowDropDown, contentDescription = null)
                    }
                    DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                        s.collections.forEach { c ->
                            DropdownMenuItem(
                                text = { Text(c.name) },
                                onClick = {
                                    addCollectionId = c.id
                                    menuOpen = false
                                },
                            )
                        }
                    }
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { addAsWishlist = !addAsWishlist },
                    ) {
                        Checkbox(checked = addAsWishlist, onCheckedChange = { addAsWishlist = it })
                        Text(
                            stringResource(R.string.home_add_dialog_as_wishlist),
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            },
        )
    }
}

@Composable
private fun JumpToTile(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier
            .heightIn(min = 96.dp)
            .clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 20.dp, horizontal = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Icon(
                icon,
                contentDescription = null,
                modifier = Modifier.size(32.dp),
            )
            Spacer(Modifier.height(6.dp))
            Text(
                label,
                style = MaterialTheme.typography.labelMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun ResultRow(
    item: ItemDto,
    collections: List<CollectionDto>,
    onClick: () -> Unit,
) {
    val brand = (item.attrs["brand"] as? String)?.takeIf { it.isNotBlank() }
    val cat = item.category_slug?.takeIf { it.isNotBlank() }?.substringAfterLast('.')
    val collectionName = collections.firstOrNull { it.id == item.collection_id }?.name
    val statusRes = when {
        item.list_type != null -> R.string.home_status_on_list
        item.archived_at != null -> R.string.home_status_archived
        item.wanted -> R.string.home_status_wishlist
        item.depleted -> R.string.home_status_depleted
        else -> R.string.home_status_owned
    }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    item.title,
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.weight(1f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    stringResource(statusRes),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            val metaParts = buildList {
                brand?.let { add(it) }
                cat?.let { add(it) }
                collectionName?.let { add(it) }
                if (item.quantity > 1) add("\u00d7${item.quantity}")
            }
            if (metaParts.isNotEmpty()) {
                Text(
                    metaParts.joinToString(" \u00b7 "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            (item.subtitle ?: item.notes)?.takeIf { it.isNotBlank() }?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}
