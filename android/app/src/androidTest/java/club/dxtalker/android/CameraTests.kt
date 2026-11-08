package club.dxtalker.android

import android.Manifest
import android.content.pm.PackageManager
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.matcher.RootMatchers.isDialog
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CameraTests {
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private fun permissionButton(id:String) {
        val automation=instrumentation.uiAutomation
        automation.serviceInfo=automation.serviceInfo.apply { flags=flags or android.accessibilityservice.AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS }
        val deadline=SystemClock.uptimeMillis()+10000
        while(SystemClock.uptimeMillis()<deadline) {
            fun find(node:AccessibilityNodeInfo?):AccessibilityNodeInfo? {
                if(node==null)return null
                if(node.viewIdResourceName?.endsWith("/$id")==true)return node
                for(i in 0 until node.childCount) { val found=find(node.getChild(i));if(found!=null)return found }
                return null
            }
            val node=find(automation.rootInActiveWindow)
            if(node!=null && node.isVisibleToUser) { assertTrue(node.performAction(AccessibilityNodeInfo.ACTION_CLICK));return }
            SystemClock.sleep(50)
        }
        fail("Android camera permission button did not appear: $id")
    }
    @Test fun cameraDenialGrantPreviewAndReturn() {
        assertEquals("Fresh test installation must start without camera access",PackageManager.PERMISSION_DENIED,context.checkSelfPermission(Manifest.permission.CAMERA))
        context.getSharedPreferences("dx",0).edit().clear().putBoolean("diagnostics",true).commit()
        if(android.os.Build.VERSION.SDK_INT>=33) android.os.ParcelFileDescriptor.AutoCloseInputStream(instrumentation.uiAutomation.executeShellCommand("pm grant ${context.packageName} android.permission.POST_NOTIFICATIONS")).use { it.readBytes() }
        ActivityScenario.launch(QrScanActivity::class.java).use {
            onView(withSubstring("Camera permission is unavailable")).check(matches(isDisplayed()))
            onView(withText("Close scanner")).perform(click())
        }
        ActivityScenario.launch(MainActivity::class.java).use {
            onView(withText("Clusters")).perform(click())
            onView(withText("Scan desktop QR collection")).perform(click())
            permissionButton("permission_deny_button")
            onView(withText("Camera permission needed")).inRoot(isDialog()).check(matches(isDisplayed()))
            onView(withText("Close")).inRoot(isDialog()).perform(click())
            onView(withText("Scan desktop QR collection")).perform(click())
            permissionButton("permission_allow_foreground_only_button")
            onView(withText("Close scanner")).check(matches(isDisplayed()))
            val deadline=SystemClock.uptimeMillis()+10000
            val log=java.io.File(context.filesDir,"diagnostics/events.jsonl")
            while(SystemClock.uptimeMillis()<deadline && (!log.exists() || !log.readText().contains("qr_camera_preview_started"))) SystemClock.sleep(100)
            assertTrue("Virtual camera preview must actually start",log.exists() && log.readText().contains("qr_camera_preview_started"))
            onView(withText("Close scanner")).perform(click())
            onView(withText("Scan desktop QR collection")).check(matches(isDisplayed()))
        }
    }
}
