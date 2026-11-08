plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "club.dxtalker.android"
    compileSdk = 35
    defaultConfig {
        applicationId = "club.dxtalker.android"
        minSdk = 29
        targetSdk = 35
        versionCode = 14
        versionName = "0.2.0a20"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}

val syncBrand by tasks.registering(Copy::class) {
    from(rootProject.file("../assets/brand")) { include("icon.png", "logo-dark.png"); rename("icon.png", "dxt_icon.png"); rename("logo-dark.png", "dxt_logo_dark.png") }
    into(layout.buildDirectory.dir("generated/brand-res/drawable"))
}
android.sourceSets.getByName("main").res.srcDir(layout.buildDirectory.dir("generated/brand-res"))
tasks.matching { it.name == "preBuild" }.configureEach { dependsOn(syncBrand) }

val syncCatalog by tasks.registering(Copy::class) {
    from(rootProject.file("../assets/catalog")) { include("clusters.json") }
    into(layout.buildDirectory.dir("generated/catalog-assets/catalog"))
}
android.sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/catalog-assets"))
tasks.matching { it.name == "preBuild" }.configureEach { dependsOn(syncCatalog) }
