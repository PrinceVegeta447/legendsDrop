import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CallbackContext
from shivu import application, user_collection

# States for conversation handlers
DEPOSIT_AMOUNT, WITHDRAW_AMOUNT, LOAN_AMOUNT, CONFIRM_REPAY = range(4)

# Bank System Constants
DAILY_INTEREST_RATE = 0.02  # 2% interest per day
LOAN_INTEREST_RATE = 0.10   # 10% loan interest
LOAN_REPAY_DAYS = 7
LOAN_PENALTY = 0.05  # 5% penalty if overdue
MIN_DEPOSIT = 500
MAX_WITHDRAW_PERCENT = 50  # Max 50% of bank balance per day

# ✅ Apply Daily Interest
async def apply_interest():
    while True:
        users = await user_collection.find({"bank_balance": {"$gt": 0}}).to_list(None)
        for user in users:
            interest = int(user["bank_balance"] * DAILY_INTEREST_RATE)
            await user_collection.update_one({"id": user["id"]}, {"$inc": {"bank_balance": interest}})
        await asyncio.sleep(86400)  # Run once per day

# ✅ Bank Summary Command
async def bank_summary(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    zeni = user.get("coins", 0)
    bank_balance = user.get("bank_balance", 0)
    loan = user.get("loan", 0)
    loan_due = user.get("loan_due", 0)

    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data="bank_deposit"),
         InlineKeyboardButton("💸 Withdraw", callback_data="bank_withdraw")],
        [InlineKeyboardButton("📌 Take Loan", callback_data="bank_loan")]
    ]

    text = f"""
🏦 **Bank Summary**
💰 **Wallet Zeni:** {coins}
🏦 **Bank Balance:** {bank_balance}
📌 **Loan Taken:** {loan} (Due: {loan_due} days)
💲 **Daily Interest:** {int(bank_balance * DAILY_INTEREST_RATE)} Zeni
    """.strip()

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ✅ Deposit System
async def start_deposit(update: Update, context: CallbackContext):
    await update.callback_query.message.reply_text("💰 Enter the amount of Zeni you want to deposit:")
    return DEPOSIT_AMOUNT

async def deposit_amount(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    try:
        amount = int(update.message.text)
        if amount < MIN_DEPOSIT:
            await update.message.reply_text(f"❌ Minimum deposit is {MIN_DEPOSIT} Zeni.")
            return DEPOSIT_AMOUNT

        if amount > user.get("coins", 0):
            await update.message.reply_text("❌ You don't have enough Zeni!")
            return DEPOSIT_AMOUNT

        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -amount, "bank_balance": amount}})
        await update.message.reply_text(f"✅ Deposited {amount} Zeni to your bank!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return DEPOSIT_AMOUNT

# ✅ Withdraw System
async def start_withdraw(update: Update, context: CallbackContext):
    await update.callback_query.message.reply_text("💸 Enter the amount of Zeni you want to withdraw:")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    try:
        amount = int(update.message.text)
        max_withdraw = int(user.get("bank_balance", 0) * (MAX_WITHDRAW_PERCENT / 100))

        if amount > max_withdraw:
            await update.message.reply_text(f"❌ You can only withdraw up to {max_withdraw} Zeni today.")
            return WITHDRAW_AMOUNT

        if amount > user.get("bank_balance", 0):
            await update.message.reply_text("❌ You don't have enough balance!")
            return WITHDRAW_AMOUNT

        await user_collection.update_one({"id": user_id}, {"$inc": {"bank_balance": -amount, "coins": amount}})
        await update.message.reply_text(f"✅ Withdrawn {amount} Zeni from your bank!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return WITHDRAW_AMOUNT

# ✅ Loan System
async def start_loan(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    max_loan = int(user.get("coins", 0) * 0.5)
    if max_loan <= 0:
        await update.message.reply_text("❌ You are not eligible for a loan!")
        return ConversationHandler.END

    await update.message.reply_text(f"🏦 Enter loan amount (Max: {max_loan} Zeni):")
    return LOAN_AMOUNT

async def loan_amount(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    try:
        amount = int(update.message.text)
        max_loan = int(user.get("coins", 0) * 0.5)

        if amount > max_loan:
            await update.message.reply_text(f"❌ You can only take up to {max_loan} Zeni.")
            return LOAN_AMOUNT

        loan_due = LOAN_REPAY_DAYS
        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": amount, "loan": amount}, "$set": {"loan_due": loan_due}})
        await update.message.reply_text(f"✅ Loan of {amount} Zeni taken! Repay within {loan_due} days.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return LOAN_AMOUNT

# ✅ Handlers
application.add_handler(CommandHandler("bank", bank_summary))
application.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(start_deposit, pattern="^bank_deposit$")],
    states={DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount)]},
    fallbacks=[]
))
application.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(start_withdraw, pattern="^bank_withdraw$")],
    states={WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)]},
    fallbacks=[]
))
application.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(start_loan, pattern="^bank_loan$")],
    states={LOAN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, loan_amount)]},
    fallbacks=[]
))

# ✅ Start Bank System
async def start_bank_system():
    asyncio.create_task(apply_interest())

asyncio.create_task(start_bank_system())  # Start interest system
