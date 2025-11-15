import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from game import SlotMachine
from db import (
    init_db, get_user, get_balance, update_balance,
    record_spin, can_claim_bonus, claim_bonus,
    top_balances, set_display_name
)

APP_TITLE = "🎰 Однорукий бандит"
START_BALANCE = 1000
MIN_BET = 10
MAX_BET = 200
BONUS_AMOUNT = 200
BONUS_COOLDOWN = 24 * 60 * 60
ANIM_FRAMES = 3
ANIM_DELAY = 0.4

WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://localhost:8000")

slot = SlotMachine()


def fmt_grid(grid):
    rows = [" ".join(row) for row in grid]
    return "\n".join(rows)


def build_keyboard(bet: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🎮 Открыть мини‑приложение", web_app=WebAppInfo(url=WEBAPP_URL)),
        ],
        [
            InlineKeyboardButton("➖ Ставка", callback_data="bet_minus"),
            InlineKeyboardButton(f"💰 {bet}", callback_data="noop"),
            InlineKeyboardButton("Ставка ➕", callback_data="bet_plus"),
        ],
        [
            InlineKeyboardButton("🎰 SPIN", callback_data="spin"),
            InlineKeyboardButton("🎁 Бонус", callback_data="bonus"),
        ],
        [
            InlineKeyboardButton("🏆 Топ", callback_data="top"),
            InlineKeyboardButton("ℹ️ Инфо", callback_data="info"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = context.user_data
    if "bet" not in ud:
        ud["bet"] = MIN_BET
    user = update.effective_user
    display = (user.first_name or "Player") if user else "Player"

    # Создадим запись пользователя (если её нет) и отобразим баланс
    db_user = await get_user(user.id if user else 0, START_BALANCE, display)
    # Сохраним отображаемое имя (на будущее для топа)
    if user:
        await set_display_name(user.id, display)

    text = (
        f"<b>{APP_TITLE}</b>\n\n"
        f"Баланс: <b>{db_user['balance']}</b>\n"
        f"Ставка: <b>{ud['bet']}</b>\n\n"
        "Нажми 🎰 SPIN, чтобы крутить барабаны!"
    )
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=build_keyboard(ud["bet"]),
    )


def clamp_bet(b: int) -> int:
    return max(MIN_BET, min(MAX_BET, b))


async def on_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    user = update.effective_user
    balance = await get_balance(user.id if user else 0, START_BALANCE)
    bet = ud.get("bet", MIN_BET)

    if query.data == "bet_minus":
        bet = clamp_bet(bet - 10)
        ud["bet"] = bet
        await query.edit_message_reply_markup(build_keyboard(bet))
        return

    if query.data == "bet_plus":
        bet = clamp_bet(bet + 10)
        ud["bet"] = bet
        await query.edit_message_reply_markup(build_keyboard(bet))
        return

    if query.data == "info":
        info = (
            "Правила:\n"
            "- Совпадение 3 символов по линии платит по таблице выплат.\n"
            "- 🌟 — дикий символ, заменяет любой.\n"
            "- Линии: 3 горизонтали + 2 диагонали.\n"
            f"- Ставка от {MIN_BET} до {MAX_BET}."
        )
        await query.reply_text(info)
        return

    if query.data == "bonus":
        can, remain = await can_claim_bonus(user.id if user else 0, None, BONUS_COOLDOWN, START_BALANCE)
        if not can:
            hours = remain // 3600
            mins = (remain % 3600) // 60
            await query.reply_text(f"Бонус будет доступен через {hours}ч {mins}м")
            return
        await claim_bonus(user.id if user else 0, BONUS_AMOUNT, START_BALANCE)
        balance = await get_balance(user.id if user else 0, START_BALANCE)
        await query.edit_message_text(
            text=(
                f"<b>{APP_TITLE}</b>\n\n"
                f"Бонус 🎁 +{BONUS_AMOUNT}!\n\n"
                f"Баланс: <b>{balance}</b>\n"
                f"Ставка: <b>{bet}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=build_keyboard(bet),
        )
        return

    if query.data == "top":
        top = await top_balances(10)
        if not top:
            await query.reply_text("Пока нет данных для топа")
            return
        lines = [f"{i+1}. {name}: {bal}" for i, (name, bal) in enumerate(top)]
        await query.reply_text("🏆 Топ игроков по балансу:\n" + "\n".join(lines))
        return

    if query.data == "noop":
        return

    if query.data == "spin":
        if balance < bet:
            await query.edit_message_text(
                text=(
                    f"<b>{APP_TITLE}</b>\n\n"
                    f"Недостаточно средств. Баланс: <b>{balance}</b>\n"
                    f"Ставка: <b>{bet}</b>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=build_keyboard(bet),
            )
            return

        # Списываем ставку
        new_balance = balance - bet
        await update_balance(user.id if user else 0, new_balance)

        # Короткая анимация спина
        anim_text = (
            f"<b>{APP_TITLE}</b>\n\n"
            f"Крутим барабаны...\n\n"
            f"Баланс: <b>{new_balance}</b>\n"
            f"Ставка: <b>{bet}</b>"
        )
        await query.edit_message_text(
            text=anim_text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_keyboard(bet),
        )
        for _ in range(ANIM_FRAMES):
            grid_text = fmt_grid(slot.spin())
            await asyncio.sleep(ANIM_DELAY)
            await query.edit_message_text(
                text=(
                    f"<b>{APP_TITLE}</b>\n\n"
                    f"{grid_text}\n\n"
                    f"Баланс: <b>{new_balance}</b>\n"
                    f"Ставка: <b>{bet}</b>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=build_keyboard(bet),
            )

        # Финальный результат
        result = slot.play(bet)
        win = result.total_win
        final_balance = new_balance + win
        await update_balance(user.id if user else 0, final_balance)
        await record_spin(user.id if user else 0, bet, win)

        grid_text = fmt_grid(result.grid)
        lines_desc = []
        for payout, matched in result.lines:
            if payout > 0:
                lines_desc.append(f"✅ Выигрыш линия: {' '.join(matched)} = +{payout}")
        if not lines_desc:
            lines_desc.append("❌ Нет выигрыша")
        lines_text = "\n".join(lines_desc)

        text = (
            f"<b>{APP_TITLE}</b>\n\n"
            f"{grid_text}\n\n"
            f"{lines_text}\n\n"
            f"Ставка: <b>{bet}</b> | Выигрыш: <b>{win}</b>\n"
            f"Баланс: <b>{final_balance}</b>"
        )

        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_keyboard(bet),
        )
        return


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    top = await top_balances(10)
    if not top:
        await update.effective_message.reply_text("Пока нет данных для топа")
        return
    lines = [f"{i+1}. {name}: {bal}" for i, (name, bal) in enumerate(top)]
    await update.effective_message.reply_text("🏆 Топ игроков по балансу:\n" + "\n".join(lines))


def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Please set TELEGRAM_TOKEN environment variable")

    # Явно создаём и устанавливаем event loop (актуально для Python 3.12)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Инициализируем БД до запуска приложения
    loop.run_until_complete(init_db())

    app = ApplicationBuilder().token(token).build()

    # Ensure webhook is removed to avoid conflicts with polling
    loop.run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(on_buttons))

    app.run_polling()


if __name__ == "__main__":
    main()
    