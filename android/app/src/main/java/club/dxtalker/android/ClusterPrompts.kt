package club.dxtalker.android

object ClusterPrompts {
    private fun isSpot(text: String)=text.trimStart().startsWith("DX de ",true)
    private val login=Regex("(?<![A-Z0-9])(?:login|call\\s*sign|callsign|call|user\\s*name)\\s*[:>]\\s*$",RegexOption.IGNORE_CASE)
    private val password=Regex("(?<![A-Z0-9])password\\s*[:>]\\s*$",RegexOption.IGNORE_CASE)
    fun login(text: String)=!isSpot(text) && login.containsMatchIn(text)
    fun password(text: String)=!isSpot(text) && password.containsMatchIn(text)
}
