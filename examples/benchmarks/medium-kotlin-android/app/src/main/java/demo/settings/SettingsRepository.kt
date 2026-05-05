package demo.settings

class SettingsRepository {
    fun load(): SettingsLanguageState {
        return SettingsLanguageState(
            locale = "en",
            voiceEnabled = true,
            compactDensity = false,
        )
    }

    fun save(state: SettingsLanguageState): SettingsLanguageState {
        return state.copy(locale = state.locale.trim().lowercase())
    }
}
