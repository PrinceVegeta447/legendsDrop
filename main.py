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

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    # Initialize lock for group if not present
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # ✅ Fetch the latest droptime from MongoDB
        chat_data = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_data.get("message_frequency", 100) if chat_data else 100

        # ✅ Debugging log (AFTER fetching from DB)
        current_count = message_counts.get(chat_id, 0)
        print(f"🔍 [DEBUG] Group: {chat_id} | Messages: {current_count} | Drop at: {message_frequency}")

        # ✅ Count messages for this group
        message_counts[chat_id] = current_count + 1

        # ✅ If message count reaches the threshold, drop a character
        if message_counts[chat_id] >= message_frequency:
            print(f"🟢 [DEBUG] Triggering send_image() in {chat_id}")
            await send_image(update, context)
            message_counts[chat_id] = 0  # Reset counter



async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    all_characters = list(await collection.find({}).to_list(length=None))

    if not all_characters:
        print(f"❌ [DEBUG] No characters found in MongoDB for {chat_id}!")
        return  # No characters available in the database

    print(f"🟢 [DEBUG] Dropping character in {chat_id} | Total Characters: {len(all_characters)}")

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    available_characters = [c for c in all_characters if c['_id'] not in sent_characters[chat_id]]

    if not available_characters:
        print(f"❌ [DEBUG] All characters already dropped in {chat_id}, resetting...")
        sent_characters[chat_id] = []
        return

    character = random.choice(available_characters)
    sent_characters[chat_id].append(character['_id'])
    last_characters[chat_id] = character

    print(f"🎯 [DEBUG] Selected Character: {character['name']} | Image: {character['img_url']}")

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""🔥 **A Character Has Appeared!** 🔥  
⚡ Be the first to **/collect Character Name** to claim them!""",
        parse_mode='Markdown'
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

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text(f'❌ Already guessed by someone. Try next time!')
        return

    guess = ' '.join(context.args).lower() if context.args else ''

    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text("❌ Invalid guess format.")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()

    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):

        first_correct_guesses[chat_id] = user_id
        character_data = last_characters[chat_id]
        character_rarity = character_data["rarity"]

        # Assign rewards based on rarity
        if character_rarity in REWARD_TABLE:
            coin_min, coin_max, cc_min, cc_max = REWARD_TABLE[character_rarity]
            coins_won = random.randint(coin_min, coin_max)
            chrono_crystals_won = random.randint(cc_min, cc_max)
        else:
            coins_won = random.randint(100, 200)  # Default fallback
            chrono_crystals_won = random.randint(1, 5)

        # Update user collection
        user = await user_collection.find_one({'id': user_id})
        if user:
            update_fields = {}
            if hasattr(update.effective_user, 'username') and update.effective_user.username != user.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})

            await user_collection.update_one({'id': user_id}, {'$push': {'characters': character_data}})
            await user_collection.update_one({'id': user_id}, {'$inc': {'coins': coins_won, 'chrono_crystals': chrono_crystals_won}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [character_data],
                'coins': coins_won,
                'chrono_crystals': chrono_crystals_won
            })

        # Update group user stats
        group_user_total = await group_user_totals_collection.find_one({'user_id': user_id, 'group_id': chat_id})
        if group_user_total:
            await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$inc': {'count': 1}})
        else:
            await group_user_totals_collection.insert_one({
                'user_id': user_id,
                'group_id': chat_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'count': 1
            })

        # Update top global groups
        group_info = await top_global_groups_collection.find_one({'group_id': chat_id})
        if group_info:
            await top_global_groups_collection.update_one({'group_id': chat_id}, {'$inc': {'count': 1}})
        else:
            await top_global_groups_collection.insert_one({
                'group_id': chat_id,
                'group_name': update.effective_chat.title,
                'count': 1
            })

        # Create response message
        keyboard = [[InlineKeyboardButton(f"See Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You guessed a new character! ✅️\n\n'
            f'🆔 **Name:** <b>{character_data["name"]}</b>\n'
            f'🔹 **Category:** <b>{character_data["category"]}</b>\n'
            f'🎖 **Rarity:** <b>{character_data["rarity"]}</b>\n\n'
            f'🏆 **Rewards:**\n'
            f'💰 **Zeni:** {coins_won}\n'
            f'💎 **Chrono Crystals:** {chrono_crystals_won}\n\n'
            f'This character has been added to your collection. Use /collection to see your collection!',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        await update.message.reply_text('❌ Incorrect character name. Try again!')

  

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
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    # Start polling for Telegram bot commands
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    LOGGER.info("Starting Pyrogram Client...")
    shivuu.start()  # Ensure Pyrogram client starts correctly
    LOGGER.info("Pyrogram Client started successfully!")

    LOGGER.info("Starting Telegram Bot...")
    main()  # Now start the Telegram bot
