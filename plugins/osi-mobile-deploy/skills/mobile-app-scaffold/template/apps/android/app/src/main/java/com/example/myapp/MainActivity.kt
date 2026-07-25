package com.example.myapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.example.myapp.ui.MainScreen
import com.example.myapp.ui.theme.AppTheme

// scaffold のエントリポイント。実プロダクトでは Navigation を差し込む想定。
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AppTheme { MainScreen() }
        }
    }
}
