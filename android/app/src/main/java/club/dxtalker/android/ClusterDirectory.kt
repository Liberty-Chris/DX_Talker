package club.dxtalker.android
import org.json.JSONObject
import org.json.JSONArray

object ClusterDirectory {
    fun read(text:String):JSONArray {
        require(text.toByteArray().size<=65536)
        val data=JSONObject(text)
        require(data.getString("schema")=="dxtalker-directory" && data.getInt("version") in 1..2)
        val entries=data.getJSONArray("entries");val ids=mutableSetOf<String>()
        for(i in 0 until entries.length()) {
            val e=entries.getJSONObject(i)
            require(e.keys().asSequence().toSet()==setOf("id","name","connection","status","checked","description"))
            require(e.getString("id").isNotBlank() && ids.add(e.getString("id")))
            require(e.getString("status") in listOf("active","retired"))
            for(key in listOf("checked","description"))require(e.getString(key).length<=400)
            val sample=JSONObject().put("schema","dxtalker-transfer").put("version",3).put("profiles",JSONArray().put(JSONObject().put("name",e.getString("name")).put("connection",e.getJSONObject("connection")))).put("filters",JSONObject())
            TransferCodec.decode(sample.toString())
        }
        return entries
    }
}
