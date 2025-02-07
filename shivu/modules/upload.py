import urllib.request
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, OWNER_ID, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

# ✅ Correct command usage instructions
WRONG_FORMAT_TEXT = """❌ Incorrect Format!
Use: `/upload <image_url> <character-name> <rarity-number> <category-number>`

Example:  
`/upload https://example.com/goku.jpg Goku 5 1`

🎖️ **Rarity Guide:**  
1️⃣ Common  
2️⃣ Uncommon  
3️⃣ Rare  
4️⃣ Extreme  
5️⃣ Sparking  
6️⃣ Ultra  
7️⃣ Legends Limited  
8️⃣ Zenkai  
9️⃣ Event-Exclusive  

🔹 **Category Guide:**  
1️⃣ Saiyan  
2️⃣ Hybrid Saiyan  
3️⃣ Android  
4️⃣ Frieza Force  
5️⃣ God Ki  
6️⃣ Super Warrior  
7️⃣ Regeneration  
8️⃣ Fusion Warrior  
"""

# ✅ Function to upload a character
async def upload(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # 🔒 Check if user has permission
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to upload characters!")
        return

    try:
        args = context.args
        if len(args) != 4:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        image_url, character_name, rarity_input, category_input = args[0], args[1].replace('-', ' ').title(), args[2], args[3]

        # ✅ Validate image URL
        try:
            urllib.request.urlopen(image_url)
        except:
            await update.message.reply_text("❌ Invalid Image URL. Please provide a working link.")
            return

        # ✅ Define DBL rarity levels
        rarity_map = {
            "1": "⚪ Common",
            "2": "🟢 Uncommon",
            "3": "🔵 Rare",
            "4": "🟣 Extreme",
            "5": "🟡 Sparking",
            "6": "🟠 Ultra",
            "7": "💠 Legends Limited",
            "8": "🔮 Zenkai",
            "9": "🏆 Event-Exclusive"
        }
        rarity = rarity_map.get(rarity_input)
        if not rarity:
            await update.message.reply_text("❌ Invalid Rarity. Use numbers: 1-9.")
            return

        # ✅ Define character categories
        category_map = {
            "1": "🏆 Saiyan",
            "2": "🔥 Hybrid Saiyan",
            "3": "🤖 Android",
            "4": "❄️ Frieza Force",
            "5": "✨ God Ki",
            "6": "💪 Super Warrior",
            "7": "🩸 Regeneration",
            "8": "🔀 Fusion Warrior"
        }
        category = category_map.get(category_input)
        if not category:
            await update.message.reply_text("❌ Invalid Category. Use numbers: 1-8.")
            return

        # ✅ Generate unique character ID
        char_id = str(await get_next_sequence_number("character_id")).zfill(3)

        character = {
            'img_url': image_url,
            'name': character_name,
            'rarity': rarity,
            'category': category,
            'id': char_id
        }

        # ✅ Send the character image to the character channel
        message = await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=image_url,
            caption=f"🏆 **New Character Added!**\n\n"
                    f"🔥 **Character:** {character_name}\n"
                    f"🎖️ **Rarity:** {rarity}\n"
                    f"🔹 **Category:** {category}\n"
                    f"🆔 **ID:** {char_id}\n\n"
                    f"👤 Added by [{update.effective_user.first_name}](tg://user?id={user_id})",
            parse_mode='Markdown'
        )

        character["message_id"] = message.message_id
        await collection.insert_one(character)
        await update.message.reply_text(f"✅ `{character_name}` successfully added!")

    except Exception as e:
        await update.message.reply_text(f"❌ Upload failed! Error: {str(e)}\nContact support: {SUPPORT_CHAT}")
