import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import application, user_collection

# 🎰 Slot Machine
async def slot_machine(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    args = context.args

    if not args or not args[0].isdigit():
        return await update.message.reply_text("🎰 **Usage:** `/slot <bet_amount>`")

    bet = int(args[0])
    user = await user_collection.find_one({"id": user_id}) or {}

    if bet <= 0 or bet > user.get("coins", 0):
        return await update.message.reply_text("❌ **Invalid Bet!** You don’t have enough Zeni.")

    # 🎰 Slot Symbols
    symbols = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
    result = [random.choice(symbols) for _ in range(3)]
    reward = 0

    if result[0] == result[1] == result[2]:
        reward = bet * 5  # Triple match = 5x reward
    elif result[0] == result[1] or result[1] == result[2]:
        reward = bet * 2  # Two matches = 2x reward

    net_gain = reward - bet
    await user_collection.update_one({"id": user_id}, {"$inc": {"coins": net_gain}})

    text = f"🎰 **Slot Machine** 🎰\n"
    text += f"{' '.join(result)}\n\n"
    text += f"**You Bet:** {bet} Zeni\n"
    text += f"**You Won:** {reward} Zeni\n" if reward else "❌ **You Lost!**\n"

    await update.message.reply_text(text)

# 🎲 Dice Roll
async def dice_roll(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    args = context.args

    if not args or not args[0].isdigit():
        return await update.message.reply_text("🎲 **Usage:** `/dice <bet_amount>`")

    bet = int(args[0])
    user = await user_collection.find_one({"id": user_id}) or {}

    if bet <= 0 or bet > user.get("coins", 0):
        return await update.message.reply_text("❌ **Invalid Bet!** You don’t have enough Zeni.")

    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    text = f"🎲 **Dice Battle!** 🎲\n\nYou rolled: 🎲 {user_roll}\nBot rolled: 🎲 {bot_roll}\n\n"

    if user_roll > bot_roll:
        reward = bet * 2
        text += f"✅ **You Win!** +{reward} Zeni"
    elif user_roll < bot_roll:
        reward = -bet
        text += "❌ **You Lost!**"
    else:
        reward = 0
        text += "⚖️ **It’s a Draw!**"

    await user_collection.update_one({"id": user_id}, {"$inc": {"coins": reward}})
    await update.message.reply_text(text)

# 🪙 Coin Flip
async def coin_flip(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    args = context.args

    if len(args) < 2 or args[0] not in ["heads", "tails"] or not args[1].isdigit():
        return await update.message.reply_text("🪙 **Usage:** `/flip <heads/tails> <bet_amount>`")

    choice, bet = args[0].lower(), int(args[1])
    user = await user_collection.find_one({"id": user_id}) or {}

    if bet <= 0 or bet > user.get("coins", 0):
        return await update.message.reply_text("❌ **Invalid Bet!** You don’t have enough Zeni.")

    result = random.choice(["heads", "tails"])
    text = f"🪙 **Coin Flip!**\n\nYou chose: `{choice.capitalize()}`\nResult: `{result.capitalize()}`\n\n"

    if result == choice:
        reward = bet * 2
        text += f"✅ **You Win!** +{reward} Zeni"
    else:
        reward = -bet
        text += "❌ **You Lost!**"

    await user_collection.update_one({"id": user_id}, {"$inc": {"coins": reward}})
    await update.message.reply_text(text)

# 📌 Handlers
application.add_handler(CommandHandler("slot", slot_machine, block=False))
application.add_handler(CommandHandler("dice", dice_roll, block=False))
application.add_handler(CommandHandler("flip", coin_flip, block=False))
