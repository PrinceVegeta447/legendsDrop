import urllib.request
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

# Correct command usage instructions
WRONG_FORMAT_TEXT = """❌ Incorrect Format!
Use: `/upload <image_url> <character-name> <rarity-number>`

Example:  
`/upload https://example.com/goku.jpg Goku 1`

🎖️ **Rarity Guide:**  
1️⃣ HERO  
2️⃣ EXTREME  
3️⃣ SPARKING  
4️⃣ ULTRA  
5️⃣ LEGENDS LIMITED (LL)
"""

# Function to generate a unique character ID
async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name}, 
        {'$inc': {'sequence_value': 1}}, 
        return_document=ReturnDocument.AFTER
    )
    if not sequence_document:
        await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
        return 0
    return sequence_document['sequence_value']

# Function to upload a character
async def upload(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to upload characters!")
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        character_name = args[1].replace('-', ' ').title()

        # Validate image URL
        try:
            urllib.request.urlopen(args[0])
        except:
            await update.message.reply_text("❌ Invalid Image URL. Please provide a working link.")
            return

        # Define DBL rarity levels
        rarity_map = {
            1: "🔵 HERO",
            2: "🟣 EXTREME",
            3: "🟡 SPARKING",
            4: "🟠 ULTRA",
            5: "💠 LEGENDS LIMITED (LL)"
        }
        try:
            rarity = rarity_map[int(args[2])]
        except KeyError:
            await update.message.reply_text("❌ Invalid Rarity. Use numbers: 1, 2, 3, 4, or 5.")
            return

        # Generate unique character ID
        char_id = str(await get_next_sequence_number("character_id")).zfill(3)

        character = {
            'img_url': args[0],
            'name': character_name,
            'game': "Dragon Ball Legends",
            'rarity': rarity,
            'id': char_id
        }

        try:
            # Send the character image to the character channel
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=args[0],
                caption=f"🏆 **New Character Added!**\n\n"
                        f"🔥 **Character:** {character_name}\n"
                        f"🎮 **Game:** Dragon Ball Legends\n"
                        f"🎖️ **Rarity:** {rarity}\n"
                        f"🆔 **ID:** {char_id}\n\n"
                        f"👤 Added by [{update.effective_user.first_name}](tg://user?id={update.effective_user.id})",
                parse_mode='Markdown'
            )
            character["message_id"] = message.message_id
            await collection.insert_one(character)
            await update.message.reply_text("✅ Character successfully added to the database!")
        except:
            await collection.insert_one(character)
            await update.message.reply_text("⚠️ Character added, but no database channel found!")

    except Exception as e:
        await update.message.reply_text(f"❌ Upload failed! Error: {str(e)}\nContact support: {SUPPORT_CHAT}")

# Function to delete a character
async def delete(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in sudo_users:
        await update.message.reply_text("🚫 Only bot owners can delete characters!")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Incorrect format! Use: `/delete <Character ID>`")
            return

        character = await collection.find_one_and_delete({'id': args[0]})

        if character:
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character["message_id"])
            await update.message.reply_text(f"✅ Character `{args[0]}` deleted successfully.")
        else:
            await update.message.reply_text("⚠️ Character deleted from the database, but was not found in the channel.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting character: {str(e)}")

# Function to update a character's details
async def update(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in sudo_users:
        await update.message.reply_text("🚫 You do not have permission to update characters!")
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("❌ Incorrect format! Use: `/update <ID> <field> <new_value>`")
            return

        character = await collection.find_one({'id': args[0]})
        if not character:
            await update.message.reply_text("❌ Character not found.")
            return

        valid_fields = ["img_url", "name", "rarity"]
        if args[1] not in valid_fields:
            await update.message.reply_text(f"❌ Invalid field! Use one of: {', '.join(valid_fields)}")
            return

        # Handle rarity update
        if args[1] == "rarity":
            rarity_map = {
                1: "🔵 HERO",
                2: "🟣 EXTREME",
                3: "🟡 SPARKING",
                4: "🟠 ULTRA",
                5: "💠 LEGENDS LIMITED (LL)"
            }
            try:
                new_value = rarity_map[int(args[2])]
            except KeyError:
                await update.message.reply_text("❌ Invalid rarity. Use 1, 2, 3, 4, or 5.")
                return
        else:
            new_value = args[2]

        # Update the database
        await collection.find_one_and_update({'id': args[0]}, {'$set': {args[1]: new_value}})

        await update.message.reply_text(f"✅ Character `{args[0]}` updated successfully!")

    except Exception as e:
        await update.message.reply_text("❌ Update failed! Make sure the bot has channel permissions.")

# Add handlers
application.add_handler(CommandHandler("upload", upload, block=False))
application.add_handler(CommandHandler("delete", delete, block=False))
application.add_handler(CommandHandler("update", update, block=False))
