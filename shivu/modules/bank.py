import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CallbackContext
from shivu import application, user_collection

# Conversation states
DEPOSIT_AMOUNT, WITHDRAW_AMOUNT, LOAN_AMOUNT, CONFIRM_REPAY = range(4)

# Interest & Loan Settings
DAILY_INTEREST_RATE = 0.02  # 2% daily interest
LOAN_INTEREST_RATE = 0.10   # 10% loan interest
LOAN_REPAY_DAYS = 7
MIN_DEPOSIT = 500  # Minimum Zeni to deposit
MAX_WITHDRAW_PERCENT = 50  # Max 50% of bank balance per day

# ✅ Apply daily interest to all users
async def apply_interest():
    while True:
        users = await user_collection.find({"bank_balance": {"$gt": 0}}).to_list(None)
        for user in users:
            interest = int(user["bank_balance"] * DAILY_INTEREST_RATE)
            await user_collection.update_one({"id": user["id"]}, {"$inc": {"bank_balance": interest}})
        await asyncio.sleep(86400)  # Run once per day

# ✅ Check Bank Balance
async def check_balance(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    bank_balance = user.get("bank_balance", 0)
    zeni = user.get("coins", 0)
    loan = user.get("loan", 0)
    loan_due = user.get("loan_due", 0)

    text = f"""
🏦 **Bank Account Summary**
💰 **Wallet Zeni:** {coins}
🏦 **Bank Balance:** {bank_balance}
📌 **Loan Taken:** {loan} (Due: {loan_due} days)
    """.strip()
    await update.message.reply_text(text)

# ✅ Bank Info Command
async def bank_info(update: Update, context: CallbackContext):
    text = """
🏦 **Bank System Explanation**

💰 **Deposit & Withdraw:**
- Minimum deposit: 500 Zeni
- Max daily withdrawal: 50% of bank balance
- Deposited Zeni earns **2% daily interest**

📌 **Loan System:**
- Max loan: 50% of your Wallet Zeni
- Loan must be repaid within **7 days**
- Loan has **10% interest**

💸 **Interest & Loan Penalty:**
- Interest is added daily to your bank balance
- If loan is not repaid in **7 days**, extra penalties apply!

Use `/bank` to check your balance.
    """.strip()
    await update.message.reply_text(text)

# ✅ Start Deposit
async def deposit(update: Update, context: CallbackContext):
    await update.message.reply_text("💰 Enter the amount of Zeni you want to deposit:")
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

# ✅ Start Withdraw
async def withdraw(update: Update, context: CallbackContext):
    await update.message.reply_text("💸 Enter the amount of Zeni you want to withdraw:")
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

# ✅ Take Loan
async def take_loan(update: Update, context: CallbackContext):
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
        max_loan = int(user.get("zeni", 0) * 0.5)

        if amount > max_loan:
            await update.message.reply_text(f"❌ You can only take up to {max_loan} Zeni.")
            return LOAN_AMOUNT

        loan_due = LOAN_REPAY_DAYS
        await user_collection.update_one({"id": user_id}, {"$inc": {"zeni": amount, "loan": amount}, "$set": {"loan_due": loan_due}})
        await update.message.reply_text(f"✅ Loan of {amount} Zeni taken! Repay within {loan_due} days.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return LOAN_AMOUNT

# ✅ Repay Loan
async def repay_loan(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    loan = user.get("loan", 0)
    if loan <= 0:
        await update.message.reply_text("✅ You have no active loans!")
        return ConversationHandler.END

    loan_due = user.get("loan_due", 0)
    total_due = int(loan * (1 + LOAN_INTEREST_RATE))  # 10% interest

    buttons = [
        [InlineKeyboardButton(f"✅ Repay {total_due} Zeni", callback_data="confirm_repay")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_repay")]
    ]

    await update.message.reply_text(
        f"⚠️ Loan Due: {loan_due} days left\n💰 Total Due: {total_due} Zeni\n\nRepay now?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CONFIRM_REPAY

async def confirm_repay(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    total_due = int(user["loan"] * (1 + LOAN_INTEREST_RATE))
    if user["zeni"] < total_due:
        await query.message.edit_text("❌ You don't have enough Zeni!")
        return ConversationHandler.END

    await user_collection.update_one({"id": user_id}, {"$inc": {"zeni": -total_due, "loan": -user["loan"]}, "$set": {"loan_due": 0}})
    await query.message.edit_text("✅ Loan repaid successfully!")
    return ConversationHandler.END



async def start_bank_system():
    asyncio.create_task(apply_interest())
# ✅ Handlers
application.add_handler(CommandHandler("bank", check_balance))
application.add_handler(CommandHandler("bankinfo", bank_info))
application.add_handler(CommandHandler("deposit", deposit))
application.add_handler(CommandHandler("withdraw", withdraw))
application.add_handler(CommandHandler("loan", take_loan))
application.add_handler(CommandHandler("repay", repay_loan))
application.add_handler(CallbackQueryHandler(confirm_repay, pattern="confirm_repay"))

# ✅ Start Interest System
asyncio.run(start_bank_system())  # Start the async bank system
