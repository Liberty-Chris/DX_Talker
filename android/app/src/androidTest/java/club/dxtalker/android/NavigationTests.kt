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
import org.junit.Assert.*
import org.junit.Test
import org.junit.Before
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class NavigationTests {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    @Before fun reset() {
        context.stopService(Intent(context,ListenerService::class.java))
        InstrumentationRegistry.getInstrumentation().runOnMainSync { ListenerService.muted=false;ListenerService.paused=false }
        context.getSharedPreferences("dx",Context.MODE_PRIVATE).edit().clear().putString("appearance","Dark").commit()
        if(android.os.Build.VERSION.SDK_INT>=33) InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand("pm grant ${context.packageName} android.permission.POST_NOTIFICATIONS").close()
    }
    private fun screenshot(name: String) {
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        android.os.SystemClock.sleep(250)
        val image=InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        val values=android.content.ContentValues().apply {
            put(android.provider.MediaStore.Images.Media.DISPLAY_NAME,"$name.png")
            put(android.provider.MediaStore.Images.Media.MIME_TYPE,"image/png")
            put(android.provider.MediaStore.Images.Media.RELATIVE_PATH,"Pictures/DXTalker-verification")
        }
        val uri=context.contentResolver.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values)!!
        context.contentResolver.openOutputStream(uri)!!.use { image.compress(Bitmap.CompressFormat.PNG,100,it) };image.recycle()
    }
    @Test fun navigationBackDraftsAndRecreation() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            onView(withText("Recent spots")).check(matches(isDisplayed())); screenshot("listen-dark")
            onView(withText("Clusters")).perform(click())
            onView(withText("Add cluster")).perform(click())
            onView(withContentDescription("Profile name")).perform(replaceText("Dad portable"),closeSoftKeyboard())
            scenario.recreate()
            onView(withText("Dad portable")).check(matches(isDisplayed())); screenshot("edit-cluster")
            androidx.test.espresso.Espresso.pressBack()
            onView(withText("Bring your clusters along")).check(matches(isDisplayed()))
            onView(withText("Settings")).perform(click())
            onView(withText("What do you want to hear?")).perform(click())
            onView(withText("Bands: All")).perform(click())
            onView(withText("20m")).perform(click())
            onView(withText("Use selection")).perform(click())
            onView(withText("Bands: 20m")).check(matches(isDisplayed())); screenshot("filters")
            androidx.test.espresso.Espresso.pressBack()
            onView(withText("Voice and announcement")).perform(click())
            onView(withText("Announcement builder")).check(matches(isDisplayed()))
            onView(withText("Intro")).check(matches(isDisplayed()))
            onView(withText("Frequency")).check(matches(isDisplayed()))
            onView(withText("Callsign")).check(matches(isDisplayed()))
            onView(withContentDescription("Move intro down")).perform(click())
            onView(withContentDescription("Move intro down")).perform(click())
            onView(withText("Save announcement")).perform(scrollTo(),click())
            assertEquals("{frequency} {unit}. {call}. New DX on.",context.getSharedPreferences("dx",Context.MODE_PRIVATE).getString("format",""))
            androidx.test.espresso.Espresso.pressBack()
            onView(withText("Voice and announcement")).perform(click())
            onView(withContentDescription("Intro phrase")).check(matches(withText("New DX on")))
            onView(withText("Intro")).check(matches(isDisplayed())); screenshot("speech")
            androidx.test.espresso.Espresso.pressBack()
            onView(withText("Listen")).perform(click())
            onView(withText("Recent spots")).check(matches(isDisplayed()))
        }
    }
    @Test fun navigationAndFilterApplyKeepTheSameLiveConnection() {
        val server=java.net.ServerSocket(0)
        val accepted=java.util.concurrent.CountDownLatch(1)
        val release=java.util.concurrent.CountDownLatch(1)
        val closed=java.util.concurrent.atomic.AtomicBoolean(false)
        val received=java.util.concurrent.atomic.AtomicBoolean(false)
        val probed=java.util.concurrent.CountDownLatch(1)
        val worker=Thread {
            try { server.accept().use { socket ->
                socket.soTimeout=200
                val stamp=java.time.format.DateTimeFormatter.ofPattern("HHmm'Z'").withZone(java.time.ZoneOffset.UTC).format(java.time.Instant.now())
                socket.getOutputStream().write("DX de N0CALL: 14074 WB4IUY FT8 POTA $stamp\r\n".toByteArray());socket.getOutputStream().flush();accepted.countDown()
                while(release.count>0) {
                    try { if(socket.getInputStream().read()<0) { closed.set(true);break } else received.set(true);probed.countDown() }
                    catch(_:java.net.SocketTimeoutException) { probed.countDown() }
                }
            } } catch(_:Exception) { if(release.count>0)closed.set(true) }
        };worker.start()
        context.getSharedPreferences("dx",Context.MODE_PRIVATE).edit().putString("host","127.0.0.1").putString("port",server.localPort.toString()).putString("call","KF4DBX").commit()
        InstrumentationRegistry.getInstrumentation().runOnMainSync { ListenerService.muted=true }
        try {
            ActivityScenario.launch(MainActivity::class.java).use {
                onView(withText("Start listening")).perform(click())
                assertTrue(accepted.await(5,java.util.concurrent.TimeUnit.SECONDS))
                onView(withText("Settings")).perform(click())
                onView(withText("Stop listening")).check(matches(isDisplayed()))
                onView(withText("What do you want to hear?")).perform(click())
                onView(withText("Apply filters")).check(matches(isDisplayed())).perform(click())
                assertTrue(ListenerService.listeningActive)
                assertFalse("Navigation or filtering closed the original TCP session",closed.get())
                assertTrue(probed.await(3,java.util.concurrent.TimeUnit.SECONDS))
                assertFalse("A spotter callsign or spot comment triggered an unsolicited command",received.get())
                onView(withText("Recent spots")).check(matches(isDisplayed()))
                onView(withText("Stop listening")).perform(click())
            }
        } finally { release.countDown();server.close();worker.join(1000);context.stopService(Intent(context,ListenerService::class.java)) }
    }
    @Test fun liveListKeepsUsefulSpaceAboveSystemNavigation() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                val decor=activity.window.decorView
                val all=mutableListOf<android.view.View>()
                fun collect(view:android.view.View) { all.add(view);if(view is android.view.ViewGroup)for(i in 0 until view.childCount)collect(view.getChildAt(i)) }
                collect(decor)
                val list=all.filterIsInstance<android.widget.ScrollView>().single()
                val visible=android.graphics.Rect();list.getGlobalVisibleRect(visible)
                assertTrue("Live spots must retain a useful scrolling area",visible.height()>=decor.height/4)
                val navigation=all.filterIsInstance<android.widget.Button>().first { it.text=="Settings" }
                val position=IntArray(2);navigation.getLocationOnScreen(position)
                assertTrue("System navigation must not overlap app navigation",position[1]+navigation.height<=decor.height)
            }
            screenshot("live-list-space")
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
