package com.example.myapp.ui.theme

import androidx.compose.ui.graphics.Color

// AI OSI URI ブランドを意識した Material3 パレット（scaffold 用の最小構成）。
// 本番テーマが必要になったらここを起点に上書きする。
val Primary = Color(0xFF6200EE)
val OnPrimary = Color(0xFFFFFFFF)
val PrimaryContainer = Color(0xFFEADDFF)
val OnPrimaryContainer = Color(0xFF21005D)

val Secondary = Color(0xFF625B71)
val OnSecondary = Color(0xFFFFFFFF)

val Background = Color(0xFFFFFBFE)
val OnBackground = Color(0xFF1C1B1F)
val SurfaceLight = Color(0xFFFFFBFE)
val OnSurfaceLight = Color(0xFF1C1B1F)

// ダーク用（values-night/themes.xml と揃える想定）。
val PrimaryDark = Color(0xFFD0BCFF)
val OnPrimaryDark = Color(0xFF381E72)
val BackgroundDark = Color(0xFF1C1B1F)
val OnBackgroundDark = Color(0xFFE6E1E5)
val SurfaceDark = Color(0xFF1C1B1F)
val OnSurfaceDark = Color(0xFFE6E1E5)
