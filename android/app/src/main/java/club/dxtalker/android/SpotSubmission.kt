package club.dxtalker.android
import java.math.BigDecimal

object SpotSubmission {
    fun command(callText:String,frequency:String,unit:String,comment:String):String {
        val call=callText.trim().uppercase(java.util.Locale.US)
        require(Regex("[A-Z0-9][A-Z0-9/\\-]{1,19}").matches(call) && call.any { it.isDigit() } && call.any { it.isLetter() }) { "Enter the station callsign" }
        require(unit in listOf("kHz","MHz"))
        val f=frequency.trim().toBigDecimal().multiply(if(unit=="MHz")BigDecimal(1000)else BigDecimal.ONE)
        require(f>=BigDecimal.ONE && f<=BigDecimal(10000000) && f.stripTrailingZeros().scale()<=4) { "Check the frequency and units" }
        require(comment.length<=100 && comment.all { it.code in 32..126 && it !in ";|" }) { "Use a short comment without command separators" }
        return "DX "+f.stripTrailingZeros().toPlainString()+" "+call+if(comment.isNotBlank())" "+comment.trim()else ""
    }
}
