package club.dxtalker.android

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.*
import android.text.InputType

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("dx", MODE_PRIVATE)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(28, 36, 28, 16) }
        fun field(label: String, key: String, default: String): EditText {
            layout.addView(TextView(this).apply { text = label })
            return EditText(this).also {
                it.setText(prefs.getString(key, default))
                it.setSingleLine(true)
                layout.addView(it)
            }
        }
        layout.addView(TextView(this).apply { text = "DXt  |  DX Talker Android"; textSize = 25f })
        val host = field("Cluster host", "host", "w4mr.ddns.net")
        val port = field("Port", "port", "7373").apply { inputType = InputType.TYPE_CLASS_NUMBER }
        val call = field("Login callsign", "call", "")
        val password = field("Password (if required)", "password", "").apply { inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD }
        val format = field("Announcement template ({call} {frequency})", "format", "New DX {call} on {frequency}")
        val status = TextView(this).apply { text = "Not connected"; textSize = 17f }
        layout.addView(status)
        fun command(action: String) {
            prefs.edit().putString("host", host.text.toString()).putString("port", port.text.toString())
                .putString("call", call.text.toString()).putString("password", password.text.toString())
                .putString("format", format.text.toString()).apply()
            val intent = Intent(this, ListenerService::class.java).setAction(action)
            if (action == "start") startForegroundService(intent) else startService(intent)
            status.text = "Command sent: $action"
        }
        listOf("Start listening" to "start", "Mute / unmute" to "mute", "Pause / resume" to "pause", "Stop" to "stop").forEach { (label, action) ->
            layout.addView(Button(this).apply { text = label; setOnClickListener { command(action) } })
        }
        layout.addView(TextView(this).apply { text = "Initial Android listener. Cluster profile management and live spots UI are planned for the next iteration." })
        setContentView(ScrollView(this).apply { addView(layout) })
    }
}
