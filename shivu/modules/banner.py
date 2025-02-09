import pytz
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, banners_collection, collection, sudo_users, OWNER_ID

IST = pytz.timezone("Asia/Kolkata")  # Indian Standard Time

async def create_banner(update: Update, context: CallbackContext) -> None:
    """Create a limited-time summon banner."""
    user_id = update.effective_user.id

    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to create banners!")
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("❌ Usage: `/createbanner <banner_name> <start_time (YYYY-MM-DD HH:MM)> <end_time (YYYY-MM-DD HH:MM)>`")
            return

        banner_name, start_time_str, end_time_str = args[0], args[1], args[2]

        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
        end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M").replace(tzinfo=IST)

        if start_time >= end_time:
            await update.message.reply_text("❌ End time must be after start time!")
            return

        banner_data = {
            "name": banner_name,
            "start_time": start_time,
            "end_time": end_time,
            "characters": []  # Empty at creation
        }

        await banners_collection.insert_one(banner_data)
        await update.message.reply_text(f"✅ Banner **{banner_name}** created!\n🕒 **Starts:** {start_time.astimezone(IST).strftime('%Y-%m-%d %H:%M IST')}\n🕓 **Ends:** {end_time.astimezone(IST).strftime('%Y-%m-%d %H:%M IST')}")

    except Exception as e:
        await update.message.reply_text(f"❌ Failed to create banner: {str(e)}")

async def upload_to_banner(update: Update, context: CallbackContext) -> None:
    """Upload an exclusive character to a banner using /bupload."""
    user_id = update.effective_user.id

    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to upload banner characters!")
        return

    try:
        args = context.args
        if len(args) < 5:
            await update.message.reply_text("❌ Usage: `/bupload <banner_name> <image_url> <character_name> <rarity> <category>`")
            return

        banner_name, image_url, character_name, rarity, category = args[0], args[1], ' '.join(args[2:-2]), args[-2], args[-1]

        banner = await banners_collection.find_one({"name": banner_name})
        if not banner:
            await update.message.reply_text("❌ No such banner found!")
            return

        character_data = {
            "img_url": image_url,
            "name": character_name,
            "rarity": rarity,
            "category": category
        }

        await banners_collection.update_one(
            {"name": banner_name},
            {"$push": {"characters": character_data}}
        )

        await update.message.reply_text(f"✅ Character **{character_name}** added to **{banner_name}** banner!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading to banner: {str(e)}")

async def view_banners(update: Update, context: CallbackContext) -> None:
    """View all active banners."""
    now = datetime.datetime.now(IST)
    active_banners = await banners_collection.find({"start_time": {"$lte": now}, "end_time": {"$gte": now}}).to_list(length=None)

    if not active_banners:
        await update.message.reply_text("❌ No active banners at the moment.")
        return

    banner_text = "**📢 Active Summon Banners**\n\n"
    for banner in active_banners:
        banner_text += f"🎴 **{banner['name']}**\n🕒 **Ends:** {banner['end_time'].astimezone(IST).strftime('%Y-%m-%d %H:%M IST')}\n🔹 Characters: {len(banner['characters'])} available\n\n"

    await update.message.reply_text(banner_text)

async def summon_from_banner(update: Update, context: CallbackContext) -> None:
    """Summon a character from an active banner."""
    user_id = update.effective_user.id

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Usage: `/bannersummon <banner_name>`")
            return

        banner_name = args[0]
        banner = await banners_collection.find_one({"name": banner_name})
        if not banner:
            await update.message.reply_text("❌ Banner not found!")
            return

        if not banner["characters"]:
            await update.message.reply_text("❌ No characters in this banner yet!")
            return

        summoned_character = random.choice(banner["characters"])
        await update.message.reply_photo(
            photo=summoned_character['img_url'],
            caption=f"🎉 **You Summoned:** {summoned_character['name']}!\n🎖 **Rarity:** {summoned_character['rarity']}\n🔹 **Category:** {summoned_character['category']}",
            parse_mode="Markdown"
        )

        await user_collection.update_one({'id': user_id}, {'$push': {'characters': summoned_character}})

    except Exception as e:
        await update.message.reply_text(f"❌ Summon failed: {str(e)}")

# ✅ Add Handlers
application.add_handler(CommandHandler("createbanner", create_banner, block=False))
application.add_handler(CommandHandler("bupload", upload_to_banner, block=False))
application.add_handler(CommandHandler("banners", view_banners, block=False))
application.add_handler(CommandHandler("bsummon", summon_from_banner, block=False))
