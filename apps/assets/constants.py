SUPPORTED_IMPORT_FIELDS = {
    "name": {"required": True},
    "serial_number": {"required": False},
    "model": {"required": False},
    "category": {"required": False},
    "location_country": {"required": False},
}

COUNTRY_ALIASES = {
    "united states": "US",
    "usa": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    "us": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "england": "GB",
    "uae": "AE",
}