package club.dxtalker.android

import android.content.SharedPreferences
import org.json.JSONObject
import org.json.JSONArray
import java.util.Base64
import java.util.zip.Inflater

object TransferCodec {
    private const val MAX = 65536
    private val connectionKeys = setOf("source_type","host","port","login","feed_url","poll_seconds")
    private const val LISTENING_VERSION = 4
    private const val PRESETS = "listening_presets"
    private val filterKeys = ListeningSettings.defaults.keys + PRESETS
    fun isListening(data: JSONObject) = data.getInt("version") == LISTENING_VERSION
    private fun keys(value: JSONObject) = value.keys().asSequence().toSet()
    fun decode(text: String): JSONObject {
        val raw = text.toByteArray(Charsets.UTF_8)
        if (text.startsWith("DXT1:")) {
            require(raw.size <= 1800) { "QR transfer too large" }
            return decodeCompressed(Base64.getUrlDecoder().decode(text.substring(5)))
        }
        require(raw.size <= MAX) { "Transfer exceeds 64 KiB" }
        val data = JSONObject(String(raw, Charsets.UTF_8))
        require(data.opt("schema") == "dxtalker-transfer" && data.opt("version") is Int &&
                data.getInt("version") in 1..LISTENING_VERSION) { "Unsupported DX Talker transfer" }
        val fields = setOf("schema", "version", "filters")
        require(keys(data) == if (isListening(data)) fields else fields + "profiles") { "Invalid DX Talker transfer fields" }
        if (!isListening(data)) validateProfiles(data.getJSONArray("profiles"))
        validateFilters(data.getJSONObject("filters"))
        return data
    }
    private fun validateProfiles(profiles: JSONArray) {
        require(profiles.length() > 0) { "No profiles in transfer" }
        for (i in 0 until profiles.length()) {
            val p = profiles.getJSONObject(i)
            require(keys(p) == setOf("name","connection")) { "Credentials cannot be imported" }
            val name = p.getString("name")
            require(name.isNotBlank() && name.length <= 80 && name.none { it.code < 32 }) { "Invalid profile name" }
            val c = p.getJSONObject("connection")
            require(keys(c) == connectionKeys) { "Invalid connection fields" }
            require(c.getString("source_type") in listOf("TCP/Telnet","HTTPS JSON"))
            require(c.opt("port") is Int && c.opt("poll_seconds") is Int) { "Connection numbers must be integers" }
            require(c.getInt("port") in 1..65535 && c.getInt("poll_seconds") in 15..3600)
            val login = c.getString("login")
            require(login.isEmpty() || Regex("[A-Za-z0-9][A-Za-z0-9/\\-]{1,19}").matches(login) && login.any { it.isDigit() } && login.any { it.isLetter() }) { "Invalid callsign" }
            if (c.getString("source_type") == "TCP/Telnet") {
                val host = c.getString("host")
                require(host.isNotBlank() && host.length <= 253 && host.none { it.isWhitespace() || it in "/:@" }) { "Invalid hostname" }
            } else {
                val uri = java.net.URI(c.getString("feed_url"))
                require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null && uri.fragment == null && uri.query == null) { "Feed URL must be HTTPS without credentials or query parameters" }
            }
        }
    }
    fun validateFilters(f: JSONObject, allowPresets: Boolean = true) {
        require(filterKeys.containsAll(keys(f)) && (allowPresets || !f.has(PRESETS))) { "Unsupported filter fields" }
        for(key in keys(f)){
            val value=f.get(key)
            if(value is String)require(value.length <= (if(key=="listening_presets")32768 else if(key in setOf("location_overrides","special_keywords"))8192 else 2048) && value.none { it.code<32 })
            if(key in setOf("special_keywords_only","special_calls_only","special_calls_portable","activity_announcements","license_unknown","geography_unknown"))require(value is Boolean)
            else if(key=="frequency_unit" || key.startsWith("filter_") || key in setOf("special_keywords","special_alert","special_calls","license_class","license_region","location_overrides","listening_presets"))require(value is String) else {
                require(value is Number && value.toDouble().isFinite()) { "Filter numbers must be numeric" }
                if(key in setOf("max_age_seconds","repeat_seconds","spacing_seconds")) require(value is Int) { "Timing values must be integers" }
            }
        }
        val low = f.optDouble("min_khz",1.0); val high = f.optDouble("max_khz",10000000.0)
        require(low.isFinite() && high.isFinite() && low >= 1 && high >= low && high <= 10000000)
        require(f.optInt("max_age_seconds",180) in 30..600 && f.optInt("repeat_seconds",300) in 30..3600 && f.optInt("spacing_seconds",5) in 0..120)
        require(f.optString("frequency_unit","kHz") in listOf("kHz","MHz"))
        SpotFilters.selection(f.optString("filter_bands",""),SpotFilters.bands.keys+"Other")
        SpotFilters.selection(f.optString("filter_modes",""),SpotFilters.modes)
        SpotFilters.selection(f.optString("filter_activities",""),SpotFilters.activities)
        val words=SpotFilters.keywordSelection(f.optString("special_keywords",""))
        require(!f.optBoolean("special_keywords_only",false) || words.isNotEmpty()) { "Add a special word or turn off Only these words" }
        require(f.optString("special_alert","Off") in SpecialAlert.sounds) { "Choose a valid special match sound" }
        val calls=SpotFilters.callsSelection(f.optString("special_calls",""))
        require(!f.optBoolean("special_calls_only",false) || calls.isNotEmpty()) { "Add a special callsign or turn off Only these calls" }
        require(f.optString("license_class","Off") in UsPrivileges.classes && f.optString("license_region","US Region 2") in UsPrivileges.regions)
        SpotLocations.validate { key -> f.optString(key,"") }
        val presets=JSONObject(f.optString("listening_presets","{}"));require(presets.length()<=30)
        for(name in keys(presets)) {
            require(name.isNotBlank() && name.length<=60 && name.none { it.code<32 })
            validateFilters(presets.getJSONObject(name), allowPresets = false)
        }
    }
    fun decodeCompressed(compressed: ByteArray): JSONObject {
        require(compressed.size <= MAX + 1024) { "Compressed transfer too large" }
        val inflater = Inflater()
        try {
            inflater.setInput(compressed)
            val out = ByteArray(MAX + 1)
            var count = 0
            while (!inflater.finished() && count < out.size) {
                val read = inflater.inflate(out, count, out.size-count)
                require(read > 0) { "Incomplete compressed transfer" }
                count += read
            }
            require(inflater.finished() && inflater.remaining == 0 && count <= MAX) { "Oversized or incomplete transfer" }
            val text = String(out, 0, count, Charsets.UTF_8)
            require(text.trimStart().startsWith("{")) { "Expected a transfer document" }
            return decode(text)
        } finally { inflater.end() }
    }
    fun importInto(data: JSONObject, prefs: SharedPreferences) {
        // Commit the filters and presets together after review and validation.
        val editor = prefs.edit()
        val filters = data.getJSONObject("filters")
        val incomingPresets = filters.optString(PRESETS, "{}")
        val presets = if (isListening(data)) {
            mergePresets(prefs.getString(PRESETS, "{}").orEmpty(), incomingPresets)
        } else {
            editor.putString("profiles", appendProfiles(data.getJSONArray("profiles"), prefs))
            incomingPresets
        }
        for ((key, default) in ListeningSettings.defaults) {
            editor.putString(key, filters.opt(key)?.toString() ?: default)
        }
        editor.putString(PRESETS, presets)
        check(editor.commit()) { "Could not save imported listening settings" }
    }
    private fun mergePresets(saved: String, incoming: String): String {
        val existing = JSONObject(saved)
        val additions = JSONObject(incoming)
        for (name in keys(additions)) {
            val values = additions.getJSONObject(name)
            var candidate = name
            var suffix = 2
            while (existing.has(candidate) && !samePreset(existing.getJSONObject(candidate), values)) {
                val ending = " (import ${suffix++})"
                candidate = name.take(60 - ending.length) + ending
            }
            existing.put(candidate, values)
        }
        val merged = existing.toString()
        require(existing.length() <= 30 && merged.length <= 32768) {
            "The combined listening presets exceed the limit. Remove some presets before importing."
        }
        return merged
    }
    private fun samePreset(left: JSONObject, right: JSONObject): Boolean =
        keys(left) == keys(right) && keys(left).all { left.get(it).toString() == right.get(it).toString() }

    private fun appendProfiles(incoming: JSONArray, prefs: SharedPreferences): String {
        val existing = JSONArray(prefs.getString("profiles", "[]"))
        val names = (0 until existing.length()).map { existing.getJSONObject(it).optString("name").lowercase() }.toMutableSet()
        for (i in 0 until incoming.length()) {
            val p = incoming.getJSONObject(i); val c = p.getJSONObject("connection")
            var name = p.getString("name"); var suffix = 2
            while (name.lowercase() in names) { name = p.getString("name").take(65) + " (import $suffix)"; suffix++ }
            names.add(name.lowercase())
            existing.put(JSONObject().put("name",name).put("host",c.getString("host")).put("port",c.getInt("port").toString())
                .put("call",c.getString("login")).put("password", "").put("source_type",c.getString("source_type"))
                .put("feed_url",c.getString("feed_url")).put("poll_seconds",c.getInt("poll_seconds")))
        }
        return existing.toString()
    }
}
