package io.github.bradbrownjr.tangible.ui

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import io.github.bradbrownjr.tangible.data.auth.SessionStore
import javax.inject.Inject

@HiltViewModel
class RootViewModel @Inject constructor(session: SessionStore) : ViewModel() {
    val loggedIn: Flow<Boolean> = session.token.map { !it.isNullOrBlank() }
}
