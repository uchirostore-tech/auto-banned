import io
import html
import logging
import re
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ChatMemberUpdated,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import config
from database import Database
from i18n import t, format_duration_localized

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database(config.DB_PATH)


def is_admin(user_id: int) -> bool:
    """Check if a Telegram user ID is in the configured ADMIN_IDS."""
    if not config.ADMIN_IDS:
        return True
    return user_id in config.ADMIN_IDS


def get_main_menu_keyboard(lang: str = "km") -> ReplyKeyboardMarkup:
    """Returns persistent, easy-to-use touch buttons for the mobile Telegram interface."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t("btn_report", lang)), KeyboardButton(t("btn_top20", lang))],
            [KeyboardButton(t("btn_settings", lang)), KeyboardButton(t("btn_lookup", lang))],
            [KeyboardButton(t("btn_export", lang)), KeyboardButton(t("btn_language", lang))],
        ],
        resize_keyboard=True
    )


async def calculate_ban_duration(days_joined: Optional[float], lang: str = "km") -> Tuple[int, Optional[datetime], str]:
    """
    Computes ban duration based on active admin settings or dynamic tiered rules.
    Returns: (ban_days, until_date_obj, localized_rule_description)
    ban_days: 0 means permanent.
    """
    ban_mode = await db.get_setting("ban_mode", "tiered")
    now = datetime.now(timezone.utc)

    if ban_mode == "forever":
        return 0, None, t("mode_forever", lang)
    elif ban_mode == "1_year":
        until = now + timedelta(days=365)
        return 365, until, t("mode_1_year", lang)
    elif ban_mode == "3_months":
        until = now + timedelta(days=90)
        return 90, until, t("mode_3_months", lang)
    elif ban_mode == "1_month":
        until = now + timedelta(days=30)
        return 30, until, t("mode_1_month", lang)
    elif ban_mode == "1_week":
        until = now + timedelta(days=7)
        return 7, until, t("mode_1_week", lang)

    # Default: Tiered Mode
    if days_joined is None:
        until = now + timedelta(days=365)
        label = t("mode_1_year", lang)
        desc = t("unit_unknown", lang)
        return 365, until, f"{label} ({desc})"

    # Khmer / English tier definitions
    if lang == "km":
        tiers_localized = [
            {"max_days": 1, "ban_days": 365, "label": "ចូលក្រោម ១ ថ្ងៃ (ចាកចេញថ្ងៃនេះ)", "desc": "ហាមឃាត់ ១ ឆ្នាំ (1 Year Ban)"},
            {"max_days": 7, "ban_days": 90, "label": "ស្នាក់នៅ ១ - ៧ ថ្ងៃ (១ សប្តាហ៍)", "desc": "ហាមឃាត់ ៣ ខែ (3 Months Ban)"},
            {"max_days": 30, "ban_days": 30, "label": "ស្នាក់នៅ ១ - ៤ សប្តាហ៍ (១ ខែ)", "desc": "ហាមឃាត់ ១ ខែ (1 Month Ban)"},
            {"max_days": 180, "ban_days": 14, "label": "ស្នាក់នៅ ១ - ៦ ខែ", "desc": "ហាមឃាត់ ២ សប្តាហ៍ (2 Weeks Ban)"},
            {"max_days": None, "ban_days": 0, "label": "ស្នាក់នៅលើស ៦ ខែ", "desc": "ហាមឃាត់រហូត (Forever)"},
        ]
    else:
        tiers_localized = await db.get_tiered_rules()

    for tier in tiers_localized:
        max_days = tier.get("max_days")
        ban_days = tier.get("ban_days", 365)
        desc = tier.get("desc", f"{ban_days} Days Ban")
        label = tier.get("label", "")

        if max_days is None or days_joined < max_days:
            if ban_days == 0:
                return 0, None, f"{label} ➔ {t('mode_forever', lang)}"
            else:
                until = now + timedelta(days=ban_days)
                return ban_days, until, f"{label} ➔ {desc}"

    # Fallback
    until = now + timedelta(days=365)
    return 365, until, t("mode_1_year", lang)


async def track_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Listens for member joins, voluntary leaves, and executes auto-bans."""
    chat_member_update: ChatMemberUpdated = update.chat_member
    if not chat_member_update:
        return

    chat = chat_member_update.chat
    user = chat_member_update.new_chat_member.user

    # Ignore bots
    if user.is_bot:
        return

    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status

    was_member = old_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    ]

    is_member = new_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    ]

    update_date = chat_member_update.date
    if update_date.tzinfo is None:
        update_date = update_date.replace(tzinfo=timezone.utc)

    # 1. User Joined or Re-joined
    if not was_member and is_member:
        logger.info(f"User @{user.username} (ID: {user.id}) joined {chat.title} ({chat.id})")
        await db.record_join(
            user_id=user.id,
            chat_id=chat.id,
            username=user.username,
            full_name=user.full_name,
            joined_at=update_date
        )
        return

    # 2. User Left voluntarily
    if was_member and new_status == ChatMemberStatus.LEFT:
        logger.info(f"User @{user.username} (ID: {user.id}) left {chat.title} ({chat.id}). Auto-banning...")

        lang = await db.get_language()
        auto_ban_enabled = (await db.get_setting("auto_ban_enabled", "true")) == "true"

        # Lookup join date in database
        member_record = await db.get_member(user_id=user.id, chat_id=chat.id)
        joined_at: Optional[datetime] = None
        duration_str = t("unit_unknown", lang)
        days_count_str = "?"
        days_joined: Optional[float] = None

        if member_record and member_record.get("joined_at"):
            try:
                joined_at = datetime.fromisoformat(member_record["joined_at"])
                if joined_at.tzinfo is None:
                    joined_at = joined_at.replace(tzinfo=timezone.utc)

                diff_seconds = (update_date - joined_at).total_seconds()
                days_joined = diff_seconds / 86400.0
                duration_str = format_duration_localized(diff_seconds, lang)
                days_int = int(diff_seconds // 86400)
                days_count_str = f"{days_int} {t('unit_days', lang)}"
            except Exception as e:
                logger.error(f"Error parsing joined_at timestamp: {e}")

        # Compute ban duration based on tiered rules
        ban_days, ban_until_date, rule_desc = await calculate_ban_duration(days_joined, lang)

        ban_successful = False
        ban_error_msg = ""

        if auto_ban_enabled:
            try:
                until_timestamp = int(ban_until_date.timestamp()) if (ban_days > 0 and ban_until_date) else 0
                await context.bot.ban_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    until_date=until_timestamp
                )
                ban_successful = True
                logger.info(f"Successfully banned user {user.id} ({rule_desc}) from chat {chat.id}")
            except BadRequest as e:
                ban_error_msg = e.message
                logger.error(f"Failed to ban user {user.id} from chat {chat.id}: {e.message}")
            except Exception as e:
                ban_error_msg = str(e)
                logger.error(f"Unexpected error banning user {user.id}: {e}", exc_info=True)
        else:
            ban_error_msg = "Auto-ban is disabled."

        # Record ban event in database
        await db.record_ban(
            user_id=user.id,
            chat_id=chat.id,
            channel_title=chat.title or "Channel",
            username=user.username,
            full_name=user.full_name,
            joined_at=joined_at,
            left_at=update_date,
            days_joined=days_joined,
            ban_duration_days=ban_days,
            ban_until_date=ban_until_date
        )
        await db.remove_member(user_id=user.id, chat_id=chat.id)

        # Format dates for notification
        left_time_str = update_date.strftime("%Y-%m-%d %H:%M:%S UTC")
        joined_time_str = joined_at.strftime("%Y-%m-%d %H:%M:%S UTC") if joined_at else t("unit_unknown", lang)
        ban_until_str = ban_until_date.strftime("%Y-%m-%d %H:%M:%S UTC") if ban_until_date else t("mode_forever", lang)

        user_tag = f"@{user.username}" if user.username else "No username"
        user_mention = f"<a href=\"tg://user?id={user.id}\">{html.escape(user.full_name)}</a>"
        channel_name = html.escape(chat.title or "Channel")

        if ban_successful:
            header = t("alert_banned_header", lang)
            action_desc = (
                f"{t('alert_ban_duration', lang)} <b>{html.escape(rule_desc)}</b>\n"
                f"{t('alert_banned_until', lang)} <code>{ban_until_str}</code>"
            )
        elif not auto_ban_enabled:
            header = t("alert_disabled_header", lang)
            action_desc = "<i>Auto-Ban is disabled.</i>"
        else:
            header = t("alert_failed_header", lang)
            action_desc = f"<i>Error: {html.escape(ban_error_msg)}</i>"

        alert_text = (
            f"{header}\n\n"
            f"{t('alert_user', lang)} {user_mention} ({user_tag})\n"
            f"{t('alert_id', lang)} <code>{user.id}</code>\n"
            f"{t('alert_channel', lang)} <b>{channel_name}</b> (<code>{chat.id}</code>)\n"
            f"{t('alert_joined', lang)} {joined_time_str}\n"
            f"{t('alert_left', lang)} {left_time_str}\n"
            f"{t('alert_duration', lang)} <b>{duration_str}</b> ({days_count_str})\n\n"
            f"{action_desc}\n\n"
            f"{t('alert_unban_hint', lang)}"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_unban_user", lang), callback_data=f"unban:{chat.id}:{user.id}")]
        ])

        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=alert_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard if ban_successful else None
                )
            except Exception as e:
                logger.error(f"Error sending ban notification to admin {admin_id}: {e}")

        if config.LOG_CHANNEL_ID:
            try:
                await context.bot.send_message(
                    chat_id=config.LOG_CHANNEL_ID,
                    text=alert_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard if ban_successful else None
                )
            except Exception as e:
                logger.error(f"Error sending ban alert to log channel: {e}")


async def handle_unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles 1-click Unban button from notifications."""
    query = update.callback_query
    if not query or not query.data:
        return

    lang = await db.get_language()
    user_clicking = query.from_user
    if not is_admin(user_clicking.id):
        await query.answer(t("unauthorized", lang), show_alert=True)
        return

    match = re.match(r"^unban:(-?\d+):(\d+)$", query.data)
    if not match:
        await query.answer("Invalid request.", show_alert=True)
        return

    target_chat_id = int(match.group(1))
    target_user_id = int(match.group(2))

    try:
        await context.bot.unban_chat_member(
            chat_id=target_chat_id,
            user_id=target_user_id,
            only_if_banned=True
        )
        await db.mark_unbanned(
            chat_id=target_chat_id,
            user_id=target_user_id,
            unbanned_by=user_clicking.id
        )

        admin_name = html.escape(user_clicking.full_name)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        original_text = query.message.text_html if query.message else ""
        updated_text = (
            f"{original_text}\n\n"
            f"{t('alert_unbanned_status', lang)}\n"
            f"{t('alert_unbanned_by', lang)} <a href=\"tg://user?id={user_clicking.id}\">{admin_name}</a>\n"
            f"{t('alert_time', lang)} {now_str}"
        )

        try:
            await query.edit_message_text(
                text=updated_text,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        except Exception:
            await query.edit_message_reply_markup(reply_markup=None)

        msg_success = "✅ បានដោះលែងជោគជ័យ!" if lang == "km" else "✅ User unbanned successfully!"
        await query.answer(msg_success, show_alert=True)
        logger.info(f"Admin {user_clicking.id} unbanned user {target_user_id}")

    except BadRequest as e:
        await query.answer(f"Failed to unban: {e.message}", show_alert=True)
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        await query.answer("Error unbanning user.", show_alert=True)


# --- Member Scan: Top 20 Oldest & Loyal Members ---
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        lang = await db.get_language()
        await update.message.reply_text(t("unauthorized", lang))
        return

    lang = await db.get_language()
    msg_wait = await update.message.reply_text(t("scan_scanning", lang))
    top_members = await db.get_top_oldest_members(limit=20)

    if not top_members:
        await msg_wait.edit_text(t("scan_empty", lang))
        return

    lines = [t("scan_title", lang)]
    u_days_active = t("scan_days_active", lang)

    for idx, mem in enumerate(top_members, 1):
        uname = f"@{mem['username']}" if mem.get("username") else "No username"
        name = html.escape(mem.get("full_name") or "Member")
        days = mem.get("days_active", 0)
        joined_date = mem.get("joined_at", "")[:10]

        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        lines.append(
            f"{medal} <b>{name}</b> ({uname})\n"
            f"   🆔 <code>{mem['user_id']}</code> | 📅 <code>{joined_date}</code> | 🌟 <b>{days} {u_days_active}</b>"
        )

    lines.append(f"\n📊 <i>{len(top_members)} members shown</i>")
    await msg_wait.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


# --- Daily Report ---
async def build_report_message(target_date: Optional[datetime] = None, lang: str = "km") -> str:
    summary = await db.get_daily_summary(target_date)
    growth_sym = "+" if summary["net_change"] >= 0 else ""

    return (
        f"{t('report_title', lang, date=summary['date'])}\n\n"
        f"{t('report_joined', lang)} <code>+{summary['joins']}</code>\n"
        f"{t('report_left', lang)} <code>-{summary['leaves']}</code>\n"
        f"{t('report_banned', lang)} <code>{summary['bans']}</code>\n"
        f"{t('report_unbanned', lang)} <code>{summary['unbans']}</code>\n"
        f"{t('report_growth', lang)} <b>{growth_sym}{summary['net_change']}</b>\n\n"
        f"{t('report_total_members', lang)} <code>{summary['total_tracked']}</code>\n"
        f"{t('report_total_bans', lang)} <code>{summary['total_historical_bans']}</code>\n\n"
        f"{t('report_generated_at', lang, time=datetime.now(timezone.utc).strftime('%H:%M:%S'))}"
    )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = await db.get_language()
    if not user or not is_admin(user.id):
        await update.message.reply_text(t("unauthorized", lang))
        return

    args = context.args or []
    target_dt = datetime.now(timezone.utc)
    if args and args[0].lower() in ["yesterday", "prev"]:
        target_dt -= timedelta(days=1)

    report_text = await build_report_message(target_dt, lang)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_refresh_today", lang), callback_data="report:today"),
            InlineKeyboardButton(t("btn_yesterday", lang), callback_data="report:yesterday")
        ]
    ])
    await update.message.reply_text(report_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def handle_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    lang = await db.get_language()
    if not is_admin(query.from_user.id):
        await query.answer(t("unauthorized", lang), show_alert=True)
        return

    target_dt = datetime.now(timezone.utc)
    if query.data == "report:yesterday":
        target_dt -= timedelta(days=1)

    report_text = await build_report_message(target_dt, lang)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_refresh_today", lang), callback_data="report:today"),
            InlineKeyboardButton(t("btn_yesterday", lang), callback_data="report:yesterday")
        ]
    ])
    try:
        await query.edit_message_text(report_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception:
        pass
    await query.answer()


# --- Background Daily Report Worker ---
async def send_scheduled_daily_report(application: Application):
    enabled = (await db.get_setting("daily_report_enabled", "true")) == "true"
    if not enabled:
        return

    lang = await db.get_language()
    report_text = await build_report_message(datetime.now(timezone.utc), lang)
    header = t("report_daily_header", lang)

    for admin_id in config.ADMIN_IDS:
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text=f"{header}\n\n{report_text}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error sending scheduled report to admin {admin_id}: {e}")

    if config.LOG_CHANNEL_ID:
        try:
            await application.bot.send_message(
                chat_id=config.LOG_CHANNEL_ID,
                text=f"{header}\n\n{report_text}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error sending scheduled report to log channel: {e}")


async def daily_report_background_worker(application: Application):
    logger.info("Daily report background scheduler active.")
    last_sent_date = None

    while True:
        try:
            now = datetime.now(timezone.utc)
            if now.hour == 0 and last_sent_date != now.date():
                await send_scheduled_daily_report(application)
                last_sent_date = now.date()
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in background daily report: {e}")
            await asyncio.sleep(60)


# --- Settings Panel ---
async def get_settings_panel(lang: str = "km") -> Tuple[str, InlineKeyboardMarkup]:
    auto_ban = (await db.get_setting("auto_ban_enabled", "true")) == "true"
    ban_mode = await db.get_setting("ban_mode", "tiered")
    daily_report = (await db.get_setting("daily_report_enabled", "true")) == "true"

    cur_mode_label = t(f"mode_{ban_mode}", lang) if f"mode_{ban_mode}" in STRINGS[lang] else ban_mode

    status_autoban = "🟢 បើកដំណើរការ (ON)" if (auto_ban and lang == "km") else ("🔴 បានបិទ (PAUSED)" if lang == "km" else ("🟢 ENABLED" if auto_ban else "🔴 DISABLED"))
    status_report = "🟢 បើក (ON)" if (daily_report and lang == "km") else ("🔴 បិទ (OFF)" if lang == "km" else ("🟢 ON" if daily_report else "🔴 OFF"))

    text = (
        f"{t('settings_title', lang)}\n"
        f"{t('settings_autoban', lang)} <b>{status_autoban}</b>\n"
        f"{t('settings_mode', lang)} <b>{cur_mode_label}</b>\n"
        f"{t('settings_daily_report', lang)} <b>{status_report}</b>\n\n"
        f"{t('settings_hint', lang)}"
    )

    btn_autoban = InlineKeyboardButton(
        t("btn_pause_autoban", lang) if auto_ban else t("btn_enable_autoban", lang),
        callback_data="set:toggle_autoban"
    )
    btn_report = InlineKeyboardButton(
        t("btn_disable_report", lang) if daily_report else t("btn_enable_report", lang),
        callback_data="set:toggle_report"
    )
    btn_modes = InlineKeyboardButton(t("btn_change_mode", lang), callback_data="set:choose_mode")
    btn_rules = InlineKeyboardButton(t("btn_view_rules", lang), callback_data="set:view_rules")
    btn_lang = InlineKeyboardButton(t("btn_language", lang), callback_data="set:language_menu")

    keyboard = InlineKeyboardMarkup([
        [btn_autoban],
        [btn_modes],
        [btn_report],
        [btn_rules],
        [btn_lang]
    ])
    return text, keyboard


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = await db.get_language()
    if not user or not is_admin(user.id):
        await update.message.reply_text(t("unauthorized", lang))
        return

    text, keyboard = await get_settings_panel(lang)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    lang = await db.get_language()
    if not is_admin(query.from_user.id):
        await query.answer(t("unauthorized", lang), show_alert=True)
        return

    data = query.data

    if data == "set:toggle_autoban":
        cur = (await db.get_setting("auto_ban_enabled", "true")) == "true"
        await db.set_setting("auto_ban_enabled", "false" if cur else "true")
        await query.answer("Updated Auto-Ban!")
    elif data == "set:toggle_report":
        cur = (await db.get_setting("daily_report_enabled", "true")) == "true"
        await db.set_setting("daily_report_enabled", "false" if cur else "true")
        await query.answer("Updated Daily Report!")
    elif data == "set:language_menu":
        text = t("lang_select", lang)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇰🇭 ភាសាខ្មែរ (Khmer)", callback_data="lang:km")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
            [InlineKeyboardButton(t("btn_back_settings", lang), callback_data="set:back")]
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return
    elif data == "set:choose_mode":
        text = t("settings_choose_mode_title", lang)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("mode_tiered", lang), callback_data="set:mode:tiered")],
            [InlineKeyboardButton(t("mode_forever", lang), callback_data="set:mode:forever")],
            [InlineKeyboardButton(t("mode_1_year", lang), callback_data="set:mode:1_year")],
            [InlineKeyboardButton(t("mode_3_months", lang), callback_data="set:mode:3_months")],
            [InlineKeyboardButton(t("mode_1_month", lang), callback_data="set:mode:1_month")],
            [InlineKeyboardButton(t("mode_1_week", lang), callback_data="set:mode:1_week")],
            [InlineKeyboardButton(t("btn_back_settings", lang), callback_data="set:back")]
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return
    elif data.startswith("set:mode:"):
        new_mode = data.replace("set:mode:", "")
        await db.set_setting("ban_mode", new_mode)
        await query.answer(f"Switched mode to {new_mode}!")
    elif data == "set:view_rules":
        lines = [t("rules_title", lang)]
        if lang == "km":
            rules_list = [
                "• <b>ចូលក្រោម ១ ថ្ងៃ (ចាកចេញថ្ងៃនេះ):</b> ➔ <b>ហាមឃាត់ ១ ឆ្នាំ</b>",
                "• <b>ស្នាក់នៅ ១ - ៧ ថ្ងៃ (១ សប្តាហ៍):</b> ➔ <b>ហាមឃាត់ ៣ ខែ</b>",
                "• <b>ស្នាក់នៅ ១ - ៤ សប្តាហ៍ (១ ខែ):</b> ➔ <b>ហាមឃាត់ ១ ខែ</b>",
                "• <b>ស្នាក់នៅ ១ - ៦ ខែ:</b> ➔ <b>ហាមឃាត់ ២ សប្តាហ៍</b>",
                "• <b>ស្នាក់នៅលើស ៦ ខែ:</b> ➔ <b>ហាមឃាត់រហូត / Custom</b>",
            ]
        else:
            rules_list = [
                "• <b>Joined < 1 Day (Left Today):</b> ➔ <b>1 Year Ban</b>",
                "• <b>Joined 1 - 7 Days (1 Week):</b> ➔ <b>3 Months Ban</b>",
                "• <b>Joined 1 - 4 Weeks (1 Month):</b> ➔ <b>1 Month Ban</b>",
                "• <b>Joined 1 - 6 Months:</b> ➔ <b>2 Weeks Ban</b>",
                "• <b>Joined > 6 Months:</b> ➔ <b>Permanent Ban</b>",
            ]
        lines.extend(rules_list)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_back_settings", lang), callback_data="set:back")]
        ])
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return

    lang = await db.get_language()
    text, keyboard = await get_settings_panel(lang)
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception:
        pass


# --- Language Switcher ---
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await db.get_language()
    text = t("lang_select", lang)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇰🇭 ភាសាខ្មែរ (Khmer)", callback_data="lang:km")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")]
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    new_lang = query.data.replace("lang:", "")
    await db.set_language(new_lang)

    confirmation = t("lang_updated", new_lang)
    await query.answer(confirmation, show_alert=True)

    # Send confirmation with new touch keyboard
    await query.message.reply_text(
        confirmation,
        reply_markup=get_main_menu_keyboard(new_lang)
    )


# --- User Lookup ---
async def lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = await db.get_language()
    if not user or not is_admin(user.id):
        await update.message.reply_text(t("unauthorized", lang))
        return

    args = context.args
    if not args:
        await update.message.reply_text(t("lookup_usage", lang), parse_mode=ParseMode.HTML)
        return

    target = args[0]
    result = await db.lookup_user(target)
    mem = result.get("member")
    bans = result.get("bans", [])

    if not mem and not bans:
        await update.message.reply_text(t("lookup_not_found", lang, query=html.escape(target)), parse_mode=ParseMode.HTML)
        return

    lines = [t("lookup_title", lang, query=html.escape(target))]

    if mem:
        now = datetime.now(timezone.utc)
        try:
            j_dt = datetime.fromisoformat(mem["joined_at"])
            if j_dt.tzinfo is None:
                j_dt = j_dt.replace(tzinfo=timezone.utc)
            days = round(max(0, (now - j_dt).total_seconds() / 86400.0), 1)
        except Exception:
            days = "?"

        lines.append(
            f"{t('lookup_active', lang)}\n"
            f"👤 <b>Name:</b> {html.escape(mem.get('full_name') or '')} (@{mem.get('username') or 'None'})\n"
            f"🆔 <b>ID:</b> <code>{mem['user_id']}</code>\n"
            f"📅 <b>Joined:</b> <code>{mem['joined_at'][:10]}</code> ({days} {t('unit_days', lang)})\n"
        )
    else:
        lines.append(f"{t('lookup_inactive', lang)}\n")

    if bans:
        lines.append(t("lookup_history", lang))
        latest_ban = bans[0]
        unbanned_status = "✅ បានដោះលែង (Unbanned)" if latest_ban.get("unbanned") else "🚫 កំពុងស្ថិតក្នុងការ Ban (Banned)"
        lines.append(
            f"• <b>Status:</b> {unbanned_status}\n"
            f"• <b>Left:</b> <code>{latest_ban.get('left_at')}</code>\n"
            f"• <b>Stayed:</b> {round(latest_ban.get('days_joined') or 0, 1)} {t('unit_days', lang)}\n"
            f"• <b>Ban Duration:</b> {latest_ban.get('ban_duration_days')} {t('unit_days', lang)} (Until: {latest_ban.get('ban_until_date') or t('mode_forever', lang)})"
        )

        keyboard = None
        if not latest_ban.get("unbanned"):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_unban_user", lang), callback_data=f"unban:{latest_ban['chat_id']}:{latest_ban['user_id']}")]
            ])
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# --- Data Export (CSV) ---
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = await db.get_language()
    if not user or not is_admin(user.id):
        await update.message.reply_text(t("unauthorized", lang))
        return

    msg = await update.message.reply_text("📦 កំពុងរៀបចំទាញយកទិន្នន័យ CSV...")

    members_csv = await db.export_members_csv()
    bans_csv = await db.export_bans_csv()

    mem_file = io.BytesIO(members_csv.encode("utf-8"))
    mem_file.name = f"members_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=mem_file,
        caption="👥 <b>Active Members CSV (សមាជិកសកម្ម)</b>",
        parse_mode=ParseMode.HTML
    )

    ban_file = io.BytesIO(bans_csv.encode("utf-8"))
    ban_file.name = f"bans_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=ban_file,
        caption="🚫 <b>Ban Logs CSV (កំណត់ត្រា Ban)</b>",
        parse_mode=ParseMode.HTML
    )

    await msg.delete()


# --- Start & Help ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    lang = await db.get_language()
    admin_tag = "✅ Admin" if is_admin(user.id) else "⚠️ Not Admin"
    msg = t("welcome_title", lang, user_id=user.id, admin_tag=admin_tag)
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(lang)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await db.get_language()
    if lang == "km":
        msg = (
            "📚 <b>មគ្គុទ្ទេសក៍ការប្រើប្រាស់ BOT:</b>\n\n"
            "⚙️ <b>ប៊ូតុងមុខងារងាយស្រួល:</b>\n"
            "• <b>📊 របាយការណ៍:</b> មើលចំនួនចូល ចាកចេញ និងកំណើនថ្ងៃនេះ\n"
            "• <b>👑 សមាជិកចាស់:</b> ស្កេនសមាជិកចាស់វស្សា ២០ នាក់ក្នុងឆានែល\n"
            "• <b>⚙️ ការកំណត់:</b> បើក/បិទ Auto-Ban, ប្តូររយៈពេល Ban (១ ឆ្នាំ, ៣ ខែ, ១ ខែ, រហូត...)\n"
            "• <b>🔍 ស្វែងរក:</b> វាយ <code>/lookup &lt;id/@username&gt;</code> ដើម្បីឆែកប្រវត្តិ\n"
            "• <b>📦 ទាញយក CSV:</b> ទាញយកបញ្ជីសមាជិក និងប្រវត្តិ Ban\n"
            "• <b>🌐 ភាសា:</b> ប្តូររវាង ភាសាខ្មែរ និង English\n\n"
            "🛡 <b>ការកំណត់សិទ្ធិក្នុងឆានែល:</b>\n"
            "ដាក់ Bot ជា Administrator ក្នុងឆានែល និងបើកសិទ្ធិ <b>'Ban Users'</b> (ហាមឃាត់អ្នកប្រើប្រាស់)។"
        )
    else:
        msg = (
            "📚 <b>BOT COMMAND GUIDE:</b>\n\n"
            "• <b>Daily Report:</b> View today's joins, leaves & net growth\n"
            "• <b>Top 20 Members:</b> Scan oldest veteran members in channel\n"
            "• <b>Settings:</b> Toggle auto-ban & change ban durations (1 year, 3 months, forever...)\n"
            "• <b>Lookup:</b> Type <code>/lookup &lt;id/@username&gt;</code> to check user history\n"
            "• <b>Export CSV:</b> Download full database of members & bans\n"
            "• <b>Language:</b> Switch between Khmer and English\n\n"
            "🛡 <b>Permissions Required:</b>\n"
            "Add the bot as an Administrator in your Telegram Channel with <b>'Ban Users'</b> permission."
        )
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(lang)
    )


# --- Handler for Touch Menu Text Buttons ---
async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles clicks on the mobile Reply Keyboard buttons."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        return

    text = update.message.text.strip()
    lang = await db.get_language()

    # Match Report
    if text in [STRINGS["km"]["btn_report"], STRINGS["en"]["btn_report"]]:
        await report_command(update, context)
    # Match Top 20
    elif text in [STRINGS["km"]["btn_top20"], STRINGS["en"]["btn_top20"]]:
        await scan_command(update, context)
    # Match Settings
    elif text in [STRINGS["km"]["btn_settings"], STRINGS["en"]["btn_settings"]]:
        await settings_command(update, context)
    # Match Lookup
    elif text in [STRINGS["km"]["btn_lookup"], STRINGS["en"]["btn_lookup"]]:
        hint = (
            "🔍 <b>របៀបស្វែងរកសមាជិក:</b>\n\nសូមផ្ញើសារតាមទម្រង់:\n<code>/lookup 123456789</code>\nឬ\n<code>/lookup @username</code>"
            if lang == "km" else
            "🔍 <b>How to Lookup:</b>\n\nPlease send:\n<code>/lookup 123456789</code>\nor\n<code>/lookup @username</code>"
        )
        await update.message.reply_text(hint, parse_mode=ParseMode.HTML)
    # Match Export
    elif text in [STRINGS["km"]["btn_export"], STRINGS["en"]["btn_export"]]:
        await export_command(update, context)
    # Match Language
    elif text in [STRINGS["km"]["btn_language"], STRINGS["en"]["btn_language"]]:
        await language_command(update, context)
    # Match Help
    elif text in [STRINGS["km"]["btn_help"], STRINGS["en"]["btn_help"]]:
        await help_command(update, context)


async def post_init(application: Application) -> None:
    await db.init()
    logger.info("Database initialized successfully.")
    bot_info = await application.bot.get_me()
    logger.info(f"Bot started as @{bot_info.username} (ID: {bot_info.id})")
    asyncio.create_task(daily_report_background_worker(application))


def main() -> None:
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is missing! Please configure it in your environment.")
        return

    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(["scan", "top20"], scan_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler(["lang", "language"], language_command))
    application.add_handler(CommandHandler("lookup", lookup_command))
    application.add_handler(CommandHandler("export", export_command))

    # Text Menu Handler (for bottom mobile touch buttons)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu))

    # Event Handlers
    application.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.CHAT_MEMBER))

    # Callback Query Handlers
    application.add_handler(CallbackQueryHandler(handle_unban_callback, pattern=r"^unban:"))
    application.add_handler(CallbackQueryHandler(handle_report_callback, pattern=r"^report:"))
    application.add_handler(CallbackQueryHandler(handle_settings_callback, pattern=r"^set:"))
    application.add_handler(CallbackQueryHandler(handle_language_callback, pattern=r"^lang:"))

    logger.info("Starting bot polling loop...")
    application.run_polling(
        allowed_updates=[
            Update.CHAT_MEMBER,
            Update.MESSAGE,
            Update.CALLBACK_QUERY,
            Update.MY_CHAT_MEMBER,
        ]
    )


if __name__ == "__main__":
    main()
