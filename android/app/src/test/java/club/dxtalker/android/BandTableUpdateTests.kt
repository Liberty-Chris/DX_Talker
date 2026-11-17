package club.dxtalker.android

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.time.Instant

class BandTableUpdateTests {
    @Test fun individualModesDigitalAndUnknownStayDistinct() {
        for(mode in SpotFilters.modes.filter { it!="Unknown" }) {
            assertEquals(mode,SpotFilters.mode(mode,"","3540".toBigDecimal()))
        }
        assertEquals("CW",SpotFilters.mode("","","3540".toBigDecimal()))
        assertEquals("Unknown",SpotFilters.mode("","","14074".toBigDecimal()))
        assertEquals("Unknown",SpotFilters.mode("CW DIGITAL","","3540".toBigDecimal()))
        assertEquals("Unknown",SpotFilters.mode("JT65","","3540".toBigDecimal()))
        assertEquals("MFSK",SpotFilters.mode("MFSK16"))
        assertEquals("HELL",SpotFilters.mode("HELLSCHREIBER"))
    }
    @Test fun exactBandPolicyEdgesAndDiscreteChannels() {
        for((frequency,mode,expected) in listOf(
            Triple("14074","FT8","eligible"),Triple("14075.9999","FT8","eligible"),Triple("14076","FT8","outside"),
            Triple("14075","DIGITAL","eligible"),Triple("14075","Unknown","unknown"),
            Triple("5332","CW","eligible"),Triple("5332.0001","CW","outside"),
            Triple("3540","RTTY","outside"))) {
            assertEquals(expected,SpotFilters.bandPolicy(frequency.toBigDecimal(),mode,"General"))
        }
        // Legal emission authorization and the supplied listening table stay separate.
        assertEquals("eligible",UsPrivileges.eligibility("3540".toBigDecimal(),"RTTY","General"))
    }
    @Test fun receivedUntaggedSelfSubmissionHonorsBothUnknownOptions() {
        val spot=SpotPolicy.parse("DX de KF4DBX:   146520.0  AC4QD        pota                           0557Z",Instant.parse("2026-11-17T05:57:00Z"))!!
        for(license in listOf("Technician","General","Advanced","Extra")) {
            val values=mapOf("license_class" to license,"license_region" to "US Region 2","license_unknown" to "true","filter_modes" to SpotFilters.modes.joinToString(","))
            fun reason(changes:Map<String,String> = emptyMap()):String {
                val settings=values+changes
                return SpotPresentation.decide(spot) { settings[it].orEmpty() }.reason
            }
            assertEquals("",reason())
            val admitted=SpotPresentation.decide(spot) { values[it].orEmpty() }
            assertTrue(admitted.row.contains("AC4QD"))
            assertTrue(admitted.speech.isNotBlank())
            assertEquals("License eligibility unverified",reason(mapOf("license_unknown" to "false")))
            assertEquals("Mode unknown",reason(mapOf("filter_modes" to "FM")))
            assertEquals("Band",reason(mapOf("filter_bands" to "20m")))
            assertEquals("Outside selected license segments",reason(mapOf("license_class" to "Novice")))
            assertEquals("Frequency range",reason(mapOf("max_khz" to "30000")))
            assertEquals("Outside selected license segments",SpotFilters.rejection(spot.copy(frequency="149000".toBigDecimal())) { values[it].orEmpty() })
            assertEquals(if(license=="Technician")"Outside selected license segments" else "Outside selected band table",SpotFilters.rejection(spot.copy(frequency="3540".toBigDecimal(),comment="RTTY")) { values[it].orEmpty() })
        }
    }
    @Test fun allNewActivitiesHaveAnnouncementText() {
        for(tag in listOf("IOTA","JOTA","LLOTA")) {
            val spot=DxSpot("W1AW/3","14225".toBigDecimal(),Instant.now(),"SSB $tag")
            assertTrue(SpotPolicy.speak(spot,"{call}. {frequency} {unit}.","MHz",true).startsWith(tag))
            assertEquals(setOf("General"),SpotFilters.tags("NOT$tag"))
        }
    }
    @Test fun specialCallsTransferRetainsTypedOptions() {
        val data=JSONObject("""{"schema":"dxtalker-transfer","version":3,"profiles":[{"name":"Test","connection":{"source_type":"TCP/Telnet","host":"cluster.example","port":7373,"login":"KF4DBX","feed_url":"","poll_seconds":30}}],"filters":{"special_calls":"W1AW,TZ4AM","special_calls_only":true,"special_calls_portable":false,"filter_modes":"WSPR,DIGITAL,Unknown","filter_activities":"IOTA,LLOTA"}}""")
        assertEquals("W1AW,TZ4AM",TransferCodec.decode(data.toString()).getJSONObject("filters").getString("special_calls"))
        data.getJSONObject("filters").put("special_calls", "")
        assertThrows(Exception::class.java) { TransferCodec.decode(data.toString()) }
        assertEquals(setOf("W1AW"),SpotFilters.callsSelection("W1AW,w1aw"))
    }
}
