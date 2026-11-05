package club.dxtalker.android

import android.Manifest
import android.app.Activity
import android.content.*
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var spotsView: LinearLayout
    private lateinit var root: LinearLayout
    private val prefs by lazy { getSharedPreferences("dx", MODE_PRIVATE) }
    private val background = Color.rgb(14, 22, 34)
    private val surface = Color.rgb(29, 43, 60)
    private val accent = Color.rgb(109, 193, 245)
    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) { refresh() }
    }
    private fun label(text: String, size: Float = 16f, color: Int = Color.WHITE): TextView =
        TextView(this).apply { this.text = text; textSize = size; setTextColor(color); setPadding(8, 12, 8, 12) }
    private fun button(text: String, action: () -> Unit): Button =
        Button(this).apply { this.text = text; setOnClickListener { action() }; isAllCaps = false }
    private fun section(title: String): LinearLayout {
        root.addView(label(title, 21f, accent).apply { setTypeface(null, Typeface.BOLD) })
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(14, 10, 14, 12)
            setBackgroundColor(surface)
            root.addView(this)
        }
    }
    private fun edit(container: LinearLayout, name: String, value: String, password: Boolean = false): EditText {
        container.addView(label(name, 13f, accent))
        return EditText(this).apply {
            setText(value)
            setTextColor(Color.WHITE)
            setHintTextColor(Color.LTGRAY)
            setSingleLine(true)
            if (password) inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            container.addView(this)
        }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = background
        window.navigationBarColor = background
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 100)
        }
        showHome()
    }
    private fun command(action: String) {
        val intent = Intent(this, ListenerService::class.java).setAction(action)
        if (action == "start") startForegroundService(intent) else startService(intent)
        refresh()
    }
    private fun showHome() {
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(background) }
        val scroll = ScrollView(this).apply { fillViewport = true; addView(root) }
        setContentView(scroll)
        root.addView(label("DXt", 38f, accent).apply { setTypeface(null, Typeface.BOLD) })
        root.addView(label("DX Talker  |  Android listener", 14f, Color.LTGRAY))
        val listening = section("Listening")
        status = label("", 17f)
        listening.addView(status)
        listening.addView(button("Start listening") { command("start") })
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(button("Mute / unmute") { command("mute") }, LinearLayout.LayoutParams(0, -2, 1f))
        row.addView(button("Pause / resume") { command("pause") }, LinearLayout.LayoutParams(0, -2, 1f))
        listening.addView(row)
        listening.addView(button("Stop listening") { command("stop") })
        listening.addView(button("Test speech") { command("test") })
        val cluster = section("Cluster")
        cluster.addView(label("Current: " + prefs.getString("host", "w4mr.ddns.net") + ":" + prefs.getString("port", "7373"), 15f))
        cluster.addView(button("Manage cluster profiles") { showProfiles() })
        val speech = section("Speech")
        speech.addView(label("Template: " + prefs.getString("format", "New DX {call} on {frequency} kilohertz"), 14f))
        speech.addView(button("Edit announcement") { showSpeech() })
        val spots = section("Live DX spots")
        spotsView = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        spots.addView(spotsView)
        refresh()
    }
    private fun refresh() {
        if (!::status.isInitialized || !::spotsView.isInitialized) return
        status.text = ListenerService.status + "\n" +
            (if (ListenerService.muted) "Muted" else "Audio enabled") + "  |  " +
            (if (ListenerService.paused) "Paused" else "Active") + "  |  " +
            (if (ListenerService.speechReady) "Speech ready" else "Speech unavailable")
        spotsView.removeAllViews()
        val items = synchronized(ListenerService.spots) { ListenerService.spots.toList() }
        if (items.isEmpty()) spotsView.addView(label("No spots received yet. Connect to a cluster to begin.", 14f, Color.LTGRAY))
        items.take(60).forEach { spotsView.addView(label(it, 14f)) }
    }
    private fun profiles(): JSONArray = try { JSONArray(prefs.getString("profiles", "[]")) } catch (_: Exception) { JSONArray() }
    private fun showProfiles() {
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(background) }
        setContentView(ScrollView(this).apply { addView(root) })
        root.addView(button("Back to listener") { showHome() })
        root.addView(label("Cluster profiles", 25f, accent))
        val profiles = profiles()
        for (i in 0 until profiles.length()) {
            val profile = profiles.optJSONObject(i) ?: continue
            val row = section(profile.optString("name", "Cluster"))
            row.addView(label(profile.optString("host") + ":" + profile.optString("port")))
            row.addView(button("Use this cluster") {
                prefs.edit().putString("host", profile.optString("host")).putString("port", profile.optString("port"))
                    .putString("call", profile.optString("call")).putString("password", profile.optString("password")).apply()
                showHome()
            })
            row.addView(button("Edit") { editProfile(i) })
            row.addView(button("Delete") {
                val updated = JSONArray()
                for (j in 0 until profiles.length()) if (j != i) updated.put(profiles.getJSONObject(j))
                prefs.edit().putString("profiles", updated.toString()).apply()
                showProfiles()
            })
        }
        root.addView(button("Add cluster") { editProfile(null) })
    }
    private fun editProfile(index: Int?) {
        val profile = if (index == null) JSONObject().put("host", prefs.getString("host", "w4mr.ddns.net"))
            .put("port", prefs.getString("port", "7373")).put("call", prefs.getString("call", ""))
            else profiles().getJSONObject(index)
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(background) }
        setContentView(ScrollView(this).apply { addView(root) })
        root.addView(button("Cancel") { showProfiles() })
        val panel = section(if (index == null) "Add cluster" else "Edit cluster")
        val name = edit(panel, "Profile name", profile.optString("name", "My cluster"))
        val host = edit(panel, "Hostname", profile.optString("host", ""))
        val port = edit(panel, "TCP port", profile.optString("port", "7373")).apply { inputType = InputType.TYPE_CLASS_NUMBER }
        val call = edit(panel, "Login callsign", profile.optString("call", ""))
        val password = edit(panel, "Password (optional)", profile.optString("password", ""), true)
        panel.addView(button("Save profile") {
            if (host.text.isBlank() || port.text.toString().toIntOrNull() !in 1..65535) {
                Toast.makeText(this, "Enter a valid host and port", Toast.LENGTH_LONG).show()
            } else {
                val updated = profiles()
                val value = JSONObject().put("name", name.text.toString()).put("host", host.text.toString().trim())
                    .put("port", port.text.toString()).put("call", call.text.toString().trim())
                    .put("password", password.text.toString())
                if (index == null) updated.put(value) else updated.put(index, value)
                prefs.edit().putString("profiles", updated.toString()).putString("host", host.text.toString().trim())
                    .putString("port", port.text.toString()).putString("call", call.text.toString().trim())
                    .putString("password", password.text.toString()).apply()
                showProfiles()
            }
        })
    }
    private fun showSpeech() {
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(background) }
        setContentView(ScrollView(this).apply { addView(root) })
        root.addView(button("Back") { showHome() })
        val panel = section("Speech announcement")
        panel.addView(label("Use {call}, {frequency} and {unit}. Reorder or omit any component.", 14f))
        val template = edit(panel, "Spoken format", prefs.getString("format", "New DX {call} on {frequency} kilohertz").orEmpty())
        panel.addView(button("Save announcement") {
            prefs.edit().putString("format", template.text.toString()).apply()
            showHome()
        })
        panel.addView(button("Test speech") { command("test") })
    }
    override fun onStart() {
        super.onStart()
        registerReceiver(receiver, IntentFilter(ListenerService.UPDATE), RECEIVER_NOT_EXPORTED)
        if (::status.isInitialized) refresh()
    }
    override fun onStop() { unregisterReceiver(receiver); super.onStop() }
}
