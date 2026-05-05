package demo.settings

data class SettingsLanguageState(
    val locale: String,
    val voiceEnabled: Boolean,
    val compactDensity: Boolean,
)

class SettingsLanguagePresenter {
    fun label(state: SettingsLanguageState): String {
        return when (state.locale) {
            "ja" -> "Language"
            "ko" -> "Language"
            else -> "Language"
        }
    }

    fun voiceAction(state: SettingsLanguageState): String {
        return if (state.voiceEnabled) "Use voice instead" else "Voice disabled"
    }
}
