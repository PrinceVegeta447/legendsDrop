import importlib
import time
import random
import re
import asyncio
from html import escape 
from flask import Flask
import threading

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters
from pyrogram import Client, filters
from pyrogram.types import Message

from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, shivuu
from shivu import application, SUPPORT_CHAT, UPDATE_CHAT, db, LOGGER
from shivu.modules import ALL_MODULES



app = Flask(__name__)

@app.route('/')
def health_check():
    return "OK", 200

def run_health_check():
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start Flask health check in a separate thread
    threading.Thread(target=run_health_check, daemon=True).start()

   
locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}


for module_name in ALL_MODULES:
    imported_module = importlib.import_module("shivu.modules." + module_name)


last_user = {}
warned_users = {}
def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)



import asyncio

# Lock system to prevent race conditions in high-traffic groups
locks = {}

@shivuu.on_message(filters.all)
async def message_counter(client: Client, message: Message):  # Correct order
    chat_id = str(message.chat.id)
    user_id = message.from_user.id

    # ✅ Avoid counting bot's own messages and service messages
    if not user_id or user_id == client.me.id:
        return

    # ✅ Initialize lock for the group if not present
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # ✅ Fetch latest droptime from MongoDB
        chat_data = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_data.get("message_frequency", 100) if chat_data else 100

        # ✅ Debugging log
        current_count = message_counts.get(chat_id, 0)
        print(f"🔍 [DEBUG] Group: {chat_id} | Messages: {current_count} | Drop at: {message_frequency}")

        # ✅ Count messages for this group
        message_counts[chat_id] = current_count + 1

        # ✅ If message count reaches the threshold, drop a character
        if message_counts[chat_id] >= message_frequency:
            print(f"🟢 [DEBUG] Triggering send_image() in {chat_id}")
            await send_image(client, message)  # Correct parameter order
            message_counts[chat_id] = 0  # Reset counter

RESTRICTED_RARITIES = ["🟡 Sparking", "🔱 Ultra", "💠 Legends Limited", "🔮 Zenkai", "🏆 Event-Exclusive"]

async def send_image(update: Update, context: CallbackContext) -> None:
    """Drops a character in the chat while avoiding restricted rarities."""
    chat_id = message.chat.id

    # ✅ Fetch all characters that are **not restricted**
    all_characters = list(await collection.find({"rarity": {"$nin": RESTRICTED_RARITIES}}).to_list(length=None))

    if not all_characters:
        print(f"❌ [DEBUG] No valid characters found for dropping in {chat_id}!")
        return  # No valid characters available

    # ✅ Track dropped characters to prevent duplicates
    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    # ✅ Reset if all characters are already dropped
    available_characters = [c for c in all_characters if c['id'] not in sent_characters[chat_id]]
    if not available_characters:
        sent_characters[chat_id] = []  # Reset tracking
        available_characters = all_characters  # Refill with all valid characters

    # ✅ Select a **random character**
    character = random.choice(available_characters)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    # ✅ Reset guess tracking for this character
    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    # ✅ Use **file_id** instead of image URL
    file_id = character.get('file_id', None)
    if not file_id:
        print(f"❌ [DEBUG] Missing `file_id` for {character['name']} | Skipping drop...")
        return  # Skip if no file_id is present

    character = random.choice(available_characters)
    sent_characters[chat_id].append(character['_id'])
    last_characters[chat_id] = character

    print(f"🎯 [DEBUG] Selected Character: {character['name']} | Image: {character['file_id']}")

    await context.bot.send_photo(  # ✅ Use `client.send_photo()`
        chat_id=chat_id,
        photo=character['file_id'],
        caption=f"""🔥 𝑨 𝑪𝒉𝒂𝒓𝒂𝒄𝒕𝒆𝒓 𝑯𝒂𝒔 𝑨𝒑𝒑𝒆𝒂𝒓𝒆𝒅!🔥  
⚡ 𝑩𝒆 𝒕𝒉𝒆 𝒇𝒊𝒓𝒔𝒕 𝒕𝒐 /𝒄𝒐𝒍𝒍𝒆𝒄𝒕 𝑪𝒉𝒂𝒓𝒂𝒄𝒕𝒆𝒓 𝑵𝒂𝒎𝒆 𝒕𝒐 𝒄𝒍𝒂𝒊𝒎 𝒕𝒉𝒆𝒎!""",
        parse_mode='markdown'
    )
            

# Define rewards based on rarity
REWARD_TABLE = {
    "⚪ Common": (100, 150, 1, 3),
    "🟢 Uncommon": (150, 250, 2, 5),
    "🔵 Rare": (200, 350, 3, 7),
    "🟣 Extreme": (300, 450, 5, 10),
    "🟡 Sparking": (400, 600, 7, 12),
    "🔱 Ultra": (500, 800, 10, 15),
    "💠 Legends Limited": (750, 1200, 15, 20),
    "🔮 Zenkai": (800, 1300, 20, 25),
    "🏆 Event-Exclusive": (1000, 1500, 25, 30)
}


async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # ✅ Check if a character has been dropped
    if chat_id not in last_characters:
        await update.message.reply_text("❌ No character has been dropped yet!")
        return

    dropped_character = last_characters[chat_id]
    character_name = dropped_character["name"].lower()
    character_rarity = dropped_character.get("rarity", "Common")

    # ✅ Reset tracking when a new character appears
    if chat_id not in first_correct_guesses or first_correct_guesses[chat_id] != dropped_character['id']:
        first_correct_guesses[chat_id] = None  

    # ✅ Check if the character has already been guessed
    if first_correct_guesses[chat_id] is not None:
        await update.message.reply_text("❌ This character has already been guessed!")
        return

    # ✅ Extract user's guess
    guess_text = ' '.join(context.args).lower() if context.args else ''
    if not guess_text:
        await update.message.reply_text("❌ Please provide a character name.")
        return

    if "()" in guess_text or "&" in guess_text:
        await update.message.reply_text("❌ Invalid characters in guess.")
        return

    # ✅ Check if the guessed name matches
    name_parts = character_name.split()
    if sorted(name_parts) == sorted(guess_text.split()) or any(part == guess_text for part in name_parts):
        first_correct_guesses[chat_id] = dropped_character['id']  # ✅ Mark character as guessed

        # ✅ Assign rewards based on rarity
        if character_rarity in REWARD_TABLE:
            coin_min, coin_max, cc_min, cc_max = REWARD_TABLE[character_rarity]
            coins_won = random.randint(coin_min, coin_max)
            chrono_crystals_won = random.randint(cc_min, cc_max)
        else:
            coins_won = random.randint(100, 200)  # Default fallback
            chrono_crystals_won = random.randint(1, 5)

        # ✅ Update user collection
        user = await user_collection.find_one({'id': user_id})
        if user:
            update_fields = {}
            if update.effective_user.username and update.effective_user.username != user.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})

            await user_collection.update_one({'id': user_id}, {'$push': {'characters': dropped_character}})
            await user_collection.update_one({'id': user_id}, {'$inc': {'coins': coins_won, 'chrono_crystals': chrono_crystals_won}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [dropped_character],
                'coins': coins_won,
                'chrono_crystals': chrono_crystals_won
            })

        # ✅ Update group user stats
        await group_user_totals_collection.update_one(
            {'user_id': user_id, 'group_id': chat_id},
            {'$inc': {'count': 1}},
            upsert=True
        )

        # ✅ Update top global groups
        await top_global_groups_collection.update_one(
            {'group_id': chat_id},
            {'$inc': {'count': 1}},
            upsert=True
        )

        # ✅ Send success message
        keyboard = [[InlineKeyboardButton("See Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You guessed a new character! ✅️\n\n'
            f'🆔 <b>Name:</b> {dropped_character["name"]}\n'
            f'🔹 <b>Category:</b> {dropped_character["category"]}\n'
            f'🎖 <b>Rarity:</b> {dropped_character["rarity"]}\n\n'
            f'🏆 <b>Rewards:</b>\n'
            f'💰 <b>Zeni:</b> {coins_won}\n'
            f'💎 <b>Chrono Crystals:</b> {chrono_crystals_won}\n\n'
            f'This character has been added to your collection. Use /collection to see your collection!',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        await update.message.reply_text("❌ Incorrect character name. Try again!")


  

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    
    if not context.args:
        await update.message.reply_text('Please provide Character id...')
        return

    character_id = context.args[0]

    
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text('You have not Guessed any characters yet....')
        return


    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('This Character is Not In your collection')
        return

    
    user['favorites'] = [character_id]

    
    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': user['favorites']}})

    await update.message.reply_text(f'Character {character["name"]} has been added to your favorite...')
    



def main() -> None:
    """Run bot."""

    # Add command handlers
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.all, message_counter, block=False))

    # Start polling for Telegram bot commands
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    LOGGER.info("Starting Pyrogram Client...")
    shivuu.start()  # Ensure Pyrogram client starts correctly
    LOGGER.info("Pyrogram Client started successfully!")

    LOGGER.info("Starting Telegram Bot...")
    main()  # Now start the Telegram bot
