from pymongo import ReturnDocument
from pyrogram.enums import ChatMemberStatus
from shivu import user_totals_collection, shivuu, sudo_users, OWNER_ID  
from pyrogram import Client, filters
from pyrogram.types import Message

ADMINS = [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

@shivuu.on_message(filters.command("set_droptime"))
async def change_time(client: Client, message: Message):
    chat_id = str(message.chat.id)  # Store chat_id as a string for consistency
    user_id = message.from_user.id

    # ✅ Check admin permissions
    member = await shivuu.get_chat_member(chat_id, user_id)
    if member.status not in ADMINS and user_id not in sudo_users and user_id != OWNER_ID:
        await message.reply_text("🚫 You are not authorized to change droptime.")
        return

    try:
        args = message.command
        if len(args) != 2:
            await message.reply_text("❌ Usage: `/set_droptime <number>`")
            return

        new_droptime = int(args[1])

        # ✅ Enforce 100+ limit for regular admins (Owner/Sudo can set any value)
        if new_droptime < 100 and user_id not in sudo_users and user_id != OWNER_ID:
            await message.reply_text("⚠️ Droptime must be **100+ messages** for non-owners.")
            return

        # ✅ Update in MongoDB (ensuring persistence after restarts)
        await user_totals_collection.update_one(
            {'chat_id': chat_id},
            {'$set': {'message_frequency': new_droptime}},
            upsert=True
        )

        # ✅ Confirm update with a check
        updated_chat = await user_totals_collection.find_one({'chat_id': chat_id})
        if updated_chat and updated_chat.get("message_frequency") == new_droptime:
            await message.reply_text(f"✅ Droptime successfully updated to **{new_droptime} messages**.")
        else:
            await message.reply_text("⚠️ Droptime update may not have saved correctly. Please try again.")

    except ValueError:
        await message.reply_text("❌ Please enter a valid number.")
    except Exception as e:
        await message.reply_text(f"❌ Error updating droptime: {str(e)}")

@shivuu.on_message(filters.command("droptime"))
async def view_droptime(client: Client, message: Message):
    chat_id = message.chat.id

    try:
        # Fetch the current droptime for this group
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 100) if chat_frequency else 100

        await message.reply_text(f"📊 **Current Droptime:** `{message_frequency} messages`")
    except Exception as e:
        await message.reply_text(f"❌ Failed to fetch droptime: {str(e)}")
