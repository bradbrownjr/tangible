package io.github.bradbrownjr.tangible.ui.screen.chores

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AssignmentTurnedIn
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.remote.ChoreCompletePayloadDto
import io.github.bradbrownjr.tangible.data.remote.ChoreCreateDto
import io.github.bradbrownjr.tangible.data.remote.ChoreDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

data class ChoresUi(
    val collectionId: String = "",
    val collectionName: String = "",
    val chores: List<ChoreDto> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null,
)

// ---------------------------------------------------------------------------
// ViewModel
// ---------------------------------------------------------------------------

@HiltViewModel
class ChoresViewModel @Inject constructor(
    private val api: TangibleApi,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val collectionId: String = checkNotNull(savedStateHandle["collectionId"])
    private val collectionName: String = savedStateHandle["collectionName"] ?: ""

    private val _state = MutableStateFlow(
        ChoresUi(collectionId = collectionId, collectionName = collectionName)
    )
    val state: StateFlow<ChoresUi> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        if (_state.value.loading) return
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val chores = api.listChores(collectionId)
                _state.value = _state.value.copy(chores = chores, loading = false)
            } catch (e: Throwable) {
                _state.value = _state.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun createChore(
        name: String,
        notes: String?,
        intervalDays: Int?,
        nextDueAt: String?,
        onDone: () -> Unit,
    ) {
        viewModelScope.launch {
            try {
                val chore = api.createChore(
                    collectionId,
                    ChoreCreateDto(
                        name = name,
                        notes = notes?.takeIf { it.isNotBlank() },
                        interval_days = intervalDays,
                        next_due_at = nextDueAt?.takeIf { it.isNotBlank() },
                    ),
                )
                _state.value = _state.value.copy(
                    chores = (_state.value.chores + chore).sortedWith(
                        compareBy(nullsLast()) { it.next_due_at }
                    )
                )
                onDone()
            } catch (e: Throwable) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun completeChore(choreId: String, notes: String?, onDone: () -> Unit) {
        viewModelScope.launch {
            try {
                val updated = api.completeChore(
                    choreId,
                    ChoreCompletePayloadDto(notes = notes?.takeIf { it.isNotBlank() }),
                )
                _state.value = _state.value.copy(
                    chores = _state.value.chores
                        .map { if (it.id == choreId) updated else it }
                        .sortedWith(compareBy(nullsLast()) { it.next_due_at })
                )
                onDone()
            } catch (e: Throwable) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun deleteChore(choreId: String) {
        viewModelScope.launch {
            try {
                api.deleteChore(choreId)
                _state.value = _state.value.copy(
                    chores = _state.value.chores.filter { it.id != choreId }
                )
            } catch (e: Throwable) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChoresScreen(
    onBack: () -> Unit,
    vm: ChoresViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    val scope = rememberCoroutineScope()

    // Add chore sheet
    var showAddSheet by remember { mutableStateOf(false) }
    val addSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    // Complete chore dialog state
    var completingChore by remember { mutableStateOf<ChoreDto?>(null) }
    var completeNotes by remember { mutableStateOf("") }

    // Delete confirm dialog state
    var deletingChore by remember { mutableStateOf<ChoreDto?>(null) }

    // Dismiss add sheet helper
    val dismissAddSheet: () -> Unit = {
        scope.launch { addSheetState.hide() }.invokeOnCompletion { showAddSheet = false }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        if (s.collectionName.isNotBlank())
                            "${s.collectionName} — ${stringResource(R.string.chores)}"
                        else
                            stringResource(R.string.chores)
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddSheet = true }) {
                Icon(Icons.Default.Add, contentDescription = stringResource(R.string.add_chore))
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                s.loading && s.chores.isEmpty() -> {
                    CircularProgressIndicator(Modifier.align(Alignment.Center))
                }
                s.chores.isEmpty() -> {
                    Text(
                        stringResource(R.string.chores_empty),
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 8.dp),
                    ) {
                        items(s.chores, key = { it.id }) { chore ->
                            ChoreCard(
                                chore = chore,
                                onComplete = {
                                    completingChore = chore
                                    completeNotes = ""
                                },
                                onDelete = { deletingChore = chore },
                            )
                        }
                    }
                }
            }

            // Inline error banner
            s.error?.let { err ->
                Text(
                    err,
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }

    // ---- Add Chore Bottom Sheet ----
    if (showAddSheet) {
        AddChoreSheet(
            sheetState = addSheetState,
            onDismiss = dismissAddSheet,
            onConfirm = { name, notes, intervalDays, nextDueAt ->
                vm.createChore(name, notes, intervalDays, nextDueAt) { dismissAddSheet() }
            },
        )
    }

    // ---- Mark Complete Dialog ----
    completingChore?.let { chore ->
        AlertDialog(
            onDismissRequest = { completingChore = null },
            title = { Text(stringResource(R.string.chore_complete)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(chore.name, fontWeight = FontWeight.SemiBold)
                    OutlinedTextField(
                        value = completeNotes,
                        onValueChange = { completeNotes = it },
                        label = { Text(stringResource(R.string.chore_complete_notes_hint)) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = false,
                        minLines = 2,
                    )
                }
            },
            confirmButton = {
                Button(onClick = {
                    val id = chore.id
                    vm.completeChore(id, completeNotes.takeIf { it.isNotBlank() }) {
                        completingChore = null
                    }
                }) {
                    Text(stringResource(R.string.chore_complete))
                }
            },
            dismissButton = {
                TextButton(onClick = { completingChore = null }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }

    // ---- Delete Confirm Dialog ----
    deletingChore?.let { chore ->
        AlertDialog(
            onDismissRequest = { deletingChore = null },
            title = { Text(stringResource(R.string.delete)) },
            text = {
                Text(stringResource(R.string.delete_chore_confirm, chore.name))
            },
            confirmButton = {
                Button(
                    onClick = {
                        vm.deleteChore(chore.id)
                        deletingChore = null
                    },
                    colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                    ),
                ) {
                    Text(stringResource(R.string.delete))
                }
            },
            dismissButton = {
                TextButton(onClick = { deletingChore = null }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }
}

// ---------------------------------------------------------------------------
// Chore card
// ---------------------------------------------------------------------------

@Composable
private fun ChoreCard(
    chore: ChoreDto,
    onComplete: () -> Unit,
    onDelete: () -> Unit,
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    chore.name,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                chore.next_due_at?.let { due ->
                    val dateStr = due.take(10) // ISO date portion
                    Text(
                        stringResource(R.string.chore_due_label, dateStr),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                chore.interval_days?.let { interval ->
                    Text(
                        stringResource(R.string.chore_interval_label, interval),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                chore.last_completed_at?.let { last ->
                    val dateStr = last.take(10)
                    Text(
                        stringResource(R.string.chore_last_done_label, dateStr),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                chore.notes?.let { notes ->
                    if (notes.isNotBlank()) {
                        Text(
                            notes,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
            Row {
                IconButton(onClick = onComplete) {
                    Icon(
                        Icons.Default.AssignmentTurnedIn,
                        contentDescription = stringResource(R.string.chore_complete),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
                IconButton(onClick = onDelete) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = stringResource(R.string.delete),
                        tint = MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Add Chore bottom sheet
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddChoreSheet(
    sheetState: androidx.compose.material3.SheetState,
    onDismiss: () -> Unit,
    onConfirm: (name: String, notes: String?, intervalDays: Int?, nextDueAt: String?) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var intervalText by remember { mutableStateOf("") }
    var nextDueText by remember { mutableStateOf("") }
    var nameError by remember { mutableStateOf(false) }

    // Reset fields when sheet opens
    LaunchedEffect(Unit) {
        name = ""; notes = ""; intervalText = ""; nextDueText = ""; nameError = false
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                stringResource(R.string.add_chore),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )

            OutlinedTextField(
                value = name,
                onValueChange = { name = it; nameError = false },
                label = { Text(stringResource(R.string.chore_name_hint)) },
                isError = nameError,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            OutlinedTextField(
                value = notes,
                onValueChange = { notes = it },
                label = { Text(stringResource(R.string.chore_notes_hint)) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = false,
                minLines = 2,
            )

            OutlinedTextField(
                value = intervalText,
                onValueChange = { intervalText = it.filter { c -> c.isDigit() } },
                label = { Text(stringResource(R.string.chore_interval_hint)) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                    keyboardType = androidx.compose.ui.text.input.KeyboardType.Number,
                ),
            )

            OutlinedTextField(
                value = nextDueText,
                onValueChange = { nextDueText = it },
                label = { Text(stringResource(R.string.chore_next_due_hint)) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                placeholder = { Text("YYYY-MM-DD") },
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                TextButton(onClick = onDismiss) {
                    Text(stringResource(R.string.cancel))
                }
                Button(
                    onClick = {
                        if (name.isBlank()) {
                            nameError = true
                            return@Button
                        }
                        onConfirm(
                            name.trim(),
                            notes.takeIf { it.isNotBlank() },
                            intervalText.toIntOrNull(),
                            nextDueText.takeIf { it.isNotBlank() },
                        )
                    },
                    modifier = Modifier.padding(start = 8.dp),
                ) {
                    Text(stringResource(R.string.save))
                }
            }
        }
    }
}
