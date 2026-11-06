package club.dxtalker.android

import org.json.JSONObject
import java.security.MessageDigest
import java.util.Base64

/** Bounded, unordered collection assembly. Nothing is imported before checksum and schema validation. */
class QrCollection {
    private val parts = mutableMapOf<Int, String>()
    private var identity = ""
    var total = 0; private set
    val scanned: Int get() = parts.size
    fun reset() { parts.clear(); identity = ""; total = 0 }
    fun saved(): ArrayList<String> = ArrayList(parts.values)
    fun accept(text: String): JSONObject? {
        if (!text.startsWith("DXT2:")) {
            require(parts.isEmpty()) { "Finish this collection or reset before scanning another" }
            return TransferCodec.decode(text)
        }
        require(text.length <= 1800) { "QR page is too large" }
        val fields = text.split(':')
        require(fields.size == 5 && Regex("[0-9a-f]{64}").matches(fields[1])) { "Invalid collection QR" }
        val index = fields[2].toInt(); val count = fields[3].toInt()
        require(count in 2..66 && index in 1..count) { "Invalid page number" }
        val bytes = Base64.getUrlDecoder().decode(fields[4])
        require(bytes.isNotEmpty() && bytes.size <= 1024) { "Invalid page data" }
        require(identity.isEmpty() || identity == fields[1] && total == count) { "This QR belongs to a different collection. Reset to start it." }
        require(parts[index] == null || parts[index] == text) { "Conflicting QR page" }
        identity = fields[1]; total = count; parts[index] = text
        if (parts.size != total) return null
        val compressed = (1..total).map { Base64.getUrlDecoder().decode(parts.getValue(it).substringAfterLast(':')) }
            .fold(java.io.ByteArrayOutputStream()) { out, chunk -> out.apply { write(chunk) } }.toByteArray()
        require(compressed.size <= 66560) { "Collection is too large" }
        val hash = MessageDigest.getInstance("SHA-256").digest(compressed).joinToString("") { "%02x".format(it.toInt() and 255) }
        require(hash == identity) { "Collection checksum does not match" }
        return TransferCodec.decodeCompressed(compressed)
    }
}
