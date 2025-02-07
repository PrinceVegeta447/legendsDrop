import random
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, PHOTO_URL, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import pm_users as collection 


async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    user_data = await collection.find_one({"_id": user_id})

    if user_data is None:
        await collection.insert_one({"_id": user_id, "first_name": first_name, "username": username})
        
        # Announce new users in the support group
        await context.bot.send_message(
            chat_id=GROUP_ID, 
            text=f"🔥 **A New Saiyan Has Joined!** 🔥\n"
                 f"**User:** <a href='tg://user?id={user_id}'>{escape(first_name)}</a>\n"
                 f"**Welcome to Dragon Ball Legends!** 🐉⚡",
            parse_mode='HTML'
        )
    else:
        # Update user info if changed
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await collection.update_one({"_id": user_id}, {"$set": {"first_name": first_name, "username": username}})

    # Private Chat Start Message
    if update.effective_chat.type == "private":
        caption = f"""
🔥 **Welcome, Warrior!** 🔥

I am your **Dragon Ball Legends Collector Bot**! 🐉✨  
🔹 I will drop random **DBL characters** in group chats.  
🔹 Use `/collect <character>` to claim them.  
🔹 See your **collection** with `/fav`.  

💥 **Become the strongest and collect them all!** 💥
"""

        keyboard = [
            [InlineKeyboardButton("⚡ ADD ME TO GROUP ⚡", url=f'http://t.me/{BOT_USERNAME}?startgroup=new')],
            [InlineKeyboardButton("🔹 SUPPORT", url=f'https://t.me/{SUPPORT_CHAT}'),
            InlineKeyboardButton("🔸 UPDATES", url=f'https://t.me/{UPDATE_CHAT}')],
            [InlineKeyboardButton("📜 HELP", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        photo_url = random.choice(PHOTO_URL)

        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url, caption=caption, reply_markup=reply_markup, parse_mode='markdown')

    else:
        photo_url = random.choice(PHOTO_URL)
        keyboard = [
            [InlineKeyboardButton("⚡ ADD ME TO GROUP ⚡", url=f'http://t.me/{BOT_USERNAME}?startgroup=new')],
            [InlineKeyboardButton("🔹 SUPPORT", url=f'https://t.me/{SUPPORT_CHAT}'),
            InlineKeyboardButton("🔸 UPDATES", url=f'https://t.me/{UPDATE_CHAT}')],
            [InlineKeyboardButton("📜 HELP", callback_data='help')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url, caption="⚡ **Bot Activated!** Send me a private message for details.", reply_markup=reply_markup)

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        help_text = """
⚡ **Help Section** ⚡

🔹 `/collect <character>` → Collect a dropped character  
🔹 `/fav` → View your **favorite** DBL characters  
🔹 `/trade` → Trade characters with another player  
🔹 `/gift` → Gift a character to another player  
🔹 `/collection` → View your **entire collection**  
🔹 `/topgroups` → View **Top Groups**  
🔹 `/top` → View **Top Players**  
🔹 `/set_droptime` → Change character drop frequency (Admins only)  
🔹 `/droptime` → View current droptime in your group
"""
        help_keyboard = [[InlineKeyboardButton("⏪ Back", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(help_keyboard)
        
        await context.bot.edit_message_caption(chat_id=update.effective_chat.id, message_id=query.message.message_id, caption=help_text, reply_markup=reply_markup, parse_mode='markdown')

    elif query.data == 'back':
        caption = """
🔥 **Welcome Back, Warrior!** 🔥

💥 I am the **Dragon Ball Legends Collector Bot**! 💥  
🟢 Add me to a **group**, and I will drop **random characters**!  
🟢 Use `/collect <character>` to claim them.  
🟢 Check your **collection** with `/fav`.  
"""

        keyboard = [
            [InlineKeyboardButton("⚡ ADD ME TO GROUP ⚡", url=f'http://t.me/{BOT_USERNAME}?startgroup=new')],
            [InlineKeyboardButton("🔹 SUPPORT", url=f'https://t.me/{SUPPORT_CHAT}'),
            InlineKeyboardButton("🔸 UPDATES", url=f'https://t.me/{UPDATE_CHAT}')],
            [InlineKeyboardButton("📜 HELP", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.edit_message_caption(chat_id=update.effective_chat.id, message_id=query.message.message_id, caption=caption, reply_markup=reply_markup, parse_mode='markdown')

application.add_handler(CallbackQueryHandler(button, pattern='^help$|^back$', block=False))
start_handler = CommandHandler('start', start, block=False)
application.add_handler(start_handler)
