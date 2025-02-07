from pymongo import ReturnDocument
from pyrogram.enums import ChatMemberStatus
from shivu import user_totals_collection, shivuu, sudo_users, OWNER_ID  
from pyrogram import Client, filters
from pyrogram.types import Message

ADMINS = [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]


@shivuu.on_message(filters.command("set_droptime"))
async def change_time(client: Client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    member = await shivuu.get_chat_member(chat_id, user_id)

    # Allow only admins, sudo users, or bot owner
    if member.status not in ADMINS and user_id not in sudo_users and user_id != OWNER_ID:
        await message.reply_text("🚫 You are not authorized to use this command.")
        return

    try:
        args = message.command
        if len(args) != 2:
            await message.reply_text("⚠️ **Usage:** `/set_droptime NUMBER`")
            return

        new_frequency = int(args[1])

        # Enforce 100+ limit for regular admins, allow any value for sudo/owner
        if new_frequency < 100 and user_id not in sudo_users and user_id != OWNER_ID:
            await message.reply_text("⚠️ The message frequency must be **100 or higher**.")
            return

        # Update droptime in MongoDB (Ensure chat_id is stored as an integer)
        await user_totals_collection.find_one_and_update(
            {'chat_id': chat_id},  
            {'$set': {'message_frequency': new_frequency}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        await message.reply_text(f"✅ Successfully changed droptime to **{new_frequency} messages**.")
    except ValueError:
        await message.reply_text("❌ Invalid input. Please enter a **valid number**.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to change droptime: {str(e)}")


@shivuu.on_message(filters.command("droptime"))
async def view_droptime(client: Client, message: Message):
    chat_id = message.chat.id

    try:
        # Fetch the current droptime for this group
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 5) if chat_frequency else 5

        await message.reply_text(f"📊 **Current Droptime:** `{message_frequency} messages`")
    except Exception as e:
        await message.reply_text(f"❌ Failed to fetch droptime: {str(e)}")
