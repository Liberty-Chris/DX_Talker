package club.dxtalker.android

/** Local metadata matching. Never places comments in speech or diagnostics. */
object SpotFilters {
    val bands = linkedMapOf(
        "160m" to (1800L to 2000L),
        "80m" to (3500L to 4000L),
        "60m" to (5250L to 5450L),
        "40m" to (7000L to 7300L),
        "30m" to (10100L to 10150L),
        "20m" to (14000L to 14350L),
        "17m" to (18068L to 18168L),
        "15m" to (21000L to 21450L),
        "12m" to (24890L to 24990L),
        "10m" to (28000L to 29700L),
        "6m" to (50000L to 54000L),
        "4m" to (70000L to 70500L),
        "2m" to (144000L to 148000L),
        "1.25m" to (222000L to 225000L),
        "70cm" to (420000L to 450000L),
        "33cm" to (902000L to 928000L),
        "23cm" to (1240000L to 1300000L))
    val modes = listOf("CW","SSB","FT8","FT4","RTTY","PSK","FM","AM","Unknown")
    val activities = listOf("POTA","SOTA","FOTA","General")
    private val modeWord = Regex("(?<![A-Z0-9])(?:CW|SSB|USB|LSB|FT8|FT4|RTTY|PSK(?:31|63|125)?|FM|AM)(?![A-Z0-9])",RegexOption.IGNORE_CASE)
    fun clean(value: String) = value.filter { it.code in 32..126 }.take(160)
    private fun normalize(value: String): String = when(val v=value.uppercase(java.util.Locale.US)) { "USB","LSB" -> "SSB"; else -> if(v.startsWith("PSK")) "PSK" else v }
    fun mode(comment: String,explicit: String = ""): String {
        if(explicit.isNotEmpty())return if(modeWord.matches(explicit))normalize(explicit) else "Unknown"
        val found=modeWord.findAll(comment).map { normalize(it.value) }.toSet()
        return found.singleOrNull() ?: "Unknown"
    }
    fun tags(comment: String): Set<String> = activities.dropLast(1).filter {
        Regex("(?<![A-Z0-9])"+it+"(?![A-Z0-9])",RegexOption.IGNORE_CASE).containsMatchIn(comment)
    }.toSet().ifEmpty { setOf("General") }
    fun selection(value: String,allowed: Collection<String>): Set<String> {
        val parts=if(value.isEmpty()) emptyList() else value.split(',')
        require(parts.size == parts.toSet().size && allowed.containsAll(parts)) { "Invalid spot filters" }
        return parts.toSet()
    }
    fun rejection(spot:DxSpot,get:(String)->String):String {
        val selectedBands=selection(get("filter_bands"),bands.keys+"Other")
        val selectedModes=selection(get("filter_modes"),modes)
        val selectedActivities=selection(get("filter_activities"),activities)
        val band=bands.entries.firstOrNull { spot.frequency>=it.value.first.toBigDecimal() && spot.frequency<it.value.second.toBigDecimal() }?.key ?: "Other"
        if(selectedBands.isNotEmpty() && band !in selectedBands)return "Band"
        val mode=mode(spot.comment,spot.mode)
        if(selectedModes.isNotEmpty() && mode !in selectedModes)return if(mode=="Unknown")"Mode unknown"else "Mode"
        if(selectedActivities.isNotEmpty() && tags(spot.comment).none { it in selectedActivities })return "Activity tag"
        val eligibility=UsPrivileges.eligibility(spot.frequency,mode,get("license_class").ifBlank { "Off" },get("license_region").ifBlank { "US Region 2" })
        if(eligibility=="outside")return "Outside selected license segments"
        if(eligibility=="unknown" && get("license_unknown")!="true")return "License eligibility unverified"
        return SpotLocations.rejection(spot,get)
    }
    fun matches(spot:DxSpot,get:(String)->String)=rejection(spot,get).isEmpty()
    fun summary(get: (String)->String):String {
        val parts=mutableListOf<String>()
        if(get("license_class").isNotBlank() && get("license_class")!="Off")parts.add(get("license_class")+" class")
        for((key,default) in listOf("filter_bands" to "All bands","filter_modes" to "All modes","filter_activities" to "All activities"))parts.add(get(key).replace("General","No activity tag").ifBlank { default })
        for((key,title) in listOf("filter_spotter_countries" to "Reported from","filter_spotter_continents" to "Reporting continents","filter_spotter_regions" to "Reporting regions","filter_dx_countries" to "DX countries","filter_dx_continents" to "DX continents"))if(get(key).isNotBlank())parts.add(title+": "+get(key))
        return parts.joinToString(" · ")
    }
}
