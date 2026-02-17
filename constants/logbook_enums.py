WIND_STRENGTH_KEYS = [
    "bft0", "bft1", "bft2", "bft3", "bft4", "bft5",
    "bft6", "bft7", "bft8", "bft9", "bft10", "bft11", "bft12",
]

VISIBILITY_KEYS = [
    "very_good", "good", "moderate", "poor", "very_poor",
]

SAIL_PLAN_KEYS = [
    "motor_none", "mainsail", "genoa", "main_genoa", "no_sails",
]

GERMAN_TO_WIND_KEY = {
    "0 Bft (0 kn) - Windstille": "bft0",
    "1 Bft (1-3 kn) - Leiser Zug": "bft1",
    "2 Bft (4-6 kn) - Leichte Brise": "bft2",
    "3 Bft (7-10 kn) - Schwache Brise": "bft3",
    "4 Bft (11-16 kn) - Mäßige Brise": "bft4",
    "5 Bft (17-21 kn) - Frische Brise": "bft5",
    "6 Bft (22-27 kn) - Starker Wind": "bft6",
    "7 Bft (28-33 kn) - Steifer Wind": "bft7",
    "8 Bft (34-40 kn) - Stürmischer Wind": "bft8",
    "9 Bft (41-47 kn) - Sturm": "bft9",
    "10 Bft (48-55 kn) - Schwerer Sturm": "bft10",
    "11 Bft (56-63 kn) - Orkanartiger Sturm": "bft11",
    "12 Bft (64+ kn) - Orkan": "bft12",
}

GERMAN_TO_VISIBILITY_KEY = {
    "Sehr gut (>10 nm)": "very_good",
    "Gut (5-10 nm)": "good",
    "Mäßig (2-5 nm)": "moderate",
    "Schlecht (<2 nm)": "poor",
    "Sehr schlecht (<1 nm)": "very_poor",
}

GERMAN_TO_SAIL_PLAN_KEY = {
    "Motor / keine Segel": "motor_none",
    "Großsegel": "mainsail",
    "Genua": "genoa",
    "Großsegel + Genua": "main_genoa",
    "Keine Segel": "no_sails",
}

EVENT_CATEGORY_KEYS = [
    "maneuver", "weather_change", "sighting", "repair", "emergency", "other",
]

GERMAN_TO_EVENT_CATEGORY_KEY = {
    "Manöver": "maneuver",
    "Wetterwechsel": "weather_change",
    "Sichtung": "sighting",
    "Reparatur": "repair",
    "Notfall": "emergency",
    "Sonstiges": "other",
}

EVENT_CATEGORY_I18N_MAP = {
    "maneuver": "logbook.event_maneuver",
    "weather_change": "logbook.event_weather_change",
    "sighting": "logbook.event_sighting",
    "repair": "logbook.event_repair",
    "emergency": "logbook.event_emergency",
    "other": "logbook.event_other",
}

SEA_STATE_I18N_MAP = {
    "calm": "logbook.sea_calm",
    "slight": "logbook.sea_slight",
    "moderate": "logbook.sea_moderate",
    "rough": "logbook.sea_rough",
    "very_rough": "logbook.sea_very_rough",
    "high": "logbook.sea_high",
}

WIND_I18N_MAP = {k: f"logbook.bft{k.replace('bft', '')}" for k in WIND_STRENGTH_KEYS}

VISIBILITY_I18N_MAP = {
    "very_good": "logbook.visibility_very_good",
    "good": "logbook.visibility_good",
    "moderate": "logbook.visibility_moderate",
    "poor": "logbook.visibility_poor",
    "very_poor": "logbook.visibility_very_poor",
}

SAIL_PLAN_I18N_MAP = {
    "motor_none": "logbook.sail_motor_none",
    "mainsail": "logbook.sail_mainsail",
    "genoa": "logbook.sail_genoa",
    "main_genoa": "logbook.sail_main_genoa",
    "no_sails": "logbook.sail_none",
}


def normalize_wind(value):
    if not value:
        return value
    if value in WIND_STRENGTH_KEYS:
        return value
    return GERMAN_TO_WIND_KEY.get(value, value)


def normalize_visibility(value):
    if not value:
        return value
    if value in VISIBILITY_KEYS:
        return value
    return GERMAN_TO_VISIBILITY_KEY.get(value, value)


def normalize_sail_plan(value):
    if not value:
        return value
    if value in SAIL_PLAN_KEYS:
        return value
    return GERMAN_TO_SAIL_PLAN_KEY.get(value, value)


def display_wind(value, t_func):
    if not value:
        return ""
    key = normalize_wind(value)
    i18n_key = WIND_I18N_MAP.get(key)
    if i18n_key:
        return t_func(i18n_key)
    return value


def display_visibility(value, t_func):
    if not value:
        return ""
    key = normalize_visibility(value)
    i18n_key = VISIBILITY_I18N_MAP.get(key)
    if i18n_key:
        return t_func(i18n_key)
    return value


def display_sail_plan(value, t_func):
    if not value:
        return ""
    key = normalize_sail_plan(value)
    i18n_key = SAIL_PLAN_I18N_MAP.get(key)
    if i18n_key:
        return t_func(i18n_key)
    return value


def normalize_event_category(value):
    if not value:
        return value
    if value in EVENT_CATEGORY_KEYS:
        return value
    return GERMAN_TO_EVENT_CATEGORY_KEY.get(value, value)


def display_event_category(value, t_func):
    if not value:
        return ""
    key = normalize_event_category(value)
    i18n_key = EVENT_CATEGORY_I18N_MAP.get(key)
    if i18n_key:
        return t_func(i18n_key)
    return value


def display_sea_state(value, t_func):
    if not value:
        return ""
    val = value.value if hasattr(value, 'value') else value
    i18n_key = SEA_STATE_I18N_MAP.get(val)
    if i18n_key:
        return t_func(i18n_key)
    return val
