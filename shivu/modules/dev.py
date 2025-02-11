from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, OWNER_ID, user_collection, collection

# ✅ Function to erase a user's collection
async def erase_collection(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Only bot owners can erase user collections!")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Incorrect format! Use: `/erase <user_id>`")
            return

        user_id = int(args[0])

        # Remove all characters from the user's collection
        result = await user_collection.update_one({"id": user_id}, {"$set": {"characters": []}})

        if result.modified_count > 0:
            await update.message.reply_text(f"✅ Successfully erased the collection of user `{user_id}`.")
        else:
            await update.message.reply_text(f"⚠️ No collection found for user `{user_id}`.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error erasing collection: {str(e)}")

# ✅ Function to add a character to a user's collection
async def add_character(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Only bot owners can add characters to user collections!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Incorrect format! Use: `/addch <user_id> <character_id>`")
            return

        user_id = int(args[0])
        character_id = args[1]

        # Find the character in the database
        character = await collection.find_one({"id": character_id})
        if not character:
            await update.message.reply_text("❌ Character not found in the database.")
            return

        # Add character to the user's collection
        result = await user_collection.update_one({"id": user_id}, {"$push": {"characters": character}}, upsert=True)

        if result.modified_count > 0:
            await update.message.reply_text(f"✅ Added `{character['name']}` to `{user_id}`'s collection.")
        else:
            await update.message.reply_text(f"⚠️ Unable to add character to `{user_id}`'s collection.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error adding character: {str(e)}")


# ✅ Function to add all characters from the database to a user's collection
async def add_all_characters(update: Update, context: CallbackContext) -> None:
    """Adds all characters from the database to a user's collection."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Only bot owners can add all characters!")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Incorrect format! Use: `/addall <user_id>`")
            return

        user_id = int(args[0])

        # Fetch all characters from the database
        characters = await collection.find({}).to_list(length=None)
        if not characters:
            await update.message.reply_text("❌ No characters found in the database.")
            return

        # Add all characters to the user's collection
        result = await user_collection.update_one({"id": user_id}, {"$set": {"characters": characters}}, upsert=True)

        if result.modified_count > 0:
            await update.message.reply_text(f"✅ Added all `{len(characters)}` characters to `{user_id}`'s collection.")
        else:
            await update.message.reply_text(f"⚠️ Unable to add all characters to `{user_id}`'s collection.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error adding characters: {str(e)}")


# ✅ Add command handlers
application.add_handler(CommandHandler("erase", erase_collection, block=False))
application.add_handler(CommandHandler("addch", add_character, block=False))
application.add_handler(CommandHandler("addall", add_all_characters, block=False))
