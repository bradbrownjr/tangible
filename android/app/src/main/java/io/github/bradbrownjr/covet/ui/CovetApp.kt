package io.github.bradbrownjr.covet.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import io.github.bradbrownjr.covet.ui.screen.collection.CollectionDetailScreen
import io.github.bradbrownjr.covet.ui.screen.collections.CollectionListScreen
import io.github.bradbrownjr.covet.ui.screen.login.LoginScreen
import io.github.bradbrownjr.covet.ui.screen.scan.ScannerScreen
import io.github.bradbrownjr.covet.ui.screen.settings.SettingsScreen

object Routes {
    const val LOGIN = "login"
    const val COLLECTIONS = "collections"
    const val COLLECTION_DETAIL = "collection/{id}"
    fun collectionDetail(id: String) = "collection/$id"
    const val SCANNER = "scanner"
    const val SETTINGS = "settings"
}

@Composable
fun CovetApp() {
    val nav = rememberNavController()
    val rootVm: RootViewModel = hiltViewModel()
    val loggedIn by rootVm.loggedIn.collectAsState(initial = null)

    Scaffold { padding ->
        NavHost(
            navController = nav,
            // Wait until we know whether the user has a token before picking a start dest.
            startDestination = when (loggedIn) {
                true  -> Routes.COLLECTIONS
                false -> Routes.LOGIN
                null  -> Routes.LOGIN
            },
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.LOGIN) {
                LoginScreen(onLoggedIn = {
                    nav.navigate(Routes.COLLECTIONS) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                    }
                })
            }
            composable(Routes.COLLECTIONS) {
                CollectionListScreen(
                    onOpen = { nav.navigate(Routes.collectionDetail(it)) },
                    onSettings = { nav.navigate(Routes.SETTINGS) },
                )
            }
            composable(Routes.COLLECTION_DETAIL) { backStack ->
                val id = backStack.arguments?.getString("id").orEmpty()
                CollectionDetailScreen(
                    collectionId = id,
                    onScan = { nav.navigate(Routes.SCANNER) },
                    onBack = { nav.popBackStack() },
                )
            }
            composable(Routes.SCANNER) {
                ScannerScreen(onResult = { code ->
                    // TODO Phase 5.4: prefill new-item dialog with looked-up metadata
                    nav.popBackStack()
                })
            }
            composable(Routes.SETTINGS) {
                SettingsScreen(
                    onSignOut = {
                        nav.navigate(Routes.LOGIN) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                    onBack = { nav.popBackStack() },
                )
            }
        }
    }
}
