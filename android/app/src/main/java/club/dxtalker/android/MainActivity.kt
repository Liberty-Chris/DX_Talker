package club.dxtalker.android

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import com.google.zxing.integration.android.IntentIntegrator
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
    private lateinit var listenButton: Button
    private lateinit var spotsView: LinearLayout
    private lateinit var root: LinearLayout
    private val prefs by lazy { getSharedPreferences("dx", MODE_PRIVATE) }
    private val background = Color.rgb(15, 23, 31)
    private val surface = Color.rgb(24, 36, 47)
    private val accent = Color.rgb(0, 183, 232)
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
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(this@MainActivity.background) }
        val scroll = ScrollView(this).apply { isFillViewport = true; addView(root) }
        setContentView(scroll)
        root.addView(ImageView(this).apply { setImageResource(R.drawable.dxt_logo_dark);adjustViewBounds=true;contentDescription="DX Talker" },LinearLayout.LayoutParams(-1,100))
        root.addView(label("DX Talker  |  Android listener", 14f, Color.LTGRAY))
        val listening = section("Listening")
        status = label("", 17f)
        listening.addView(status)
        listenButton=button("Start listening") { command(if(ListenerService.listeningActive)"stop" else "start") };listening.addView(listenButton)
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(button("Mute / unmute") { command("mute") }, LinearLayout.LayoutParams(0, -2, 1f))
        row.addView(button("Pause / resume") { command("pause") }, LinearLayout.LayoutParams(0, -2, 1f))
        listening.addView(row)

        listening.addView(button("Test speech") { command("test") })
        val cluster = section("Cluster")
        cluster.addView(label("Current: " + prefs.getString("host", "w4mr.ddns.net") + ":" + prefs.getString("port", "7373"), 15f))
        cluster.addView(button("Manage cluster profiles") { showProfiles() })
        val speech = section("Speech")
        speech.addView(label("Template: " + prefs.getString("format", "New DX on. {frequency} {unit}. {call}."), 14f))
        speech.addView(button("Edit announcement") { showSpeech() })
        speech.addView(button("Filters and frequency units") { showFilters() })
        val diagnostics=section("Diagnostics")
        diagnostics.addView(CheckBox(this).apply { text="Keep local diagnostic logs. No automatic upload.";setTextColor(Color.WHITE)
            isChecked=prefs.getBoolean("diagnostics",true);setOnCheckedChangeListener{_,checked->prefs.edit().putBoolean("diagnostics",checked).apply()} })
        diagnostics.addView(button("Export diagnostic report") {startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").putExtra(Intent.EXTRA_TITLE,"DXTalker-Android-diagnostics.zip"),202)})
        val spots = section("Live DX spots")
        spotsView = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        spots.addView(spotsView)
        refresh()
    }
    private fun refresh() {
        if (!::status.isInitialized || !::spotsView.isInitialized) return
        listenButton.text=if(ListenerService.listeningActive)"Listening. Tap to stop" else "Start listening"
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
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(this@MainActivity.background) }
        setContentView(ScrollView(this).apply { addView(root) })
        root.addView(button("Back to listener") { showHome() })
        root.addView(label("Cluster profiles", 25f, accent))
        root.addView(button("Scan desktop QR") { IntentIntegrator(this).setDesiredBarcodeFormats(IntentIntegrator.QR_CODE)
            .setPrompt("Scan the DX Talker profile QR").setBeepEnabled(false).setOrientationLocked(false).initiateScan() })
        root.addView(button("Import profile file") {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE), 201)
        })
        val profiles = profiles()
        for (i in 0 until profiles.length()) {
            val profile = profiles.optJSONObject(i) ?: continue
            val row = section(profile.optString("name", "Cluster"))
            row.addView(label(profile.optString("host") + ":" + profile.optString("port")))
            row.addView(button("Use this cluster") {
                stopService(Intent(this,ListenerService::class.java))
                prefs.edit().putString("host", profile.optString("host")).putString("port", profile.optString("port"))
                    .putString("call", profile.optString("call")).putString("password", profile.optString("password"))
                    .putString("source_type",profile.optString("source_type","TCP/Telnet"))
                    .putString("feed_url",profile.optString("feed_url"))
                    .putString("poll_seconds",profile.optString("poll_seconds","30")).apply()
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
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(this@MainActivity.background) }
        setContentView(ScrollView(this).apply { addView(root) })
        root.addView(button("Cancel") { showProfiles() })
        val panel = section(if (index == null) "Add cluster" else "Edit cluster")
        val name = edit(panel, "Profile name", profile.optString("name", "My cluster"))
        val host = edit(panel, "Hostname", profile.optString("host", ""))
        val port = edit(panel, "TCP port", profile.optString("port", "7373")).apply { inputType = InputType.TYPE_CLASS_NUMBER }
        val call = edit(panel, "Login callsign", profile.optString("call", ""))
        val password = edit(panel, "Password (optional)", runCatching{SecretStore.reveal(profile.optString("password", ""))}.getOrDefault(""), true)
        panel.addView(button("Save profile") {
            if (host.text.isBlank() || (port.text.toString().toIntOrNull() ?: 0) !in 1..65535) {
                Toast.makeText(this, "Enter a valid host and port", Toast.LENGTH_LONG).show()
            } else {
                val updated = profiles()
                val value = JSONObject().put("name", name.text.toString()).put("host", host.text.toString().trim())
                    .put("port", port.text.toString()).put("call", call.text.toString().trim())
                    .put("password", SecretStore.protect(password.text.toString()))
                if (index == null) updated.put(value) else updated.put(index, value)
                prefs.edit().putString("profiles", updated.toString()).putString("host", host.text.toString().trim())
                    .putString("port", port.text.toString()).putString("call", call.text.toString().trim())
                    .putString("password", SecretStore.protect(password.text.toString())).apply()
                showProfiles()
            }
        })
    }
    private fun showSpeech() {
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 22, 20, 24); setBackgroundColor(this@MainActivity.background) }
        setContentView(ScrollView(this).apply { addView(root) })
        root.addView(button("Back") { showHome() })
        val panel = section("Speech announcement")
        panel.addView(label("Use {call}, {frequency} and {unit}. Reorder or omit any component.", 14f))
        val template = edit(panel, "Spoken format", prefs.getString("format", "New DX on. {frequency} {unit}. {call}.").orEmpty())
        panel.addView(button("Save announcement") {
            prefs.edit().putString("format", template.text.toString()).apply()
            showHome()
        })
        panel.addView(button("Test speech") { command("test") })
    }
    private fun showFilters(){
        root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(20,22,20,24);setBackgroundColor(this@MainActivity.background)}
        setContentView(ScrollView(this).apply{addView(root)})
        root.addView(button("Back"){showHome()});val panel=section("Listening filters")
        val specs=listOf("min_khz" to "1","max_khz" to "10000000","max_age_seconds" to "180","repeat_seconds" to "300","spacing_seconds" to "5","frequency_unit" to "kHz")
        val fields=specs.associate{(key,default)->key to edit(panel,key.replace('_',' '),prefs.getString(key,default).orEmpty())}
        panel.addView(label("Filters use kHz. Frequency units may be kHz or MHz. Save, then restart listening to apply.",14f))
        panel.addView(button("Save filters"){
            try{val f=JSONObject();for((key,field)in fields)f.put(key,field.text.toString())
                val low=f.getDouble("min_khz");val high=f.getDouble("max_khz")
                require(low.isFinite()&&high.isFinite()&&low>=1&&high>=low&&high<=10000000)
                require(f.getInt("max_age_seconds") in 30..600&&f.getInt("repeat_seconds") in 30..3600&&f.getInt("spacing_seconds") in 1..120&&f.getString("frequency_unit") in listOf("kHz","MHz"))
                val editor=prefs.edit();for((key,field)in fields)editor.putString(key,field.text.toString());editor.apply();showHome()
            }catch(_:Exception){Toast.makeText(this,"Check frequency limits, units and timing ranges",Toast.LENGTH_LONG).show()}
        })
    }
    private fun reviewImport(text: String) {
        try {
            val data = TransferCodec.decode(text)
            val profiles = data.getJSONArray("profiles")
            val description = (0 until profiles.length()).joinToString("\n") {
                val p = profiles.getJSONObject(it); val c = p.getJSONObject("connection")
                p.getString("name") + ": " + (if (c.getString("source_type") == "TCP/Telnet") c.getString("host") + ":" + c.getInt("port") else c.getString("feed_url"))
            }
            AlertDialog.Builder(this).setTitle("Import profiles and filters?")
                .setMessage(description + "\n\nNo credentials are included. Existing profiles are preserved; duplicate names are renamed. Imported filters apply on the next start. No connection starts automatically.")
                .setNegativeButton("Cancel",null).setPositiveButton("Import") { _, _ ->
                    try { TransferCodec.importInto(data,prefs); showProfiles() }
                    catch (_: Exception) { Toast.makeText(this,"Import could not be saved",Toast.LENGTH_LONG).show() }
                }.show()
        } catch (_: Exception) { Toast.makeText(this,"Invalid or unsupported DX Talker transfer",Toast.LENGTH_LONG).show() }
    }
    @Deprecated("Legacy activity results are used by the QR scanner")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode,resultCode,data)
        val result = IntentIntegrator.parseActivityResult(requestCode,resultCode,data)
        if (result != null) { result.contents?.let { reviewImport(it) }; return }
        if(requestCode==202&&resultCode==RESULT_OK){
            try{val uri=data?.data?:return;contentResolver.openOutputStream(uri)?.use{output->java.util.zip.ZipOutputStream(output).use{zip->
                val dir=java.io.File(filesDir,"diagnostics")
                dir.listFiles()?.filter{it.name.startsWith("events.jsonl")&&it.length()<=1024*1024}?.forEach{file->zip.putNextEntry(java.util.zip.ZipEntry(file.name));file.inputStream().use{it.copyTo(zip)};zip.closeEntry()}
            }}}catch(_:Exception){Toast.makeText(this,"Could not export diagnostics",Toast.LENGTH_LONG).show()};return
        }
        if (requestCode == 201 && resultCode == RESULT_OK) {
            try {
                val uri = data?.data ?: return
                contentResolver.openInputStream(uri)?.use { input ->
                    val output = java.io.ByteArrayOutputStream()
                    val buffer = ByteArray(4096)
                    while (true) { val n=input.read(buffer); if(n<0) break; output.write(buffer,0,n); require(output.size()<=65536) }
                    reviewImport(output.toString("UTF-8"))
                }
            } catch (_: Exception) { Toast.makeText(this,"Cannot read transfer file (maximum 64 KiB)",Toast.LENGTH_LONG).show() }
        }
    }
    override fun onStart() {
        super.onStart()
        if(Build.VERSION.SDK_INT>=33)registerReceiver(receiver, IntentFilter(ListenerService.UPDATE), RECEIVER_NOT_EXPORTED)
        else @Suppress("DEPRECATION") registerReceiver(receiver,IntentFilter(ListenerService.UPDATE))
        if (::status.isInitialized) refresh()
    }
    override fun onStop() { unregisterReceiver(receiver); super.onStop() }
}
