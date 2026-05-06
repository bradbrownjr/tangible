package io.github.bradbrownjr.tangible.ui.screen.collections

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.CategoryDto
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.ItemDto
import io.github.bradbrownjr.tangible.data.repo.CategoryRepository
import io.github.bradbrownjr.tangible.data.repo.CollectionRepository
import io.github.bradbrownjr.tangible.data.repo.ItemRepository
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Lightweight "Collections as swipeable tabs" home view.
 *
 * Each collection is a tab; the page beneath shows that collection's items as
 * a simple list. Tapping any item (or "Add item" in the empty state) opens
 * the existing [io.github.bradbrownjr.tangible.ui.screen.collection.CollectionDetailScreen]
 * where every advanced action lives. The FAB opens the new-collection wizard.
 */

data class CollectionsTabsUi(
    val collections: List<CollectionDto> = emptyList(),
    val itemsByCollection: Map<String, List<ItemDto>> = emptyMap(),
    val loadingByCollection: Map<String, Boolean> = emptyMap(),
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    val wizardStep: WizardStep = WizardStep.CLOSED,
    val presets: List<CategoryDto> = emptyList(),
    val selectedPreset: CategoryDto? = null,
    val newName: String = "",
    val newDescription: String = "",
)

@HiltViewModel
class CollectionsTabsViewModel @Inject constructor(
    private val collectionsRepo: CollectionRepository,
    private val itemsRepo: ItemRepository,
    private val categoryRepo: CategoryRepository,
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
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun CollectionsTabsScreen(
    onOpenCollection: (String) -> Unit,
    onOpenItem: (String) -> Unit = {},
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
        }
        return
    }

    val pagerState = rememberPagerState(pageCount = { s.collections.size })
    val currentColl = s.collections.getOrNull(pagerState.currentPage)
    val currentPageLoading = currentColl?.let { s.loadingByCollection[it.id] == true } ?: false

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
                                        OutlinedButton(onClick = { onOpenCollection(coll.id) }) {
                                            Text(stringResource(R.string.add_item))
                                        }
                                    }
                                }
                            }
                        }
                        else -> LazyColumn(Modifier.fillMaxSize()) {
                            items(items, key = { it.id }) { item ->
                                ItemRow(item = item, onClick = { onOpenItem(item.id) })
                                HorizontalDivider()
                            }
                        }
                    }
                }
            }
        }
        WizardDialogs(s, vm)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ItemRow(item: ItemDto, onClick: () -> Unit) {
    val supporting: (@Composable () -> Unit)? = when {
        !item.subtitle.isNullOrBlank() -> ({ Text(item.subtitle!!) })
        !item.notes.isNullOrBlank() -> ({ Text(item.notes!!, maxLines = 1) })
        else -> null
    }
    val trailing: (@Composable () -> Unit)? = if (item.quantity > 1) {
        ({ Text("\u00D7${item.quantity}") })
    } else null
    ListItem(
        headlineContent = { Text(item.title) },
        supportingContent = supporting,
        trailingContent = trailing,
        modifier = Modifier.clickable { onClick() },
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
