package demo

data class SettingsState(
    val locale: String,
    val voiceEnabled: Boolean,
    val compactMode: Boolean,
)

class SettingsPresenter {
    fun title(state: SettingsState): String {
        return when (state.locale) {
            "ja" -> "Settings"
            "ko" -> "Settings"
            else -> "Settings"
        }
    }

    fun voiceLabel(state: SettingsState): String {
        return if (state.voiceEnabled) "Use voice instead" else "Voice off"
    }
}
