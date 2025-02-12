import time
import random
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection

# Cooldown times (in seconds)
DAILY_RESET = 86400  # 1 day
WEEKLY_RESET = 604800  # 7 days
MONTHLY_RESET = 2592000  # 30 days

# Reward ranges
DAILY_CC = (20, 40)
DAILY_ZENI = (5000, 8000)

WEEKLY_CC = (120, 200)
WEEKLY_ZENI = (10000, 20000)

MONTHLY_CC = (300, 500)
MONTHLY_ZENI = (45000, 60000)

async def claim_reward(update: Update, context: CallbackContext) -> None:
    """Handles /daily, /weekly, and /monthly commands for claiming rewards."""
    user = update.message.from_user
    user_id = user.id

    # ✅ Fetch User Data (Ensure Proper Await)
    user_data = await user_collection.find_one({"_id": user_id})
    
    # ✅ Create User Entry If Not Exists
    if not user_data:
        user_data = {
            "_id": user_id,
            "first_name": user.first_name,
            "chrono_crystals": 0,
            "coins": 0,
            "last_daily_claim": 0,
            "last_weekly_claim": 0,
            "last_monthly_claim": 0
        }
        await user_collection.insert_one(user_data)  # ✅ Await insert

    command = update.message.text.lower()
    current_time = int(time.time())

    if command == "/daily":
        last_claim = user_data.get("last_daily_claim", 0)
        cooldown = DAILY_RESET
        reward_cc = random.randint(*DAILY_CC)
        reward_zeni = random.randint(*DAILY_ZENI)
        update_field = "last_daily_claim"

    elif command == "/weekly":
        last_claim = user_data.get("last_weekly_claim", 0)
        cooldown = WEEKLY_RESET
        reward_cc = random.randint(*WEEKLY_CC)
        reward_zeni = random.randint(*WEEKLY_ZENI)
        update_field = "last_weekly_claim"

    elif command == "/monthly":
        last_claim = user_data.get("last_monthly_claim", 0)
        cooldown = MONTHLY_RESET
        reward_cc = random.randint(*MONTHLY_CC)
        reward_zeni = random.randint(*MONTHLY_ZENI)
        update_field = "last_monthly_claim"

    else:
        return  # Invalid command

    # ✅ Check Cooldown
    time_left = cooldown - (current_time - last_claim)
    if time_left > 0:
        hours, minutes = divmod(time_left // 60, 60)
        await update.message.reply_text(
            f"⏳ You already claimed this! Try again in {hours}h {minutes}m."
        )
        return

    # ✅ Update User Data (Properly Awaited)
    await user_collection.update_one(
        {"_id": user_id},
        {
            "$inc": {"chrono_crystals": reward_cc, "coins": reward_zeni},
            "$set": {update_field: current_time}
        }
    )

    await update.message.reply_text(
        f"🎉 **Claim Successful!**\n"
        f"💎 Chrono Crystals: `{reward_cc}`\n"
        f"🪙 Zeni: `{reward_zeni}`"
    )

# ✅ Register the command handler
application.add_handler(CommandHandler(["daily", "weekly", "monthly"], claim_reward))
