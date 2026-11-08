package club.dxtalker.android

import org.junit.Test
import org.junit.Assert.*
import java.math.BigDecimal
import java.time.Instant

class SpotPresentationTests {
    private val spot=DxSpot("WB4IUY",BigDecimal("14225"),Instant.parse("2026-11-08T12:34:00Z"),"SSB")
    @Test fun displayOnlyIncludesReportedModeAndRealActivityTags() {
        val plain=SpotPresentation.row(spot,"kHz")
        assertTrue(plain.contains("SSB"));assertFalse(plain.contains("General"));assertFalse(plain.contains("No activity"))
        assertTrue(SpotPresentation.row(spot.copy(comment="SSB POTA"),"MHz").contains("POTA"))
        assertFalse(SpotPresentation.row(spot.copy(comment="CQ"),"kHz").contains("Unknown"))
        assertTrue(SpotPresentation.row(spot,"MHz").contains("14.225 MHz"))
    }
    @Test fun bandModeAndLicenseRejectionsProduceNeitherRowsNorSpeech() {
        val filters=mapOf("filter_bands" to "20m","filter_modes" to "SSB","license_class" to "General","license_region" to "US Region 2","frequency_unit" to "MHz")
        val accepted=SpotPresentation.decide(spot) { filters[it].orEmpty() }
        assertEquals("",accepted.reason);assertTrue(accepted.row.contains("14.225 MHz"));assertTrue(accepted.speech.contains("megahertz"))
        for((bad,reason) in listOf(spot.copy(frequency=BigDecimal("7225")) to "Band",spot.copy(comment="CW") to "Mode",spot.copy(frequency=BigDecimal("14200")) to "Outside selected license segments")) {
            val result=SpotPresentation.decide(bad) { filters[it].orEmpty() }
            assertEquals(reason,result.reason);assertEquals("",result.row);assertEquals("",result.speech)
        }
        val pota=SpotPresentation.decide(spot) { if(it=="filter_activities")"POTA"else filters[it].orEmpty() }
        assertEquals("Activity tag",pota.reason);assertEquals("",pota.speech)
    }
}
