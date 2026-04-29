package io.github.bradbrownjr.covet

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import dagger.hilt.android.AndroidEntryPoint
import io.github.bradbrownjr.covet.ui.CovetApp
import io.github.bradbrownjr.covet.ui.theme.CovetTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            CovetTheme {
                CovetApp()
            }
        }
    }
}
