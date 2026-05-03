package io.github.bradbrownjr.tangible.ui.screen.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.autofill.AutofillNode
import androidx.compose.ui.autofill.AutofillType
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.boundsInWindow
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalAutofill
import androidx.compose.ui.platform.LocalAutofillTree
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import io.github.bradbrownjr.tangible.data.repo.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import android.content.Context
import javax.inject.Inject

data class LoginUi(
    val baseUrl: String = "",
    val username: String = "",
    val password: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val done: Boolean = false,
    val testBusy: Boolean = false,
    val testResult: String? = null,
    val testOk: Boolean = false,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val auth: AuthRepository,
    session: SessionStore,
    @ApplicationContext private val context: Context,
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

    fun update(block: LoginUi.() -> LoginUi) {
        val old = _state.value
        val new = old.block()
        _state.value = if (new.baseUrl != old.baseUrl) new.copy(testResult = null, testOk = false) else new
    }

    fun testConnection() {
        val s = _state.value
        if (s.testBusy || s.baseUrl.isBlank()) return
        _state.value = s.copy(testBusy = true, testResult = null, error = null)
        viewModelScope.launch {
            val (msg, ok) = try {
                auth.testConnection(s.baseUrl)
                Pair(context.getString(R.string.msg_connected_successfully), true)
            } catch (t: Throwable) {
                Pair(t.message ?: context.getString(R.string.msg_connection_failed), false)
            }
            _state.value = _state.value.copy(testBusy = false, testResult = msg, testOk = ok)
        }
    }

    fun submit() {
        val s = _state.value
        if (s.busy) return
        _state.value = s.copy(busy = true, error = null)
        viewModelScope.launch {
            try {
                auth.login(serverUrl = s.baseUrl, username = s.username, password = s.password)
                _state.value = _state.value.copy(busy = false, done = true)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(busy = false, error = t.message ?: context.getString(R.string.msg_login_failed))
            }
        }
    }
}

@OptIn(ExperimentalComposeUiApi::class)
@Composable
private fun AutofillTextField(
    value: String,
    onValueChange: (String) -> Unit,
    autofillTypes: List<AutofillType>,
    label: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    visualTransformation: VisualTransformation = VisualTransformation.None,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    keyboardActions: KeyboardActions = KeyboardActions.Default,
) {
    val autofillNode = AutofillNode(autofillTypes = autofillTypes, onFill = onValueChange)
    val autofill = LocalAutofill.current
    LocalAutofillTree.current += autofillNode
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = label,
        singleLine = true,
        visualTransformation = visualTransformation,
        keyboardOptions = keyboardOptions,
        keyboardActions = keyboardActions,
        modifier = modifier
            .onGloballyPositioned { autofillNode.boundingBox = it.boundsInWindow() }
            .onFocusChanged { focus ->
                autofill?.run {
                    if (focus.isFocused) requestAutofillForNode(autofillNode)
                    else cancelAutofillForNode(autofillNode)
                }
            },
    )
}

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun LoginScreen(onLoggedIn: () -> Unit, vm: LoginViewModel = hiltViewModel()) {
    val s by vm.state.collectAsState()

    LaunchedEffect(s.done) { if (s.done) onLoggedIn() }

    val userFocus = remember { FocusRequester() }
    val passFocus = remember { FocusRequester() }

    Column(
        Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Tangible", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(24.dp))

        OutlinedTextField(
            value = s.baseUrl,
            onValueChange = { v -> vm.update { copy(baseUrl = v) } },
            label = { Text(stringResource(R.string.server_url_hint)) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Uri,
                imeAction = ImeAction.Next,
            ),
            keyboardActions = KeyboardActions(onNext = { userFocus.requestFocus() }),
        )
        Spacer(Modifier.height(4.dp))
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedButton(
                onClick = { vm.testConnection() },
                enabled = s.baseUrl.isNotBlank() && !s.testBusy && !s.busy,
            ) {
                if (s.testBusy) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                } else {
                    Text(stringResource(R.string.test_connection))
                }
            }
            if (s.testResult != null) {
                Text(
                    text = s.testResult!!,
                    color = if (s.testOk) Color(0xFF2E7D32) else MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        Spacer(Modifier.height(8.dp))

        AutofillTextField(
            value = s.username,
            onValueChange = { v -> vm.update { copy(username = v) } },
            autofillTypes = listOf(AutofillType.Username),
            label = { Text(stringResource(R.string.username)) },
            modifier = Modifier
                .fillMaxWidth()
                .focusRequester(userFocus),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Text,
                imeAction = ImeAction.Next,
            ),
            keyboardActions = KeyboardActions(onNext = { passFocus.requestFocus() }),
        )
        Spacer(Modifier.height(8.dp))
        AutofillTextField(
            value = s.password,
            onValueChange = { v -> vm.update { copy(password = v) } },
            autofillTypes = listOf(AutofillType.Password),
            label = { Text(stringResource(R.string.password)) },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier
                .fillMaxWidth()
                .focusRequester(passFocus),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Password,
                imeAction = ImeAction.Done,
            ),
            keyboardActions = KeyboardActions(onDone = { vm.submit() }),
        )
        Spacer(Modifier.height(16.dp))

        if (s.busy) {
            CircularProgressIndicator()
        } else {
            Button(
                onClick = { vm.submit() },
                enabled = s.baseUrl.isNotBlank() && s.username.isNotBlank() && s.password.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.sign_in))
            }
        }
        if (s.error != null) {
            Spacer(Modifier.height(12.dp))
            Text(s.error!!, color = MaterialTheme.colorScheme.error)
        }
    }
}
