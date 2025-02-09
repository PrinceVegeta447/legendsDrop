import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, banners_collection, user_collection, OWNER_ID, sudo_users
from bson import ObjectId


# ✅ Define Rarity Map
RARITY_MAP = {
    "1": "⚪ Common",
    "2": "🟢 Uncommon",
    "3": "🔵 Rare",
    "4": "🟣 Extreme",
    "5": "🟡 Sparking",
    "6": "🔱 Ultra",
    "7": "💠 Legends Limited",
    "8": "🔮 Zenkai",
    "9": "🏆 Event-Exclusive"
}

# ✅ Define Category Map
CATEGORY_MAP = {
    "1": "🏆 Saiyan",
    "2": "🔥 Hybrid Saiyan",
    "3": "🤖 Android",
    "4": "❄️ Frieza Force",
    "5": "✨ God Ki",
    "6": "💪 Super Warrior",
    "7": "🩸 Regeneration",
    "8": "🔀 Fusion Warrior",
    "9": "🤝 Duo"
    "10": "🔱 Super Saiyan God SS",
    "11": "🗿 Ultra Instinct Sign",
    "12": "⚡ Super Saiyan",
    "13": "❤️‍🔥 Dragon Ball Saga",
    "14": "💫 Majin Buu Saga",
    "15": "👾 Cell Saga",
    "16": "📽️ Sagas From the Movies",
    "17": "☠️ Lineage Of Evil"
}
# ✅ Create a new banner
async def create_banner(update: Update, context: CallbackContext) -> None:
    """Allows bot owners to create new banners."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to create banners!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Usage: `/createbanner <name> <image_url>`")
            return

        name, image_url = args

        banner = {
            "name": name,
            "image_url": image_url,
            "characters": []
        }

        banner_doc = await banners_collection.insert_one(banner)
        banner_id = str(banner_doc.inserted_id)  # Convert ObjectId to string

        await update.message.reply_text(f"✅ Banner `{name}` created successfully!\n🆔 Banner ID: `{banner_id}`")
    except Exception as e:
        await update.message.reply_text(f"❌ Error creating banner: {str(e)}")

# ✅ Upload a character to a banner
async def banner_upload(update: Update, context: CallbackContext) -> None:
    """Uploads a character to a banner (Exclusive Characters)."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to upload banner characters!")
        return

    try:
        args = context.args
        if len(args) != 5:
            await update.message.reply_text("❌ Usage: `/bupload <banner_id> <image_url> <character_name> <rarity> <category>`")
            return

        banner_id, image_url, character_name, rarity, category = args

        # ✅ Convert banner_id to ObjectId safely
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        # ✅ Fetch the banner
        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        # ✅ Validate rarity & category
        rarity_name = RARITY_MAP.get(rarity)
        category_name = CATEGORY_MAP.get(category)

        if not rarity_name:
            await update.message.reply_text("❌ Invalid rarity! Use numbers 1-9.")
            return

        if not category_name:
            await update.message.reply_text("❌ Invalid category! Use numbers 1-9.")
            return

        # ✅ Create character object
        character = {
            "image_url": image_url,
            "name": character_name,
            "rarity": rarity_name,
            "category": category_name
        }

        # ✅ Add character to the banner
        await banners_collection.update_one({"_id": banner_id}, {"$push": {"characters": character}})
        await update.message.reply_text(f"✅ Character `{character_name}` added to `{banner['name']}` banner!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading character: {str(e)}")
        

# ✅ View all available banners
async def view_banners(update: Update, context: CallbackContext) -> None:
    """Shows all available banners."""
    banners = await banners_collection.find({}).to_list(length=None)

    if not banners:
        await update.message.reply_text("❌ No active banners!")
        return

    for banner in banners:
        keyboard = [
            [InlineKeyboardButton("🎟 Summon", callback_data=f"summon:{banner['_id']}")],
            [InlineKeyboardButton("🔍 View Characters", callback_data=f"view:{banner['_id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_photo(photo=banner["image_url"],
                                         caption=f"🎟 **{banner['name']}**",
                                         parse_mode="Markdown", reply_markup=reply_markup)

# ✅ Delete a banner
async def delete_banner(update: Update, context: CallbackContext) -> None:
    """Deletes a banner and removes all its characters."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to delete banners!")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Usage: `/deletebanner <banner_id>`")
            return

        banner_id = args[0]

        # ✅ Convert banner_id to ObjectId
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        # ✅ Check if banner exists
        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ Invalid Banner ID!")
            return

        # ✅ Delete the banner
        await banners_collection.delete_one({"_id": banner_id})
        await update.message.reply_text(f"✅ Banner `{banner['name']}` deleted successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting banner: {str(e)}")

# ✅ Summon a character from a banner
async def summon_from_banner(update: Update, context: CallbackContext, banner_id: str):
    """Handles summoning characters from a specific banner."""
    user_id = update.effective_user.id

    # ✅ Fetch user data
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.callback_query.message.reply_text("❌ You need Chrono Crystals to summon!")
        return

    # ✅ Check if the banner exists
    try:
        banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})
        if not banner:
            await update.callback_query.message.reply_text("❌ This banner does not exist!")
            return
    except:
        await update.callback_query.message.reply_text("❌ Invalid Banner ID!")
        return

    # ✅ Fetch banner characters
    banner_characters = banner.get("characters", [])
    if not banner_characters:
        await update.callback_query.message.reply_text("❌ No characters available in this banner!")
        return

    # ✅ Check if user has enough CC
    summon_cost = 60  # Per summon
    if user.get("chrono_crystals", 0) < summon_cost:
        await update.callback_query.message.reply_text(f"❌ Not enough Chrono Crystals! You need {summon_cost} CC.")
        return

    # ✅ Deduct Chrono Crystals
    await user_collection.update_one({'id': user_id}, {'$inc': {'chrono_crystals': -summon_cost}})

    # ✅ Randomly select a character from the banner
    summoned_character = random.choice(banner_characters)

    # ✅ Add the character to the user's collection
    await user_collection.update_one({'id': user_id}, {'$push': {'characters': summoned_character}})

    # ✅ Send the summon result
    await update.callback_query.message.reply_photo(
        photo=summoned_character["image_url"],
        caption=f"🎉 **Summon Result** 🎉\n\n"
                f"🔥 **Character:** {summoned_character['name']}\n"
                f"🎖️ **Rarity:** {summoned_character['rarity']}\n"
                f"🔹 **Category:** {summoned_character['category']}\n\n"
                f"Use /collection to view your collection!",
        parse_mode="Markdown"
    )

# ✅ Handle summon button click
async def summon_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    data = query.data.split(":")
    
    if data[0] == "summon":
        banner_id = data[1]
        await summon_from_banner(update, context, banner_id)  # Call summon function

# ✅ Add Handlers
application.add_handler(CommandHandler("createbanner", create_banner))
application.add_handler(CommandHandler("bupload", banner_upload))
application.add_handler(CommandHandler("banners", view_banners))
application.add_handler(CommandHandler("deletebanner", delete_banner))
application.add_handler(CallbackQueryHandler(summon_callback, pattern="^summon:"))
