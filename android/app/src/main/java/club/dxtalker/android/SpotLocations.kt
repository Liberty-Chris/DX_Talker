package club.dxtalker.android

object SpotLocations {
    val continents=listOf("AF","AN","AS","EU","NA","OC","SA")
    val fields=listOf("dx_country","dx_continent","spotter_country","spotter_continent","spotter_region")
    fun filterKey(field:String)="filter_"+field.replace("country","countries").replace("continent","continents").replace("region","regions")
    fun clean(key:String,value:String):String {
        val text=value.trim().uppercase(java.util.Locale.US)
        return if(when { key.endsWith("country")->Regex("[A-Z]{2}").matches(text);key.endsWith("continent")->text in continents;else->Regex("[A-Z0-9 ]{1,30}").matches(text) })text else ""
    }
    fun overrides(text:String):Map<String,Map<String,String>> = text.split(';').filter { it.isNotBlank() }.associate { row ->
        val parts=row.trim().split('=');require(parts.size==2)
        val call=parts[0];require(Regex("[A-Z0-9][A-Z0-9/\\-]{1,19}").matches(call) && call.any { it.isDigit() } && call.any { it.isLetter() })
        val values=parts[1].split(',');require(values.size in 2..3)
        val result=mapOf("dx_country" to values[0],"dx_continent" to values[1],"spotter_region" to values.getOrElse(2){""})
        require(result.all { (key,value) -> value.isEmpty() || clean(key,value)==value })
        call to result
    }
    fun rejection(spot:DxSpot,get:(String)->String):String {
        val known=overrides(get("location_overrides"))
        val data=spot.location.toMutableMap()
        for((role,call) in listOf("dx" to spot.call,"spotter" to spot.spotter)) {
            val entry=known[call] ?: emptyMap()
            for((suffix,source) in listOf("country" to "dx_country","continent" to "dx_continent","region" to "spotter_region")) {
                val key=role+"_"+suffix
                if(key in fields && data[key].isNullOrEmpty())data[key]=entry[source].orEmpty()
            }
        }
        for(field in fields) {
            val selected=get(filterKey(field)).split(',').filter { it.isNotEmpty() }
            val actual=data[field].orEmpty()
            if(selected.isNotEmpty() && actual !in selected && (actual.isNotEmpty() || get("geography_unknown")!="true"))return if(actual.isEmpty())"Location unknown"else if(field.startsWith("spotter"))"Reporting station location"else "DX station location"
        }
        return ""
    }
    fun validate(get:(String)->String) {
        for(field in fields) {
            val value=get(filterKey(field))
            if(value.isNotEmpty()) { val parts=value.split(',');require(parts.size==parts.toSet().size && parts.all { clean(field,it)==it }) }
        }
        overrides(get("location_overrides"))
    }
}
