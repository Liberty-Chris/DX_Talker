package club.dxtalker.android
import java.math.BigDecimal
import java.time.Instant
import java.time.ZoneOffset
import java.time.temporal.ChronoUnit
import java.util.Locale

data class DxSpot(val call: String, val frequency: BigDecimal, val time: Instant, val comment: String = "", val mode: String = "", val spotter: String = "", val location: Map<String,String> = emptyMap()) {
    fun frequency(unit: String): String = (if(unit=="MHz") frequency.divide(BigDecimal(1000)) else frequency).stripTrailingZeros().toPlainString()
}
object SpotPolicy {
    private val callPattern = Regex("[A-Z0-9][A-Z0-9/\\-]{1,19}")
    private val pattern = Regex("^DX de ([A-Z0-9/\\-]+):\\s+(\\d{1,7}(?:\\.\\d{1,4})?)\\s+([A-Z0-9/\\-]+)\\s+(?:(.*?)\\s+)?(\\d{4})Z?\\s*$", RegexOption.IGNORE_CASE)
    private val phonetics = "Alpha Bravo Charlie Delta Echo Foxtrot Golf Hotel India Juliet Kilo Lima Mike November Oscar Papa Quebec Romeo Sierra Tango Uniform Victor Whiskey Xray Yankee Zulu".split(' ')
    private val digits = "zero one two three four five six seven eight nine".split(' ')
    private fun validCall(call:String)=callPattern.matches(call) && call.any{it.isDigit()} && call.any{it in 'A'..'Z'}
    fun parse(line:String, now:Instant=Instant.now()):DxSpot? = try {
        val match=pattern.matchEntire(line.trim())
        if(match==null) null else {
            val spotter=match.groupValues[1].uppercase(Locale.US); val call=match.groupValues[3].uppercase(Locale.US)
            val frequency=match.groupValues[2].toBigDecimal(); val stamp=match.groupValues[5]
            val day=now.atZone(ZoneOffset.UTC).withHour(stamp.take(2).toInt()).withMinute(stamp.takeLast(2).toInt()).withSecond(0).withNano(0).toInstant()
            val time=listOf(day.minus(1,ChronoUnit.DAYS),day,day.plus(1,ChronoUnit.DAYS)).minBy{ kotlin.math.abs(it.epochSecond-now.epochSecond) }
            if(!validCall(call)||!validCall(spotter)||frequency<BigDecimal.ONE||frequency>BigDecimal(10000000)||time>now.plusSeconds(120)) null else DxSpot(call,frequency,time,SpotFilters.clean(match.groupValues[4]),spotter=spotter)
        }
    } catch(_:Exception){null}
    fun speak(spot:DxSpot, template:String, unit:String):String {
        val call=spot.call.map { c-> when { c in 'A'..'Z' -> phonetics[c-'A']; c.isDigit()->digits[c-'0']; c=='/'->"stroke"; else->"dash" } }.joinToString(" ")
        val frequency=spot.frequency(unit).map{if(it=='.')"point" else digits[it-'0']}.joinToString(" ")
        return template.replace("{call}",call,true).replace("{frequency}",frequency,true).replace("{unit}",if(unit=="MHz")"megahertz" else "kilohertz",true)
    }
}
class TelnetText {
    private var state=0; private var negotiation=0; private var terminal=0
    fun feed(bytes:ByteArray,count:Int,reply:(ByteArray)->Unit):String {
        val out=StringBuilder()
        for(i in 0 until count){val b=bytes[i].toInt() and 255
            when(state){
                1->{when(b){251,252,253,254->{negotiation=b;state=2};250->state=3;else->state=0};continue}
                2->{reply(byteArrayOf(255.toByte(),(if(negotiation==253||negotiation==254)252 else 254).toByte(),b.toByte()));state=0;continue}
                3->{if(b==255)state=4;continue}
                4->{state=if(b==240)0 else 3;continue}
            }
            if(b==255){state=1;continue}
            when(terminal){
                1->{terminal=when(b){91->2;93->3;else->0};continue}
                2->{if(b in 64..126)terminal=0;continue}
                3->{if(b==7)terminal=0 else if(b==27)terminal=4;continue}
                4->{terminal=if(b==92)0 else 3;continue}
            }
            if(b==27){terminal=1;continue}
            if(b==10||b==13||b==9||b in 32..126)out.append(b.toChar())
        }
        return out.toString()
    }
}
