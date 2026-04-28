BASE_URL = "https://disinfocode.eu/reports"

WAVES = {
    5: "March 2025",
    6: "September 2025",
    8: "March 2026",
}

# (slug, platform_label, service_label)
# Wave 5: Microsoft y Google van consolidados; wave 6 y 8 están separados
REPORT_TARGETS = {
    5: [
        ("microsoft",   "Microsoft",     "Bing + LinkedIn + Ads"),
        ("meta",        "Meta",          "Facebook + Instagram + Messenger + WhatsApp"),
        ("google",      "Google",        "Search + YouTube + Ads"),
        ("tiktok",      "TikTok",        "TikTok"),
        ("youtube",     "YouTube",       "YouTube"),
    ],
    6: [
        ("microsoft-bing",    "Microsoft",     "Bing"),
        ("microsoft-ads",     "Microsoft Ads", "Microsoft Ads"),
        ("microsoft-linkedin","LinkedIn",       "LinkedIn"),
        ("meta",              "Meta",          "Facebook + Instagram + Messenger + WhatsApp"),
        ("facebook",          "Facebook",      "Facebook"),
        ("instagram",         "Instagram",     "Instagram"),
        ("google",            "Google",        "Search + YouTube + Ads"),
        ("google-ads",        "Google Ads",    "Google Ads"),
        ("tiktok",            "TikTok",        "TikTok"),
        ("youtube",           "YouTube",       "YouTube"),
    ],
    8: [
        ("microsoft-bing",    "Microsoft",     "Bing"),
        ("microsoft-ads",     "Microsoft Ads", "Microsoft Ads"),
        ("microsoft-linkedin","LinkedIn",       "LinkedIn"),
        ("meta",              "Meta",          "Facebook + Instagram + Messenger + WhatsApp"),
        ("facebook",          "Facebook",      "Facebook"),
        ("instagram",         "Instagram",     "Instagram"),
        ("google",            "Google",        "Search + YouTube + Ads"),
        ("google-ads",        "Google Ads",    "Google Ads"),
        ("tiktok",            "TikTok",        "TikTok"),
        ("youtube",           "YouTube",       "YouTube"),
    ],
}

EU_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
    "Spain", "Sweden",
    "Norway", "Iceland", "Liechtenstein",
]
