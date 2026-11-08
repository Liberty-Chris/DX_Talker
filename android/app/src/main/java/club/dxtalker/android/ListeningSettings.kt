package club.dxtalker.android
import org.json.JSONObject

object ListeningSettings {
    val defaults=linkedMapOf("min_khz" to "1","max_khz" to "10000000","max_age_seconds" to "180","repeat_seconds" to "300","spacing_seconds" to "5","frequency_unit" to "kHz","filter_bands" to "","filter_modes" to "","filter_activities" to "","license_class" to "Off","license_region" to "US Region 2","license_unknown" to "false","filter_dx_countries" to "","filter_dx_continents" to "","filter_spotter_countries" to "","filter_spotter_continents" to "","filter_spotter_regions" to "","geography_unknown" to "false","location_overrides" to "")
    fun json(get:(String)->String):JSONObject {
        val result=JSONObject()
        for((key,default) in defaults) {
            val value=get(key).ifBlank { default }
            result.put(key,when(key) {
                "license_unknown","geography_unknown"->value=="true"
                "min_khz","max_khz"->value.toDouble()
                "max_age_seconds","repeat_seconds","spacing_seconds"->value.toInt()
                else->value
            })
        }
        return result
    }
    fun validate(filters:JSONObject) {
        val sample=JSONObject("""{"schema":"dxtalker-transfer","version":3,"profiles":[{"name":"Validation","connection":{"source_type":"TCP/Telnet","host":"cluster.example","port":7373,"login":"","feed_url":"","poll_seconds":30}}],"filters":{}}""")
        sample.put("filters",filters);TransferCodec.decode(sample.toString())
    }
}
