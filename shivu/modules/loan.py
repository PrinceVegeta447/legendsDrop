from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from datetime import datetime, timedelta
from shivu import application, user_collection, OWNER_ID, LOAN_CHANNEL_ID

LOAN_PLANS = {
    "basic": {"duration": 7, "interest": 5},  # 5% interest, 7 days
    "premium": {"duration": 14, "interest": 3},  # 3% interest, 14 days
}

async def request_loan(update: Update, context: CallbackContext) -> None:
    """Handle loan requests."""
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

    existing_loan = await user_collection.find_one({"user_id": user_id, "loan.status": {"$in": ["pending", "approved"]}})
    if existing_loan:
        await update.message.reply_text("❌ You already have a loan in progress!")
        return

    plan = LOAN_PLANS["basic"]
    due_date = datetime.utcnow() + timedelta(days=plan["duration"])
    interest = int(amount * (plan["interest"] / 100))
    total_repay = amount + interest

    loan_data = {
        "status": "pending",
        "amount": amount,
        "currency": currency,
        "reason": reason,
        "approved_by": None,
        "due_date": due_date,
        "loan_plan": "Basic 7-day Loan",
        "total_repay": total_repay,
    }

    await user_collection.update_one({"user_id": user_id}, {"$set": {"loan": loan_data}}, upsert=True)

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
    """Approve a loan request and credit the user."""
    query = update.callback_query
    _, user_id = query.data.split(":")
    user_id = int(user_id)

    loan = await user_collection.find_one({"user_id": user_id, "loan.status": "pending"})
    if not loan:
        await query.answer("❌ Loan request not found!", show_alert=True)
        return

    amount = loan["loan"]["amount"]
    currency = loan["loan"]["currency"]

    # Update loan status and credit amount
    await user_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {"loan.status": "approved", "loan.approved_by": query.from_user.id},
            "$inc": {currency: amount},  # Add loan amount to balance
        }
    )

    # Notify the user
    await context.bot.send_message(user_id, f"✅ Your loan of {amount} {currency.capitalize()} has been **approved**! Repay before the due date.")

    # Update the admin message
    await query.message.edit_text(f"✅ Loan for user {user_id} has been **approved**!\n💰 {amount} {currency.capitalize()} added to their account.")

application.add_handler(CallbackQueryHandler(approve_loan, pattern="^approve_loan:", block=False))

async def repay_loan(update: Update, context: CallbackContext) -> None:
    """Handle loan repayment."""
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

    # Check user balance before deducting
    user_data = await user_collection.find_one({"user_id": user_id})
    if user_data.get(currency, 0) < amount:
        await update.message.reply_text(f"❌ Insufficient {currency.capitalize()} balance!")
        return

    remaining = loan_amount - amount

    if remaining <= 0:
        await user_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"loan": ""}, "$inc": {currency: -amount}}
        )
        await update.message.reply_text("🎉 Loan fully repaid!")
    else:
        await user_collection.update_one(
            {"user_id": user_id},
            {"$set": {"loan.total_repay": remaining}, "$inc": {currency: -amount}}
        )
        await update.message.reply_text(f"✅ Partial payment received! Remaining: {remaining} {currency.capitalize()}")

application.add_handler(CommandHandler("repay", repay_loan, block=False))

async def check_loans(context: CallbackContext):
    """Check overdue loans and freeze accounts if necessary."""
    now = datetime.utcnow()
    overdue_loans = await user_collection.find({"loan.status": "approved", "loan.due_date": {"$lt": now}}).to_list(length=100)

    for user in overdue_loans:
        user_id = user["user_id"]
        await user_collection.update_one({"user_id": user_id}, {"$set": {"account_frozen": True}})

        await context.bot.send_message(user_id, "🚫 Your account has been frozen due to **loan default**! Contact support to resolve.")

# Schedule to run daily
application.job_queue.run_daily(check_loans, time=datetime.time(hour=0, minute=0))
