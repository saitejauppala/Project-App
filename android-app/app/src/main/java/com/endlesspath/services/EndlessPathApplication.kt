package com.endlesspath.services

import android.app.Application

class EndlessPathApplication : Application() {

    val appContainer: AppContainer by lazy {
        AppContainer(applicationContext)
    }
}
