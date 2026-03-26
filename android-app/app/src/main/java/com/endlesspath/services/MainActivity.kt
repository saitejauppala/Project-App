package com.endlesspath.services

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.endlesspath.services.ui.EndlessPathApp
import com.endlesspath.services.ui.theme.EndlessPathTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EndlessPathTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    EndlessPathApp()
                }
            }
        }
    }
}

