from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection

# 🏆 Rank System
RANKS = [
    (0, "🆕 Newbie"),
    (10, "🔰 Beginner"),
    (50, "⚔️ Warrior"),
    (100, "🏆 Champion"),
    (200, "🌟 Legend"),
    (500, "🔥 Ultimate Collector"),
]

def get_rank(total_characters):
    """Determine rank based on character count."""
    for threshold, rank in reversed(RANKS):
        if total_characters >= threshold:
            return rank
    return "🆕 Newbie"

def progress_bar(value, max_value=500, length=5):
    """Generate a compact progress bar for currency display."""
    filled_blocks = int((value / max_value) * length)
    return "🟩" * filled_blocks + "⬜" * (length - filled_blocks)

async def profile(update: Update, context: CallbackContext) -> None:
    """Displays the user's profile with improved UI."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id}) or {}

    # ✅ Initialize missing fields
    user.setdefault("coins", 0)
    user.setdefault("chrono_crystals", 0)
    user.setdefault("summon_tickets", 0)
    user.setdefault("exclusive_tokens", 0)

    total_characters = len(user.get("characters", []))
    rank = get_rank(total_characters)

    # 🏆 **Enhanced Profile UI**
    profile_message = (
        f"👤 <b>{update.effective_user.first_name}'s Profile</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"🎖 <b>Rank:</b> {rank}\n"
        f"🎴 <b>Characters:</b> <code>{total_characters}</code>\n"
        "━━━━━━━━━━━━━━\n"
        f"💰 <b>Zeni:</b> <code>{user['coins']}</code> {progress_bar(user['coins'])}\n"
        f"💎 <b>Chrono Crystals:</b> <code>{user['chrono_crystals']}</code> {progress_bar(user['chrono_crystals'], max_value=100)}\n"
        f"🎟 <b>Summon Tickets:</b> <code>{user['summon_tickets']}</code>\n"
        f"🛡 <b>Exclusive Tokens:</b> <code>{user['exclusive_tokens']}</code>\n"
    )

    # ✅ Fetch Telegram profile picture
    user_photo = await context.bot.get_user_profile_photos(user_id)
    if user_photo.photos:
        photo_file_id = user_photo.photos[0][-1].file_id
        await update.message.reply_photo(photo=photo_file_id, caption=profile_message, parse_mode="HTML")
    else:
        await update.message.reply_text(profile_message, parse_mode="HTML")

# ✅ **Add Command Handlers**
application.add_handler(CommandHandler("profile", profile, block=False))
