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
import io.github.bradbrownjr.tangible.nfc.NfcManager
import io.github.bradbrownjr.tangible.ui.screen.about.AboutScreen
import io.github.bradbrownjr.tangible.ui.screen.collection.CollectionDetailScreen
import io.github.bradbrownjr.tangible.ui.screen.collections.CollectionListScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.GroceryAisleEditorScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.GroceryListScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.GroceryStoreListScreen
import io.github.bradbrownjr.tangible.ui.screen.item.ItemDetailScreen
import io.github.bradbrownjr.tangible.ui.screen.login.LoginScreen
import io.github.bradbrownjr.tangible.ui.screen.maintenance.MaintenanceScreen
import io.github.bradbrownjr.tangible.ui.screen.scan.ScannerScreen
import io.github.bradbrownjr.tangible.ui.screen.settings.SettingsScreen

object Routes {
    const val LOGIN = "login"
    const val COLLECTIONS = "collections"
    const val GROCERY_LIST = "grocery-list"
    const val GROCERY_STORES = "grocery-stores"
    const val GROCERY_STORE_AISLES = "grocery-stores/{storeId}"
    fun groceryStoreAisles(storeId: String) = "grocery-stores/$storeId"
    const val MAINTENANCE = "maintenance"
    const val COLLECTION_DETAIL = "collection/{id}"
    fun collectionDetail(id: String) = "collection/$id"
    const val ITEM_DETAIL = "item/{itemId}"
    fun itemDetail(id: String) = "item/$id"
    const val SCANNER = "scanner"
    const val SETTINGS = "settings"
    const val ABOUT = "about"
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
        nav.navigate(Routes.itemDetail(id))
    }

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
                    onGroceryList = { nav.navigate(Routes.GROCERY_LIST) },
                    onMaintenance = { nav.navigate(Routes.MAINTENANCE) },
                    onSettings = { nav.navigate(Routes.SETTINGS) },
                    onAbout = { nav.navigate(Routes.ABOUT) },
                )
            }
            composable(Routes.GROCERY_LIST) {
                GroceryListScreen(
                    onBack = { nav.popBackStack() },
                    onNavigateToCollection = { collectionId -> nav.navigate(Routes.collectionDetail(collectionId)) },
                    onManageStores = { nav.navigate(Routes.GROCERY_STORES) },
                )
            }
            composable(Routes.GROCERY_STORES) {
                GroceryStoreListScreen(
                    onBack = { nav.popBackStack() },
                    onOpenStore = { storeId -> nav.navigate(Routes.groceryStoreAisles(storeId)) },
                )
            }
            composable(Routes.GROCERY_STORE_AISLES) {
                GroceryAisleEditorScreen(onBack = { nav.popBackStack() })
            }
            composable(Routes.MAINTENANCE) {
                MaintenanceScreen(onBack = { nav.popBackStack() })
            }
            composable(Routes.COLLECTION_DETAIL) { backStack ->
                val id = backStack.arguments?.getString("id").orEmpty()
                val scannedBarcode by backStack.savedStateHandle
                    .getStateFlow<String?>("barcode", null)
                    .collectAsState()
                CollectionDetailScreen(
                    collectionId = id,
                    scannedBarcode = scannedBarcode,
                    onScan = { nav.navigate(Routes.SCANNER) },
                    onItem = { itemId -> nav.navigate(Routes.itemDetail(itemId)) },
                    onBack = { nav.popBackStack() },
                )
            }
            composable(Routes.ITEM_DETAIL) {
                ItemDetailScreen(onBack = { nav.popBackStack() })
            }
            composable(Routes.SCANNER) {
                ScannerScreen(onResult = { code ->
                    // A tangible://item/<id> QR code navigates directly to the item.
                    if (code.startsWith("tangible://item/")) {
                        val itemId = code.removePrefix("tangible://item/").trim('/')
                        if (itemId.isNotBlank()) {
                            nav.navigate(Routes.itemDetail(itemId)) {
                                popUpTo(Routes.SCANNER) { inclusive = true }
                            }
                            return@ScannerScreen
                        }
                    }
                    nav.previousBackStackEntry?.savedStateHandle?.set("barcode", code)
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
            composable(Routes.ABOUT) {
                AboutScreen(onBack = { nav.popBackStack() })
            }
        }
    }
}


