package club.dxtalker.android

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
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
    private val filterSaves=mutableMapOf<String,Runnable>()
    private var filterApplyStatus:TextView?=null
    private val qrCollection = QrCollection()
    private var cameraScanRequested = false
    private lateinit var status: TextView
    private lateinit var listenButton: Button
    private lateinit var muteButton: Button
    private lateinit var pauseButton: Button
    private lateinit var spotsView: LinearLayout
    private lateinit var queueLabel: TextView
    private lateinit var spotResult: TextView
    private lateinit var root: LinearLayout
    private val prefs by lazy { getSharedPreferences("dx", MODE_PRIVATE) }
    private val uiHandler = android.os.Handler(android.os.Looper.getMainLooper())
    private var refreshQueued = false
    private val refreshTask = Runnable { refreshQueued=false;refresh() }
    private val scrollPositions = mutableMapOf<String,Int>()
    private var undoAction: (() -> Unit)? = null
    private var notice = ""
    private var importData: JSONObject? = null
    private var speechSave: Runnable? = null
    private var speechStatus: TextView? = null
    private fun draftPage() = if(page=="Edit cluster") "Edit cluster:${editIndex ?: "new"}" else page
    private fun inform(message: String, undo: (() -> Unit)? = null) { notice=message;undoAction=undo;render() }
    private var page = "Listen"
    private val history = java.util.ArrayDeque<String>()
    private val drafts = mutableMapOf<String, String>()
    private var editIndex: Int? = null
    private var background = Color.rgb(15, 23, 31)
    private var surface = Color.rgb(24, 36, 47)
    private var ink = Color.WHITE
    private var secondary = Color.LTGRAY
    private var accent = Color.rgb(0, 185, 239)
    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) { refreshControls();if(!refreshQueued) { refreshQueued=true;uiHandler.postDelayed(refreshTask,150) } }
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun rounded(color: Int, radius: Float = 16f) = GradientDrawable().apply {
        setColor(color); cornerRadius = dp(radius.toInt()).toFloat()
    }
    private fun label(text: String, size: Float = 16f, color: Int = ink): TextView =
        TextView(this).apply { this.text = text; textSize = size; setTextColor(color); setPadding(dp(4), dp(8), dp(4), dp(8)) }
    private fun button(text: String, action: () -> Unit): Button = Button(this).apply {
        this.text = text; setOnClickListener { action() }; isAllCaps = false
        setTextColor(android.content.res.ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled),intArrayOf()),intArrayOf(secondary,ink)))
        minHeight = dp(48); minWidth=dp(48); textSize = 15f; elevation=0f
        val fill=if(ink==Color.WHITE) Color.rgb(32,46,60) else Color.rgb(229,237,244)
        background=android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(Color.argb(70,0,185,239)),rounded(fill,12f),null)
        setPadding(dp(12),dp(8),dp(12),dp(8))
        layoutParams=LinearLayout.LayoutParams(-1,-2).apply { topMargin=dp(4);bottomMargin=dp(4) }
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
        val caption=label(name, 13f, secondary)
        container.addView(caption)
        return EditText(this).apply {
            id=View.generateViewId();caption.labelFor=id;contentDescription=name
            setText(drafts["${draftPage()}:$key"] ?: value); setTextColor(ink); setHintTextColor(secondary)
            setSingleLine(true); minHeight = dp(48)
            if (password) inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { drafts["${draftPage()}:$key"] = s.toString();if(page=="Filters")scheduleFilterSave(key) else if(page=="Speech")scheduleSpeechSave() }
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
        accent = if(dark) Color.rgb(0,185,239) else Color.rgb(0,125,166)
        secondary = if(dark) Color.rgb(185,201,214) else Color.rgb(67,83,98)
        if(prefs.getString("appearance", "") == "High contrast") { background = Color.BLACK; surface = Color.BLACK; secondary = Color.WHITE }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        theme(); super.onCreate(savedInstanceState)
        window.statusBarColor = background; window.navigationBarColor = background
        savedInstanceState?.getStringArrayList("qr_pages")?.forEach {
            try { qrCollection.accept(it) } catch (_: Exception) { qrCollection.reset() }
        }
        cameraScanRequested = savedInstanceState?.getBoolean("camera_scan_requested") ?: false
        importData=savedInstanceState?.getString("import_data")?.let { runCatching { JSONObject(it) }.getOrNull() }
        page = savedInstanceState?.getString("page") ?: "Listen"
        savedInstanceState?.getStringArrayList("history")?.let { history.addAll(it) }
        savedInstanceState?.getBundle("drafts")?.let { b -> b.keySet().forEach { drafts[it] = b.getString(it).orEmpty() } }
        savedInstanceState?.takeIf { it.containsKey("edit_index") }?.let { editIndex = it.getInt("edit_index").takeIf { i -> i >= 0 } }
        savedInstanceState?.getBundle("scrolls")?.let { b->b.keySet().forEach { scrollPositions[it]=b.getInt(it) } }
        render()
        if(Build.VERSION.SDK_INT >= 33) onBackInvokedDispatcher.registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT) { onBackPressed() }
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 100)
    }
    override fun onSaveInstanceState(outState: Bundle) {
        rememberScroll()
        outState.putBundle("scrolls",Bundle().apply { scrollPositions.forEach { (key,value)->putInt(key,value) } })
        outState.putBoolean("camera_scan_requested", cameraScanRequested)
        outState.putStringArrayList("qr_pages", qrCollection.saved())
        outState.putString("import_data",importData?.toString());
        outState.putString("page", page); outState.putStringArrayList("history", ArrayList(history))
        outState.putInt("edit_index", editIndex ?: -1)
        outState.putBundle("drafts", Bundle().apply { drafts.forEach { (k,v) -> putString(k,v) } })
        super.onSaveInstanceState(outState)
    }
    private fun go(destination: String, tab: Boolean = false) {
        rememberScroll()
        flushSpeech()
        if(tab) history.clear() else if(destination != page) history.addLast(page)
        page = destination; render()
    }
    @Deprecated("Activity back compatibility")
    override fun onBackPressed() {
        rememberScroll();flushSpeech()
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
        if(page !in listOf("Listen","Clusters","Settings")) heading.addView(button("Back") { onBackPressed() }.apply { background=rounded(Color.TRANSPARENT);setTextColor(accent) },LinearLayout.LayoutParams(dp(76),-2))
        if(page == "Listen") heading.addView(ImageView(this).apply { setImageResource(R.drawable.dxt_icon); contentDescription="DX Talker logo" },LinearLayout.LayoutParams(dp(40),dp(40)).apply { rightMargin=dp(8) })
        heading.addView(label(if(page == "Listen") "DX Talker" else page, 24f).apply { setTypeface(null,Typeface.BOLD) })
        shell.addView(heading)
        if(notice.isNotBlank()) {
            val feedback=LinearLayout(this).apply { setPadding(dp(12),0,dp(12),0) }
            feedback.addView(label(notice,13f,secondary),LinearLayout.LayoutParams(0,-2,1f))
            if(undoAction!=null)feedback.addView(button("Undo") { val action=undoAction;undoAction=null;notice="Restored";action?.invoke();render() },LinearLayout.LayoutParams(dp(76),-2))
            feedback.addView(button("Dismiss") { notice="";undoAction=null;render() },LinearLayout.LayoutParams(dp(90),-2))
            shell.addView(feedback)
        }
        root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(16),dp(8),dp(16),dp(8)) }
        if(page=="Listen")shell.addView(root,LinearLayout.LayoutParams(-1,0,1f))
        else shell.addView(ScrollView(this).apply { isFillViewport = true; addView(root) }, LinearLayout.LayoutParams(-1,0,1f))
        filterApplyStatus=null
        when(page) { "Listen" -> homeContent(); "Clusters" -> profilesContent(); "Edit cluster" -> profileContent(); "Speech" -> speechContent(); "Filters" -> filterContent(); "Spot" -> spotContent(); "Directory" -> directoryContent(); "Import collection" -> importContent(); else -> settingsContent() }
        if(page=="Filters") {
            val actions=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(16),dp(4),dp(16),dp(4));setBackgroundColor(surface) }
            filterApplyStatus=label("",12f,secondary);actions.addView(filterApplyStatus)
            shell.addView(actions);refreshFilterPending()
        }
        val player = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12),dp(4),dp(12),dp(4)); setBackgroundColor(surface) }
        status = label("",13f,secondary).apply { maxLines=2;ellipsize=android.text.TextUtils.TruncateAt.END;accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE }
        player.addView(status)
        val controls = LinearLayout(this)
        listenButton = button("Listen") { command(if(ListenerService.listeningActive) "stop" else "start") }
        listenButton.backgroundTintList=android.content.res.ColorStateList.valueOf(accent); listenButton.setTextColor(if(ink==Color.WHITE) Color.BLACK else Color.WHITE)
        muteButton = button("Mute") { command("mute") }; pauseButton = button("Pause") { command("pause") }
        for(b in listOf(listenButton,muteButton,pauseButton)) controls.addView(b,LinearLayout.LayoutParams(0,-2,1f).apply { marginEnd=dp(6);topMargin=dp(4);bottomMargin=dp(4) })
        player.addView(controls); shell.addView(player)
        val nav = LinearLayout(this).apply { setPadding(dp(4),0,dp(4),dp(4)); setBackgroundColor(surface) }
        val activeTab=if(page in listOf("Listen","Clusters","Settings"))page else history.firstOrNull { it in listOf("Listen","Clusters","Settings") } ?: "Settings"
        for(tab in listOf("Listen","Clusters","Settings")) nav.addView(button(tab) { go(tab,true) }.apply {
            isSelected = tab == activeTab; setTextColor(if(isSelected) accent else secondary)
            background=rounded(if(isSelected) { if(ink==Color.WHITE) Color.rgb(6,65,83) else Color.rgb(211,231,240) } else Color.TRANSPARENT,12f)
            contentDescription = if(isSelected) "$tab, selected" else tab
        },LinearLayout.LayoutParams(0,-2,1f))
        shell.addView(nav); setContentView(shell);shell.requestApplyInsets()
        if(Build.VERSION.SDK_INT>=30) {
            val light=android.view.WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or android.view.WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS
            window.insetsController?.setSystemBarsAppearance(if(ink==Color.WHITE)0 else light,light)
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility=if(ink==Color.WHITE)0 else View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        }
        refresh()
        (root.parent as? ScrollView)?.post { (root.parent as? ScrollView)?.scrollTo(0,scrollPositions[draftPage()] ?: 0) }
    }
    private fun rememberScroll() { (root.parent as? ScrollView)?.let { scrollPositions[draftPage()]=it.scrollY } }
    private fun frequencyUnitsAnchor():View = root.findViewWithTag("frequency_units")
    private fun refreshFilterPending() {
        val pending=ListeningSettings.defaults.any { (key,default) ->
            (drafts["Filters:$key"] ?: prefs.getString(key,default).orEmpty()) != prefs.getString(key,default).orEmpty()
        }
        filterApplyStatus?.text=if(pending)"Complete the unfinished fields. Other choices are saved."else "Filter changes save automatically."
    }
    private fun saveFilters(keys:Set<String>) {
        try {
            val changes=keys.filter { it in ListeningSettings.defaults }
            if(changes.none { (drafts["Filters:$it"] ?: prefs.getString(it,ListeningSettings.defaults[it])) != prefs.getString(it,ListeningSettings.defaults[it]) }) { refreshFilterPending();return }
            for(key in changes)if(key in listOf("min_khz","max_khz","max_age_seconds","repeat_seconds","spacing_seconds"))require(!drafts["Filters:$key"].isNullOrBlank())
            val values=ListeningSettings.json { key -> if(key in changes)drafts["Filters:$key"] ?: prefs.getString(key,ListeningSettings.defaults[key]).orEmpty() else prefs.getString(key,ListeningSettings.defaults[key]).orEmpty() }
            ListeningSettings.validate(values)
            val editor=prefs.edit();for(key in changes)editor.putString(key,values.get(key).toString());editor.apply()
            for(key in changes)drafts.remove("Filters:$key")
            if(ListenerService.listeningActive)command("apply") else { ListenerService.refilterDisplayed { key -> prefs.getString(key,ListeningSettings.defaults[key] ?: "").orEmpty() };synchronized(ListenerService.hidden){ListenerService.hidden.clear()} }
            refreshFilterPending()
        } catch(error:Exception) { filterApplyStatus?.text="Not saved: "+keys.joinToString(", ") { it.replace('_',' ') }+". Check this field and its allowed range." }
    }
    private fun saveFilter(key:String) {
        val keys=if(key in listOf("min_khz","max_khz"))setOf("min_khz","max_khz").filter { drafts.containsKey("Filters:$it") }.toSet() else setOf(key)
        saveFilters(keys)
    }
    private fun scheduleFilterSave(key:String) {
        filterSaves.remove(key)?.let { uiHandler.removeCallbacks(it) }
        val task=Runnable { filterSaves.remove(key);saveFilter(key) }
        filterSaves[key]=task;uiHandler.postDelayed(task,450)
        filterApplyStatus?.text="Saving when you finish typing…"
    }
    override fun onPause() {
        for((key,task) in filterSaves.toMap()) { uiHandler.removeCallbacks(task);saveFilter(key) }
        filterSaves.clear();flushSpeech();rememberScroll();super.onPause()
    }
    private fun homeContent() {
        val toolbar=LinearLayout(this).apply { gravity=Gravity.CENTER_VERTICAL }
        toolbar.addView(button(prefs.getString("profile_name","Choose cluster").orEmpty()) { go("Clusters",true) }.apply { maxLines=1;ellipsize=android.text.TextUtils.TruncateAt.END;contentDescription="Change cluster" },LinearLayout.LayoutParams(0,-2,1f))
        toolbar.addView(button("Filters") { go("Filters") },LinearLayout.LayoutParams(dp(84),-2))
        toolbar.addView(button("Spot") { go("Spot") },LinearLayout.LayoutParams(dp(70),-2));root.addView(toolbar)
        root.addView(label(SpotFilters.summary { key -> prefs.getString(key,"").orEmpty() },12f,secondary).apply { maxLines=2;ellipsize=android.text.TextUtils.TruncateAt.END })
        val heading=LinearLayout(this).apply { gravity=Gravity.CENTER_VERTICAL }
        heading.addView(label("Recent spots",16f).apply { setTypeface(null,Typeface.BOLD) },LinearLayout.LayoutParams(0,-2,1f))
        heading.addView(button(prefs.getString("frequency_unit","kHz").orEmpty()) {
            val menu=PopupMenu(this,frequencyUnitsAnchor())
            for(unit in listOf("kHz","MHz"))menu.menu.add(unit)
            menu.setOnMenuItemClickListener { choice ->
                prefs.edit().putString("frequency_unit",choice.title.toString()).apply()
                drafts.remove("Filters:frequency_unit");drafts.remove("Filters:Frequency units")
                ListenerService.reformatSpots(choice.title.toString())
                if(ListenerService.listeningActive)command("units")
                render();true
            };menu.show()
        }.apply { contentDescription="Change frequency units";tag="frequency_units" },LinearLayout.LayoutParams(dp(76),-2))
        heading.addView(button("Why hidden?") { val counts=synchronized(ListenerService.hidden){ListenerService.hidden.toMap()};AlertDialog.Builder(this).setTitle("Filtered reports").setMessage(if(counts.isEmpty())"No reports have been hidden in this session."else counts.entries.joinToString("\n"){it.key+": "+it.value}).setPositiveButton("Close",null).show() },LinearLayout.LayoutParams(dp(118),-2))
        root.addView(heading)
        spotsView=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(8),0,dp(8),0);background=rounded(surface) }
        root.addView(ScrollView(this).apply { isFillViewport=true;addView(spotsView) },LinearLayout.LayoutParams(-1,0,1f))
        val queueRow=LinearLayout(this).apply { gravity=Gravity.CENTER_VERTICAL }
        queueLabel=label("",12f,secondary);queueRow.addView(queueLabel,LinearLayout.LayoutParams(0,-2,1f))
        queueRow.addView(button("Live now") { command("catch_up") }.apply { contentDescription="Clear pending spots and catch up to live" },LinearLayout.LayoutParams(dp(100),-2));root.addView(queueRow)
    }
    private fun spotContent() {
        val panel=section("Share a DX spot")
        val call=edit(panel,"Station callsign",ListenerService.activeCall.ifBlank { prefs.getString("call","").orEmpty() })
        panel.addView(button("Use my callsign") { call.setText(ListenerService.activeCall) })
        val frequency=edit(panel,"Frequency","").apply { inputType=InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL }
        val unit=spinner(panel,"Units",listOf("kHz","MHz"),prefs.getString("frequency_unit","kHz").orEmpty())
        val comment=edit(panel,"Comment (optional)","").apply { filters=arrayOf(android.text.InputFilter.LengthFilter(100)) }
        spotResult=label(ListenerService.spotStatus,14f,secondary).apply { accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE };panel.addView(spotResult)
        panel.addView(label("Sends only to the TCP cluster you are monitoring. Cluster policy determines acceptance and propagation. A sent command is not confirmation of acceptance.",14f,secondary))
        panel.addView(button("Send spot") {
            try {
                require(ListenerService.listeningActive && ListenerService.connected) { "Connect and sign in to a TCP cluster first" }
                SpotSubmission.command(call.text.toString(),frequency.text.toString(),unit.selectedItem.toString(),comment.text.toString())
                val token=ListenerService.connectionToken
                startService(Intent(this,ListenerService::class.java).setAction("submit_spot").putExtra("session",token).putExtra("call",call.text.toString()).putExtra("frequency",frequency.text.toString()).putExtra("unit",unit.selectedItem.toString()).putExtra("comment",comment.text.toString()))
            } catch(error:Exception) { spotResult.text=error.message ?: "Check the callsign and frequency" }
        })
    }
    private fun refreshControls() {
        if(!::status.isInitialized)return
        listenButton.text = if(ListenerService.listeningActive) "Stop listening" else "Start listening"
        muteButton.text = if(ListenerService.muted) "Unmute" else "Mute"
        muteButton.backgroundTintList=android.content.res.ColorStateList.valueOf(if(ListenerService.muted) { if(ink==Color.WHITE)Color.rgb(23,88,60)else Color.rgb(214,243,227) } else surface)
        pauseButton.text = if(ListenerService.paused) "Resume" else "Pause"
        muteButton.isEnabled = ListenerService.listeningActive; pauseButton.isEnabled = ListenerService.listeningActive
        status.text = ListenerService.status + if(ListenerService.listeningActive) " · " + (if(ListenerService.muted) "Muted" else if(ListenerService.paused) "Paused" else "Audio on") else ""
    }
    private fun refresh() {
        refreshControls()
        if(page=="Spot" && ::spotResult.isInitialized)spotResult.text=ListenerService.spotStatus
        if(page != "Listen" || !::spotsView.isInitialized)return
        queueLabel.text="${ListenerService.queued} pending · oldest ${ListenerService.oldestSeconds}s · ${ListenerService.expired} expired"
        val items = synchronized(ListenerService.spots) { ListenerService.spots.toList() }
        if(spotsView.tag == items)return
        spotsView.tag = items; spotsView.removeAllViews()
        if(items.isEmpty()) spotsView.addView(label("Start listening to hear new matching spots. Your recent spots will appear here.",15f,secondary))
        items.take(60).forEach { item ->
            val row=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(0,dp(6),0,dp(6)) }
            row.addView(label(item.substringBefore('\n'),18f).apply { setTypeface(null,Typeface.BOLD) })
            if(item.contains('\n'))row.addView(label(item.substringAfter('\n'),13f,secondary))
            spotsView.addView(row)
        }
    }
    private fun showHome() = go("Listen",true)
    private fun showProfiles() = go("Clusters",true)
    private fun profiles(): JSONArray = try { JSONArray(prefs.getString("profiles", "[]")) } catch (_: Exception) { JSONArray() }
    private fun profilesContent() {
        val tools = section("Bring your clusters along")
        tools.addView(button("Scan desktop QR collection") { scanQr() })
        if(qrCollection.scanned > 0) { tools.addView(label("${qrCollection.scanned} of ${qrCollection.total} QR pages collected",14f)); tools.addView(button("Reset scan") { qrCollection.reset(); render() }) }
        tools.addView(button("Import profile file") { startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE),201) })
        tools.addView(button("Browse recommended clusters") { go("Directory") })
        tools.addView(button("Load cluster directory file") { startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE),203) })
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
                val previous=entries.toString()
                val updated=JSONArray();for(j in 0 until entries.length())if(j!=i)updated.put(entries.getJSONObject(j))
                prefs.edit().putString("profiles",updated.toString()).apply()
                inform("Profile removed. The active session is unchanged.") { prefs.edit().putString("profiles",previous).apply() }

            },LinearLayout.LayoutParams(0,-2,1f)); row.addView(actions)
        }
    }
    private fun directoryContent() {
        val panel=section("Recommended clusters")
        panel.addView(label("Choose a reviewed node to save its connection details. Nothing connects automatically. Retired entries cannot be added. Remove saved profiles from Clusters.",14f,secondary))
        try {
            val raw=prefs.getString("cluster_directory",null) ?: assets.open("catalog/clusters.json").bufferedReader().use { it.readText() }
            val entries=ClusterDirectory.read(raw)
            if(entries.length()==0)panel.addView(label("No recommended entries are installed. Add a cluster yourself, import a profile collection or load a reviewed directory file.",14f,secondary))
            for(i in 0 until entries.length()) {
                val entry=entries.getJSONObject(i);val card=section(entry.getString("name"));val c=entry.getJSONObject("connection")
                card.addView(label(entry.getString("description")+"\n"+c.getString("host")+":"+c.getInt("port")+"\n"+entry.getString("status")+" · checked "+entry.getString("checked"),14f,secondary))
                card.addView(button("Add to my clusters") {
                    val current=profiles();val name=entry.getString("name")
                    if((0 until current.length()).any { current.getJSONObject(it).optString("name")==name })Toast.makeText(this,"A profile with this name is already saved",Toast.LENGTH_LONG).show()
                    else {
                        current.put(JSONObject().put("name",name).put("host",c.getString("host")).put("port",c.getInt("port").toString()).put("call",c.getString("login").ifBlank { prefs.getString("call","").orEmpty() }).put("password","").put("source_type",c.getString("source_type")).put("feed_url",c.getString("feed_url")).put("poll_seconds",c.getInt("poll_seconds").toString()))
                        prefs.edit().putString("profiles",current.toString()).apply();Toast.makeText(this,"Cluster saved. Choose it in Clusters when ready.",Toast.LENGTH_LONG).show()
                    }
                }.apply { isEnabled=entry.getString("status")=="active" })
            }
        }catch(_:Exception) { panel.addView(label("The directory could not be read. Load a valid reviewed directory file.",14f,secondary)) }
    }
    private fun editProfile(index: Int?) {
        editIndex = index; go("Edit cluster")
    }
    private fun profileContent() {
        val p = editIndex?.let { profiles().optJSONObject(it) } ?: JSONObject().put("host","w4mr.ddns.net").put("port","7373")
        val panel = section(if(editIndex == null) "New cluster" else "Connection details")
        val name = edit(panel,"Profile name",p.optString("name","My cluster"))
        val type = spinner(panel,"Connection type",listOf("TCP/Telnet","HTTPS JSON"),p.optString("source_type","TCP/Telnet"))
        val host = edit(panel,"Hostname",p.optString("host")); val port = edit(panel,"Port",p.optString("port","7373")).apply { inputType = InputType.TYPE_CLASS_NUMBER }
        val url = edit(panel,"HTTPS feed URL",p.optString("feed_url")); val poll = edit(panel,"Poll interval (seconds)",p.optString("poll_seconds","30"))
        fun relevant() {
            val https = type.selectedItem == "HTTPS JSON"
            for((field,show) in listOf(host to !https,port to !https,url to https,poll to https)) {
                field.visibility=if(show)View.VISIBLE else View.GONE
                for(i in 0 until panel.childCount) {
                    val caption=panel.getChildAt(i)
                    if(caption is TextView && caption.labelFor==field.id)caption.visibility=field.visibility
                }
            }
        }
        type.onItemSelectedListener = object : AdapterView.OnItemSelectedListener { override fun onNothingSelected(parent: AdapterView<*>?) {} ; override fun onItemSelected(parent: AdapterView<*>?,view: View?,position: Int,id: Long) { drafts["${draftPage()}:Connection type"] = type.selectedItem.toString(); relevant() } }; relevant()
        val call = edit(panel,"Login callsign",p.optString("call"))
        val password = edit(panel,"Password or bearer token",runCatching { SecretStore.reveal(p.optString("password")) }.getOrDefault(""),true)
        panel.addView(CheckBox(this).apply { text = "Show password or token"; setTextColor(ink); setOnCheckedChangeListener { _, checked -> password.transformationMethod = if(checked) null else android.text.method.PasswordTransformationMethod.getInstance() } })
        val profileError=label("",13f,secondary);panel.addView(profileError)
        val activeProfile = editIndex != null && p.optString("name")==prefs.getString("profile_name","")
        panel.addView(button(if(activeProfile && ListenerService.listeningActive) "Save and reconnect" else "Save profile") {
            try {
                val source = type.selectedItem.toString(); val portValue = if(source=="TCP/Telnet")port.text.toString().toIntOrNull() ?: 0 else 7373; val pollValue = if(source=="HTTPS JSON")poll.text.toString().toIntOrNull() ?: 0 else 30
                require(name.text.isNotBlank() && name.length()<=80) { "Enter a profile name up to 80 characters." }
                require(portValue in 1..65535) { "Port must be between 1 and 65535." }
                require(pollValue in 15..3600) { "Poll interval must be between 15 and 3600 seconds." }
                val hostValue = host.text.toString().trim(); val login = call.text.toString().trim()
                require(login.isEmpty() || Regex("[A-Za-z0-9][A-Za-z0-9/\\-]{1,19}").matches(login) && login.any { it.isDigit() } && login.any { it.isLetter() })
                if(source == "TCP/Telnet") require(hostValue.isNotBlank() && hostValue.length <= 253 && hostValue.none { it.isWhitespace() || it in "/:@" })
                else { val uri = java.net.URI(url.text.toString()); require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null && uri.fragment == null) }
                val value = JSONObject().put("name",name.text.toString().trim()).put("source_type",source).put("host",hostValue).put("port",portValue.toString()).put("call",login)
                    .put("password",SecretStore.protect(password.text.toString())).put("feed_url",url.text.toString()).put("poll_seconds",pollValue.toString())
                val entries = profiles(); if(editIndex == null) entries.put(value) else entries.put(editIndex!!,value)
                prefs.edit().putString("profiles",entries.toString()).apply()
                if(activeProfile) {
                    val editor=prefs.edit().putString("profile_name",value.getString("name"))
                    for(key in listOf("host","port","call","password","source_type","feed_url","poll_seconds"))editor.putString(key,value.optString(key))
                    editor.apply();if(ListenerService.listeningActive)command("switch")
                }
                drafts.keys.filter { it.startsWith("${draftPage()}:") }.toList().forEach { drafts.remove(it) }; onBackPressed()
            } catch(error:Exception) { profileError.text=error.message?.takeIf { it!="Failed requirement." } ?: "Check the connection address and login callsign." }
        })
    }
    private fun spinner(panel: LinearLayout, title: String, values: List<String>, selected: String, key:String=title): Spinner {
        panel.addView(label(title,13f,secondary))
        return Spinner(this).apply {
            contentDescription=title
            adapter = ArrayAdapter(this@MainActivity,android.R.layout.simple_spinner_dropdown_item,values)
            setSelection(values.indexOf(drafts["${draftPage()}:$key"] ?: selected).coerceAtLeast(0)); panel.addView(this)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) {}
                override fun onItemSelected(parent: AdapterView<*>?,view: View?,position: Int,id: Long) { drafts["${draftPage()}:$key"] = values[position];if(page=="Filters")saveFilter(key) }
            }
        }
    }
    private fun settingsContent() {
        val sound = section("Make it sound right")
        sound.addView(button("Voice and announcement") { go("Speech") }); sound.addView(button("What do you want to hear?") { go("Filters") })
        val appearance = section("Appearance")
        val picker = spinner(appearance,"Theme",listOf("System","Light","Dark","High contrast"),prefs.getString("appearance","System").orEmpty())
        picker.onItemSelectedListener=object:AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent:AdapterView<*>?) {}
            override fun onItemSelected(parent:AdapterView<*>?,view:View?,position:Int,id:Long) {
                val selected=picker.selectedItem.toString()
                if(selected!=prefs.getString("appearance","System")) { prefs.edit().putString("appearance",selected).apply();recreate() }
            }
        }
        val diagnostics = section("Help and diagnostics")
        diagnostics.addView(label("Listening continues when you change pages. Pause holds announcements for Resume while the feed stays connected. Mute discards audio while spots continue updating. Android Back returns to the previous page.",14f,secondary))
        diagnostics.addView(CheckBox(this).apply { text="Keep diagnostic logs locally"; setTextColor(ink); isChecked=prefs.getBoolean("diagnostics",true); setOnCheckedChangeListener { _,checked -> prefs.edit().putBoolean("diagnostics",checked).apply() } })
        diagnostics.addView(button("Export diagnostic report") { startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").putExtra(Intent.EXTRA_TITLE,"DXTalker-Android-diagnostics.zip"),202) })
        diagnostics.addView(label("No automatic log upload. DX Talker " + packageManager.getPackageInfo(packageName,0).versionName,13f,secondary))
    }
    private fun speechContent() {
        val panel = section("Announcement builder")
        panel.addView(label("Choose what to say and move the sections into your preferred order. Comments are never spoken.",14f,secondary))
        val current = prefs.getString("format","New DX on. {frequency} {unit}. {call}.").orEmpty()
        val layout=AnnouncementLayout.read(current)
        val intro = edit(panel,"Intro phrase",layout.intro.ifBlank { "New DX" }).apply { filters=arrayOf(android.text.InputFilter.LengthFilter(80)) }
        val initialOrder=layout.order
        val order = (drafts["Speech:order"] ?: initialOrder.joinToString(",")).split(',').toMutableList()
        val flags = mutableMapOf<String,CheckBox>()
        val rows = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }; panel.addView(rows)
        fun draw() {
            rows.removeAllViews()
            order.forEachIndexed { index,key ->
                val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
                val enabled = drafts["Speech:include_$key"]?.toBoolean() ?: (key in layout.included)
                val check = CheckBox(this).apply { text=key.replaceFirstChar { it.uppercase() }; setTextColor(ink); isChecked=enabled; setOnCheckedChangeListener { _,checked -> drafts["Speech:include_$key"] = checked.toString();scheduleSpeechSave() } }
                flags[key]=check; row.addView(check,LinearLayout.LayoutParams(0,-2,1f))
                row.addView(button("Up") { java.util.Collections.swap(order,index,index-1); drafts["Speech:order"]=order.joinToString(","); draw();scheduleSpeechSave() }.apply { isEnabled=index>0; contentDescription="Move $key up" },LinearLayout.LayoutParams(dp(72),-2).apply { marginEnd=dp(4) })
                row.addView(button("Down") { java.util.Collections.swap(order,index,index+1); drafts["Speech:order"]=order.joinToString(","); draw();scheduleSpeechSave() }.apply { isEnabled=index<order.lastIndex; contentDescription="Move $key down" },LinearLayout.LayoutParams(dp(72),-2)); rows.addView(row)
            }
        }; draw()
        val units = CheckBox(this).apply { text="Speak kHz or MHz"; setTextColor(ink); isChecked=drafts["Speech:units"]?.toBoolean() ?: layout.units; setOnCheckedChangeListener { _,checked -> drafts["Speech:units"]=checked.toString();scheduleSpeechSave() } }; panel.addView(units)
        speechStatus=label("Announcement changes save automatically.",13f,secondary);panel.addView(speechStatus)
        val voice = section("System voice")
        voice.addView(label("Uses your installed Android speech engine. Voice downloads and engine choices are managed in Android settings.",14f,secondary))
        voice.addView(button("Open speech settings") { try { startActivity(Intent("com.android.settings.TTS_SETTINGS")) } catch(_:Exception) { Toast.makeText(this,"Open Android Settings and search for text to speech",Toast.LENGTH_LONG).show() } })
        voice.addView(button("Test announcement") { flushSpeech();command("test") })
    }
    private fun scheduleSpeechSave() {
        speechSave?.let { uiHandler.removeCallbacks(it) }
        speechStatus?.text="Saving when you finish editing…"
        speechSave=Runnable { speechSave=null;saveSpeech() }.also { uiHandler.postDelayed(it,450) }
    }
    private fun flushSpeech() { speechSave?.let { uiHandler.removeCallbacks(it);speechSave=null;saveSpeech() } }
    private fun saveSpeech() {
        val layout=AnnouncementLayout.read(prefs.getString("format","New DX on. {frequency} {unit}. {call}.").orEmpty())
        val order=(drafts["Speech:order"] ?: layout.order.joinToString(",")).split(',')
        val units=drafts["Speech:units"]?.toBoolean() ?: layout.units
        val parts=order.filter { drafts["Speech:include_$it"]?.toBoolean() ?: (it in layout.included) }.map {
            when(it) { "intro" -> (drafts["Speech:Intro phrase"] ?: layout.intro).trim().replace("{","").replace("}","")
                "callsign" -> "{call}";else -> "{frequency}"+if(units)" {unit}"else "" }
        }
        if(parts.isEmpty() || parts.any { it.isBlank() }) { speechStatus?.text="Not saved. Enter an intro or disable it and keep at least one section.";return }
        val format=parts.joinToString(". ")+"."
        if(format!=prefs.getString("format","")) { prefs.edit().putString("format",format).apply();if(ListenerService.listeningActive)command("format") }
        speechStatus?.text="Saved. Example: "+format.replace("{frequency}",if(prefs.getString("frequency_unit","kHz")=="MHz")"14.0255"else "14025.5").replace("{unit}",prefs.getString("frequency_unit","kHz").orEmpty()).replace("{call}","WB4IUY")
    }
    private fun chooseFilter(key: String,title: String,values: List<String>) {
        val selected=prefs.getString(key,"").orEmpty().split(',').toSet()
        val checks=BooleanArray(values.size) { values[it] in selected || prefs.getString(key,"").isNullOrEmpty() && (key!="filter_modes" || values[it]!="Unknown") }
        val dialog=AlertDialog.Builder(this).setTitle(title).setMultiChoiceItems(values.map { if(it=="General")"No activity tag"else if(it=="Unknown")"Include unknown"else it }.toTypedArray(),checks) { dialog,index,checked ->
            checks[index]=checked
            if(key=="filter_modes" && values[index]=="Unknown" && checked && prefs.getString(key,"").isNullOrEmpty()) {
                values.indices.forEach { checks[it]=true;(dialog as AlertDialog).listView.setItemChecked(it,true) }
            }
            drafts["Filters:$key"]=values.filterIndexed { i,_ -> checks[i] }.joinToString(",").ifEmpty { "None" }
            saveFilter(key)
        }.setNeutralButton(if(key=="filter_modes")"All known modes"else "All") { _,_ -> drafts["Filters:$key"]="";saveFilter(key) }
            .setNegativeButton("None") { _,_-> drafts["Filters:$key"]="None";saveFilter(key) }.setPositiveButton("Close",null).create()
        dialog.setOnDismissListener { render() };dialog.show()
    }
    private fun filterContent() {
        val panel = section("What do you want to hear?")
        fun staged(key:String)=drafts["Filters:$key"] ?: prefs.getString(key,ListeningSettings.defaults[key] ?: "").orEmpty()
        panel.addView(label(SpotFilters.summary { staged(it) }+" · "+staged("frequency_unit"),14f,secondary))
        panel.addView(label("Changes save automatically and update displayed and announced spots. Your cluster stays connected.",13f,secondary))
        val saved=section("Listening presets").apply { visibility=if(drafts["Filters:presets_open"]=="true")View.VISIBLE else View.GONE }
        panel.addView(button("Listening presets") { drafts["Filters:presets_open"]=(drafts["Filters:presets_open"]!="true").toString();render() })
        val presets=runCatching { JSONObject(prefs.getString("listening_presets","{}").orEmpty()) }.getOrDefault(JSONObject())
        val preset=spinner(saved,"Saved listening preset",listOf("Choose preset")+presets.keys().asSequence().toList(),"Choose preset")
        var lastPresetChoice=preset.selectedItem.toString()
        preset.onItemSelectedListener=object:AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent:AdapterView<*>?) {}
            override fun onItemSelected(parent:AdapterView<*>?,view:View?,position:Int,id:Long) {
                val chosen=preset.selectedItem.toString()
                if(chosen==lastPresetChoice)return
                lastPresetChoice=chosen
                presets.optJSONObject(chosen)?.let { values ->
                    for((key,default) in ListeningSettings.defaults)drafts["Filters:$key"]=values.opt(key)?.toString() ?: default
                    val changed=ListeningSettings.defaults.any { (key,default)->(drafts["Filters:$key"] ?: default)!=prefs.getString(key,default) }
                    saveFilters(ListeningSettings.defaults.keys)
                    drafts["Filters:Saved listening preset"]=preset.selectedItem.toString()
                    if(changed)render()
                }
            }
        }
        saved.addView(button("Save current choices as preset") {
            val name=EditText(this).apply { setSingleLine();hint="For example Portable POTA" }
            AlertDialog.Builder(this).setTitle("Name this listening preset").setView(name).setNegativeButton("Cancel",null).setPositiveButton("Save") { _,_ ->
                try {
                    val title=name.text.toString().trim();require(title.isNotBlank() && title.length<=60 && title.none { it.code<32 })
                    val values=ListeningSettings.json { staged(it) };ListeningSettings.validate(values)
                    presets.put(title,values);require(presets.length()<=30)
                    prefs.edit().putString("listening_presets",presets.toString()).apply();render()
                } catch(_:Exception) { Toast.makeText(this,"Check the name and current filter choices",Toast.LENGTH_LONG).show() }
            }.show()
        })
        saved.addView(button("Remove selected preset") {
            val previous=presets.toString();presets.remove(preset.selectedItem.toString());prefs.edit().putString("listening_presets",presets.toString()).apply()
            inform("Preset removed.") { prefs.edit().putString("listening_presets",previous).apply() }
        })
        for((key,title,values) in listOf(Triple("filter_bands","Bands",SpotFilters.bands.keys.toList()+"Other"),Triple("filter_modes","Modes",SpotFilters.modes),Triple("filter_activities","Activities",SpotFilters.activities))) {
            panel.addView(button(title+": "+staged(key).replace("General","No activity tag").replace("Unknown","Include unknown").ifBlank { if(key=="filter_modes")"All known modes"else "All" }) { chooseFilter(key,title,values) })
        }
        panel.addView(label("Choose POTA, 20m and SSB to require all three. Selecting several bands accepts any of those bands. Mode comes from a reported tag or a single mode band segment. Include unknown admits uncertain modes within your other selections.",14f,secondary))
        panel.addView(CheckBox(this).apply { text="Use POTA / FOTA / SOTA wording during mixed listening";setTextColor(ink);isChecked=staged("activity_announcements")=="true";setOnCheckedChangeListener { _,checked -> drafts["Filters:activity_announcements"]=checked.toString();saveFilter("activity_announcements") } })
        panel.addView(label("Activity-only selections use this wording automatically: activity, mode, frequency, callsign. Unknown modes are omitted. All listening filters still apply.",14f,secondary))
        val license=section("My operating privileges (optional)")
        spinner(license,"FCC license class",UsPrivileges.classes,staged("license_class"),key="license_class").apply {
            onItemSelectedListener=object:AdapterView.OnItemSelectedListener { override fun onNothingSelected(p:AdapterView<*>?){};override fun onItemSelected(p:AdapterView<*>?,v:View?,position:Int,id:Long){drafts["Filters:license_class"]=UsPrivileges.classes[position];saveFilter("license_class")} }
        }
        spinner(license,"Operating region",UsPrivileges.regions,staged("license_region"),key="license_region").apply {
            onItemSelectedListener=object:AdapterView.OnItemSelectedListener { override fun onNothingSelected(p:AdapterView<*>?){};override fun onItemSelected(p:AdapterView<*>?,v:View?,position:Int,id:Long){drafts["Filters:license_region"]=UsPrivileges.regions[position];saveFilter("license_region")} }
        }
        license.addView(CheckBox(this).apply { text="Include unverified license eligibility";setTextColor(ink);isChecked=staged("license_unknown")=="true";setOnCheckedChangeListener { _,checked -> drafts["Filters:license_unknown"]=checked.toString();saveFilter("license_unknown") } })
        panel.addView(button("Location, timing and frequency limits") { drafts["Filters:advanced"] = (!(drafts["Filters:advanced"]?.toBoolean() ?: false)).toString();render() })
        val advanced=section("Location and advanced filters").apply { visibility=if(drafts["Filters:advanced"]?.toBoolean()==true)View.VISIBLE else View.GONE }
        for((key,title) in listOf("filter_spotter_countries" to "Reporting station countries (US,CA)","filter_spotter_continents" to "Reporting station continents (NA,EU)","filter_spotter_regions" to "Reporting station regions (NC,SC,GA)","filter_dx_countries" to "DX station countries (US,JP)","filter_dx_continents" to "DX station continents (NA,EU)","location_overrides" to "Known station locations (CALL=US,NA,NC)"))edit(advanced,title,staged(key),key=key)
        advanced.addView(CheckBox(this).apply { text="Include unknown locations";setTextColor(ink);isChecked=staged("geography_unknown")=="true";setOnCheckedChangeListener { _,checked->drafts["Filters:geography_unknown"]=checked.toString();saveFilter("geography_unknown") } })
        advanced.addView(label("Location requires feed metadata or your known station list. Callsigns alone do not establish current locations. Separate known stations with a semicolon. Leave location fields blank to accept all.",14f,secondary))
        for((key,title) in listOf("min_khz" to "Minimum frequency (kHz)","max_khz" to "Maximum frequency (kHz)","max_age_seconds" to "Maximum spot age (30 to 600 seconds)","repeat_seconds" to "Repeat suppression (30 to 3600 seconds)","spacing_seconds" to "Additional gap (0 to 120 seconds)"))edit(advanced,title,staged(key),key=key).apply { inputType=InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL }
        root.addView(button("Filter help and FCC sources") {
            AlertDialog.Builder(this).setTitle("Listening filters").setMessage("Unknown means no single mode can be identified from the report or frequency. Include unknown admits those spots for display and speech within your other selections. No activity tag means no POTA, SOTA or FOTA tag was recognized. License filtering checks reported frequency and mode, not occupied bandwidth, split frequency or every location and station condition. It does not grant permission to transmit. Sources and current limitations are in the maintained Help page.")
                .setPositiveButton("Open Help") { _,_->startActivity(Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://github.com/Liberty-Chris/DX_Talker/blob/main/docs/help/listening_filters.md"))) }.setNegativeButton("Close",null).show()
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
            importData=data
            go("Import collection")
        } catch (_: Exception) { Toast.makeText(this,"Invalid or unsupported DX Talker transfer",Toast.LENGTH_LONG).show() }
    }
    private fun importContent() {
        val data=importData ?: return
        val panel=section("Import collection")
        val entries=data.getJSONArray("profiles")
        for(i in 0 until entries.length())panel.addView(label(entries.getJSONObject(i).getString("name")))
        panel.addView(label("Adds these profiles and imports their filters. Existing profiles are preserved and duplicate names are renamed. Credentials are excluded. No connection starts automatically.",14f,secondary))
        panel.addView(button("Import ${entries.length()} profiles and filters") {
            try { TransferCodec.importInto(data,prefs);drafts.keys.filter { it.startsWith("Filters:") }.toList().forEach { drafts.remove(it) };importData=null;showProfiles() }
            catch(_:Exception) { inform("Import could not be saved. Try again.") }
        })
    }
    private fun scanQr() {
        if (!packageManager.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)) {
            Toast.makeText(this,"No camera is available. Import a transfer file instead.",Toast.LENGTH_LONG).show(); return
        }
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            cameraScanRequested = true
            requestPermissions(arrayOf(Manifest.permission.CAMERA), 303)
            return
        }
        launchQrCamera()
    }
    private fun launchQrCamera() {
        cameraScanRequested = false
        try { startActivityForResult(Intent(this,QrScanActivity::class.java).putStringArrayListExtra("qr_pages",qrCollection.saved()),304) }
        catch (error:RuntimeException) {
            MobileDiagnostics.record(this,"qr_camera_launch_failed",error)
            Toast.makeText(this,"The scanner could not open. Import a transfer file or export diagnostics.",Toast.LENGTH_LONG).show()
        }
    }
    override fun onRequestPermissionsResult(requestCode:Int, permissions:Array<out String>, grantResults:IntArray) {
        super.onRequestPermissionsResult(requestCode,permissions,grantResults)
        if (requestCode != 303) return
        val requested = cameraScanRequested; cameraScanRequested = false
        if (requested && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) launchQrCamera()
        else {
            MobileDiagnostics.record(this,"qr_camera_permission_denied")
            AlertDialog.Builder(this).setTitle("Camera permission needed")
                .setMessage("QR scanning needs camera access. Allow it in Android app settings or import a transfer file instead. Your collected QR pages are preserved.")
                .setNegativeButton("Close",null).setPositiveButton("App settings") { _,_ ->
                    startActivity(Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,android.net.Uri.parse("package:$packageName")))
                }.show()
        }
    }
    @Deprecated("Legacy activity results are used by the QR scanner")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode,resultCode,data)
        if(requestCode==304) {
            data?.getStringArrayListExtra("qr_pages")?.let { pages -> qrCollection.reset();pages.forEach { runCatching { qrCollection.accept(it) } } }
            data?.getStringExtra("collection_json")?.takeIf { resultCode==RESULT_OK }?.let { raw ->
                try { val collection=TransferCodec.decode(raw);qrCollection.reset();reviewImportData(collection) }
                catch(_:Exception) { inform("The scanned collection could not be read. Scan it again or import a file.") }
            }
            return
        }
        if(requestCode==202&&resultCode==RESULT_OK){
            try{val uri=data?.data?:return;contentResolver.openOutputStream(uri)?.use{output->java.util.zip.ZipOutputStream(output).use{zip->
                val dir=java.io.File(filesDir,"diagnostics")
                dir.listFiles()?.filter{it.name.startsWith("events.jsonl")&&it.length()<=1024*1024}?.forEach{file->zip.putNextEntry(java.util.zip.ZipEntry(file.name));file.inputStream().use{it.copyTo(zip)};zip.closeEntry()}
            }}}catch(_:Exception){Toast.makeText(this,"Could not export diagnostics",Toast.LENGTH_LONG).show()};return
        }
        if (requestCode in listOf(201,203) && resultCode == RESULT_OK) {
            try {
                val uri = data?.data ?: return
                contentResolver.openInputStream(uri)?.use { input ->
                    val output = java.io.ByteArrayOutputStream()
                    val buffer = ByteArray(4096)
                    while (true) { val n=input.read(buffer); if(n<0) break; output.write(buffer,0,n); require(output.size()<=65536) }
                    val text=output.toString("UTF-8")
                    if(requestCode==203) {
                        val entries=ClusterDirectory.read(text)
                        val previous=prefs.getString("cluster_directory",null)
                        prefs.edit().putString("cluster_directory",text).apply();go("Directory")
                        inform("Loaded ${entries.length()} directory entries.") { val edit=prefs.edit();if(previous==null)edit.remove("cluster_directory")else edit.putString("cluster_directory",previous);edit.apply() }
                    }else reviewImport(text)
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
    override fun onStop() { uiHandler.removeCallbacks(refreshTask);refreshQueued=false;unregisterReceiver(receiver); super.onStop() }
}
