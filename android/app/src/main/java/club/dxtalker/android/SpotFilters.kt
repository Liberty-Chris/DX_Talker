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
    val modes = listOf("CW","AM","FM","SSB","RTTY","FT4","FT8","10MRPT","DOMINO","HELL","MFSK","MT63","OLIVIA","THROB","PSK","MSK144","FSK441","JT6M","JTSCALL","WSPR","DIGITAL","Unknown")
    val activities = listOf("POTA","SOTA","FOTA","IOTA","JOTA","LLOTA","General")
    private val modeWord = Regex("(?<![A-Z0-9])(?:CW|AM|FM|SSB|USB|LSB|RTTY|FT4|FT8|10MRPT|DOMINO(?:EX)?|HELL(?:SCHREIBER)?|MFSK(?:\\d+)?|MT63|OLIVIA|THROB|PSK(?:31|63|125)?|MSK144|FSK441|JT6M|JTSCALL|WSPR|DIGI(?:TAL)?)(?![A-Z0-9])",RegexOption.IGNORE_CASE)
    fun clean(value: String) = value.filter { it.code in 32..126 }.take(160)
    private fun normalize(value: String): String = when(val v=value.uppercase(java.util.Locale.US)) { "USB","LSB" -> "SSB"; else -> when { v.startsWith("PSK")->"PSK";v.startsWith("MFSK")->"MFSK";v=="DOMINOEX"->"DOMINO";v=="HELLSCHREIBER"->"HELL";v=="DIGI"->"DIGITAL";else->v } }
    // US operating practice inference, separate from license privileges.
    // Digital overlaps remain Unknown. Sources: docs/mode_inference.md.
    val modeSegments = BandTableData.inference
    private val otherModeWord = Regex("(?<![A-Z0-9])(?:FT2|FT9|JT(?!6M(?![A-Z0-9]))\\d+[A-Z]*|JS8(?:CALL)?|Q65|QRA64|SSTV|FAX|DATA|DMR|DSTAR|D-STAR|C4FM|FUSION|DV)(?![A-Z0-9])",RegexOption.IGNORE_CASE)
    fun mode(comment: String,explicit: String = "",frequency: java.math.BigDecimal? = null): String {
        if(explicit.isNotEmpty())return if(modeWord.matches(explicit))normalize(explicit) else "Unknown"
        val found=modeWord.findAll(comment).map { normalize(it.value) }.toSet()
        if(otherModeWord.containsMatchIn(comment))return "Unknown"
        if(found.isNotEmpty())return found.singleOrNull() ?: "Unknown"
        return modeSegments.firstOrNull { frequency!=null && frequency>=it.first && frequency<it.second }?.third ?: "Unknown"
    }
    fun tags(comment: String): Set<String> = activities.dropLast(1).filter {
        Regex("(?<![A-Z0-9])"+it+"(?![A-Z0-9])",RegexOption.IGNORE_CASE).containsMatchIn(comment)
    }.toSet().ifEmpty { setOf("General") }
    fun selection(value: String,allowed: Collection<String>): Set<String> {
        if(value=="None")return setOf("None")
        val parts=if(value.isEmpty()) emptyList() else value.split(',')
        require(parts.size == parts.toSet().size && allowed.containsAll(parts)) { "Invalid spot filters" }
        return parts.toSet()
    }
    fun activityTags(comment:String)=listOf("POTA","FOTA","SOTA","IOTA","JOTA","LLOTA").filter { it in tags(comment) }
    fun activityStyle(get:(String)->String):Boolean {
        val selected=selection(get("filter_activities"),activities)
        return get("activity_announcements")=="true" || selected.isNotEmpty() && selected.all { it in listOf("POTA","FOTA","SOTA","IOTA","JOTA","LLOTA") }
    }
    fun rejection(spot:DxSpot,get:(String)->String):String {
        val selectedBands=selection(get("filter_bands"),bands.keys+"Other")
        val selectedModes=selection(get("filter_modes"),modes)
        val selectedActivities=selection(get("filter_activities"),activities)
        val band=bands.entries.firstOrNull { spot.frequency>=it.value.first.toBigDecimal() && spot.frequency<it.value.second.toBigDecimal() }?.key ?: "Other"
        val calls=callsSelection(get("special_calls"))
        val portable=get("special_calls_portable")!="false"
        val callMatch=spot.call.uppercase() in calls || portable && calls.any { '/' !in it && it in spot.call.uppercase().split('/') }
        if(selectedBands.isNotEmpty() && band !in selectedBands && !callMatch)return "Band"
        val mode=mode(spot.comment,spot.mode,spot.frequency)
        if(mode=="Unknown" && "Unknown" !in selectedModes)return "Mode unknown"
        if(selectedModes.isNotEmpty() && mode !in selectedModes)return if(mode=="Unknown")"Mode unknown"else "Mode"
        val wordMatch=keywordMatches(spot.comment,keywordSelection(get("special_keywords")))
        if(get("special_calls_only")=="true" || get("special_keywords_only")=="true") {
            if(!(get("special_calls_only")=="true" && callMatch || get("special_keywords_only")=="true" && wordMatch))return if(get("special_keywords_only")=="true")"Special calls or words" else "Special calls"
        } else if(selectedActivities.isNotEmpty() && tags(spot.comment).none { it in selectedActivities } && !callMatch && !wordMatch)return "Activity tag"
        val eligibility=UsPrivileges.eligibility(spot.frequency,mode,get("license_class").ifBlank { "Off" },get("license_region").ifBlank { "US Region 2" })
        if(eligibility=="outside")return "Outside selected license segments"
        if(eligibility=="unknown" && get("license_unknown")!="true")return "License eligibility unverified"
        if(get("license_class").ifBlank { "Off" }!="Off" && get("license_region").ifBlank { "US Region 2" }=="US Region 2") {
            val policy=bandPolicy(spot.frequency,mode,get("license_class"))
            if(policy=="outside")return "Outside selected band table"
            if(policy=="unknown" && get("license_unknown")!="true")return "License eligibility unverified"
        }
        return SpotLocations.rejection(spot,get)
    }
    fun callsSelection(value:String):Set<String> {
        val calls=value.split(',').map { it.trim().uppercase(java.util.Locale.US) }.filter { it.isNotEmpty() }
        require(calls.size<=50 && calls.size==calls.toSet().size && calls.all { Regex("[A-Z0-9][A-Z0-9/\\-]{1,19}").matches(it) && it.any(Char::isDigit) && it.any(Char::isLetter) }) { "Enter up to 50 distinct callsigns separated by commas" }
        return calls.toSet()
    }
    fun keywordSelection(value:String):List<String> {
        val words=value.split(',').filter { it.isNotBlank() }.map { it.trim().replace(Regex("\\s+")," ").uppercase(java.util.Locale.US) }
        require(words.size<=50 && words.size==words.toSet().size && words.all { it.length<=80 && it.any(Char::isLetterOrDigit) && it.all { c->c.code in 32..126 } }) { "Enter up to 50 distinct words or phrases separated by commas" }
        return words
    }
    fun keywordMatches(comment:String,words:List<String>):Boolean {
        val text=comment.trim().replace(Regex("\\s+")," ").uppercase(java.util.Locale.US)
        return words.any { Regex("(?<![A-Z0-9])"+Regex.escape(it)+"(?![A-Z0-9])").containsMatchIn(text) }
    }
    fun specialMatch(spot:DxSpot,get:(String)->String):Boolean {
        val calls=callsSelection(get("special_calls"));val call=spot.call.uppercase(java.util.Locale.US)
        return call in calls || get("special_calls_portable")!="false" && calls.any { '/' !in it && it in call.split('/') } || keywordMatches(spot.comment,keywordSelection(get("special_keywords")))
    }
    private data class PolicyRule(val low:java.math.BigDecimal,val high:java.math.BigDecimal,val point:Boolean,val result:String)
    private val policyIndex by lazy { BandTableData.rules.groupBy { it[0] to it[1] }.mapValues { (_, rows)->rows.map { r-> PolicyRule(r[2].toBigDecimal(),r[3].toBigDecimal(),r[4]=="point",r[5]) } } }
    fun bandPolicy(f:java.math.BigDecimal,mode:String,license:String):String {
        if(license=="Off")return "eligible"
        val results=policyIndex[license to mode].orEmpty().filter { r->if(r.point)f.compareTo(r.low)==0 else f>=r.low && f<r.high }.map { it.result }
        return if("Eligible" in results)"eligible" else if("Unverified" in results)"unknown" else "outside"
    }
    fun matches(spot:DxSpot,get:(String)->String)=rejection(spot,get).isEmpty()
    fun summary(get: (String)->String):String {
        val parts=mutableListOf<String>()
        if(get("license_class").isNotBlank() && get("license_class")!="Off")parts.add("License filter: "+get("license_class"))
        for((key,default) in listOf("filter_bands" to "All bands","filter_modes" to "All known modes","filter_activities" to "All activities"))parts.add(get(key).replace("General","No activity tag").replace("Unknown","Include unknown").ifBlank { default })
        for((key,title) in listOf("filter_spotter_countries" to "Reported from","filter_spotter_continents" to "Reporting continents","filter_spotter_regions" to "Reporting regions","filter_dx_countries" to "DX countries","filter_dx_continents" to "DX continents"))if(get(key).isNotBlank())parts.add(title+": "+get(key))
        if(get("special_calls").isNotBlank())parts.add((if(get("special_calls_only")=="true")"Only calls: " else "Special calls: ")+get("special_calls"))
        if(get("special_keywords").isNotBlank())parts.add((if(get("special_keywords_only")=="true")"Only words: " else "Special words: ")+get("special_keywords"))
        return parts.joinToString(" · ")
    }
}
