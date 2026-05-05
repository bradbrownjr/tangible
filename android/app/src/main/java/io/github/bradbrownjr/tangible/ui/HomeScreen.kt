package io.github.bradbrownjr.tangible.ui

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.ui.screen.about.AboutScreen
import io.github.bradbrownjr.tangible.ui.screen.collections.CollectionListScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.ShoppingListScreen
import io.github.bradbrownjr.tangible.ui.screen.maintenance.MaintenanceScreen
import io.github.bradbrownjr.tangible.ui.screen.settings.SettingsScreen
import kotlinx.coroutines.launch

private data class NavSection(
    val labelRes: Int,
    val icon: ImageVector,
)

private val HOME_SECTIONS = listOf(
    NavSection(R.string.collections, Icons.Default.Folder),
    NavSection(R.string.grocery_list, Icons.AutoMirrored.Filled.List),
    NavSection(R.string.maintenance, Icons.Default.Build),
    NavSection(R.string.settings, Icons.Default.Settings),
    NavSection(R.string.about, Icons.Default.Info),
)

@Composable
fun HomeScreen(
    onOpenCollection: (String) -> Unit,
    onNavigateToCollection: (String) -> Unit,
    onManageStores: () -> Unit,
    onNavigateToScanner: () -> Unit,
    onSignOut: () -> Unit,
    scannedBarcode: String? = null,
    initialSection: Int = 0,
) {
    val pagerState = rememberPagerState(
        initialPage = initialSection,
        pageCount = { HOME_SECTIONS.size },
    )
    val scope = rememberCoroutineScope()

    // Sync pager page to nav bar selection and vice versa
    LaunchedEffect(pagerState.targetPage) { /* pager drives nav bar highlight via currentPage */ }

    Scaffold(
        bottomBar = {
            NavigationBar(windowInsets = WindowInsets(0)) {
                HOME_SECTIONS.forEachIndexed { index, section ->
                    NavigationBarItem(
                        selected = pagerState.currentPage == index,
                        onClick = { scope.launch { pagerState.animateScrollToPage(index) } },
                        icon = { Icon(section.icon, contentDescription = stringResource(section.labelRes)) },
                    )
                }
            }
        },
    ) { innerPadding ->
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.padding(bottom = innerPadding.calculateBottomPadding()),
            beyondViewportPageCount = 1,
        ) { page ->
            when (page) {
                0 -> CollectionListScreen(onOpen = onOpenCollection)
                1 -> ShoppingListScreen(
                    onBack = { scope.launch { pagerState.animateScrollToPage(0) } },
                    showBackButton = false,
                    onNavigateToCollection = onNavigateToCollection,
                    onManageStores = onManageStores,
                    onNavigateToScanner = onNavigateToScanner,
                    scannedBarcode = scannedBarcode,
                )
                2 -> MaintenanceScreen(onBack = {}, showBackButton = false)
                3 -> SettingsScreen(
                    onSignOut = onSignOut,
                    onBack = {},
                    showBackButton = false,
                )
                4 -> AboutScreen(onBack = {}, showBackButton = false)
            }
        }
    }
}
