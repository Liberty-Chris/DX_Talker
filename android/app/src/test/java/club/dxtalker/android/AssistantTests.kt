package club.dxtalker.android
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Test
import org.junit.Assert.*
import java.time.Instant
import java.math.BigDecimal

class AssistantTests {
    @Test fun reviewedLicenseBoundariesMatchDesktop() {
        val cases=JSONArray(javaClass.getResource("/us_privileges.json")!!.readText())
        for(i in 0 until cases.length()) {
            val c=cases.getJSONArray(i)
            assertEquals(c.toString(),c.getString(4),UsPrivileges.eligibility(c.getString(2).toBigDecimal(),c.getString(1),c.getString(0),c.getString(3)))
        }
    }
    @Test fun combinationsAndLocationRolesAreIndependent() {
        val spot=DxSpot("JA1ABC",BigDecimal("14225"),Instant.now(),"POTA SSB",spotter="WB4IUY",location=mapOf("dx_country" to "JP","dx_continent" to "AS","spotter_country" to "US","spotter_continent" to "NA","spotter_region" to "NC"))
        val selected=mapOf("filter_bands" to "20m,40m","filter_modes" to "SSB","filter_activities" to "POTA","filter_spotter_countries" to "US","filter_dx_countries" to "JP","filter_spotter_regions" to "NC,SC","license_class" to "General")
        assertTrue(SpotFilters.matches(spot) { selected[it].orEmpty() })
        assertFalse(SpotFilters.matches(spot) { if(it=="filter_dx_countries")"US"else selected[it].orEmpty() })
        val missing=spot.copy(location=mapOf("dx_country" to "JP"))
        assertEquals("Location unknown",SpotFilters.rejection(missing) { selected[it].orEmpty() })
        assertTrue(SpotFilters.matches(missing) { if(it=="location_overrides")"WB4IUY=US,NA,NC"else selected[it].orEmpty() })
        assertFalse(SpotFilters.matches(spot.copy(mode="",comment="POTA")) { selected[it].orEmpty() })
        assertTrue(SpotFilters.matches(spot.copy(mode="",comment="POTA")) { when(it){"license_unknown"->"true";"filter_modes"->"";else->selected[it].orEmpty()} })
    }
    @Test fun v3TransfersCarryPresetsAndRejectUnsafeFieldsAndInvalidTypes() {
        val filters=ListeningSettings.json { when(it) { "license_class"->"General";"spacing_seconds"->"0";"filter_bands"->"20m";else->"" } }
        filters.put("listening_presets","""{"POTA":{"filter_activities":"POTA","filter_bands":"20m"}}""")
        ListeningSettings.validate(filters)
        assertThrows(Exception::class.java) { ListeningSettings.validate(JSONObject(filters.toString()).put("listening_presets","""{"bad":{"password":"secret"}}""")) }
        assertThrows(Exception::class.java) { ListeningSettings.validate(JSONObject(filters.toString()).put("license_unknown","true")) }
        assertThrows(Exception::class.java) { ListeningSettings.validate(JSONObject(filters.toString()).put("filter_spotter_continents","XX")) }
        assertThrows(Exception::class.java) { ListeningSettings.validate(JSONObject(filters.toString()).put("spacing_seconds",-1)) }
    }
    @Test fun spottingUsesOnlyValidatedSingleCommands() {
        assertEquals("DX 14225 WB4IUY POTA US-0001",SpotSubmission.command("wb4iuy","14.2250000","MHz","POTA US-0001"))
        for(comment in listOf("hello\nBYE","test; BYE","test|BYE"))assertThrows(Exception::class.java) { SpotSubmission.command("WB4IUY","14225","kHz",comment) }
        assertThrows(Exception::class.java) { SpotSubmission.command("BAD","14225","kHz","") }
        assertThrows(Exception::class.java) { SpotSubmission.command("WB4IUY","NaN","kHz","") }
    }
    @Test fun directoryRetainsStatusAndRejectsCredentials() {
        val entry=JSONObject("""{"id":"fixture","name":"Fixture","connection":{"source_type":"TCP/Telnet","host":"cluster.example","port":7373,"login":"","feed_url":"","poll_seconds":30},"status":"retired","checked":"2026-11-07","description":"Offline test"}""")
        val data=JSONObject().put("schema","dxtalker-directory").put("version",1).put("entries",JSONArray().put(entry))
        assertEquals("retired",ClusterDirectory.read(data.toString()).getJSONObject(0).getString("status"))
        entry.getJSONObject("connection").put("password","secret")
        assertThrows(Exception::class.java) { ClusterDirectory.read(data.toString()) }
    }
}
