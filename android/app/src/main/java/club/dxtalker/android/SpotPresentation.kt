package club.dxtalker.android

import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/** One acceptance decision gates both display and announcement text. */
object SpotPresentation {
    data class Decision(val reason:String, val row:String="", val speech:String="")
    fun row(spot:DxSpot,unit:String):String {
        val details=mutableListOf<String>()
        SpotFilters.mode(spot.comment,spot.mode).takeIf { it!="Unknown" }?.let { details.add(it) }
        details.addAll(SpotFilters.tags(spot.comment).filter { it!="General" }.sorted())
        details.add(DateTimeFormatter.ofPattern("HH:mm 'UTC'").withZone(ZoneOffset.UTC).format(spot.time))
        return spot.call+"  "+spot.frequency(unit)+" "+unit+"\n"+details.joinToString(" · ")
    }
    fun decide(spot:DxSpot,get:(String)->String):Decision {
        val low=get("min_khz").ifBlank { "1" }.toBigDecimal()
        val high=get("max_khz").ifBlank { "10000000" }.toBigDecimal()
        val reason=if(spot.frequency<low || spot.frequency>high)"Frequency range"else SpotFilters.rejection(spot,get)
        if(reason.isNotEmpty())return Decision(reason)
        val unit=get("frequency_unit").ifBlank { "kHz" }
        val format=get("format").ifBlank { "New DX on. {frequency} {unit}. {call}." }
        return Decision("",row(spot,unit),SpotPolicy.speak(spot,format,unit))
    }
}
