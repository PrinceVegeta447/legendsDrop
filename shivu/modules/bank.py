import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, CallbackContext
from shivu import application, user_collection

# Conversation states
DEPOSIT_AMOUNT, WITHDRAW_AMOUNT = range(2)

# Deposit & Withdraw Settings
MIN_DEPOSIT = 5000  # Minimum deposit amount
MAX_WITHDRAW_PERCENT = 50  # Max 50% of bank balance per day

# ✅ Check Bank Balance
async def check_balance(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id})  # Directly await the MongoDB query

    if not user:
        user = {"bank_balance": 0, "coins": 0}  # Default values

    text = f"""
🏦 **Bank Account Summary**
💰 **Wallet Zeni:** {user.get("coins", 0)}
🏦 **Bank Balance:** {user.get("bank_balance", 0)}
    """.strip()

    await update.message.reply_text(text)

# ✅ Start Deposit
async def deposit(update: Update, context: CallbackContext):
    await update.message.reply_text("💰 Enter the amount of Zeni you want to deposit:")
    return DEPOSIT_AMOUNT

async def deposit_amount(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id})  

    if not user:
        user = {"bank_balance": 0, "coins": 0}

    try:
        amount = int(update.message.text)
        if amount < MIN_DEPOSIT:
            await update.message.reply_text(f"❌ Minimum deposit is {MIN_DEPOSIT} Zeni.")
            return DEPOSIT_AMOUNT

        if amount > user.get("coins", 0):
            await update.message.reply_text("❌ You don't have enough Zeni!")
            return DEPOSIT_AMOUNT

        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -amount, "bank_balance": amount}}, upsert=True)
        await update.message.reply_text(f"✅ Deposited {amount} Zeni to your bank!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return DEPOSIT_AMOUNT

# ✅ Start Withdraw
async def withdraw(update: Update, context: CallbackContext):
    await update.message.reply_text("💸 Enter the amount of Zeni you want to withdraw:")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id})  

    if not user:
        user = {"bank_balance": 0, "coins": 0}

    try:
        amount = int(update.message.text)
        max_withdraw = int(user.get("bank_balance", 0) * (MAX_WITHDRAW_PERCENT / 100))

        if amount > max_withdraw:
            await update.message.reply_text(f"❌ You can only withdraw up to {max_withdraw} Zeni today.")
            return WITHDRAW_AMOUNT

        if amount > user.get("bank_balance", 0):
            await update.message.reply_text("❌ You don't have enough balance!")
            return WITHDRAW_AMOUNT

        await user_collection.update_one({"id": user_id}, {"$inc": {"bank_balance": -amount, "coins": amount}}, upsert=True)
        await update.message.reply_text(f"✅ Withdrawn {amount} Zeni from your bank!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return WITHDRAW_AMOUNT

# ✅ Handlers
application.add_handler(CommandHandler("bank", check_balance))
application.add_handler(CommandHandler("deposit", deposit))
application.add_handler(CommandHandler("withdraw", withdraw))
