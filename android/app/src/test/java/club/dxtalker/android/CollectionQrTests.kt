package club.dxtalker.android

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.util.Base64
import java.security.MessageDigest
import java.util.zip.Deflater

class CollectionQrTests {
    private fun fixture() = JSONObject(javaClass.getResource("/desktop_collection.json")!!.readText())
    @Test fun importsTheEntireDesktopCollectionAfterUnorderedScansAndDuplicates() {
        val pages = fixture().getJSONArray("pages")
        val collector = QrCollection()
        val last = pages.getString(pages.length()-1)
        assertNull(collector.accept(last));assertNull(collector.accept(last));assertEquals(1,collector.scanned)
        val restored = QrCollection();collector.saved().forEach { restored.accept(it) }
        for (i in pages.length()-2 downTo 1) assertNull(restored.accept(pages.getString(i)))
        val complete = restored.accept(pages.getString(0))!!
        assertEquals(55,complete.getJSONArray("profiles").length())
        assertEquals("MHz",complete.getJSONObject("filters").getString("frequency_unit"))
        for(i in 0 until 55) assertEquals(fixture().getJSONObject("data").getJSONArray("profiles").getJSONObject(i).getString("name"),complete.getJSONArray("profiles").getJSONObject(i).getString("name"))
        restored.reset();assertEquals(0,restored.scanned)
    }
    @Test fun rejectsMixedCollectionsInvalidPagesAndTamperingWithoutImporting() {
        val pages = fixture().getJSONArray("pages");val first=pages.getString(0)
        val collector=QrCollection();assertNull(collector.accept(first))
        val other=first.replace(first.split(':')[1],"f".repeat(64))
        assertThrows(Exception::class.java) { collector.accept(other) }
        assertEquals(1,collector.scanned)
        assertThrows(Exception::class.java) { collector.accept("DXT2:x:1:999:a") }
        assertThrows(Exception::class.java) { collector.accept(first.substringBeforeLast(':')+":!!!!") }
        collector.reset()
        val corrupted=first.substringBeforeLast(':')+":"+Base64.getUrlEncoder().withoutPadding().encodeToString(ByteArray(1024){1})
        assertNull(collector.accept(corrupted))
        for(i in 1 until pages.length()-1) assertNull(collector.accept(pages.getString(i)))
        assertThrows(Exception::class.java) { collector.accept(pages.getString(pages.length()-1)) }
    }
    @Test fun rejectsCompressedBombsAndNestedTransfers() {
        fun compress(text:String):ByteArray {
            val deflater=Deflater();deflater.setInput(text.toByteArray());deflater.finish()
            val out=ByteArray(10000);val count=deflater.deflate(out);deflater.end();return out.copyOf(count)
        }
        assertThrows(Exception::class.java) { TransferCodec.decodeCompressed(compress(" ".repeat(100000))) }
        assertThrows(Exception::class.java) { TransferCodec.decodeCompressed(compress("DXT1:aaaa")) }
    }
}
