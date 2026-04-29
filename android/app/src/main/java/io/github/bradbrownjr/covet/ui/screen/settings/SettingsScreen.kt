package io.github.bradbrownjr.covet.ui.screen.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import io.github.bradbrownjr.covet.data.auth.SessionStore
import io.github.bradbrownjr.covet.data.repo.AuthRepository
import javax.inject.Inject

data class SettingsUi(val baseUrl: String? = null, val username: String? = null)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    session: SessionStore,
    private val auth: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SettingsUi())
    val state: StateFlow<SettingsUi> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            session.baseUrl.combine(session.username) { url, name -> SettingsUi(url, name) }
                .collect { _state.value = it }
        }
    }

    fun signOut(after: () -> Unit) {
        viewModelScope.launch { auth.logout(); after() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onSignOut: () -> Unit,
    onBack: () -> Unit,
    vm: SettingsViewModel = hiltViewModel(),
) {
    val s by vm.state.collectAsState()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        }
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Server: ${s.baseUrl ?: "—"}")
            Text("Signed in as: ${s.username ?: "—"}")
            HorizontalDivider()
            Button(onClick = { vm.signOut(onSignOut) }) { Text("Sign out") }
        }
    }
}
