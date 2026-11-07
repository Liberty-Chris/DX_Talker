package club.dxtalker.android

/** Reads the saved template without moving an intro that was placed after the call or frequency. */
data class AnnouncementLayout(val intro: String, val order: List<String>, val included: Set<String>, val units: Boolean) {
    companion object {
        fun read(template: String): AnnouncementLayout {
            val token=Regex("\\{(?:call|frequency|unit)\\}",RegexOption.IGNORE_CASE)
            val positions=mutableMapOf<String,Int>()
            val fragments=mutableListOf<String>()
            var previous=0
            fun text(start: Int,end: Int) {
                val value=template.substring(start,end).trim { it.isWhitespace() || it=='.' }
                if(value.isNotBlank()) { fragments.add(value);positions.putIfAbsent("intro",start) }
            }
            token.findAll(template).forEach { match ->
                text(previous,match.range.first)
                val key=when(match.value.lowercase(java.util.Locale.US)) { "{call}" -> "callsign"; "{frequency}" -> "frequency"; else -> "unit" }
                positions.putIfAbsent(key,match.range.first);previous=match.range.last+1
            }
            text(previous,template.length)
            val order=listOf("intro","frequency","callsign").sortedBy { positions[it] ?: Int.MAX_VALUE }
            return AnnouncementLayout(fragments.joinToString(". "),order,positions.keys.intersect(setOf("intro","frequency","callsign")),positions.containsKey("unit"))
        }
    }
}
