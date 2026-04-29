package io.github.bradbrownjr.covet.ui.screen.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.text.KeyboardOptions
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import io.github.bradbrownjr.covet.data.auth.SessionStore
import io.github.bradbrownjr.covet.data.repo.AuthRepository
import javax.inject.Inject

data class LoginUi(
    val baseUrl: String = "",
    val username: String = "",
    val password: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val done: Boolean = false,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val auth: AuthRepository,
    session: SessionStore,
    @Suppress("UNUSED_PARAMETER") savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val _state = MutableStateFlow(LoginUi())
    val state: StateFlow<LoginUi> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            session.baseUrl.first().let { saved ->
                if (!saved.isNullOrBlank()) _state.value = _state.value.copy(baseUrl = saved)
            }
        }
    }

    fun update(block: LoginUi.() -> LoginUi) { _state.value = _state.value.block() }

    fun submit() {
        val s = _state.value
        if (s.busy) return
        _state.value = s.copy(busy = true, error = null)
        viewModelScope.launch {
            try {
                auth.login(serverUrl = s.baseUrl, username = s.username, password = s.password)
                _state.value = _state.value.copy(busy = false, done = true)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(busy = false, error = t.message ?: "Login failed")
            }
        }
    }
}

@Composable
fun LoginScreen(onLoggedIn: () -> Unit, vm: LoginViewModel = hiltViewModel()) {
    val s by vm.state.collectAsState()

    LaunchedEffect(s.done) { if (s.done) onLoggedIn() }

    Column(
        Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Covet", style = androidx.compose.material3.MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(24.dp))

        OutlinedTextField(
            value = s.baseUrl,
            onValueChange = { v -> vm.update { copy(baseUrl = v) } },
            label = { Text("Server URL (e.g. https://covet.example.com)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = s.username,
            onValueChange = { v -> vm.update { copy(username = v) } },
            label = { Text("Username") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = s.password,
            onValueChange = { v -> vm.update { copy(password = v) } },
            label = { Text("Password") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(16.dp))

        if (s.busy) {
            CircularProgressIndicator()
        } else {
            Button(onClick = { vm.submit() }, enabled = s.baseUrl.isNotBlank() && s.username.isNotBlank() && s.password.isNotBlank()) {
                Text("Sign in")
            }
        }
        if (s.error != null) {
            Spacer(Modifier.height(12.dp))
            Text(s.error!!, color = androidx.compose.material3.MaterialTheme.colorScheme.error)
        }
    }
}
