from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from datetime import datetime, timedelta
from shivu import application, user_collection, OWNER_ID, LOAN_CHANNEL_ID

LOAN_PLANS = {
    "basic": {"duration": 7, "interest": 5},  # 5% interest, 7 days
    "premium": {"duration": 14, "interest": 3},  # 3% interest, 14 days
}

async def request_loan(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 3:
        await update.message.reply_text("❌ Usage: `/loan <amount> <currency> <reason>`", parse_mode="Markdown")
        return

    try:
        amount = int(args[0])
        currency = args[1].lower()
        reason = " ".join(args[2:])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount!", parse_mode="Markdown")
        return

    if currency not in ["zeni", "cc"]:
        await update.message.reply_text("❌ Invalid currency! Use `Zeni` or `CC`.", parse_mode="Markdown")
        return

    existing_loan = await user_collection.find_one({"user_id": user_id, "loan.status": "pending"})
    if existing_loan:
        await update.message.reply_text("❌ You already have a pending loan request!")
        return

    plan = LOAN_PLANS["basic"]
    due_date = datetime.utcnow() + timedelta(days=plan["duration"])
    interest = int(amount * (plan["interest"] / 100))
    total_repay = amount + interest

    loan_data = {
        "user_id": user_id,
        "amount": amount,
        "currency": currency,
        "reason": reason,
        "status": "pending",
        "approved_by": None,
        "due_date": due_date,
        "loan_plan": "Basic 7-day Loan",
        "total_repay": total_repay
    }

    await user_collection.update_one({"user_id": user_id}, {"$set": {"loan": loan_data}}, upsert=True)

    # Notify the owner in the loan approval channel
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_loan:{user_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_loan:{user_id}")]
    ]
    
    message = (
        f"📌 **New Loan Request**\n"
        f"👤 User: {update.effective_user.first_name}\n"
        f"💰 Amount: {amount} {currency.capitalize()}\n"
        f"📝 Reason: {reason}\n"
        f"📅 Due Date: {due_date.strftime('%Y-%m-%d')}\n"
        f"💸 Total Repay: {total_repay} {currency.capitalize()}"
    )

    await context.bot.send_message(LOAN_CHANNEL_ID, message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    await update.message.reply_text("📨 Your loan request has been sent for approval!")

application.add_handler(CommandHandler("loan", request_loan, block=False))

async def approve_loan(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, user_id = query.data.split(":")
    user_id = int(user_id)

    loan = await user_collection.find_one({"user_id": user_id, "loan.status": "pending"})
    if not loan:
        await query.answer("❌ Loan request not found!", show_alert=True)
        return

    await user_collection.update_one({"user_id": user_id}, {"$set": {"loan.status": "approved", "loan.approved_by": query.from_user.id}})
    
    await context.bot.send_message(user_id, "✅ Your loan has been **approved**! Repay before the due date.")
    await query.message.edit_text(f"✅ Loan for user {user_id} has been **approved**!")

application.add_handler(CallbackQueryHandler(approve_loan, pattern="^approve_loan:", block=False))

async def repay_loan(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("❌ Usage: `/repay <amount> <currency>`", parse_mode="Markdown")
        return

    try:
        amount = int(args[0])
        currency = args[1].lower()
    except ValueError:
        await update.message.reply_text("❌ Invalid amount!", parse_mode="Markdown")
        return

    loan = await user_collection.find_one({"user_id": user_id, "loan.status": "approved"})
    if not loan:
        await update.message.reply_text("❌ You don't have an active loan!")
        return

    loan_amount = loan["loan"]["total_repay"]
    remaining = loan_amount - amount

    if remaining <= 0:
        await user_collection.update_one({"user_id": user_id}, {"$unset": {"loan": ""}})
        await update.message.reply_text("🎉 Loan fully repaid!")
    else:
        await user_collection.update_one({"user_id": user_id}, {"$set": {"loan.total_repay": remaining}})
        await update.message.reply_text(f"✅ Partial payment received! Remaining: {remaining} {currency.capitalize()}")

application.add_handler(CommandHandler("repay", repay_loan, block=False))

async def check_loans():
    now = datetime.utcnow()
    overdue_loans = await user_collection.find({"loan.status": "approved", "loan.due_date": {"$lt": now}}).to_list(length=100)

    for user in overdue_loans:
        await user_collection.update_one({"user_id": user["user_id"]}, {"$set": {"account_frozen": True}})
        await context.bot.send_message(user["user_id"], "🚫 Your account has been frozen due to **loan default**!")

# Run daily in a background task
