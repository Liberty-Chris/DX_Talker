package club.dxtalker.android

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Test
import org.junit.Assert.*
import java.time.Instant

class SpotFilterTests {
    @Test fun usesTheSameFixturesAsDesktop() {
        val cases=JSONArray(javaClass.getResource("/spot_filters.json")!!.readText())
        for(i in 0 until cases.length()) {
            val c=cases.getJSONObject(i)
            val spot=SpotPolicy.parse(c.getString("line"),Instant.parse("2026-11-06T12:34:00Z"))!!
            assertEquals(c.getString("line"),c.getString("mode"),SpotFilters.mode(spot.comment,spot.mode,spot.frequency))
            assertEquals(c.getJSONArray("activities").let { tags -> (0 until tags.length()).map { tags.getString(it) }.toSet() },SpotFilters.tags(spot.comment))
            assertEquals(c.getBoolean("match"),SpotFilters.matches(spot) { key -> c.getJSONObject("filters").optString(key,"") })
            val decision=SpotPresentation.decide(spot) { key -> c.getJSONObject("filters").optString(key,"") }
            assertEquals(c.getBoolean("match"),decision.row.isNotEmpty())
            assertEquals(c.getBoolean("match"),decision.speech.isNotEmpty())
            assertFalse(SpotPolicy.speak(spot,"{call}. {frequency} {unit}.","MHz").contains("POTA"))
        }
    }
    @Test fun explicitModesAndAmbiguityAreConservative() {
        assertEquals("SSB",SpotFilters.mode("FT8 POTA","USB"))
        assertEquals("Unknown",SpotFilters.mode("FT8 CW"))
        assertEquals("Unknown",SpotFilters.mode("FT8","invalid"))
        assertEquals(160,SpotFilters.clean("a".repeat(200)).length)
        assertEquals("POTA",SpotFilters.clean("PO\u0000TA"))
        assertThrows(Exception::class.java) { SpotFilters.selection("POTA,POTA",SpotFilters.activities) }
        assertThrows(Exception::class.java) { SpotFilters.selection("FT9",SpotFilters.modes) }
        assertNull(SpotPolicy.parse("DX de N0CALL: 14074 WB4IUY 11234Z",Instant.parse("2026-11-06T12:34:00Z")))
    }
    @Test fun acceptsV1AndV2AndRejectsUnknownFilterValues() {
        val data=JSONObject("""{"schema":"dxtalker-transfer","version":2,"profiles":[{"name":"Home","connection":{"source_type":"TCP/Telnet","host":"cluster.example","port":7373,"login":"KF4DBX","feed_url":"","poll_seconds":30}}],"filters":{"filter_bands":"20m,40m","filter_modes":"FT8,Unknown","filter_activities":"POTA,SOTA"}}""")
        assertEquals("FT8,Unknown",TransferCodec.decode(data.toString()).getJSONObject("filters").getString("filter_modes"))
        data.put("version",1);assertEquals(1,TransferCodec.decode(data.toString()).getInt("version"))
        data.getJSONObject("filters").put("filter_modes","FT9")
        assertThrows(Exception::class.java) { TransferCodec.decode(data.toString()) }
    }
    @Test fun legacyImportClearsNewSelectionsAndPreservesTheActiveProfile() {
        val values=mutableMapOf("filter_modes" to "CW","filter_activities" to "POTA","host" to "active.example")
        val editor=java.lang.reflect.Proxy.newProxyInstance(javaClass.classLoader,arrayOf(android.content.SharedPreferences.Editor::class.java)) { proxy,method,args ->
            when(method.name) { "putString" -> { values[args!![0] as String]=args[1] as String;proxy }; "commit" -> true; else -> null }
        } as android.content.SharedPreferences.Editor
        val prefs=java.lang.reflect.Proxy.newProxyInstance(javaClass.classLoader,arrayOf(android.content.SharedPreferences::class.java)) { _,method,args ->
            when(method.name) { "getString" -> values[args!![0] as String] ?: args[1]; "edit" -> editor; else -> null }
        } as android.content.SharedPreferences
        val data=TransferCodec.decode("""{"schema":"dxtalker-transfer","version":1,"profiles":[{"name":"Home","connection":{"source_type":"TCP/Telnet","host":"cluster.example","port":7373,"login":"KF4DBX","feed_url":"","poll_seconds":30}}],"filters":{}}""")
        TransferCodec.importInto(data,prefs)
        assertEquals("",values["filter_modes"]);assertEquals("",values["filter_activities"])
        assertEquals("active.example",values["host"])
        val profiles=JSONArray(values["profiles"])
        assertEquals(1,profiles.length());assertEquals("",profiles.getJSONObject(0).getString("password"))
    }

}
