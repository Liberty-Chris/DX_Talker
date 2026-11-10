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
    @Test fun optionalActivityWordingPreservesListeningFilters() {
        val filters=mutableMapOf("filter_bands" to "20m","filter_modes" to "SSB","license_class" to "General","frequency_unit" to "MHz","format" to "Custom DX {call} {unit}","activity_announcements" to "true")
        for((tag,pronunciation) in listOf("POTA" to "poughta","FOTA" to "phota","SOTA" to "sota")) {
            val tagged=spot.copy(comment=tag+" SSB private-comment")
            val result=SpotPresentation.decide(tagged) { filters[it].orEmpty() }
            assertEquals("",result.reason)
            assertTrue(result.row.contains(tag));assertEquals(tag+" SSB private-comment",tagged.comment)
            assertEquals(pronunciation+". SSB. one four point two two five megahertz. Whiskey Bravo four India Uniform Yankee.",result.speech)
            val rejected=SpotPresentation.decide(tagged) { if(it=="filter_bands")"40m"else filters[it].orEmpty() }
            assertEquals("Band",rejected.reason);assertEquals("",rejected.speech)
        }
        val multiple=SpotPresentation.decide(spot.copy(comment="sota FOTA pota SSB")) { filters[it].orEmpty() }
        assertTrue(multiple.speech.startsWith("poughta. phota. sota. SSB."))
        val tagged=spot.copy(comment="POTA SSB")
        filters["activity_announcements"]="false"
        assertTrue(SpotPresentation.decide(tagged) { filters[it].orEmpty() }.speech.startsWith("Custom DX"))
        filters["filter_activities"]="POTA"
        assertTrue(SpotPresentation.decide(tagged) { filters[it].orEmpty() }.speech.startsWith("poughta. SSB."))
        filters["filter_modes"]="Unknown";filters["license_class"]="Off"
        val unknown=SpotPresentation.decide(spot.copy(comment="POTA private-comment")) { filters[it].orEmpty() }
        assertTrue(unknown.speech.startsWith("poughta. one four"));assertFalse(unknown.speech.contains("Unknown"))
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
