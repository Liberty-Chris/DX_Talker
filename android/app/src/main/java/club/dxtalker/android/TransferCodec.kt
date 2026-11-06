package club.dxtalker.android

import android.content.SharedPreferences
import org.json.JSONObject
import org.json.JSONArray
import java.util.Base64
import java.util.zip.Inflater

object TransferCodec {
    private const val MAX = 65536
    private val connectionKeys = setOf("source_type","host","port","login","feed_url","poll_seconds")
    private val filterKeys = setOf("min_khz","max_khz","max_age_seconds","repeat_seconds","spacing_seconds","frequency_unit")
    private fun keys(value: JSONObject) = value.keys().asSequence().toSet()
    fun decode(text: String): JSONObject {
        var raw = text.toByteArray(Charsets.UTF_8)
        if (text.startsWith("DXT1:")) {
            require(raw.size <= 1800) { "QR transfer too large" }
            val inflater = Inflater()
            try {
                inflater.setInput(Base64.getUrlDecoder().decode(text.substring(5)))
                val out = ByteArray(MAX + 1)
                var count = 0
                while (!inflater.finished() && count < out.size) {
                    val read = inflater.inflate(out, count, out.size-count)
                    require(read > 0) { "Incomplete compressed transfer" }
                    count += read
                }
                require(inflater.finished() && inflater.remaining == 0 && count <= MAX) { "Oversized or incomplete transfer" }
                raw = out.copyOf(count)
            } finally { inflater.end() }
        }
        require(raw.size <= MAX) { "Transfer exceeds 64 KiB" }
        val data = JSONObject(String(raw, Charsets.UTF_8))
        require(keys(data) == setOf("schema","version","profiles","filters") && data.getString("schema") == "dxtalker-transfer" && data.opt("version") is Int && data.getInt("version") == 1) { "Unsupported DX Talker transfer" }
        val profiles = data.getJSONArray("profiles")
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
        val f = data.getJSONObject("filters")
        require(filterKeys.containsAll(keys(f))) { "Unsupported filter fields" }
        for(key in keys(f)){
            val value=f.get(key)
            if(key=="frequency_unit")require(value is String) else {
                require(value is Number && value.toDouble().isFinite()) { "Filter numbers must be numeric" }
                if(key in setOf("max_age_seconds","repeat_seconds","spacing_seconds")) require(value.toDouble()%1.0==0.0) { "Timing values must be integers" }
            }
        }
        val low = f.optDouble("min_khz",1.0); val high = f.optDouble("max_khz",10000000.0)
        require(low.isFinite() && high.isFinite() && low >= 1 && high >= low && high <= 10000000)
        require(f.optInt("max_age_seconds",180) in 30..600 && f.optInt("repeat_seconds",300) in 30..3600 && f.optInt("spacing_seconds",5) in 1..120)
        require(f.optString("frequency_unit","kHz") in listOf("kHz","MHz"))
        return data
    }
    fun importInto(data: JSONObject, prefs: SharedPreferences) {
        // Call only after decode and explicit review. One editor commits all changes atomically.
        val existing = JSONArray(prefs.getString("profiles","[]"))
        val names = (0 until existing.length()).map { existing.getJSONObject(it).optString("name").lowercase() }.toMutableSet()
        val incoming = data.getJSONArray("profiles")
        for (i in 0 until incoming.length()) {
            val p = incoming.getJSONObject(i); val c = p.getJSONObject("connection")
            var name = p.getString("name"); var suffix = 2
            while (name.lowercase() in names) { name = p.getString("name").take(65) + " (import $suffix)"; suffix++ }
            names.add(name.lowercase())
            existing.put(JSONObject().put("name",name).put("host",c.getString("host")).put("port",c.getInt("port").toString())
                .put("call",c.getString("login")).put("password", "").put("source_type",c.getString("source_type"))
                .put("feed_url",c.getString("feed_url")).put("poll_seconds",c.getInt("poll_seconds")))
        }
        val editor = prefs.edit().putString("profiles",existing.toString())
        val f = data.getJSONObject("filters")
        for (key in filterKeys) if (f.has(key)) editor.putString(key,f.get(key).toString())
        check(editor.commit()) { "Could not save imported profiles" }
    }
}
