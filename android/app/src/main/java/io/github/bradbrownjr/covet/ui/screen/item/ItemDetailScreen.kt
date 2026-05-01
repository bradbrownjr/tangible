package io.github.bradbrownjr.covet.ui.screen.item

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AddAPhoto
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Save
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import coil.compose.AsyncImage
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.covet.data.remote.ItemDto
import io.github.bradbrownjr.covet.data.remote.ItemPatch
import io.github.bradbrownjr.covet.data.remote.LocationDto
import io.github.bradbrownjr.covet.data.remote.PhotoDto
import io.github.bradbrownjr.covet.data.repo.ItemRepository
import io.github.bradbrownjr.covet.data.repo.LocationRepository
import io.github.bradbrownjr.covet.data.repo.PhotoRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ItemDetailUi(
    val item: ItemDto? = null,
    val loading: Boolean = true,
    val saving: Boolean = false,
    val editing: Boolean = false,
    val error: String? = null,
    val saved: Boolean = false,
    // Photos
    val photos: List<PhotoDto> = emptyList(),
    val photosLoading: Boolean = false,
    val fullScreenPhoto: PhotoDto? = null,
    // Editable fields (mirrors item when editing starts)
    val title: String = "",
    val subtitle: String = "",
    val notes: String = "",
    val condition: String = "",
    val quantity: String = "1",
    val purchasePrice: String = "",
    val currentValue: String = "",
    val currency: String = "",
    val locationId: String = "",
    val locations: List<LocationDto> = emptyList(),
)

@HiltViewModel
class ItemDetailViewModel @Inject constructor(
    private val items: ItemRepository,
    private val photos: PhotoRepository,
    private val locations: LocationRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val itemId: String = savedState.get<String>("itemId").orEmpty()
    private val _state = MutableStateFlow(ItemDetailUi())
    val state: StateFlow<ItemDetailUi> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val item = items.get(itemId)
                _state.value = _state.value.copy(item = item, loading = false)
                loadPhotos()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message)
            }
        }
    }

    fun loadPhotos() {
        _state.value = _state.value.copy(photosLoading = true)
        viewModelScope.launch {
            try {
                val list = photos.list(itemId)
                _state.value = _state.value.copy(photos = list, photosLoading = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(photosLoading = false)
            }
        }
    }

    fun deletePhoto(photoId: String) {
        viewModelScope.launch {
            try {
                photos.delete(photoId)
                loadPhotos()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun uploadPhoto(bytes: ByteArray, mimeType: String) {
        viewModelScope.launch {
            try {
                photos.upload(itemId, bytes, mimeType)
                loadPhotos()
            } catch (t: Throwable) {
                _state.value = _state.value.copy(error = t.message)
            }
        }
    }

    fun openFullScreen(photo: PhotoDto) {
        _state.value = _state.value.copy(fullScreenPhoto = photo)
    }

    fun closeFullScreen() {
        _state.value = _state.value.copy(fullScreenPhoto = null)
    }

    fun startEditing() {
        val item = _state.value.item ?: return
        _state.value = _state.value.copy(
            editing = true,
            title = item.title,
            subtitle = item.subtitle.orEmpty(),
            notes = item.notes.orEmpty(),
            condition = item.condition.orEmpty(),
            quantity = item.quantity.toString(),
            purchasePrice = item.purchase_price?.toString().orEmpty(),
            currentValue = item.current_value?.toString().orEmpty(),
            currency = item.currency.orEmpty(),
            locationId = item.location_id.orEmpty(),
        )
        viewModelScope.launch {
            try {
                val locs = locations.listTree(item.collection_id)
                _state.value = _state.value.copy(locations = locs)
            } catch (_: Throwable) { /* keep empty list */ }
        }
    }

    fun cancelEditing() {
        _state.value = _state.value.copy(editing = false)
    }

    fun update(block: ItemDetailUi.() -> ItemDetailUi) {
        _state.value = _state.value.block()
    }

    fun save() {
        val s = _state.value
        if (s.saving || s.title.isBlank()) return
        _state.value = s.copy(saving = true, error = null)
        viewModelScope.launch {
            try {
                val updated = items.update(
                    itemId,
                    ItemPatch(
                        title = s.title.trim().takeIf { it.isNotEmpty() },
                        subtitle = s.subtitle.trim().ifEmpty { null },
                        notes = s.notes.trim().ifEmpty { null },
                        condition = s.condition.trim().ifEmpty { null },
                        quantity = s.quantity.toIntOrNull(),
                        purchase_price = s.purchasePrice.toDoubleOrNull(),
                        current_value = s.currentValue.toDoubleOrNull(),
                        currency = s.currency.trim().ifEmpty { null },
                        location_id = s.locationId.ifBlank { null },
                    ),
                )
                _state.value = _state.value.copy(item = updated, saving = false, editing = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(saving = false, error = t.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ItemDetailScreen(
    onBack: () -> Unit,
    vm: ItemDetailViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (s.editing) "Edit item" else s.item?.title ?: "Item") },
                navigationIcon = {
                    IconButton(onClick = {
                        if (s.editing) vm.cancelEditing() else onBack()
                    }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    if (!s.loading && s.item != null) {
                        if (s.editing) {
                            IconButton(
                                onClick = vm::save,
                                enabled = !s.saving && s.title.isNotBlank(),
                            ) {
                                if (s.saving) {
                                    CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                                } else {
                                    Icon(Icons.Default.Save, contentDescription = "Save")
                                }
                            }
                        } else {
                            IconButton(onClick = vm::startEditing) {
                                Icon(Icons.Default.Edit, contentDescription = "Edit")
                            }
                        }
                    }
                },
            )
        },
    ) { padding ->
        when {
            s.loading -> Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            s.error != null && s.item == null -> Column(
                Modifier.fillMaxSize().padding(padding).padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Text(s.error!!, color = MaterialTheme.colorScheme.error)
                Spacer(Modifier.height(8.dp))
                OutlinedButton(onClick = vm::load) { Text("Retry") }
            }
            s.editing -> EditForm(s, vm, Modifier.padding(padding))
            else -> DetailView(s, vm, Modifier.padding(padding))
        }

        // Full-screen photo viewer
        s.fullScreenPhoto?.let { photo ->
            Dialog(
                onDismissRequest = vm::closeFullScreen,
                properties = DialogProperties(usePlatformDefaultWidth = false),
            ) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    AsyncImage(
                        model = "http://localhost/api/photos/${photo.id}/download",
                        contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxSize(),
                    )
                    IconButton(
                        onClick = vm::closeFullScreen,
                        modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
                    ) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = androidx.compose.ui.graphics.Color.White)
                    }
                }
            }
        }
    }
}

@Composable
private fun DetailView(s: ItemDetailUi, vm: ItemDetailViewModel, modifier: Modifier = Modifier) {
    val item = s.item ?: return
    val context = LocalContext.current

    // Gallery picker for photo upload
    val galleryLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri ?: return@rememberLauncherForActivityResult
        val cr = context.contentResolver
        val mimeType = cr.getType(uri) ?: "image/jpeg"
        val bytes = cr.openInputStream(uri)?.readBytes() ?: return@rememberLauncherForActivityResult
        vm.uploadPhoto(bytes, mimeType)
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
    ) {
        // Photo strip
        PhotoStrip(
            photos = s.photos,
            loading = s.photosLoading,
            onPhotoClick = vm::openFullScreen,
            onPhotoDelete = { photo ->
                if (photo.id.isNotEmpty()) vm.deletePhoto(photo.id)
            },
            onAddPhoto = { galleryLauncher.launch("image/*") },
        )

        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item.subtitle?.takeIf { it.isNotBlank() }?.let {
                Text(it, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            item.category_slug?.let { Field("Category", it) }
            Field("Quantity", item.quantity.toString())
            item.condition?.takeIf { it.isNotBlank() }?.let { Field("Condition", it) }
            item.location_path?.takeIf { it.isNotEmpty() }?.let { Field("Location", it.joinToString(" / ")) }
            item.purchase_price?.let { Field("Purchase price", formatPrice(it, item.currency)) }
            item.current_value?.let { Field("Current value", formatPrice(it, item.currency)) }
            item.notes?.takeIf { it.isNotBlank() }?.let {
                Spacer(Modifier.height(4.dp))
                Text("Notes", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(it, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun PhotoStrip(
    photos: List<PhotoDto>,
    loading: Boolean,
    onPhotoClick: (PhotoDto) -> Unit,
    onPhotoDelete: (PhotoDto) -> Unit,
    onAddPhoto: () -> Unit,
) {
    LazyRow(
        modifier = Modifier
            .fillMaxWidth()
            .height(120.dp)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        items(photos, key = { it.id }) { photo ->
            Box(
                modifier = Modifier
                    .size(108.dp)
                    .clickable { onPhotoClick(photo) },
            ) {
                AsyncImage(
                    model = "http://localhost/api/photos/${photo.id}/download",
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),
                )
                IconButton(
                    onClick = { onPhotoDelete(photo) },
                    modifier = Modifier.align(Alignment.TopEnd).size(28.dp),
                ) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = "Delete photo",
                        tint = MaterialTheme.colorScheme.error,
                        modifier = Modifier.size(16.dp),
                    )
                }
            }
        }
        item {
            if (loading) {
                Box(Modifier.size(108.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                }
            } else {
                OutlinedButton(
                    onClick = onAddPhoto,
                    modifier = Modifier.size(108.dp),
                    contentPadding = PaddingValues(0.dp),
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.AddAPhoto, contentDescription = "Add photo")
                    }
                }
            }
        }
    }
    HorizontalDivider()
}

@Composable
private fun Field(label: String, value: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.widthIn(min = 120.dp),
        )
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

private fun formatPrice(amount: Double, currency: String?): String =
    if (currency != null) "$amount $currency" else amount.toString()

@Composable
private fun EditForm(s: ItemDetailUi, vm: ItemDetailViewModel, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        s.error?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }
        OutlinedTextField(
            value = s.title,
            onValueChange = { vm.update { copy(title = it) } },
            label = { Text("Title *") },
            isError = s.title.isBlank(),
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = s.subtitle,
            onValueChange = { vm.update { copy(subtitle = it) } },
            label = { Text("Subtitle") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = s.condition,
                onValueChange = { vm.update { copy(condition = it) } },
                label = { Text("Condition") },
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = s.quantity,
                onValueChange = { vm.update { copy(quantity = it.filter { c -> c.isDigit() }) } },
                label = { Text("Qty") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.width(72.dp),
            )
        }
        var locationMenuOpen by remember { mutableStateOf(false) }
        val flat = remember(s.locations) {
            val out = mutableListOf<Pair<Int, LocationDto>>()
            fun walk(node: LocationDto, depth: Int) {
                out.add(depth to node)
                node.children.forEach { walk(it, depth + 1) }
            }
            s.locations.forEach { walk(it, 0) }
            out
        }
        val selectedName = flat.firstOrNull { it.second.id == s.locationId }?.second?.name
            ?: "— No location —"
        Box(modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(
                onClick = { locationMenuOpen = true },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Location: $selectedName")
            }
            DropdownMenu(
                expanded = locationMenuOpen,
                onDismissRequest = { locationMenuOpen = false },
            ) {
                DropdownMenuItem(
                    text = { Text("— No location —") },
                    onClick = {
                        vm.update { copy(locationId = "") }
                        locationMenuOpen = false
                    },
                )
                flat.forEach { (depth, loc) ->
                    DropdownMenuItem(
                        text = { Text("${"  ".repeat(depth)}${loc.name}") },
                        onClick = {
                            vm.update { copy(locationId = loc.id) }
                            locationMenuOpen = false
                        },
                    )
                }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = s.purchasePrice,
                onValueChange = { vm.update { copy(purchasePrice = it) } },
                label = { Text("Purchase price") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = s.currentValue,
                onValueChange = { vm.update { copy(currentValue = it) } },
                label = { Text("Current value") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.weight(1f),
            )
        }
        OutlinedTextField(
            value = s.currency,
            onValueChange = { vm.update { copy(currency = it.take(3).uppercase()) } },
            label = { Text("Currency (ISO, e.g. USD)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = s.notes,
            onValueChange = { vm.update { copy(notes = it) } },
            label = { Text("Notes") },
            minLines = 3,
            maxLines = 6,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
