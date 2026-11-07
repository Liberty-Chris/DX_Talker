package club.dxtalker.android

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.*
import androidx.test.espresso.matcher.ViewMatchers.*
import org.junit.Test
import org.junit.Before
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class NavigationTests {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    @Before fun reset() {
        context.stopService(Intent(context,ListenerService::class.java))
        context.getSharedPreferences("dx",Context.MODE_PRIVATE).edit().clear().putString("appearance","Dark").commit()
        if(android.os.Build.VERSION.SDK_INT>=33) InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand("pm grant ${context.packageName} android.permission.POST_NOTIFICATIONS").close()
    }
    private fun screenshot(name: String) {
        val image=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        val dir=File(context.getExternalFilesDir(null),"screenshots").apply { mkdirs() }
        File(dir,"$name.png").outputStream().use { image.compress(Bitmap.CompressFormat.PNG,100,it) };image.recycle()
    }
    @Test fun navigationBackDraftsAndRecreation() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            onView(withText("Recent spots")).check(matches(isDisplayed())); screenshot("listen-dark")
            onView(withText("Clusters")).perform(click())
            onView(withText("Add cluster")).perform(click())
            onView(withText("My cluster")).perform(replaceText("Dad portable"),closeSoftKeyboard())
            scenario.recreate()
            onView(withText("Dad portable")).check(matches(isDisplayed())); screenshot("edit-cluster")
            androidx.test.espresso.Espresso.pressBack()
            onView(withText("Bring your clusters along")).check(matches(isDisplayed()))
            onView(withText("Settings")).perform(click())
            onView(withText("Bands, modes and activities")).perform(click())
            onView(withText("Bands: All")).perform(click())
            onView(withText("20m")).perform(click())
            onView(withText("Use selection")).perform(click())
            onView(withText("Bands: 20m")).check(matches(isDisplayed())); screenshot("filters")
            androidx.test.espresso.Espresso.pressBack()
            onView(withText("Voice and announcement")).perform(click())
            onView(withText("Announcement builder")).check(matches(isDisplayed())); screenshot("speech")
            androidx.test.espresso.Espresso.pressBack()
            onView(withText("Listen")).perform(click())
            onView(withText("Recent spots")).check(matches(isDisplayed()))
        }
    }
    @Test fun lightAppearanceHasWorkingNavigation() {
        context.getSharedPreferences("dx",Context.MODE_PRIVATE).edit().putString("appearance","Light").commit()
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            onView(withText("Recent spots")).check(matches(isDisplayed())); screenshot("listen-light")
            onView(withText("Settings")).perform(click()); screenshot("settings-light")
            androidx.test.espresso.Espresso.pressBack(); onView(withText("Recent spots")).check(matches(isDisplayed()))
        }
    }
}
