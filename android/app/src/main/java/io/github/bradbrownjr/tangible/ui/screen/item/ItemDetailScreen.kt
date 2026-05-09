package io.github.bradbrownjr.tangible.ui.screen.item

import android.app.PendingIntent
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.nfc.NfcAdapter
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
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
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
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.ItemDto
import io.github.bradbrownjr.tangible.data.remote.ItemPatch
import io.github.bradbrownjr.tangible.data.remote.LocationDto
import io.github.bradbrownjr.tangible.data.remote.ManualBundleDto
import io.github.bradbrownjr.tangible.data.remote.PhotoDto
import io.github.bradbrownjr.tangible.data.repo.ItemRepository
import io.github.bradbrownjr.tangible.data.repo.LocationRepository
import io.github.bradbrownjr.tangible.data.repo.BundleRepository
import io.github.bradbrownjr.tangible.data.repo.PhotoRepository
import io.github.bradbrownjr.tangible.nfc.NfcManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.CoroutineScope
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
    val brand: String = "",
    val locations: List<LocationDto> = emptyList(),
    val bundles: List<ManualBundleDto> = emptyList(),
)

@HiltViewModel
class ItemDetailViewModel @Inject constructor(
    private val items: ItemRepository,
    private val photos: PhotoRepository,
    private val locations: LocationRepository,
    private val bundles: BundleRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val itemId: String = savedState.get<String>("itemId").orEmpty()
    private val startInEdit: Boolean = savedState.get<Boolean>("edit") ?: false
    private val _state = MutableStateFlow(ItemDetailUi())
    val state: StateFlow<ItemDetailUi> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val item = items.get(itemId)
                _state.value = _state.value.copy(item = item, loading = false)
                if (startInEdit) startEditing()
                loadPhotos()
                loadBundles()
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

    fun loadBundles() {
        viewModelScope.launch {
            try {
                val list = bundles.listForItem(itemId)
                _state.value = _state.value.copy(bundles = list)
            } catch (_: Throwable) { /* keep empty list */ }
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
            brand = (item.attrs["brand"] as? String).orEmpty(),
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
                val updatedAttrs = (s.item?.attrs?.toMutableMap() ?: mutableMapOf()).also { map ->
                    val brandVal = s.brand.trim()
                    if (brandVal.isNotEmpty()) map["brand"] = brandVal else map.remove("brand")
                }
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
                        attrs = updatedAttrs.ifEmpty { null },
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
    val context = LocalContext.current
    val galleryLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri ?: return@rememberLauncherForActivityResult
        val cr = context.contentResolver
        val mimeType = cr.getType(uri) ?: "image/jpeg"
        val bytes = cr.openInputStream(uri)?.readBytes() ?: return@rememberLauncherForActivityResult
        vm.uploadPhoto(bytes, mimeType)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(s.item?.title ?: stringResource(R.string.item_default_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                    }
                },
                actions = {
                    if (!s.loading && s.item != null && !s.editing) {
                        IconButton(onClick = vm::startEditing) {
                            Icon(Icons.Default.Edit, contentDescription = stringResource(R.string.edit))
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
                OutlinedButton(onClick = vm::load) { Text(stringResource(R.string.retry)) }
            }
            else -> DetailView(s, vm, onAddPhoto = { galleryLauncher.launch("image/*") }, Modifier.padding(padding))
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
                        Icon(Icons.Default.Close, contentDescription = stringResource(R.string.close), tint = androidx.compose.ui.graphics.Color.White)
                    }
                }
            }
        }
    }

    // Edit bottom sheet — shown as a slideout over the detail view
    if (s.editing) {
        val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        val scope = rememberCoroutineScope()
        EditItemSheet(s, vm, sheetState, scope)
    }
}

@Composable
private fun DetailView(s: ItemDetailUi, vm: ItemDetailViewModel, onAddPhoto: () -> Unit, modifier: Modifier = Modifier) {
    val item = s.item ?: return

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
    ) {
        PhotoStrip(
            photos = s.photos,
            loading = s.photosLoading,
            onPhotoClick = vm::openFullScreen,
            onPhotoDelete = { photo ->
                if (photo.id.isNotEmpty()) vm.deletePhoto(photo.id)
            },
            onAddPhoto = onAddPhoto,
        )

        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            (item.attrs["brand"] as? String)?.takeIf { it.isNotBlank() }?.let { Field(stringResource(R.string.brand), it) }
            item.subtitle?.takeIf { it.isNotBlank() }?.let {
                Text(it, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            item.category_slug?.let { Field(stringResource(R.string.category), it) }
            Field(stringResource(R.string.quantity), item.quantity.toString())
            item.condition?.takeIf { it.isNotBlank() }?.let { Field(stringResource(R.string.condition), it) }
            item.location_path?.takeIf { it.isNotEmpty() }?.let { Field(stringResource(R.string.location), it.joinToString(" / ")) }
            item.purchase_price?.let { Field(stringResource(R.string.purchase_price), formatPrice(it, item.currency)) }
            item.current_value?.let { Field(stringResource(R.string.current_value), formatPrice(it, item.currency)) }
            item.notes?.takeIf { it.isNotBlank() }?.let {
                Spacer(Modifier.height(4.dp))
                Text(stringResource(R.string.notes), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(it, style = MaterialTheme.typography.bodyMedium)
            }
            if (s.bundles.isNotEmpty()) {
                Spacer(Modifier.height(4.dp))
                Text(stringResource(R.string.manuals), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                s.bundles.forEach { b ->
                    Text(b.title, style = MaterialTheme.typography.bodyMedium)
                    if (!b.description.isNullOrBlank()) {
                        Text(b.description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (b.assets.isNotEmpty()) {
                        Text(
                            pluralStringResource(R.plurals.asset_count, b.assets.size, b.assets.size),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }

            // NFC tag write
            HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
            NfcWriteSection(itemId = item.id)
        }
    }
}

@Composable
private fun NfcWriteSection(itemId: String) {
    val context = LocalContext.current
    val nfcAdapter = remember { NfcAdapter.getDefaultAdapter(context) }
    var showDialog by remember { mutableStateOf(false) }
    var nfcMessage by remember { mutableStateOf<String?>(null) }
    val writeSuccessMsg = stringResource(R.string.nfc_write_success)
    val writeFailedPrefix = stringResource(R.string.nfc_write_failed_prefix)

    // Collect write results when dialog is open.
    LaunchedEffect(showDialog) {
        if (!showDialog) return@LaunchedEffect
        NfcManager.writeResult.collect { result ->
            nfcMessage = when (result) {
                is NfcManager.WriteResult.Success -> writeSuccessMsg
                is NfcManager.WriteResult.Failure -> "$writeFailedPrefix${result.message}"
            }
            NfcManager.pendingWriteItemId = null
        }
    }

    if (showDialog) {
        // Enable foreground NFC dispatch while dialog is open.
        DisposableEffect(Unit) {
            val activity = context as? android.app.Activity
            if (activity != null && nfcAdapter != null) {
                NfcManager.pendingWriteItemId = itemId
                val intent = Intent(activity, activity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
                val pi = PendingIntent.getActivity(
                    activity, 0, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
                )
                val filters = arrayOf(IntentFilter(NfcAdapter.ACTION_TAG_DISCOVERED))
                nfcAdapter.enableForegroundDispatch(activity, pi, filters, null)
            }
            onDispose {
                NfcManager.pendingWriteItemId = null
                if (activity != null && nfcAdapter != null) {
                    nfcAdapter.disableForegroundDispatch(activity)
                }
            }
        }

        AlertDialog(
            onDismissRequest = { showDialog = false; nfcMessage = null },
            title = { Text(stringResource(R.string.write_nfc_tag)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (nfcMessage != null) {
                        Text(nfcMessage!!, style = MaterialTheme.typography.bodyMedium)
                    } else {
                        CircularProgressIndicator(Modifier.size(20.dp).align(Alignment.CenterHorizontally), strokeWidth = 2.dp)
                        Text(
                            stringResource(R.string.nfc_write_instructions),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showDialog = false; nfcMessage = null }) { Text(stringResource(R.string.done)) }
            },
        )
    }

    if (nfcAdapter == null) {
        Text(
            stringResource(R.string.nfc_not_available),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    } else {
        OutlinedButton(
            onClick = { showDialog = true },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(stringResource(R.string.write_nfc_tag))
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
                        contentDescription = stringResource(R.string.cd_delete_photo),
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
                        Icon(Icons.Default.AddAPhoto, contentDescription = stringResource(R.string.cd_add_photo))
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun EditItemSheet(
    s: ItemDetailUi,
    vm: ItemDetailViewModel,
    sheetState: SheetState,
    scope: CoroutineScope,
) {
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
    val noLocation = stringResource(R.string.no_location)
    val selectedName = flat.firstOrNull { it.second.id == s.locationId }?.second?.name ?: noLocation

    ModalBottomSheet(
        onDismissRequest = vm::cancelEditing,
        sheetState = sheetState,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 24.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                stringResource(R.string.edit_item),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(bottom = 4.dp),
            )
            s.error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
            OutlinedTextField(
                value = s.brand,
                onValueChange = { vm.update { copy(brand = it) } },
                label = { Text(stringResource(R.string.brand_optional)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = s.title,
                onValueChange = { vm.update { copy(title = it) } },
                label = { Text(stringResource(R.string.title_required)) },
                isError = s.title.isBlank(),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = s.subtitle,
                onValueChange = { vm.update { copy(subtitle = it) } },
                label = { Text(stringResource(R.string.subtitle)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = s.notes,
                onValueChange = { vm.update { copy(notes = it) } },
                label = { Text(stringResource(R.string.notes)) },
                minLines = 2,
                maxLines = 4,
                modifier = Modifier.fillMaxWidth(),
            )
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = s.condition,
                    onValueChange = { vm.update { copy(condition = it) } },
                    label = { Text(stringResource(R.string.condition)) },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = s.quantity,
                    onValueChange = { vm.update { copy(quantity = it.filter { c -> c.isDigit() }) } },
                    label = { Text(stringResource(R.string.qty)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.width(72.dp),
                )
            }
            Box(modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = { locationMenuOpen = true },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.location_button, selectedName))
                }
                DropdownMenu(
                    expanded = locationMenuOpen,
                    onDismissRequest = { locationMenuOpen = false },
                ) {
                    DropdownMenuItem(
                        text = { Text(noLocation) },
                        onClick = { vm.update { copy(locationId = "") }; locationMenuOpen = false },
                    )
                    flat.forEach { (depth, loc) ->
                        DropdownMenuItem(
                            text = { Text("${"  ".repeat(depth)}${loc.name}") },
                            onClick = { vm.update { copy(locationId = loc.id) }; locationMenuOpen = false },
                        )
                    }
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = s.purchasePrice,
                    onValueChange = { vm.update { copy(purchasePrice = it) } },
                    label = { Text(stringResource(R.string.purchase_price)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = s.currentValue,
                    onValueChange = { vm.update { copy(currentValue = it) } },
                    label = { Text(stringResource(R.string.current_value)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.weight(1f),
                )
            }
            OutlinedTextField(
                value = s.currency,
                onValueChange = { vm.update { copy(currency = it.take(3).uppercase()) } },
                label = { Text(stringResource(R.string.currency_hint)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Button(
                    onClick = vm::save,
                    enabled = !s.saving && s.title.isNotBlank(),
                    modifier = Modifier.weight(1f),
                ) {
                    if (s.saving) {
                        CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Text(stringResource(R.string.save))
                    }
                }
                OutlinedButton(
                    onClick = {
                        scope.launch { sheetState.hide() }.invokeOnCompletion { vm.cancelEditing() }
                    },
                    modifier = Modifier.weight(1f),
                ) {
                    Text(stringResource(R.string.cancel))
                }
            }
        }
    }
}
