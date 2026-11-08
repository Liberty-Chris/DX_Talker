package club.dxtalker.android
import java.math.BigDecimal

object UsPrivileges {
    val classes=listOf("Off","Novice","Technician","General","Advanced","Extra")
    val regions=listOf("US Region 2","US Region 1","US Region 3")
    private fun inside(f:BigDecimal,spans:List<Pair<BigDecimal,BigDecimal>>) = spans.any { f>=it.first && f<it.second }
    fun eligibility(f:BigDecimal,mode:String,license:String,region:String="US Region 2"):String {
        if(license=="Off")return "eligible"
        val base=UsPrivilegeData.allocations[license] ?: return "unknown"
        if(region !in regions)return "unknown"
        val novice=license in listOf("Novice","Technician")
        var allocations=base + if(license!="Novice")UsPrivilegeData.vhf else emptyList()
        if(region!="US Region 2") {
            allocations=allocations.map { (l,h) ->
                val lo=if(region=="US Region 1" && l==BigDecimal(1800))BigDecimal(1810)else l
                val hi=when(h) { BigDecimal(2000)->if(region=="US Region 1")BigDecimal(1850)else h;BigDecimal(7300)->BigDecimal(7200);BigDecimal(4000)->BigDecimal(if(region=="US Region 3")3900 else 3800);else->h }
                lo to hi
            }.filter { it.first!=BigDecimal(222000) && it.first!=BigDecimal(902000) && !(region=="US Region 1" && it.first==BigDecimal(50000)) }.map { if(it.first==BigDecimal(420000))BigDecimal(430000) to BigDecimal(440000)else it }
        }
        if(f>=BigDecimal(5250) && f<=BigDecimal(5450)) {
            if(novice)return "outside"
            val within=f>=BigDecimal("5351.5") && f<BigDecimal("5366.5")
            if(mode=="Unknown")return if(within || listOf("5330.5","5332","5346.5","5348","5371.5","5373","5403.5","5405").any { f.compareTo(it.toBigDecimal())==0 })"unknown" else "outside"
            if(mode !in listOf("CW","SSB","FT8","FT4","RTTY","PSK"))return "outside"
            val channels=if(mode=="CW")listOf("5332","5348","5373","5405")else listOf("5330.5","5346.5","5371.5","5403.5")
            return if(within || channels.any { f.compareTo(it.toBigDecimal())==0 })"eligible" else "outside"
        }
        if(!inside(f,allocations))return "outside"
        if(mode=="Unknown")return "unknown"
        if(mode=="CW")return "eligible"
        if(novice && f<BigDecimal(28000))return "outside"
        if(f>=BigDecimal(50000)) {
            if(f<BigDecimal(50100) || f>=BigDecimal(144000) && f<BigDecimal(144100))return "outside"
            return if(mode in listOf("SSB","AM","FM","FT8","FT4","RTTY","PSK"))"eligible" else "unknown"
        }
        if(mode in listOf("FT8","FT4","RTTY","PSK"))return if(inside(f,UsPrivilegeData.data))"eligible" else "outside"
        if(mode in listOf("SSB","AM","FM")) {
            val phone=UsPrivilegeData.phone+if(region!="US Region 2")listOf(BigDecimal(7075) to BigDecimal(7100))else emptyList()
            if(region=="US Region 2" && f>=BigDecimal(7075) && f<BigDecimal(7100))return "unknown"
            if(novice && mode!="SSB")return "outside"
            if(mode=="FM" && f<BigDecimal(29000))return if(inside(f,phone))"unknown" else "outside"
            return if(inside(f,phone))"eligible" else "outside"
        }
        return "unknown"
    }
}
