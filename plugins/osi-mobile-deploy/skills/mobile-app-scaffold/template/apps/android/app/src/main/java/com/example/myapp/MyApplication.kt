package com.example.myapp

import android.app.Application
import android.util.Log
import com.google.firebase.FirebaseApp

/**
 * Custom Application class for MyApp.
 *
 * Firebase is initialized here rather than via the auto-init provider so that
 * we can guard against a missing google-services.json (e.g. when running a
 * lightweight preview build). Without this guard the app crashes at
 * `FirebaseInitProvider` before `onCreate` even runs.
 */
class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        try {
            if (FirebaseApp.getApps(this).isEmpty()) {
                FirebaseApp.initializeApp(this)
            }
            Log.i(TAG, "Firebase initialized")
        } catch (t: Throwable) {
            Log.w(TAG, "Firebase not initialized (likely missing google-services.json): ${t.message}")
        }
    }

    companion object {
        private const val TAG = "MyApp"
    }
}
