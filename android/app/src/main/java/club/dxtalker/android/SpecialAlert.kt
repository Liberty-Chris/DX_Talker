package club.dxtalker.android

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.exp
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

/** Generated offline sounds. Playback shares the TTS queue with its announcement. */
object SpecialAlert {
    val sounds=listOf("Off","Double ding","Chime","Beep")
    fun wav(kind:String):ByteArray {
        require(kind in sounds && kind!="Off")
        val rate=22050
        val notes=when(kind) {
            "Double ding"->listOf(880 to .18,880 to .18)
            "Chime"->listOf(660 to .12,880 to .12,1108 to .18)
            else->listOf(880 to .15)
        }
        val samples=ArrayList<Short>()
        for((frequency,duration) in notes) {
            repeat((rate*duration).roundToInt()) { n->
                val t=n.toDouble()/rate
                val envelope=min(1.0,t/.008)*(if(kind!="Beep")exp(-12*t)else min(1.0,(duration-t)/.01))
                val value=(7000*envelope*(sin(2*Math.PI*frequency*t)+.25*sin(4*Math.PI*frequency*t))).roundToInt()
                samples.add(value.toShort())
            }
            repeat((rate*.08).roundToInt()) { samples.add(0) }
        }
        val dataSize=samples.size*2
        val output=ByteBuffer.allocate(44+dataSize).order(ByteOrder.LITTLE_ENDIAN)
        output.put("RIFF".toByteArray()).putInt(36+dataSize).put("WAVEfmt ".toByteArray()).putInt(16)
        output.putShort(1).putShort(1).putInt(rate).putInt(rate*2).putShort(2).putShort(16)
        output.put("data".toByteArray()).putInt(dataSize)
        samples.forEach { output.putShort(it) }
        return output.array()
    }
}
