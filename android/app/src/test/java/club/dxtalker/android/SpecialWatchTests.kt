package club.dxtalker.android

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.time.Instant

class SpecialWatchTests {
    @Test fun wordsAndPhrasesAreLiteralCaseInsensitiveAndBounded() {
        val words=SpotFilters.keywordSelection("Cobia,county hunter,USS   Test")
        for(text in listOf("USS COBIA submarine","county   hunter CQ","uss test today"))assertTrue(SpotFilters.keywordMatches(text,words))
        for(text in listOf("scobias","county hunters","USStest"))assertFalse(SpotFilters.keywordMatches(text,words))
        assertTrue(SpotFilters.keywordMatches("CQ (A+B)",SpotFilters.keywordSelection("A+B")))
        assertThrows(Exception::class.java) { SpotFilters.keywordSelection("Cobia,cOBIA") }
        assertThrows(Exception::class.java) { SpotFilters.keywordSelection(".*") }
    }
    @Test fun callsOrWordsQualifyButOtherFiltersStillApply() {
        val spot=DxSpot("K1ABC","14225".toBigDecimal(),Instant.now(),"SSB USS Cobia",spotter="W1AW")
        val filters=mutableMapOf("special_calls" to "TZ4AM","special_calls_only" to "true","special_keywords" to "Cobia","special_keywords_only" to "true","filter_activities" to "POTA")
        assertTrue(SpotFilters.matches(spot) { filters[it].orEmpty() })
        assertTrue(SpotFilters.matches(spot.copy(call="TZ4AM",comment="SSB DX")) { filters[it].orEmpty() })
        assertFalse(SpotFilters.matches(spot.copy(comment="SSB DX")) { filters[it].orEmpty() })
        filters["filter_bands"]="40m"
        assertFalse(SpotFilters.matches(spot) { filters[it].orEmpty() })
        filters["filter_bands"]="20m"; filters["filter_modes"]="CW"
        assertFalse(SpotFilters.matches(spot) { filters[it].orEmpty() })
    }
    @Test fun specifiedCallMatchesTheDxStationNotReporter() {
        val s=DxSpot("K1ABC","14225".toBigDecimal(),Instant.now(),"SSB",spotter="W1AW")
        val filters=mapOf("special_calls" to "W1AW","special_calls_only" to "true")
        assertFalse(SpotFilters.matches(s) { filters[it].orEmpty() })
        assertTrue(SpotFilters.matches(s.copy(call="W1AW/3")) { filters[it].orEmpty() })
    }
    @Test fun generatedSoundsAreShortPcm16WithCorrectWaveHeader() {
        for(kind in SpecialAlert.sounds.filter { it!="Off" }) {
            val bytes=SpecialAlert.wav(kind);val header=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            assertEquals("RIFF",String(bytes.copyOfRange(0,4)))
            assertEquals(bytes.size-8,header.getInt(4))
            assertEquals(22050,header.getInt(24))
            assertEquals(bytes.size-44,header.getInt(40))
            assertTrue(bytes.size>1000 && bytes.size<44144)
            assertEquals(0,header.getShort(bytes.size-2).toInt())
        }
        assertThrows(Exception::class.java) { SpecialAlert.wav("Off") }
    }
    @Test fun transfersRetainKeywordAndSoundPreferences() {
        val data=JSONObject("""{"schema":"dxtalker-transfer","version":3,"profiles":[{"name":"Test","connection":{"source_type":"TCP/Telnet","host":"cluster.example","port":7373,"login":"KF4DBX","feed_url":"","poll_seconds":30}}],"filters":{"special_keywords":"Cobia,county hunter","special_keywords_only":true,"special_alert":"Double ding"}}""")
        assertEquals("Double ding",TransferCodec.decode(data.toString()).getJSONObject("filters").getString("special_alert"))
        data.getJSONObject("filters").put("special_keywords","")
        assertThrows(Exception::class.java) { TransferCodec.decode(data.toString()) }
    }
}
