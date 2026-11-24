from typing import Dict, Any, Optional

STRINGS: Dict[str, Dict[str, str]] = {
    "km": {
        # Buttons on Reply Keyboard (Main Menu)
        "btn_report": "📊 របាយការណ៍ (Report)",
        "btn_top20": "👑 សមាជិកចាស់ (Top 20)",
        "btn_settings": "⚙️ ការកំណត់ (Settings)",
        "btn_lookup": "🔍 ស្វែងរក (Lookup)",
        "btn_export": "📦 ទាញយក CSV (Export)",
        "btn_language": "🌐 ភាសា / Language",
        "btn_help": "❓ ជំនួយ (Help)",

        # Inline Buttons
        "btn_unban_user": "🟢 ដោះលែងសមាជិក (Unban)",
        "btn_refresh_today": "🔄 ថ្ងៃនេះ (Today)",
        "btn_yesterday": "📅 ម្សិលមិញ (Yesterday)",
        "btn_pause_autoban": "🔴 បិទ Auto-Ban ជាបណ្តោះអាសន្ន",
        "btn_enable_autoban": "🟢 បើកដំណើរការ Auto-Ban",
        "btn_change_mode": "🔄 ប្តូររយៈពេលនៃការ Ban",
        "btn_disable_report": "🔴 បិទរបាយការណ៍ស្វ័យប្រវត្តិ",
        "btn_enable_report": "🟢 បើករបាយការណ៍ស្វ័យប្រវត្តិ",
        "btn_view_rules": "📜 មើលច្បាប់ Ban តាមកម្រិត",
        "btn_back_settings": "🔙 ត្រឡប់ក្រោយ (Back)",

        # Time units
        "unit_days": "ថ្ងៃ",
        "unit_hours": "ម៉ោង",
        "unit_minutes": "នាទី",
        "unit_less_min": "ក្រោម ១ នាទី",
        "unit_unknown": "មិនស្គាល់ (ចូលមុនពេលដាក់ Bot)",

        # Ban durations
        "mode_tiered": "⚖️ Dynamic Tiered (តាមរយៈពេលស្នាក់នៅ)",
        "mode_forever": "🔒 ហាមឃាត់រហូត (Forever)",
        "mode_1_year": "🔒 ហាមឃាត់ ១ ឆ្នាំ (1 Year)",
        "mode_3_months": "🔒 ហាមឃាត់ ៣ ខែ (3 Months)",
        "mode_1_month": "🔒 ហាមឃាត់ ១ ខែ (1 Month)",
        "mode_1_week": "🔒 ហាមឃាត់ ១ សប្តាហ៍ (1 Week)",

        # Alert header
        "alert_banned_header": "🚫 <b>សមាជិកបានចាកចេញ &amp; ត្រូវហាមឃាត់ (AUTO-BANNED)!</b>",
        "alert_disabled_header": "⚠️ <b>សមាជិកបានចាកចេញ (មិនបាន Ban ព្រោះ Auto-Ban ត្រូវបានបិទ)</b>",
        "alert_failed_header": "⚠️ <b>សមាជិកបានចាកចេញ (ការ Ban បរាជ័យ)</b>",
        "alert_user": "👤 <b>សមាជិក:</b>",
        "alert_id": "🆔 <b>អត្តសញ្ញាណ (ID):</b>",
        "alert_channel": "📢 <b>ឆានែល:</b>",
        "alert_joined": "📅 <b>ថ្ងៃចូលរួម:</b>",
        "alert_left": "🚪 <b>ថ្ងៃចាកចេញ:</b>",
        "alert_duration": "⏱ <b>រយៈពេលស្នាក់នៅ:</b>",
        "alert_ban_duration": "🔒 <b>រយៈពេលហាមឃាត់:</b>",
        "alert_banned_until": "⏳ <b>ហាមឃាត់រហូតដល់:</b>",
        "alert_unban_hint": "<i>ចុចប៊ូតុងខាងក្រោមដើម្បីដោះលែង (Unban) សមាជិកនេះឡើងវិញ។</i>",
        "alert_unbanned_status": "✅ <b>បានដោះលែងជោគជ័យ (UNBANNED)</b>",
        "alert_unbanned_by": "👤 <b>ដោះលែងដោយ:</b>",
        "alert_time": "🕒 <b>កាលបរិច្ឆេទ:</b>",

        # Top 20 Scan
        "scan_scanning": "🔍 កំពុងស្កេនទិន្នន័យសមាជិកឆានែល...",
        "scan_empty": "ℹ️ មិនទាន់មានទិន្នន័យសមាជិកនៅឡើយទេ។ នៅពេលមានសមាជិកចូល ឬ Bot ដំណើរការ ពួកគេនឹងបង្ហាញនៅទីនេះ។",
        "scan_title": "👑 <b>សមាជិកចាស់វស្សា និងស្មោះត្រង់បំផុត ២០ នាក់ដំបូង:</b>\n<i>តម្រៀបតាមថ្ងៃចូលរួម និងចំនួនថ្ងៃដែលបានស្នាក់នៅក្នុងឆានែល:</i>\n",
        "scan_days_active": "ថ្ងៃក្នុងឆានែល",

        # Daily Report
        "report_title": "📈 <b>របាយការណ៍សកម្មភាពឆានែល ({date})</b>",
        "report_joined": "📥 <b>ចូលរួមថ្មី:</b>",
        "report_left": "🚪 <b>បានចាកចេញ:</b>",
        "report_banned": "🚫 <b>បាន Auto-Ban:</b>",
        "report_unbanned": "🟢 <b>បានដោះលែង (Unban):</b>",
        "report_growth": "📊 <b>កំណើនសមាជិកសុទ្ធ:</b>",
        "report_total_members": "👥 <b>សមាជិកសកម្មសរុបដែលកំពុងតាមដាន:</b>",
        "report_total_bans": "🛡 <b>ចំនួន Ban សរុបតាំងពីដើមមក:</b>",
        "report_generated_at": "<i>របាយការណ៍ស្វ័យប្រវត្តិកាលពីម៉ោង {time} UTC</i>",
        "report_daily_header": "🌅 <b>របាយការណ៍សង្ខេបប្រចាំថ្ងៃស្វ័យប្រវត្តិ</b>",

        # Settings
        "settings_title": "⚙️ <b>ការកំណត់ BOT &amp; ការគ្រប់គ្រងឆានែល:</b>\n",
        "settings_autoban": "🛡 <b>Auto-Ban ពេលចាកចេញ:</b>",
        "settings_mode": "⚖️ <b>ទម្រង់រយៈពេល Ban បច្ចុប្បន្ន:</b>",
        "settings_daily_report": "📊 <b>របាយការណ៍ប្រចាំថ្ងៃ (00:00 UTC):</b>",
        "settings_hint": "<i>សូមចុចប៊ូតុងខាងក្រោមដើម្បីផ្លាស់ប្តូរការកំណត់ភ្លាមៗ:</i>",
        "settings_choose_mode_title": "🎯 <b>ជ្រើសរើសទម្រង់រយៈពេលនៃការ Ban:</b>\n\n• <b>Dynamic Tiered:</b> រយៈពេល Ban ផ្អែកលើចំនួនថ្ងៃដែលសមាជិកស្នាក់នៅ (ចូលថ្ងៃនេះចាកចេញ ➔ Ban ១ ឆ្នាំ, ស្នាក់នៅ ១ សប្តាហ៍ ➔ Ban ៣ ខែ)\n• <b>Fixed:</b> កំណត់រយៈពេល Ban ដូចគ្នាសម្រាប់អ្នកចាកចេញទាំងអស់។",
        "rules_title": "📜 <b>ច្បាប់កម្រិតនៃការ BAN (TIERED RULES):</b>\n",

        # Lookup
        "lookup_usage": "ℹ️ របៀបប្រើ: <code>/lookup &lt;user_id ឬ @username&gt;</code>",
        "lookup_not_found": "🔍 មិនមានទិន្នន័យសម្រាប់ <code>{query}</code> ទេ។",
        "lookup_title": "👤 <b>ព័ត៌មានសមាជិក:</b> <code>{query}</code>\n",
        "lookup_active": "🟢 <b>ស្ថានភាព:</b> សមាជិកសកម្ម (ACTIVE MEMBER)",
        "lookup_inactive": "🔴 <b>ស្ថានភាព:</b> មិនមែនជាសមាជិកសកម្មបច្ចុប្បន្ន",
        "lookup_history": "📜 <b>ប្រវត្តិ Ban:</b>",

        # Start & Welcome
        "welcome_title": "👋 <b>សូមស្វាគមន៍មកកាន់ Channel Sentinel Bot!</b>\n\n🆔 <b>Telegram ID របស់អ្នក:</b> <code>{user_id}</code> ({admin_tag})\n\n<b>⚡ មុខងារសំខាន់ៗ:</b>\n• <b>Smart Tiered Auto-Ban:</b> ចាកចេញថ្ងៃនេះ ➔ Ban ១ ឆ្នាំ, ចាកចេញក្នុង ១ សប្តាហ៍ ➔ Ban ៣ ខែ\n• <b>Unban ដោយ ១ ចុច:</b> ប៊ូតុងដោះលែងភ្លាមៗនៅលើគ្រប់សារដំណឹង\n• <b>ស្កេនសមាជិកចាស់:</b> មើលសមាជិកចាស់ ២០ នាក់ជាមួយ <code>/scan</code>\n• <b>របាយការណ៍ប្រចាំថ្ងៃ:</b> ផ្ញើស្វ័យប្រវត្តរៀងរាល់ ២៤ ម៉ោង ឬមើលភ្លាមៗជាមួយ <code>/report</code>\n• <b>ការកំណត់ងាយស្រួល:</b> ប្តូរភាសា និងរយៈពេល Ban ជាមួយ <code>/settings</code>\n\n<i>ចុចប៊ូតុងម៉ឺនុយខាងក្រោមដើម្បីប្រើប្រាស់យ៉ាងងាយស្រួល!</i>",

        # Language
        "lang_select": "🌐 <b>សូមជ្រើសរើសភាសា / Please Select Language:</b>",
        "lang_updated": "✅ បានប្តូរភាសាទៅជាភាសាខ្មែរជោគជ័យ!",
        "unauthorized": "⛔ អ្នកគ្មានសិទ្ធិប្រើប្រាស់មុខងារនេះទេ។"
    },

    "en": {
        "btn_report": "📊 Daily Report",
        "btn_top20": "👑 Top 20 Members",
        "btn_settings": "⚙️ Settings",
        "btn_lookup": "🔍 Lookup User",
        "btn_export": "📦 Export CSV",
        "btn_language": "🌐 Language / ភាសា",
        "btn_help": "❓ Help",

        "btn_unban_user": "🟢 Unban User",
        "btn_refresh_today": "🔄 Refresh Today",
        "btn_yesterday": "📅 Yesterday",
        "btn_pause_autoban": "🔴 Pause Auto-Ban",
        "btn_enable_autoban": "🟢 Enable Auto-Ban",
        "btn_change_mode": "🔄 Change Ban Duration Mode",
        "btn_disable_report": "🔴 Disable Daily Report",
        "btn_enable_report": "🟢 Enable Daily Report",
        "btn_view_rules": "📜 View Tiered Rules",
        "btn_back_settings": "🔙 Back to Settings",

        "unit_days": "day(s)",
        "unit_hours": "hour(s)",
        "unit_minutes": "min",
        "unit_less_min": "less than 1 min",
        "unit_unknown": "Unknown (Joined before bot was installed)",

        "mode_tiered": "⚖️ Dynamic Tiered (Recommended)",
        "mode_forever": "🔒 Permanent (Forever)",
        "mode_1_year": "🔒 1 Year Ban",
        "mode_3_months": "🔒 3 Months Ban",
        "mode_1_month": "🔒 1 Month Ban",
        "mode_1_week": "🔒 1 Week Ban",

        "alert_banned_header": "🚫 <b>USER LEFT &amp; AUTO-BANNED!</b>",
        "alert_disabled_header": "⚠️ <b>USER LEFT (Auto-Ban Disabled)</b>",
        "alert_failed_header": "⚠️ <b>USER LEFT (Ban Failed)</b>",
        "alert_user": "👤 <b>User:</b>",
        "alert_id": "🆔 <b>User ID:</b>",
        "alert_channel": "📢 <b>Channel:</b>",
        "alert_joined": "📅 <b>Joined At:</b>",
        "alert_left": "🚪 <b>Left At:</b>",
        "alert_duration": "⏱ <b>Membership Duration:</b>",
        "alert_ban_duration": "🔒 <b>Ban Duration:</b>",
        "alert_banned_until": "⏳ <b>Banned Until:</b>",
        "alert_unban_hint": "<i>Click below to unban this user early if needed.</i>",
        "alert_unbanned_status": "✅ <b>STATUS: UNBANNED</b>",
        "alert_unbanned_by": "👤 <b>Unbanned by:</b>",
        "alert_time": "🕒 <b>Time:</b>",

        "scan_scanning": "🔍 Scanning channel member database...",
        "scan_empty": "ℹ️ No tracked members found yet. As members join or as the bot runs, they will appear here.",
        "scan_title": "👑 <b>TOP 20 OLDEST &amp; MOST LOYAL MEMBERS:</b>\n<i>Ranked by joined date and days active in your channel:</i>\n",
        "scan_days_active": "days active",

        "report_title": "📈 <b>CHANNEL ACTIVITY REPORT ({date})</b>",
        "report_joined": "📥 <b>Joined Today:</b>",
        "report_left": "🚪 <b>Left Today:</b>",
        "report_banned": "🚫 <b>Auto-Banned Today:</b>",
        "report_unbanned": "🟢 <b>Unbanned Today:</b>",
        "report_growth": "📊 <b>Net Member Growth:</b>",
        "report_total_members": "👥 <b>Total Active Tracked Members:</b>",
        "report_total_bans": "🛡 <b>All-Time Auto-Bans:</b>",
        "report_generated_at": "<i>Automated report generated at {time} UTC.</i>",
        "report_daily_header": "🌅 <b>Daily Automated Summary</b>",

        "settings_title": "⚙️ <b>BOT SETTINGS &amp; CHANNEL CONTROLS:</b>\n",
        "settings_autoban": "🛡 <b>Auto-Ban on Leave:</b>",
        "settings_mode": "⚖️ <b>Current Ban Mode:</b>",
        "settings_daily_report": "📊 <b>Daily Report:</b>",
        "settings_hint": "<i>Tap buttons below to change ban duration or toggle features instantly:</i>",
        "settings_choose_mode_title": "🎯 <b>Select Ban Duration Mode:</b>\n\n• <b>Dynamic Tiered:</b> Banning duration depends on how long user stayed (e.g. joined today ➔ 1 year, joined 1 week ➔ 3 months).\n• <b>Fixed Durations:</b> Apply the exact same ban duration to everyone who leaves.",
        "rules_title": "📜 <b>DYNAMIC TIERED BAN RULES:</b>\n",

        "lookup_usage": "ℹ️ Usage: <code>/lookup &lt;user_id or @username&gt;</code>",
        "lookup_not_found": "🔍 No records found for <code>{query}</code>.",
        "lookup_title": "👤 <b>USER LOOKUP:</b> <code>{query}</code>\n",
        "lookup_active": "🟢 <b>Status:</b> ACTIVE MEMBER",
        "lookup_inactive": "🔴 <b>Current Status:</b> Not currently an active member.",
        "lookup_history": "📜 <b>Ban History:</b>",

        "welcome_title": "👋 <b>Welcome to Channel Sentinel Bot!</b>\n\n🆔 <b>Your Telegram ID:</b> <code>{user_id}</code> ({admin_tag})\n\n<b>⚡ Key Features:</b>\n• <b>Smart Tiered Auto-Ban:</b> Leaves today ➔ 1 Year Ban, leaves in 1 week ➔ 3 Months Ban\n• <b>Interactive Unban Button:</b> 1-click unban on every alert\n• <b>Member Scanner:</b> View Top 20 oldest veteran members with <code>/scan</code>\n• <b>Daily Reports:</b> Auto-summary every 24h & on-demand with <code>/report</code>\n• <b>Admin Settings:</b> Change ban rules & duration with <code>/settings</code>\n\n<i>Tap the menu buttons below for easy navigation!</i>",

        "lang_select": "🌐 <b>Please Select Language / សូមជ្រើសរើសភាសា:</b>",
        "lang_updated": "✅ Language changed to English successfully!",
        "unauthorized": "⛔ Unauthorized."
    }
}


def t(key: str, lang: str = "km", **kwargs) -> str:
    """Retrieve localized text with parameter formatting."""
    lang_dict = STRINGS.get(lang, STRINGS["km"])
    template = lang_dict.get(key, STRINGS["en"].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def format_duration_localized(total_seconds: float, lang: str = "km") -> str:
    """Format total seconds into localized duration string."""
    total_seconds = max(0, total_seconds)
    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)

    u_days = t("unit_days", lang)
    u_hours = t("unit_hours", lang)
    u_min = t("unit_minutes", lang)

    parts = []
    if days > 0:
        parts.append(f"{days} {u_days}")
    if hours > 0:
        parts.append(f"{hours} {u_hours}")
    if minutes > 0 and days == 0:
        parts.append(f"{minutes} {u_min}")

    if not parts:
        return t("unit_less_min", lang)
    return ", ".join(parts)
