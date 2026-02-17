EXPENSE_CATEGORY_KEYS = [
    "provisions", "beverages", "mooring", "diesel", "water",
    "electricity", "gas", "taxi_transfer", "restaurant", "admissions", "other",
]

GERMAN_TO_EXPENSE_CATEGORY_KEY = {
    "Proviant": "provisions",
    "Getränke": "beverages",
    "Mooring": "mooring",
    "Diesel": "diesel",
    "Wasser": "water",
    "Strom": "electricity",
    "Gas": "gas",
    "Taxi/Transfer": "taxi_transfer",
    "Restaurant": "restaurant",
    "Eintritte": "admissions",
    "Sonstiges": "other",
}

ENGLISH_TO_EXPENSE_CATEGORY_KEY = {
    "Provisions": "provisions",
    "Beverages": "beverages",
    "Mooring": "mooring",
    "Diesel": "diesel",
    "Water": "water",
    "Electricity": "electricity",
    "Gas": "gas",
    "Taxi/Transfer": "taxi_transfer",
    "Restaurant": "restaurant",
    "Admissions": "admissions",
    "Other": "other",
}

EXPENSE_CATEGORY_I18N_MAP = {
    "provisions": "expense.cat_proviant",
    "beverages": "expense.cat_getraenke",
    "mooring": "expense.cat_mooring",
    "diesel": "expense.cat_diesel",
    "water": "expense.cat_wasser",
    "electricity": "expense.cat_strom",
    "gas": "expense.cat_gas",
    "taxi_transfer": "expense.cat_taxi",
    "restaurant": "expense.cat_restaurant",
    "admissions": "expense.cat_eintritte",
    "other": "expense.cat_sonstiges",
}


def normalize_expense_category(value):
    if not value:
        return value
    v = value.strip()
    if v in EXPENSE_CATEGORY_KEYS:
        return v
    mapped = GERMAN_TO_EXPENSE_CATEGORY_KEY.get(v)
    if mapped:
        return mapped
    mapped = ENGLISH_TO_EXPENSE_CATEGORY_KEY.get(v)
    if mapped:
        return mapped
    lower = v.lower().replace("/", "_").replace(" ", "_")
    if lower in EXPENSE_CATEGORY_KEYS:
        return lower
    return v


def display_expense_category(value, t_func):
    if not value:
        return ""
    code = normalize_expense_category(value)
    i18n_key = EXPENSE_CATEGORY_I18N_MAP.get(code)
    if i18n_key:
        return t_func(i18n_key)
    return value
