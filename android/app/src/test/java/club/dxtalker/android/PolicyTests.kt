package club.dxtalker.android
import org.junit.Test
import org.junit.Assert.*
import org.json.JSONObject
import java.time.Instant
import java.util.Base64
import java.util.zip.Deflater
class PolicyTests {
    @Test fun validatesSpotsAndConvertsFrequencyWithoutSpeakingComments(){
        val now=Instant.parse("2026-11-06T12:34:00Z")
        val spot=SpotPolicy.parse("DX de N0CALL: 14025.5 WB4IUY/P chat 1234Z",now)!!
        assertEquals("14.0255",spot.frequency("MHz"))
        assertEquals("New DX on. one four point zero two five five megahertz. Whiskey Bravo four India Uniform Yankee stroke Papa.",SpotPolicy.speak(spot,"New DX on. {frequency} {unit}. {call}.","MHz"))
        assertNotNull(SpotPolicy.parse("DX de N0CALL: 7074 WB4IUY 1234Z",now))
        assertNull(SpotPolicy.parse("login: WB4IUY",now))
        assertNull(SpotPolicy.parse("DX de N0CALL: 7074 NOCALL 1234Z",now))
        assertNull(SpotPolicy.parse("DX de N0CALL: 7074 WB4IUY 9999Z",now))
    }
    @Test fun telnetAndTerminalSequencesCanSplitAtAnyByte(){
        val bytes=byteArrayOf(255.toByte(),253.toByte(),1)+"\u001b[31mcall\u0000sign:".toByteArray()
        for(split in 0..bytes.size){val decoder=TelnetText();val replies=mutableListOf<Byte>();
            val first=decoder.feed(bytes.copyOfRange(0,split),split){replies.addAll(it.toList())}
            val second=decoder.feed(bytes.copyOfRange(split,bytes.size),bytes.size-split){replies.addAll(it.toList())}
            assertEquals("callsign:",first+second);assertEquals(listOf(255.toByte(),252.toByte(),1.toByte()),replies)
        }
    }
    private fun transfer()=JSONObject("""{"schema":"dxtalker-transfer","version":1,"profiles":[{"name":"Test","connection":{"source_type":"TCP/Telnet","host":"cluster.example","port":7373,"login":"KF4DBX","feed_url":"","poll_seconds":30}}],"filters":{"frequency_unit":"MHz","min_khz":7000,"max_khz":30000}}""")
    @Test fun readsPlainAndCompressedDesktopContract(){
        val raw=transfer().toString().toByteArray();val deflater=Deflater();deflater.setInput(raw);deflater.finish();val buffer=ByteArray(2048);val size=deflater.deflate(buffer);deflater.end()
        val qr="DXT1:"+Base64.getUrlEncoder().withoutPadding().encodeToString(buffer.copyOf(size))
        assertEquals("MHz",TransferCodec.decode(qr).getJSONObject("filters").getString("frequency_unit"))
        assertEquals(1,TransferCodec.decode(String(raw)).getJSONArray("profiles").length())
    }
    @Test fun rejectsCredentialsAndInvalidFilters(){
        val credential=transfer();credential.getJSONArray("profiles").getJSONObject(0).put("password","not-exportable")
        assertThrows(Exception::class.java){TransferCodec.decode(credential.toString())}
        val invalid=transfer();invalid.getJSONObject("filters").put("min_khz",50000)
        assertThrows(Exception::class.java){TransferCodec.decode(invalid.toString())}
        assertThrows(Exception::class.java){TransferCodec.decode("DXT1:!!!!")}
    }
}
