from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection

# Deposit & Withdraw Settings
MIN_DEPOSIT = 500  # Minimum deposit amount
MAX_WITHDRAW_PERCENT = 50  # Max 50% of bank balance per day

# 🏦 **Check Bank Balance**
async def check_balance(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {"bank_balance": 0, "coins": 0}

    text = f"""
🏦 **Bank Account Summary**
━━━━━━━━━━━━━━━━━
💰 **Wallet Zeni:** `{user.get("coins", 0):,}`
🏦 **Bank Balance:** `{user.get("bank_balance", 0):,}`
━━━━━━━━━━━━━━━━━
Use `/deposit <amount>` to save your Zeni in the bank.  
Use `/withdraw <amount>` to withdraw from the bank.
    """.strip()

    await update.message.reply_text(text, parse_mode="Markdown")

# 💰 **Deposit Command**
async def deposit(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {"bank_balance": 0, "coins": 0}

    if not context.args:
        await update.message.reply_text("❌ **Usage:** `/deposit <amount>`", parse_mode="Markdown")
        return

    try:
        amount = int(context.args[0])
        if amount < MIN_DEPOSIT:
            await update.message.reply_text(f"⚠️ **Minimum deposit is** `{MIN_DEPOSIT:,}` **Zeni**.", parse_mode="Markdown")
            return

        if amount > user.get("coins", 0):
            await update.message.reply_text("🚫 **You don't have enough Zeni!**", parse_mode="Markdown")
            return

        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -amount, "bank_balance": amount}}, upsert=True)
        await update.message.reply_text(
            f"✅ **Successfully Deposited:** `{amount:,}` **Zeni** 🏦\n"
            f"🔹 **New Wallet Balance:** `{user.get('coins', 0) - amount:,}`\n"
            f"🔹 **New Bank Balance:** `{user.get('bank_balance', 0) + amount:,}`",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ **Enter a valid number.**", parse_mode="Markdown")

# 🏦 **Withdraw Command**
async def withdraw(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = await user_collection.find_one({"id": user_id}) or {"bank_balance": 0, "coins": 0}

    if not context.args:
        await update.message.reply_text("❌ **Usage:** `/withdraw <amount>`", parse_mode="Markdown")
        return

    try:
        amount = int(context.args[0])
        max_withdraw = int(user.get("bank_balance", 0) * (MAX_WITHDRAW_PERCENT / 100))

        if amount > max_withdraw:
            await update.message.reply_text(
                f"⚠️ **You can only withdraw up to** `{max_withdraw:,}` **Zeni today.**",
                parse_mode="Markdown"
            )
            return

        if amount > user.get("bank_balance", 0):
            await update.message.reply_text("🚫 **You don't have enough balance!**", parse_mode="Markdown")
            return

        await user_collection.update_one({"id": user_id}, {"$inc": {"bank_balance": -amount, "coins": amount}}, upsert=True)
        await update.message.reply_text(
            f"✅ **Successfully Withdrawn:** `{amount:,}` **Zeni** 💰\n"
            f"🔹 **New Wallet Balance:** `{user.get('coins', 0) + amount:,}`\n"
            f"🔹 **New Bank Balance:** `{user.get('bank_balance', 0) - amount:,}`",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ **Enter a valid number.**", parse_mode="Markdown")

# ✅ Handlers
application.add_handler(CommandHandler("bank", check_balance))
application.add_handler(CommandHandler("deposit", deposit))
application.add_handler(CommandHandler("withdraw", withdraw))
