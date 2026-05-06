package io.github.bradbrownjr.tangible.ui

import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
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
import io.github.bradbrownjr.tangible.ui.screen.about.AboutScreen
import io.github.bradbrownjr.tangible.ui.screen.collections.CollectionsTabsScreen
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
    onOpenItem: (String) -> Unit,
    onItemEdit: (String) -> Unit = {},
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
                0 -> CollectionsTabsScreen(
                    onOpenCollection = onOpenCollection,
                    onOpenItem = onOpenItem,
                    onItemEdit = onItemEdit,
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

