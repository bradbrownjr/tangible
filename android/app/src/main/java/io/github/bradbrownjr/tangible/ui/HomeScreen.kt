package io.github.bradbrownjr.tangible.ui

import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.AssignmentTurnedIn
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Store
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import io.github.bradbrownjr.tangible.R
import io.github.bradbrownjr.tangible.ui.screen.alerts.AlertsScreen
import io.github.bradbrownjr.tangible.ui.screen.collections.CollectionsTabsScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.ShoppingListScreen
import io.github.bradbrownjr.tangible.ui.screen.grocery.ShoppingStoreListScreen
import io.github.bradbrownjr.tangible.ui.screen.home.HomeTabScreen
import io.github.bradbrownjr.tangible.ui.screen.maintenance.MaintenanceScreen
import io.github.bradbrownjr.tangible.ui.screen.settings.SettingsScreen
import kotlinx.coroutines.launch

private data class NavSection(
    val labelRes: Int,
    val icon: ImageVector,
)

private val HOME_SECTIONS = listOf(
    NavSection(R.string.home_tab, Icons.Default.Home),
    NavSection(R.string.collections, Icons.Default.Folder),
    NavSection(R.string.grocery_list, Icons.AutoMirrored.Filled.List),
    NavSection(R.string.stores, Icons.Default.Store),
    NavSection(R.string.tasks, Icons.Default.AssignmentTurnedIn),
    NavSection(R.string.alerts, Icons.Default.Notifications),
    NavSection(R.string.settings, Icons.Default.Settings),
)

@Composable
fun HomeScreen(
    onItemEdit: (String) -> Unit = {},
    onNavigateToStoreAisles: (storeId: String) -> Unit,
    onNavigateToScanner: () -> Unit,
    onNavigateToChores: (collectionId: String, collectionName: String) -> Unit = { _, _ -> },
    onSignOut: () -> Unit,
    onNavigateToAbout: () -> Unit = {},
    scannedBarcode: String? = null,
    initialSection: Int = 0,
) {
    val pagerState = rememberPagerState(
        initialPage = initialSection,
        pageCount = { HOME_SECTIONS.size },
    )
    val scope = rememberCoroutineScope()
    // 80dp of accumulated drag triggers a section change on the nav bar.
    val dragThresholdPx = with(LocalDensity.current) { 80.dp.toPx() }
    var navDragAccum by remember { mutableFloatStateOf(0f) }

    Scaffold(
        bottomBar = {
            NavigationBar(
                windowInsets = WindowInsets(0),
                modifier = Modifier.pointerInput(Unit) {
                    detectHorizontalDragGestures(
                        onDragEnd = { navDragAccum = 0f },
                        onDragCancel = { navDragAccum = 0f },
                        onHorizontalDrag = { _, dragAmount ->
                            navDragAccum += dragAmount
                            when {
                                navDragAccum < -dragThresholdPx -> {
                                    navDragAccum = 0f
                                    scope.launch {
                                        pagerState.animateScrollToPage(
                                            (pagerState.currentPage + 1).coerceAtMost(HOME_SECTIONS.size - 1)
                                        )
                                    }
                                }
                                navDragAccum > dragThresholdPx -> {
                                    navDragAccum = 0f
                                    scope.launch {
                                        pagerState.animateScrollToPage(
                                            (pagerState.currentPage - 1).coerceAtLeast(0)
                                        )
                                    }
                                }
                            }
                        },
                    )
                },
            ) {
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
        // userScrollEnabled = false: the outer pager no longer intercepts content-area swipes.
        // Sections with inner tabs (e.g. Lists) let their own HorizontalPager handle the gesture.
        // Section navigation from the content area is done by swiping the nav bar below.
        HorizontalPager(
            state = pagerState,
            userScrollEnabled = false,
            modifier = Modifier
                .fillMaxSize()
                .padding(bottom = innerPadding.calculateBottomPadding()),
            beyondViewportPageCount = 1,
        ) { page ->
            when (page) {
                0 -> HomeTabScreen(
                    onItemEdit = onItemEdit,
                    onJumpTo = { idx -> scope.launch { pagerState.animateScrollToPage(idx) } },
                )
                1 -> CollectionsTabsScreen(
                    onItemEdit = onItemEdit,
                    onNavigateToChores = onNavigateToChores,
                    onNavigateToScanner = onNavigateToScanner,
                    onSwipeLeft = {
                        scope.launch {
                            pagerState.animateScrollToPage(
                                (pagerState.currentPage + 1).coerceAtMost(HOME_SECTIONS.size - 1)
                            )
                        }
                    },
                    onSwipeRight = {
                        scope.launch {
                            pagerState.animateScrollToPage(
                                (pagerState.currentPage - 1).coerceAtLeast(0)
                            )
                        }
                    },
                )
                2 -> ShoppingListScreen(
                    onBack = { scope.launch { pagerState.animateScrollToPage(0) } },
                    showBackButton = false,
                    onManageStores = { scope.launch { pagerState.animateScrollToPage(3) } },
                    onNavigateToScanner = onNavigateToScanner,
                    scannedBarcode = scannedBarcode,
                )
                3 -> ShoppingStoreListScreen(
                    onBack = {},
                    showBackButton = false,
                    onOpenStore = onNavigateToStoreAisles,
                )
                4 -> MaintenanceScreen(onBack = {}, showBackButton = false, onNavigateToChores = onNavigateToChores)
                5 -> AlertsScreen(onBack = {}, showBackButton = false)
                6 -> SettingsScreen(
                    onSignOut = onSignOut,
                    onBack = {},
                    onNavigateToAbout = onNavigateToAbout,
                    showBackButton = false,
                )
            }
        }
    }
}

