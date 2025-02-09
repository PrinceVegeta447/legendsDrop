import random
from html import escape 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from shivu import application, PHOTO_URL, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import pm_users as collection  


async def start(update: Update, context: CallbackContext) -> None:
    """Handles the /start command with an interactive UI."""
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    user_data = await collection.find_one({"_id": user_id})

    if user_data is None:
        await collection.insert_one({"_id": user_id, "first_name": first_name, "username": username})
        
        # 🏆 Announce new users in the support group
        await context.bot.send_message(
            chat_id=GROUP_ID, 
            text=f"🔥 **A New Saiyan Has Arrived!** 🔥\n"
                 f"👤 **User:** [{escape(first_name)}](tg://user?id={user_id})\n"
                 f"💥 **Get ready for battle in Dragon Ball Legends!** 🐉⚡",
            parse_mode='Markdown'
        )
    else:
        # ✅ Update user info if changed
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await collection.update_one({"_id": user_id}, {"$set": {"first_name": first_name, "username": username}})

    # 🏆 **Private Chat Start Message**
    if update.effective_chat.type == "private":
        caption = f"""
🔥 **Welcome, {escape(first_name)}!** 🔥

🌍 **Step into the world of** 🐉 *Dragon Ball Legends!*  
⚡ I am your **DBL Collector Bot**, helping you collect & battle with legendary warriors!

📜 **What I Do:**  
🔹 Drop **random characters** in group chats.  
🔹 Use **/collect <character>** to claim them.  
🔹 View your **collection** with **/harem**.  
🔹 Check your **inventory** with **/inventory**.  
🔹 Buy **Chrono Crystals** & **Summon Tickets** in **/shop**.  

🏆 **Are you ready to collect them all?**  
"""
        keyboard = [
            [InlineKeyboardButton("⚡ ADD ME TO GROUP ⚡", url=f'http://t.me/{BOT_USERNAME}?startgroup=true')],
            [InlineKeyboardButton("🔹 SUPPORT", url=f'https://t.me/{SUPPORT_CHAT}'),
             InlineKeyboardButton("🔸 UPDATES", url=f'https://t.me/{UPDATE_CHAT}')],
            [InlineKeyboardButton("📜 HELP", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        photo_url = random.choice(PHOTO_URL)

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    else:
        # 🏆 **Group Chat Start Message**
        photo_url = random.choice(PHOTO_URL)
        keyboard = [
            [InlineKeyboardButton("⚡ ADD ME TO GROUP ⚡", url=f'http://t.me/{BOT_USERNAME}?startgroup=true')],
            [InlineKeyboardButton("🔹 SUPPORT", url=f'https://t.me/{SUPPORT_CHAT}'),
             InlineKeyboardButton("🔸 UPDATES", url=f'https://t.me/{UPDATE_CHAT}')],
            [InlineKeyboardButton("📜 HELP", callback_data='help')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption="⚡ **Bot Activated!** Send me a private message for details.",
            reply_markup=reply_markup
        )


async def button(update: Update, context: CallbackContext) -> None:
    """Handles interactive buttons in the start menu."""
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        help_text = """
⚡ **Dragon Ball Legends Bot - Help Menu** ⚡

🟢 **Basic Commands:**  
🔹 `/collect <character>` → Claim a dropped character  
🔹 `/collection` → View your **collection**  
🔹 `/inventory` → View your **Zeni & Chrono Crystals**  
🔹 `/shop` → Buy **Chrono Crystals & Summon Tickets**  
🔹 `/fav` → Set a favorite character  

🛠 **Admin Commands:**  
🔹 `/set_droptime <number>` → Set drop frequency (Admin only)  
🔹 `/droptime` → View current drop settings  
🔹 `/topgroups` → View **Top Groups**  
🔹 `/top` → View **Top Players**  
"""
        help_keyboard = [[InlineKeyboardButton("⏪ Back", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(help_keyboard)
        
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif query.data == 'back':
        caption = """
🔥 **Welcome Back, Warrior!** 🔥

⚡ **This is the Dragon Ball Legends Collector Bot!**  
🔹 I drop **random DBL characters** in group chats.  
🔹 Use **/collect <character>** to claim them.  
🔹 Check your **collection** with **/harem**.  
🔹 Earn **Zeni** & **Chrono Crystals** by collecting more!  
"""

        keyboard = [
            [InlineKeyboardButton("⚡ ADD ME TO GROUP ⚡", url=f'http://t.me/{BOT_USERNAME}?startgroup=true')],
            [InlineKeyboardButton("🔹 SUPPORT", url=f'https://t.me/{SUPPORT_CHAT}'),
             InlineKeyboardButton("🔸 UPDATES", url=f'https://t.me/{UPDATE_CHAT}')],
            [InlineKeyboardButton("📜 HELP", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


# ✅ **Handlers for Start & Interactive Buttons**
application.add_handler(CallbackQueryHandler(button, pattern='^help$|^back$', block=False))
start_handler = CommandHandler('start', start, block=False)
application.add_handler(start_handler)
