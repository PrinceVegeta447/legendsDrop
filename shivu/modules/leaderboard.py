import os
import random
import html
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import (
    application, PHOTO_URL, OWNER_ID, user_collection,
    top_global_groups_collection, group_user_totals_collection, sudo_users as SUDO_USERS
)

# ✅ Fetch a random image from predefined list
def get_random_photo():
    return random.choice(PHOTO_URL) if PHOTO_URL else None

# ✅ Truncate long names safely
def truncate_name(name, max_length=15):
    return name[:max_length] + "..." if len(name) > max_length else name

# ✅ Leaderboard for Top 10 Global Groups
async def global_leaderboard(update: Update, context: CallbackContext) -> None:
    cursor = top_global_groups_collection.aggregate([
        {"$project": {"group_name": 1, "count": 1}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    message = "🏆 <b>Top 10 Groups (Most Characters Guessed)</b>\n━━━━━━━━━━━━━━━━━━\n"
    for i, group in enumerate(leaderboard_data, start=1):
        group_name = truncate_name(html.escape(group.get('group_name', 'Unknown')))
        count = group['count']
        message += f"{i}. <b>{group_name}</b> ➾ <b>{count}</b>\n"

    await update.message.reply_photo(photo=get_random_photo(), caption=message, parse_mode="HTML")

# ✅ Leaderboard for Top 10 Users in a Group
async def ctop(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    cursor = group_user_totals_collection.aggregate([
        {"$match": {"group_id": chat_id}},
        {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    message = "🏅 <b>Top 10 Users (Most Characters Guessed in This Group)</b>\n━━━━━━━━━━━━━━━━━━\n"
    for i, user in enumerate(leaderboard_data, start=1):
        first_name = truncate_name(html.escape(user.get('first_name', 'Unknown')))
        username = user.get('username', 'Unknown')
        character_count = user['character_count']
        message += f"{i}. <a href='https://t.me/{username}'><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n"

    await update.message.reply_photo(photo=get_random_photo(), caption=message, parse_mode="HTML")

# ✅ Global Leaderboard (Top 10 Users with Most Characters)
async def leaderboard(update: Update, context: CallbackContext) -> None:
    cursor = user_collection.aggregate([
        {"$project": {"username": 1, "first_name": 1, "character_count": {"$size": "$characters"}}},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    message = "👑 <b>Top 10 Users (Most Characters Collected)</b>\n━━━━━━━━━━━━━━━━━━\n"
    for i, user in enumerate(leaderboard_data, start=1):
        first_name = truncate_name(html.escape(user.get('first_name', 'Unknown')))
        username = user.get('username', 'Unknown')
        character_count = user['character_count']
        message += f"{i}. <a href='https://t.me/{username}'><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n"

    await update.message.reply_photo(photo=get_random_photo(), caption=message, parse_mode="HTML")

# ✅ Stats for Total Users & Groups (Owner Only)
async def stats(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    user_count = await user_collection.count_documents({})
    group_count = len(await group_user_totals_collection.distinct('group_id'))

    await update.message.reply_text(f"📊 <b>Bot Stats</b>\n━━━━━━━━━━━━━━━━━━\n👥 Users: <b>{user_count}</b>\n🏘 Groups: <b>{group_count}</b>", parse_mode="HTML")

# ✅ Send Users List as a Document (Sudo Only)
async def send_users_document(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in SUDO_USERS:
        await update.message.reply_text("❌ Only for Sudo Users!")
        return

    cursor = user_collection.find({})
    users = [user['first_name'] for user in await cursor.to_list(length=None)]
    
    with open("users.txt", "w") as f:
        f.write("\n".join(users))

    await update.message.reply_document(document=open("users.txt", "rb"))
    os.remove("users.txt")

# ✅ Send Groups List as a Document (Sudo Only)
async def send_groups_document(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in SUDO_USERS:
        await update.message.reply_text("❌ Only for Sudo Users!")
        return

    cursor = top_global_groups_collection.find({})
    groups = [group['group_name'] for group in await cursor.to_list(length=None)]

    with open("groups.txt", "w") as f:
        f.write("\n".join(groups))

    await update.message.reply_document(document=open("groups.txt", "rb"))
    os.remove("groups.txt")


async def top_wealth(update: Update, context: CallbackContext) -> None:
    """Shows Top 10 Users with Most Zeni (💰) and Chrono Crystals (💎)."""
    cursor = user_collection.aggregate([
        {"$project": {"username": 1, "first_name": 1, "coins": 1, "chrono_crystals": 1}},
        {"$sort": {"coins": -1, "chrono_crystals": -1}},  # Sort by Zeni first, then CC
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    if not leaderboard_data:
        await update.message.reply_text("❌ No users found in the database!", parse_mode="HTML")
        return

    leaderboard_message = "🏆 <b>Top 10 Wealthiest Users</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for i, user in enumerate(leaderboard_data, start=1):
        username = user.get("username", "Unknown")
        first_name = html.escape(user.get("first_name", "Unknown"))
        first_name = first_name[:15] + "..." if len(first_name) > 15 else first_name
        zeni = user.get("coins", 0)
        chrono_crystals = user.get("chrono_crystals", 0)

        leaderboard_message += (
            f"{i}. <a href='https://t.me/{username}'><b>{first_name}</b></a>\n"
            f"   💰 <b>Zeni:</b> {zeni} | 💎 <b>CC:</b> {chrono_crystals}\n"
        )

    photo_url = random.choice(PHOTO_URL)
    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode="HTML")



# ✅ Register Command Handlers
application.add_handler(CommandHandler("top", leaderboard, block=False))
application.add_handler(CommandHandler("ctop", ctop, block=False))
application.add_handler(CommandHandler("TopGroups", global_leaderboard, block=False))
application.add_handler(CommandHandler("stats", stats, block=False))
application.add_handler(CommandHandler("list", send_users_document, block=False))
application.add_handler(CommandHandler("groups", send_groups_document, block=False))
application.add_handler(CommandHandler("wtop", top_wealth, block=False))
