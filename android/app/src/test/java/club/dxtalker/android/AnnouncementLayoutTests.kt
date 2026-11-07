package club.dxtalker.android

import org.junit.Test
import org.junit.Assert.*

class AnnouncementLayoutTests {
    @Test fun restoresAnIntroAtTheEndWithoutLosingItsWords() {
        val layout=AnnouncementLayout.read("{frequency} {unit}. {call}. New DX on.")
        assertEquals("New DX on",layout.intro)
        assertEquals(listOf("frequency","callsign","intro"),layout.order)
        assertEquals(setOf("intro","callsign","frequency"),layout.included)
        assertTrue(layout.units)
    }
    @Test fun omittedSectionsStayOmitted() {
        val layout=AnnouncementLayout.read("{call}.")
        assertEquals(setOf("callsign"),layout.included);assertFalse(layout.units)
        assertEquals("",layout.intro)
        assertEquals("callsign",layout.order.first())
    }
    @Test fun allOrdersAndOptionalSectionsSurviveReopening() {
        val orders=listOf(listOf("intro","frequency","callsign"),listOf("intro","callsign","frequency"),listOf("frequency","intro","callsign"),listOf("frequency","callsign","intro"),listOf("callsign","intro","frequency"),listOf("callsign","frequency","intro"))
        for(order in orders)for(mask in 1..7)for(units in listOf(true,false)) {
            val enabled=listOf("intro","frequency","callsign").filterIndexed { i,_ -> mask and (1 shl i) != 0 }.toSet()
            val text=order.filter { it in enabled }.joinToString(". ") { when(it) { "intro" -> "New DX"; "frequency" -> "{frequency}"+if(units)" {unit}" else ""; else -> "{call}" } }+"."
            val restored=AnnouncementLayout.read(text)
            assertEquals(enabled,restored.included)
            assertEquals(order.filter { it in enabled },restored.order.filter { it in enabled })
            assertEquals(units && "frequency" in enabled,restored.units)
        }
    }
}
