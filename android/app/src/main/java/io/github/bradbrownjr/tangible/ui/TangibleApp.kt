package io.github.bradbrownjr.tangible.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.NavType
import androidx.navigation.navArgument
import io.github.bradbrownjr.tangible.nfc.NfcManager
import io.github.bradbrownjr.tangible.ui.screen.about.AboutScreen
import io.github.bradbrownjr.tangible.ui.screen.chores.ChoresScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.ShoppingAisleEditorScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.ShoppingListScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.ShoppingStoreListScreen
import io.github.bradbrownjr.tangible.ui.screen.item.ItemDetailScreen
import io.github.bradbrownjr.tangible.ui.screen.login.LoginScreen
import io.github.bradbrownjr.tangible.ui.screen.scan.ScannerScreen

object Routes {
    const val LOGIN = "login"
    const val HOME = "home"
    const val ABOUT = "about"
    const val GROCERY_STORES = "grocery-stores"
    const val GROCERY_STORE_AISLES = "grocery-stores/{storeId}"
    fun groceryStoreAisles(storeId: String) = "grocery-stores/$storeId"
    const val ITEM_DETAIL = "item/{itemId}"
    fun itemDetailEdit(id: String) = "item/$id"
    const val SCANNER = "scanner"
    const val COLLECTION_CHORES = "collections/{collectionId}/chores?name={collectionName}"
    fun collectionChores(collectionId: String, collectionName: String = "") =
        "collections/$collectionId/chores?name=${java.net.URLEncoder.encode(collectionName, "UTF-8")}"
}

@Composable
fun TangibleApp() {
    val nav = rememberNavController()
    val rootVm: RootViewModel = hiltViewModel()
    val loggedIn by rootVm.loggedIn.collectAsState(initial = null)

    // Navigate to an item when an NFC tag is tapped.
    val nfcItemId by NfcManager.pendingNavigationItemId.collectAsState()
    LaunchedEffect(nfcItemId) {
        val id = nfcItemId ?: return@LaunchedEffect
        NfcManager.pendingNavigationItemId.value = null
        nav.navigate(Routes.itemDetailEdit(id))
    }

    // When the session token is cleared (e.g. 401 from an expired token),
    // navigate back to Login regardless of which screen is currently showing.
    LaunchedEffect(loggedIn) {
        if (loggedIn == false) {
            nav.navigate(Routes.LOGIN) {
                popUpTo(0) { inclusive = true }
            }
        }
    }

    Scaffold { padding ->
        NavHost(
            navController = nav,
            // Wait until we know whether the user has a token before picking a start dest.
            startDestination = when (loggedIn) {
                true  -> Routes.HOME
                false -> Routes.LOGIN
                null  -> Routes.LOGIN
            },
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.LOGIN) {
                LoginScreen(onLoggedIn = {
                    nav.navigate(Routes.HOME) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                    }
                })
            }
            composable(Routes.HOME) { backStack ->
                val scannedBarcode by backStack.savedStateHandle
                    .getStateFlow<String?>("barcode", null)
                    .collectAsState()
                HomeScreen(
                    onItemEdit = { nav.navigate(Routes.itemDetailEdit(it)) },
                    onNavigateToStoreAisles = { storeId -> nav.navigate(Routes.groceryStoreAisles(storeId)) },
                    onNavigateToScanner = { nav.navigate(Routes.SCANNER) },
                    onNavigateToChores = { collId, collName ->
                        nav.navigate(Routes.collectionChores(collId, collName))
                    },
                    onSignOut = {
                        nav.navigate(Routes.LOGIN) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                    onNavigateToAbout = { nav.navigate(Routes.ABOUT) },
                    scannedBarcode = scannedBarcode,
                )
            }
            composable(Routes.GROCERY_STORES) {
                ShoppingStoreListScreen(
                    onBack = { nav.popBackStack() },
                    onOpenStore = { storeId -> nav.navigate(Routes.groceryStoreAisles(storeId)) },
                )
            }
            composable(Routes.GROCERY_STORE_AISLES) {
                ShoppingAisleEditorScreen(onBack = { nav.popBackStack() })
            }
            composable(
                Routes.ITEM_DETAIL,
                arguments = listOf(
                    navArgument("itemId") { type = NavType.StringType },
                ),
            ) {
                ItemDetailScreen(onBack = { nav.popBackStack() })
            }
            composable(Routes.SCANNER) {
                ScannerScreen(onResult = { code ->
                    // A tangible://item/<id> QR code navigates directly to the item.
                    if (code.startsWith("tangible://item/")) {
                        val itemId = code.removePrefix("tangible://item/").trim('/')
                        if (itemId.isNotBlank()) {
                            nav.navigate(Routes.itemDetailEdit(itemId)) {
                                popUpTo(Routes.SCANNER) { inclusive = true }
                            }
                            return@ScannerScreen
                        }
                    }
                    nav.previousBackStackEntry?.savedStateHandle?.set("barcode", code)
                    nav.popBackStack()
                })
            }
            composable(Routes.ABOUT) {
                AboutScreen(onBack = { nav.popBackStack() })
            }
            composable(
                Routes.COLLECTION_CHORES,
                arguments = listOf(
                    navArgument("collectionId") { type = NavType.StringType },
                    navArgument("collectionName") { type = NavType.StringType; defaultValue = "" },
                ),
            ) {
                ChoresScreen(onBack = { nav.popBackStack() })
            }
        }
    }
}


