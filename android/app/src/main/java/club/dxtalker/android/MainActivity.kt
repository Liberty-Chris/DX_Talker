package club.dxtalker.android

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import com.google.zxing.integration.android.IntentIntegrator
import android.content.*
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.view.Gravity
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : Activity() {
    private val qrCollection = QrCollection()
    private lateinit var status: TextView
    private lateinit var listenButton: Button
    private lateinit var muteButton: Button
    private lateinit var pauseButton: Button
    private lateinit var spotsView: LinearLayout
    private lateinit var root: LinearLayout
    private val prefs by lazy { getSharedPreferences("dx", MODE_PRIVATE) }
    private var page = "Listen"
    private val history = java.util.ArrayDeque<String>()
    private val drafts = mutableMapOf<String, String>()
    private var editIndex: Int? = null
    private var background = Color.rgb(15, 23, 31)
    private var surface = Color.rgb(24, 36, 47)
    private var ink = Color.WHITE
    private var secondary = Color.LTGRAY
    private val accent = Color.rgb(0, 183, 232)
    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) { refresh() }
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun rounded(color: Int, radius: Float = 16f) = GradientDrawable().apply {
        setColor(color); cornerRadius = dp(radius.toInt()).toFloat()
    }
    private fun label(text: String, size: Float = 16f, color: Int = ink): TextView =
        TextView(this).apply { this.text = text; textSize = size; setTextColor(color); setPadding(dp(4), dp(8), dp(4), dp(8)) }
    private fun button(text: String, action: () -> Unit): Button = Button(this).apply {
        this.text = text; setOnClickListener { action() }; isAllCaps = false
        setTextColor(ink); minHeight = dp(48); textSize = 15f
    }
    private fun section(title: String): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setPadding(dp(16), dp(10), dp(16), dp(16))
            background = rounded(surface)
            root.addView(this, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(14) })
            addView(label(title, 19f).apply { setTypeface(null, Typeface.BOLD) })
        }
    }
    private fun edit(container: LinearLayout, name: String, value: String, password: Boolean = false, key: String = name): EditText {
        container.addView(label(name, 13f, secondary))
        return EditText(this).apply {
            setText(drafts["$page:$key"] ?: value); setTextColor(ink); setHintTextColor(secondary)
            setSingleLine(true); minHeight = dp(48)
            if (password) inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { drafts["$page:$key"] = s.toString() }
                override fun afterTextChanged(s: Editable?) {}
            })
            container.addView(this)
        }
    }
    private fun theme() {
        val dark = when(prefs.getString("appearance", "System")) {
            "Light" -> false; "Dark", "High contrast" -> true
            else -> resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
        }
        setTheme(if(dark) android.R.style.Theme_Material_NoActionBar else android.R.style.Theme_Material_Light_NoActionBar)
        background = if(dark) Color.rgb(15,23,31) else Color.rgb(241,245,249)
        surface = if(dark) Color.rgb(24,36,47) else Color.WHITE
        ink = if(dark) Color.WHITE else Color.rgb(15,23,31)
        secondary = if(dark) Color.rgb(185,201,214) else Color.rgb(67,83,98)
        if(prefs.getString("appearance", "") == "High contrast") { background = Color.BLACK; surface = Color.BLACK; secondary = Color.WHITE }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        theme(); super.onCreate(savedInstanceState)
        window.statusBarColor = background; window.navigationBarColor = background
        savedInstanceState?.getStringArrayList("qr_pages")?.forEach {
            try { qrCollection.accept(it) } catch (_: Exception) { qrCollection.reset() }
        }
        page = savedInstanceState?.getString("page") ?: "Listen"
        savedInstanceState?.getStringArrayList("history")?.let { history.addAll(it) }
        savedInstanceState?.getBundle("drafts")?.let { b -> b.keySet().forEach { drafts[it] = b.getString(it).orEmpty() } }
        savedInstanceState?.takeIf { it.containsKey("edit_index") }?.let { editIndex = it.getInt("edit_index").takeIf { i -> i >= 0 } }
        render()
        if(Build.VERSION.SDK_INT >= 33) onBackInvokedDispatcher.registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT) { onBackPressed() }
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 100)
    }
    override fun onSaveInstanceState(outState: Bundle) {
        outState.putStringArrayList("qr_pages", qrCollection.saved())
        outState.putString("page", page); outState.putStringArrayList("history", ArrayList(history))
        outState.putInt("edit_index", editIndex ?: -1)
        outState.putBundle("drafts", Bundle().apply { drafts.forEach { (k,v) -> putString(k,v) } })
        super.onSaveInstanceState(outState)
    }
    private fun go(destination: String, tab: Boolean = false) {
        if(tab) history.clear() else if(destination != page) history.addLast(page)
        page = destination; render()
    }
    @Deprecated("Activity back compatibility")
    override fun onBackPressed() {
        if(history.isNotEmpty()) { page = history.removeLast(); render() }
        else if(page != "Listen") go("Listen", true) else super.onBackPressed()
    }
    private fun command(action: String) {
        val intent = Intent(this, ListenerService::class.java).setAction(action)
        if (action == "start" || action == "switch") startForegroundService(intent) else startService(intent)
    }
    private fun render() {
        val shell = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(this@MainActivity.background) }
        shell.setOnApplyWindowInsetsListener { view, insets ->
            @Suppress("DEPRECATION")
            view.setPadding(insets.systemWindowInsetLeft,insets.systemWindowInsetTop,insets.systemWindowInsetRight,insets.systemWindowInsetBottom)
            insets
        }
        val heading = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(12),dp(6),dp(12),dp(6)) }
        if(page !in listOf("Listen","Clusters","Settings")) heading.addView(button("Back") { onBackPressed() })
        if(page == "Listen") heading.addView(ImageView(this).apply { setImageResource(R.drawable.dxt_icon); contentDescription="DX Talker logo" },LinearLayout.LayoutParams(dp(40),dp(40)).apply { rightMargin=dp(8) })
        heading.addView(label(if(page == "Listen") "DX Talker" else page, 24f).apply { setTypeface(null,Typeface.BOLD) })
        shell.addView(heading)
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(16),dp(8),dp(16),dp(8)) }
        shell.addView(ScrollView(this).apply { isFillViewport = true; addView(root) }, LinearLayout.LayoutParams(-1,0,1f))
        when(page) { "Listen" -> homeContent(); "Clusters" -> profilesContent(); "Edit cluster" -> profileContent(); "Speech" -> speechContent(); "Filters" -> filterContent(); else -> settingsContent() }
        val player = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12),dp(4),dp(12),dp(4)); setBackgroundColor(surface) }
        status = label("",13f,secondary).apply { accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE }
        player.addView(status)
        val controls = LinearLayout(this)
        listenButton = button("Listen") { command(if(ListenerService.listeningActive) "stop" else "start") }
        listenButton.backgroundTintList=android.content.res.ColorStateList.valueOf(accent); listenButton.setTextColor(Color.BLACK)
        muteButton = button("Mute") { command("mute") }; pauseButton = button("Pause") { command("pause") }
        for(b in listOf(listenButton,muteButton,pauseButton)) controls.addView(b,LinearLayout.LayoutParams(0,-2,1f))
        player.addView(controls); shell.addView(player)
        val nav = LinearLayout(this).apply { setPadding(dp(4),0,dp(4),dp(4)); setBackgroundColor(surface) }
        for(tab in listOf("Listen","Clusters","Settings")) nav.addView(button(tab) { go(tab,true) }.apply {
            isSelected = tab == page; setTextColor(if(isSelected) accent else ink)
            contentDescription = if(isSelected) "$tab, selected" else tab
        },LinearLayout.LayoutParams(0,-2,1f))
        shell.addView(nav); setContentView(shell); refresh()
    }
    private fun homeContent() {
        val cluster = section("Your listening session")
        cluster.addView(label(prefs.getString("profile_name", prefs.getString("host","w4mr.ddns.net")).orEmpty(),18f))
        cluster.addView(label("Announcements through your phone. No radio setup required.",14f,secondary))
        val row = LinearLayout(this)
        row.addView(button("Change cluster") { go("Clusters",true) },LinearLayout.LayoutParams(0,-2,1f))
        row.addView(button("Filters") { go("Filters") },LinearLayout.LayoutParams(0,-2,1f)); cluster.addView(row)
        cluster.addView(label(SpotFilters.summary { key -> prefs.getString(key,"").orEmpty() },13f,secondary))
        val live = section("Recent spots")
        spotsView = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }; live.addView(spotsView)
    }
    private fun refresh() {
        if(!::status.isInitialized)return
        listenButton.text = if(ListenerService.listeningActive) "Stop listening" else "Start listening"
        muteButton.text = if(ListenerService.muted) "Unmute" else "Mute"
        pauseButton.text = if(ListenerService.paused) "Resume" else "Pause"
        muteButton.isEnabled = ListenerService.listeningActive; pauseButton.isEnabled = ListenerService.listeningActive
        status.text = ListenerService.status + if(ListenerService.listeningActive) " · " + (if(ListenerService.muted) "Muted" else if(ListenerService.paused) "Paused" else "Audio on") else ""
        if(page != "Listen" || !::spotsView.isInitialized)return
        val items = synchronized(ListenerService.spots) { ListenerService.spots.toList() }
        if(spotsView.tag == items)return
        spotsView.tag = items; spotsView.removeAllViews()
        if(items.isEmpty()) spotsView.addView(label("Your matching spots will appear here. Listening can start before the first spot arrives.",15f,secondary))
        items.take(60).forEach { spotsView.addView(label(it,16f)) }
    }
    private fun showHome() = go("Listen",true)
    private fun showProfiles() = go("Clusters",true)
    private fun profiles(): JSONArray = try { JSONArray(prefs.getString("profiles", "[]")) } catch (_: Exception) { JSONArray() }
    private fun profilesContent() {
        val tools = section("Bring your clusters along")
        tools.addView(button("Scan desktop QR collection") { scanQr() })
        if(qrCollection.scanned > 0) { tools.addView(label("${qrCollection.scanned} of ${qrCollection.total} QR pages collected",14f)); tools.addView(button("Reset scan") { qrCollection.reset(); render() }) }
        tools.addView(button("Import profile file") { startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE),201) })
        tools.addView(button("Add cluster") { editProfile(null) })
        val entries = profiles()
        if(entries.length() == 0) root.addView(label("Add a cluster or scan your desktop collection to get started.",15f,secondary))
        for(i in 0 until entries.length()) {
            val p = entries.getJSONObject(i); val row = section(p.optString("name","Cluster"))
            row.addView(label(if(p.optString("source_type") == "HTTPS JSON") p.optString("feed_url") else p.optString("host")+":"+p.optString("port"),14f,secondary))
            row.addView(button("Use this cluster") {
                val editor = prefs.edit().putString("profile_name",p.optString("name"))
                for(key in listOf("host","port","call","password","source_type","feed_url","poll_seconds")) editor.putString(key,p.optString(key,when(key) { "source_type" -> "TCP/Telnet"; "port" -> "7373"; "poll_seconds" -> "30"; else -> "" }))
                editor.apply(); if(ListenerService.listeningActive)command("switch"); showHome()
            })
            val actions = LinearLayout(this)
            actions.addView(button("Edit") { editProfile(i) },LinearLayout.LayoutParams(0,-2,1f))
            actions.addView(button("Remove") {
                AlertDialog.Builder(this).setTitle("Remove ${p.optString("name")}?").setMessage("This removes the saved profile. An active session continues until you stop it or switch clusters.")
                    .setNegativeButton("Cancel",null).setPositiveButton("Remove") { _,_ ->
                        val updated = JSONArray(); for(j in 0 until entries.length())if(j != i)updated.put(entries.getJSONObject(j))
                        prefs.edit().putString("profiles",updated.toString()).apply(); render()
                    }.show()
            },LinearLayout.LayoutParams(0,-2,1f)); row.addView(actions)
        }
    }
    private fun editProfile(index: Int?) {
        if(editIndex != index) drafts.keys.filter { it.startsWith("Edit cluster:") }.toList().forEach { drafts.remove(it) }
        editIndex = index; go("Edit cluster")
    }
    private fun profileContent() {
        val p = editIndex?.let { profiles().optJSONObject(it) } ?: JSONObject().put("host","w4mr.ddns.net").put("port","7373")
        val panel = section(if(editIndex == null) "New cluster" else "Connection details")
        val name = edit(panel,"Profile name",p.optString("name","My cluster"))
        val type = spinner(panel,"Connection type",listOf("TCP/Telnet","HTTPS JSON"),p.optString("source_type","TCP/Telnet"))
        val host = edit(panel,"Hostname",p.optString("host")); val port = edit(panel,"Port",p.optString("port","7373")).apply { inputType = InputType.TYPE_CLASS_NUMBER }
        val url = edit(panel,"HTTPS feed URL",p.optString("feed_url")); val poll = edit(panel,"Poll interval (seconds)",p.optString("poll_seconds","30"))
        fun relevant() { val https = type.selectedItem == "HTTPS JSON"; host.isEnabled = !https; port.isEnabled = !https; url.isEnabled = https; poll.isEnabled = https }
        type.onItemSelectedListener = object : AdapterView.OnItemSelectedListener { override fun onNothingSelected(parent: AdapterView<*>?) {} ; override fun onItemSelected(parent: AdapterView<*>?,view: View?,position: Int,id: Long) { drafts["$page:Connection type"] = type.selectedItem.toString(); relevant() } }; relevant()
        val call = edit(panel,"Login callsign",p.optString("call"))
        val password = edit(panel,"Password or bearer token",runCatching { SecretStore.reveal(p.optString("password")) }.getOrDefault(""),true)
        panel.addView(CheckBox(this).apply { text = "Show password or token"; setTextColor(ink); setOnCheckedChangeListener { _, checked -> password.transformationMethod = if(checked) null else android.text.method.PasswordTransformationMethod.getInstance() } })
        panel.addView(button("Save profile") {
            try {
                val source = type.selectedItem.toString(); val portValue = port.text.toString().toInt(); val pollValue = poll.text.toString().toInt()
                require(name.text.isNotBlank() && name.length() <= 80 && portValue in 1..65535 && pollValue in 15..3600)
                val hostValue = host.text.toString().trim(); val login = call.text.toString().trim()
                require(login.isEmpty() || Regex("[A-Za-z0-9][A-Za-z0-9/\\-]{1,19}").matches(login) && login.any { it.isDigit() } && login.any { it.isLetter() })
                if(source == "TCP/Telnet") require(hostValue.isNotBlank() && hostValue.length <= 253 && hostValue.none { it.isWhitespace() || it in "/:@" })
                else { val uri = java.net.URI(url.text.toString()); require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null && uri.fragment == null) }
                val value = JSONObject().put("name",name.text.toString().trim()).put("source_type",source).put("host",hostValue).put("port",portValue.toString()).put("call",login)
                    .put("password",SecretStore.protect(password.text.toString())).put("feed_url",url.text.toString()).put("poll_seconds",pollValue.toString())
                val entries = profiles(); if(editIndex == null) entries.put(value) else entries.put(editIndex!!,value)
                prefs.edit().putString("profiles",entries.toString()).apply(); drafts.keys.filter { it.startsWith("Edit cluster:") }.toList().forEach { drafts.remove(it) }; onBackPressed()
            } catch(_:Exception) { Toast.makeText(this,"Check the name, connection address, callsign and numeric ranges.",Toast.LENGTH_LONG).show() }
        })
    }
    private fun spinner(panel: LinearLayout, title: String, values: List<String>, selected: String): Spinner {
        panel.addView(label(title,13f,secondary))
        return Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity,android.R.layout.simple_spinner_dropdown_item,values)
            setSelection(values.indexOf(drafts["$page:$title"] ?: selected).coerceAtLeast(0)); panel.addView(this)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) {}
                override fun onItemSelected(parent: AdapterView<*>?,view: View?,position: Int,id: Long) { drafts["$page:$title"] = values[position] }
            }
        }
    }
    private fun settingsContent() {
        val sound = section("Make it sound right")
        sound.addView(button("Voice and announcement") { go("Speech") }); sound.addView(button("Bands, modes and activities") { go("Filters") })
        val appearance = section("Appearance")
        val picker = spinner(appearance,"Theme",listOf("System","Light","Dark","High contrast"),prefs.getString("appearance","System").orEmpty())
        appearance.addView(button("Apply appearance") { prefs.edit().putString("appearance",picker.selectedItem.toString()).apply(); recreate() })
        val diagnostics = section("Help and diagnostics")
        diagnostics.addView(label("Listening continues when you change pages. Pause stops announcements while the feed stays connected. Mute silences announcements. Android Back returns to the previous page.",14f,secondary))
        diagnostics.addView(CheckBox(this).apply { text="Keep diagnostic logs locally"; setTextColor(ink); isChecked=prefs.getBoolean("diagnostics",true); setOnCheckedChangeListener { _,checked -> prefs.edit().putBoolean("diagnostics",checked).apply() } })
        diagnostics.addView(button("Export diagnostic report") { startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").putExtra(Intent.EXTRA_TITLE,"DXTalker-Android-diagnostics.zip"),202) })
        diagnostics.addView(label("No automatic log upload. DX Talker " + packageManager.getPackageInfo(packageName,0).versionName,13f,secondary))
    }
    private fun speechContent() {
        val panel = section("Announcement builder")
        panel.addView(label("Choose what to say and move the sections into your preferred order. Comments are never spoken.",14f,secondary))
        val current = prefs.getString("format","New DX on. {frequency} {unit}. {call}.").orEmpty()
        val intro = edit(panel,"Intro phrase",current.substringBefore('{').trim().trimEnd('.').ifBlank { "New DX" })
        val initialOrder = listOf("intro","frequency","callsign").sortedBy { key -> when(key) { "intro" -> 0; "frequency" -> current.indexOf("{frequency}").takeIf { it >= 0 } ?: Int.MAX_VALUE; else -> current.indexOf("{call}").takeIf { it >= 0 } ?: Int.MAX_VALUE } }
        val order = (drafts["Speech:order"] ?: initialOrder.joinToString(",")).split(',').toMutableList()
        val flags = mutableMapOf<String,CheckBox>()
        val rows = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }; panel.addView(rows)
        fun draw() {
            rows.removeAllViews()
            order.forEachIndexed { index,key ->
                val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
                val enabled = drafts["Speech:include_$key"]?.toBoolean() ?: when(key) { "intro" -> current.substringBefore('{').isNotBlank(); "frequency" -> current.contains("{frequency}"); else -> current.contains("{call}") }
                val check = CheckBox(this).apply { text=key.replaceFirstChar { it.uppercase() }; setTextColor(ink); isChecked=enabled; setOnCheckedChangeListener { _,checked -> drafts["Speech:include_$key"] = checked.toString() } }
                flags[key]=check; row.addView(check,LinearLayout.LayoutParams(0,-2,1f))
                row.addView(button("Up") { java.util.Collections.swap(order,index,index-1); drafts["Speech:order"]=order.joinToString(","); draw() }.apply { isEnabled=index>0; contentDescription="Move $key up" })
                row.addView(button("Down") { java.util.Collections.swap(order,index,index+1); drafts["Speech:order"]=order.joinToString(","); draw() }.apply { isEnabled=index<order.lastIndex; contentDescription="Move $key down" }); rows.addView(row)
            }
        }; draw()
        val units = CheckBox(this).apply { text="Speak kHz or MHz"; setTextColor(ink); isChecked=drafts["Speech:units"]?.toBoolean() ?: current.contains("{unit}"); setOnCheckedChangeListener { _,checked -> drafts["Speech:units"]=checked.toString() } }; panel.addView(units)
        panel.addView(button("Save announcement") {
            val parts = order.filter { flags[it]?.isChecked == true }.map { when(it) { "intro" -> intro.text.toString().trim().replace("{","").replace("}",""); "callsign" -> "{call}"; else -> "{frequency}" + if(units.isChecked) " {unit}" else "" } }.filter { it.isNotBlank() }
            if(parts.isEmpty()) Toast.makeText(this,"Choose at least one announcement section",Toast.LENGTH_LONG).show()
            else { prefs.edit().putString("format",parts.joinToString(". ")+".").apply(); if(ListenerService.listeningActive)command("apply"); Toast.makeText(this,"Announcement saved",Toast.LENGTH_SHORT).show() }
        })
        val voice = section("System voice")
        voice.addView(label("Uses your installed Android speech engine. Voice downloads and engine choices are managed in Android settings.",14f,secondary))
        voice.addView(button("Open speech settings") { try { startActivity(Intent("com.android.settings.TTS_SETTINGS")) } catch(_:Exception) { Toast.makeText(this,"Open Android Settings and search for text to speech",Toast.LENGTH_LONG).show() } })
        voice.addView(button("Test saved announcement") { command("test") })
    }
    private fun chooseFilter(key: String,title: String,values: List<String>) {
        val selected = (drafts["Filters:$key"] ?: prefs.getString(key,"").orEmpty()).split(',').toSet()
        val checks = BooleanArray(values.size) { values[it] in selected }
        AlertDialog.Builder(this).setTitle(title).setMultiChoiceItems(values.toTypedArray(),checks) { _,index,checked -> checks[index]=checked }
            .setNeutralButton("All") { _,_ -> drafts["Filters:$key"]=""; render() }.setNegativeButton("Cancel",null)
            .setPositiveButton("Use selection") { _,_ -> drafts["Filters:$key"]=values.filterIndexed { i,_ -> checks[i] }.joinToString(","); render() }.show()
    }
    private fun filterContent() {
        val panel = section("Only hear what interests you")
        for((key,title,values) in listOf(Triple("filter_bands","Bands",SpotFilters.bands.keys.toList()+"Other"),Triple("filter_modes","Modes",SpotFilters.modes),Triple("filter_activities","Activities",SpotFilters.activities))) {
            panel.addView(button(title+": "+(drafts["Filters:$key"] ?: prefs.getString(key,"").orEmpty()).ifBlank { "All" }) { chooseFilter(key,title,values) })
        }
        panel.addView(label("Modes and activities are independent. Unknown means the spot did not identify a single mode. General means no recognized activity tag. No selections accepts all. Band ranges describe filters, not transmitting permissions.",14f,secondary))
        val units = spinner(panel,"Frequency units",listOf("kHz","MHz"),prefs.getString("frequency_unit","kHz").orEmpty())
        val advanced = section("Timing and frequency limits")
        val specs = listOf(Triple("min_khz","Minimum frequency (kHz)","1"),Triple("max_khz","Maximum frequency (kHz)","10000000"),Triple("max_age_seconds","Maximum spot age (seconds)","180"),Triple("repeat_seconds","Repeat suppression (seconds)","300"),Triple("spacing_seconds","Gap between announcements (seconds)","5"))
        val fields = specs.associate { (key,title,default) -> key to edit(advanced,title,prefs.getString(key,default).orEmpty(),key=key).apply { inputType=InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL } }
        advanced.addView(button("Save filters") {
            try {
                val low=fields.getValue("min_khz").text.toString().toDouble(); val high=fields.getValue("max_khz").text.toString().toDouble()
                require(low.isFinite() && high.isFinite() && low>=1 && high>=low && high<=10000000)
                require(fields.getValue("max_age_seconds").text.toString().toInt() in 30..600 && fields.getValue("repeat_seconds").text.toString().toInt() in 30..3600 && fields.getValue("spacing_seconds").text.toString().toInt() in 1..120)
                val editor = prefs.edit(); for((key,field) in fields)editor.putString(key,field.text.toString())
                for(key in listOf("filter_bands","filter_modes","filter_activities"))editor.putString(key,drafts["Filters:$key"] ?: prefs.getString(key,"").orEmpty())
                editor.putString("frequency_unit",units.selectedItem.toString()).apply(); if(ListenerService.listeningActive)command("apply")
                Toast.makeText(this,"Filters applied. The cluster connection stays open.",Toast.LENGTH_SHORT).show()
            } catch(_:Exception) { Toast.makeText(this,"Check frequency limits and timing ranges: age 30 to 600, repeats 30 to 3600 and gap 1 to 120 seconds.",Toast.LENGTH_LONG).show() }
        })
    }
    private fun reviewImport(text: String) {
        try {
            reviewImportData(TransferCodec.decode(text))
        } catch (_: Exception) { Toast.makeText(this,"Invalid or unsupported DX Talker transfer",Toast.LENGTH_LONG).show() }
    }
    private fun reviewImportData(data: JSONObject) {
        try {
            val profiles = data.getJSONArray("profiles")
            val description = (0 until profiles.length()).joinToString("\n") {
                val p = profiles.getJSONObject(it); val c = p.getJSONObject("connection")
                p.getString("name") + ": " + (if (c.getString("source_type") == "TCP/Telnet") c.getString("host") + ":" + c.getInt("port") else c.getString("feed_url"))
            }
            AlertDialog.Builder(this).setTitle("Import profiles and filters?")
                .setMessage(description + "\n\nNo credentials are included. Existing profiles are preserved; duplicate names are renamed. Imported filters apply on the next start. No connection starts automatically.")
                .setNegativeButton("Cancel",null).setPositiveButton("Import") { _, _ ->
                    try { TransferCodec.importInto(data,prefs); drafts.keys.filter { it.startsWith("Filters:") }.toList().forEach { drafts.remove(it) }; showProfiles() }
                    catch (_: Exception) { Toast.makeText(this,"Import could not be saved",Toast.LENGTH_LONG).show() }
                }.show()
        } catch (_: Exception) { Toast.makeText(this,"Invalid or unsupported DX Talker transfer",Toast.LENGTH_LONG).show() }
    }
    private fun scanQr() {
        IntentIntegrator(this).setDesiredBarcodeFormats(IntentIntegrator.QR_CODE)
            .setPrompt("Scan DX Talker QR. ${qrCollection.scanned} pages collected")
            .setBeepEnabled(false).setOrientationLocked(false).initiateScan()
    }
    @Deprecated("Legacy activity results are used by the QR scanner")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode,resultCode,data)
        val result = IntentIntegrator.parseActivityResult(requestCode,resultCode,data)
        if (result != null) {
            result.contents?.let { text ->
                try {
                    val collection = qrCollection.accept(text)
                    if (collection != null) { qrCollection.reset(); reviewImportData(collection) }
                    else AlertDialog.Builder(this).setTitle("Collection QR progress")
                        .setMessage("Scanned ${qrCollection.scanned} of ${qrCollection.total} pages. No profiles saved yet. Scan the remaining pages in any order.")
                        .setPositiveButton("Scan next") { _, _ -> scanQr() }
                        .setNegativeButton("Continue later",null).show()
                } catch (_: Exception) {
                    AlertDialog.Builder(this).setTitle("QR could not be added")
                        .setMessage("Invalid page or a different collection. Current collection: ${qrCollection.scanned} of ${qrCollection.total} pages. Keep scanning this collection or reset to start another.")
                        .setPositiveButton("Keep collection",null).setNegativeButton("Reset") { _, _ -> qrCollection.reset() }.show()
                }
            }
            return
        }
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
