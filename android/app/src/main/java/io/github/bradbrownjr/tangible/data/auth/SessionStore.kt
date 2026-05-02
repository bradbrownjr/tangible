package io.github.bradbrownjr.tangible.data.auth

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.authStore by preferencesDataStore(name = "auth")

private val KEY_BASE_URL = stringPreferencesKey("base_url")
private val KEY_TOKEN    = stringPreferencesKey("api_token")
private val KEY_USERNAME = stringPreferencesKey("username")
private val KEY_THEME    = stringPreferencesKey("theme_mode")

/**
 * Persistent server URL + bearer token + (display) username.
 *
 * Uses DataStore preferences. Excluded from auto-backup via backup_rules.xml.
 * The token is stored in plaintext on disk; for production we'd promote to
 * EncryptedSharedPreferences or the Keystore-wrapped DataStore once available.
 */
@Singleton
class SessionStore @Inject constructor(@ApplicationContext private val ctx: Context) {

    val baseUrl:   Flow<String?> = ctx.authStore.data.map { it[KEY_BASE_URL] }
    val token:     Flow<String?> = ctx.authStore.data.map { it[KEY_TOKEN] }
    val username:  Flow<String?> = ctx.authStore.data.map { it[KEY_USERNAME] }
    val themeMode: Flow<String?> = ctx.authStore.data.map { it[KEY_THEME] }

    suspend fun save(baseUrl: String, token: String, username: String) {
        ctx.authStore.edit { p ->
            p[KEY_BASE_URL] = baseUrl.normalizedBaseUrl()
            p[KEY_TOKEN] = token
            p[KEY_USERNAME] = username
        }
    }

    suspend fun clear() {
        ctx.authStore.edit { p ->
            p.remove(KEY_TOKEN)
            p.remove(KEY_USERNAME)
            // Keep baseUrl and theme so the user doesn't have to retype on re-login.
        }
    }

    suspend fun saveTheme(mode: String) {
        ctx.authStore.edit { p -> p[KEY_THEME] = mode }
    }

    /** Returns true when the user has a saved bearer token (i.e. is logged in). */
    suspend fun isLoggedIn(): Boolean = token.first() != null
}

internal fun String.normalizedBaseUrl(): String {
    val trimmed = trim().trimEnd('/')
    return if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) trimmed
    else "https://$trimmed"
}
