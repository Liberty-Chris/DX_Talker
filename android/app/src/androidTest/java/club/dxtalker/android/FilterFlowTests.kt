package club.dxtalker.android

import android.content.Context
import android.content.Intent
import android.os.SystemClock
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.Espresso.onData
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import org.hamcrest.Matchers.equalTo
import org.hamcrest.Matchers.allOf
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.net.ServerSocket
import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class FilterFlowTests {
    private val instrumentation get()=InstrumentationRegistry.getInstrumentation()
    private val context get()=instrumentation.targetContext
    @Before fun reset() {
        context.stopService(Intent(context,ListenerService::class.java));instrumentation.waitForIdleSync()
        context.getSharedPreferences("dx",Context.MODE_PRIVATE).edit().clear().putString("appearance","Dark").commit()
        instrumentation.runOnMainSync { ListenerService.muted=true;ListenerService.paused=false }
        if(android.os.Build.VERSION.SDK_INT>=33)android.os.ParcelFileDescriptor.AutoCloseInputStream(instrumentation.uiAutomation.executeShellCommand("pm grant ${context.packageName} android.permission.POST_NOTIFICATIONS")).use { it.readBytes() }
    }
    private fun await(message:String, condition:()->Boolean) {
        val deadline=SystemClock.uptimeMillis()+8000
        while(SystemClock.uptimeMillis()<deadline) { if(condition())return;SystemClock.sleep(50) }
        assertTrue(message,condition())
    }
    private fun rows()=synchronized(ListenerService.spots){ListenerService.spots.toList()}
    @Test fun savedBandModeAndLicenseChoicesFilterTheLiveFeedWithoutReconnecting() {
        val server=ServerSocket(0);val batches=LinkedBlockingQueue<String>();val done=AtomicBoolean(false);val closed=AtomicBoolean(false);val accepted=CountDownLatch(1)
        val worker=Thread {
            try { server.accept().use { socket ->
                socket.soTimeout=50;accepted.countDown()
                while(!done.get()) {
                    batches.poll(50,TimeUnit.MILLISECONDS)?.let { batch ->
                        val stamp=java.time.format.DateTimeFormatter.ofPattern("HHmm'Z'").withZone(java.time.ZoneOffset.UTC).format(java.time.Instant.now())
                        val text=batch.lines().joinToString("\r\n",postfix="\r\n") { "DX de N0CALL: $it $stamp" }
                        socket.getOutputStream().write(text.toByteArray());socket.getOutputStream().flush()
                    }
                    try { if(socket.getInputStream().read()<0) { closed.set(true);break } }catch(_:java.net.SocketTimeoutException){}
                }
            } }catch(_:Exception){if(!done.get())closed.set(true)}
        };worker.start()
        val prefs=context.getSharedPreferences("dx",Context.MODE_PRIVATE)
        prefs.edit().putString("host","127.0.0.1").putString("port",server.localPort.toString()).putString("call","KF4DBX").commit()
        try {
            ActivityScenario.launch(MainActivity::class.java).use {
                onView(withText("Start listening")).perform(click());assertTrue(accepted.await(5,TimeUnit.SECONDS))
                val token=ListenerService.connectionToken
                onView(withText("Filters")).perform(click())
                onView(withText("Apply filters")).check(matches(isDisplayed()))
                onView(withText("Bands: All")).perform(scrollTo(),click());onView(withText("20m")).perform(click());onView(withText("Use selection")).perform(click())
                onView(withText("Modes: All")).perform(scrollTo(),click());onView(withText("CW")).perform(click());onView(withText("Use selection")).perform(click())
                assertEquals("",prefs.getString("filter_bands",""))
                onView(withText("Apply filters")).check(matches(isDisplayed())).perform(click())
                await("Saved bands reach the live service") { prefs.getString("filter_bands","")=="20m" && ListenerService.listeningActive && ListenerService.status.startsWith("Filters applied") }
                batches.put("14025 K1AAA CW\n7025 K2BBB CW")
                await("20m displayed and 40m rejected") { rows().any { it.startsWith("K1AAA ") } && synchronized(ListenerService.hidden){ListenerService.hidden["Band"]==1} }
                assertEquals(1,rows().size);assertFalse(rows().single().contains("General"))
                onView(withContentDescription("Change frequency units")).perform(click());onView(withText("MHz")).perform(click())
                await("Existing rows convert without reconnect") { rows().singleOrNull()?.contains("14.025 MHz")==true }
                onView(withText("Filters")).perform(click())
                onView(withText("Modes: CW")).perform(scrollTo(),click());onView(withText("CW")).perform(click());onView(withText("SSB")).perform(click());onView(withText("Use selection")).perform(click())
                onView(withContentDescription("FCC license class")).perform(scrollTo(),click());onData(equalTo("General")).perform(click())
                onView(withText("Apply filters")).check(matches(isDisplayed())).perform(click())
                await("Old displayed rows clear when new filters apply") { rows().isEmpty() && ListenerService.status.startsWith("Filters applied") }
                batches.put("14225 K3CCC SSB\n14025 K4DDD CW\n14200 K5EEE SSB\n7225 K6FFF SSB")
                await("Mode, license and band gates all apply") { rows().any { it.startsWith("K3CCC ") } && synchronized(ListenerService.hidden){ListenerService.hidden["Mode"]==1 && ListenerService.hidden["Outside selected license segments"]==1 && ListenerService.hidden["Band"]==1} }
                assertEquals(1,rows().size);assertTrue(rows().single().contains("14.225 MHz"))
                assertEquals(token,ListenerService.connectionToken);assertFalse(closed.get())
                onView(withText("Stop listening")).perform(click())
            }
        }finally{done.set(true);server.close();worker.interrupt();worker.join(1500);context.stopService(Intent(context,ListenerService::class.java))}
    }
    @Test fun presetUnitsUseTheCanonicalDraftAndApplyStaysVisible() {
        val prefs=context.getSharedPreferences("dx",Context.MODE_PRIVATE)
        val values=ListeningSettings.json { key -> if(key=="frequency_unit")"kHz"else ListeningSettings.defaults[key].orEmpty() }
        prefs.edit().putString("frequency_unit","MHz").putString("listening_presets",org.json.JSONObject().put("kHz preset",values).toString()).commit()
        ActivityScenario.launch(MainActivity::class.java).use {
            onView(withText("Filters")).perform(click())
            onView(allOf(withText("Listening presets"),isAssignableFrom(android.widget.Button::class.java))).perform(scrollTo(),click())
            onView(withContentDescription("Saved listening preset")).perform(scrollTo(),click());onData(equalTo("kHz preset")).perform(click())
            onView(withText("Load preset")).perform(scrollTo(),click())
            onView(withText("Apply filters")).check(matches(isDisplayed())).perform(click())
            assertEquals("kHz",prefs.getString("frequency_unit",""))
            onView(withContentDescription("Change frequency units")).check(matches(withText("kHz")))
        }
    }
}
