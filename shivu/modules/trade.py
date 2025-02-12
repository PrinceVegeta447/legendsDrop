from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shivu import user_collection, shivuu

pending_trades = {}
pending_gifts = {}

### **⚡ Trade System**
@shivuu.on_message(filters.command("trade"))
async def trade(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("⚠️ **You must reply to a user to trade a character!**")
        return

    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        await message.reply_text("❌ **You can't trade characters with yourself!**")
        return

    if len(message.command) != 3:
        await message.reply_text("🛠 **Usage:** `/trade <your_character_id> <their_character_id>`")
        return

    sender_character_id, receiver_character_id = message.command[1], message.command[2]

    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    if not sender or not sender.get('characters'):
        await message.reply_text("❌ **You don't have any characters to trade!**")
        return
    if not receiver or not receiver.get('characters'):
        await message.reply_text("❌ **The other user doesn't have any characters to trade!**")
        return

    sender_character = next((c for c in sender['characters'] if c['id'] == sender_character_id), None)
    receiver_character = next((c for c in receiver['characters'] if c['id'] == receiver_character_id), None)

    if not sender_character:
        await message.reply_text("❌ **You don't own the character you're trying to trade!**")
        return
    if not receiver_character:
        await message.reply_text("❌ **The other user doesn't own the character you're trying to trade for!**")
        return

    pending_trades[(sender_id, receiver_id)] = (sender_character_id, receiver_character_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Trade", callback_data=f"confirm_trade:{sender_id}:{receiver_id}")],
        [InlineKeyboardButton("❌ Cancel Trade", callback_data=f"cancel_trade:{sender_id}:{receiver_id}")]
    ])

    await message.reply_text(
        f"🔄 **Trade Request:**\n"
        f"🟢 **{message.from_user.mention}** wants to trade **{sender_character['name']}**\n"
        f"🔵 **{message.reply_to_message.from_user.mention}**'s **{receiver_character['name']}**\n\n"
        f"⚠️ **{message.reply_to_message.from_user.first_name}, do you accept this trade?**",
        reply_markup=keyboard
    )

@shivuu.on_callback_query(filters.regex(r"^(confirm_trade|cancel_trade):(\d+):(\d+)$"))
async def trade_callback(client, callback_query):
    action, sender_id, receiver_id = callback_query.data.split(":")
    sender_id, receiver_id = int(sender_id), int(receiver_id)

    if (sender_id, receiver_id) not in pending_trades:
        await callback_query.answer("⚠️ This trade is no longer active!", show_alert=True)
        return

    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    if not sender or not receiver:
        del pending_trades[(sender_id, receiver_id)]
        await callback_query.message.edit_text("❌ **Trade Failed: One or both users no longer exist!**")
        return

    sender_character_id, receiver_character_id = pending_trades.pop((sender_id, receiver_id))

    if action == "confirm_trade":
        sender_character = next((c for c in sender['characters'] if c['id'] == sender_character_id), None)
        receiver_character = next((c for c in receiver['characters'] if c['id'] == receiver_character_id), None)

        if not sender_character or not receiver_character:
            await callback_query.message.edit_text("❌ **Trade Failed: One or both characters no longer exist!**")
            return

        # ✅ Swap one instance of the character
        sender['characters'].remove(sender_character)
        receiver['characters'].remove(receiver_character)
        sender['characters'].append(receiver_character)
        receiver['characters'].append(sender_character)

        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})
        await user_collection.update_one({'id': receiver_id}, {'$set': {'characters': receiver['characters']}})

        await callback_query.message.edit_text(
            f"✅ **Trade Successful!**\n"
            f"🔄 **{sender_character['name']}** ⇄ **{receiver_character['name']}**"
        )
    else:
        del pending_trades[(sender_id, receiver_id)]
        await callback_query.message.edit_text("❌ **Trade Cancelled!**")


### **🎁 Gift System**
@shivuu.on_message(filters.command("gift"))
async def gift(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("⚠️ **Reply to a user to gift a character!**")
        return

    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        await message.reply_text("❌ **You can't gift a character to yourself!**")
        return

    if len(message.command) != 2:
        await message.reply_text("🛠 **Usage:** `/gift <character_id>`")
        return

    character_id = message.command[1]
    sender = await user_collection.find_one({'id': sender_id})

    if not sender or not sender.get('characters'):
        await message.reply_text("❌ **You have no characters to gift!**")
        return

    character = next((c for c in sender['characters'] if c['id'] == character_id), None)

    if not character:
        await message.reply_text("❌ **You don't own this character!**")
        return

    pending_gifts[(sender_id, receiver_id)] = character

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Confirm Gift", callback_data=f"confirm_gift:{sender_id}:{receiver_id}")],
        [InlineKeyboardButton("❌ Cancel Gift", callback_data=f"cancel_gift:{sender_id}:{receiver_id}")]
    ])

    await message.reply_text(
        f"🎁 **Gift Request:**\n"
        f"🎀 **{message.from_user.mention}** wants to gift **{character['name']}** to **{message.reply_to_message.from_user.mention}**!\n\n"
        f"⚠️ **{message.reply_to_message.from_user.first_name}, do you accept this gift?**",
        reply_markup=keyboard
    )


@shivuu.on_callback_query(filters.regex(r"^(confirm_gift|cancel_gift):(\d+):(\d+)$"))
async def gift_callback(client, callback_query):
    action, sender_id, receiver_id = callback_query.data.split(":")
    sender_id, receiver_id = int(sender_id), int(receiver_id)

    if (sender_id, receiver_id) not in pending_gifts:
        await callback_query.answer("⚠️ This gift request is no longer active!", show_alert=True)
        return

    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    if not sender or not receiver:
        await callback_query.message.edit_text("❌ **Gift Failed: One or both users no longer exist!**")
        return

    character = pending_gifts.pop((sender_id, receiver_id))

    if action == "confirm_gift":
        # ✅ Remove only one instance from sender
        sender['characters'].remove(character)
        receiver['characters'].append(character)

        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})
        await user_collection.update_one({'id': receiver_id}, {'$set': {'characters': receiver['characters']}})

        await callback_query.message.edit_text(f"✅ **Gift Successful!**\n🎁 **{character['name']}** has been gifted!")
    else:
        await callback_query.message.edit_text("❌ **Gift Cancelled!**")
