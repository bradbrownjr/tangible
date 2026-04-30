package io.github.bradbrownjr.covet.ui.screen.grocery

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.ItemDto
import io.github.bradbrownjr.covet.data.repo.CollectionRepository
import io.github.bradbrownjr.covet.data.repo.ItemRepository
import javax.inject.Inject

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
