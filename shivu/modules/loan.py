from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, OWNER_ID, LOAN_CHANNEL_ID
from datetime import datetime, timedelta

LOAN_PLANS = {
    "basic": {"max_amount": 50000, "max_cc": 200, "interest": 10, "duration": 7, "required_score": 0},
    "enhanced": {"max_amount": 150000, "max_cc": 600, "interest": 7, "duration": 14, "required_score": 200},
    "premium": {"max_amount": 300000, "max_cc": 1200, "interest": 5, "duration": 21, "required_score": 800},
}

async def view_loan_plans(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({"user_id": user_id}) or {}
    credit_score = user_data.get("credit_score", 0)

    buttons = []
    text = "**💰 Available Loan Plans:**\n\n"
    
    for plan, details in LOAN_PLANS.items():
        status = "✅ Available" if credit_score >= details["required_score"] else "❌ Locked"
        buttons.append([InlineKeyboardButton(f"{plan.capitalize()} - {status}", callback_data=f"select_plan:{plan}")])
        text += (
            f"🏷 **{plan.capitalize()} Plan**\n"
            f"💵 Max Loan: {details['max_amount']} Zeni / {details['max_cc']} CC\n"
            f"💳 Interest: {details['interest']}%\n"
            f"📅 Duration: {details['duration']} days\n"
            f"⭐ Required Score: {details['required_score']}\n\n"
        )

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def select_loan_plan(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, plan = query.data.split(":")
    user_id = query.from_user.id

    user_data = await user_collection.find_one({"user_id": user_id}) or {}
    credit_score = user_data.get("credit_score", 0)
    plan_details = LOAN_PLANS.get(plan)

    if not plan_details:
        await query.answer("Invalid plan!", show_alert=True)
        return

    if credit_score < plan_details["required_score"]:
        await query.answer("❌ You don't have enough credit score to choose this plan!", show_alert=True)
        return

    await user_collection.update_one({"user_id": user_id}, {"$set": {"selected_loan_plan": plan}}, upsert=True)
    await query.answer(f"✅ {plan.capitalize()} plan selected!", show_alert=True)
    await query.message.edit_text(f"✅ You have selected the **{plan.capitalize()}** loan plan.")

application.add_handler(CommandHandler("loanplans", view_loan_plans, block=False))
application.add_handler(CallbackQueryHandler(select_loan_plan, pattern="^select_plan:", block=False))


async def request_loan(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    args = context.args

    # Validate input
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

    # Check if user selected a loan plan
    user_data = await user_collection.find_one({"user_id": user_id}) or {}
    selected_plan = user_data.get("selected_loan_plan")

    if not selected_plan:
        await update.message.reply_text("❌ You haven't selected a loan plan! Use `/loanplans` first.")
        return

    plan_details = LOAN_PLANS[selected_plan]
    max_amount = plan_details["max_amount"] if currency == "zeni" else plan_details["max_cc"]

    if amount > max_amount:
        await update.message.reply_text(f"❌ Max loan for {selected_plan.capitalize()} is {max_amount} {currency.capitalize()}!")
        return

    existing_loan = await user_collection.find_one({"user_id": user_id, "loan.status": "pending"})
    if existing_loan:
        await update.message.reply_text("❌ You already have a pending loan request!")
        return

    # Loan details
    due_date = datetime.utcnow() + timedelta(days=plan_details["duration"])
    interest = int(amount * (plan_details["interest"] / 100))
    total_repay = amount + interest

    loan_data = {
        "user_id": user_id,
        "amount": amount,
        "currency": currency,
        "reason": reason,
        "status": "pending",
        "approved_by": None,
        "due_date": due_date,
        "loan_plan": selected_plan.capitalize(),
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

    if query.from_user.id != OWNER_ID:
        await query.answer("❌ Only the bot owner can approve loans!", show_alert=True)
        return

    loan = await user_collection.find_one({"user_id": user_id, "loan.status": "pending"})
    if not loan:
        await query.answer("❌ Loan request not found!", show_alert=True)
        return

    # Add loan to user's account
    amount = loan["loan"]["amount"]
    currency = loan["loan"]["currency"]
    
    if currency == "zeni":
        await user_collection.update_one({"user_id": user_id}, {"$inc": {"coins": amount}})
    else:
        await user_collection.update_one({"user_id": user_id}, {"$inc": {"chrono_crystals": amount}})
    
    await user_collection.update_one({"user_id": user_id}, {"$set": {"loan.status": "approved", "loan.approved_by": query.from_user.id}})

    await context.bot.send_message(user_id, "✅ Your loan has been **approved**! Repay before the due date.")
    await query.message.edit_text(f"✅ Loan for user {user_id} has been **approved**!")

async def reject_loan(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, user_id = query.data.split(":")
    user_id = int(user_id)

    if query.from_user.id != OWNER_ID:
        await query.answer("❌ Only the bot owner can reject loans!", show_alert=True)
        return

    await user_collection.update_one({"user_id": user_id}, {"$unset": {"loan": ""}})
    
    await context.bot.send_message(user_id, "❌ Your loan request has been **rejected**.")
    await query.message.edit_text(f"❌ Loan for user {user_id} has been **rejected**!")

application.add_handler(CallbackQueryHandler(approve_loan, pattern="^approve_loan:", block=False))
application.add_handler(CallbackQueryHandler(reject_loan, pattern="^reject_loan:", block=False))

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

    if currency not in ["zeni", "cc"]:
        await update.message.reply_text("❌ Invalid currency! Use `Zeni` or `CC`.", parse_mode="Markdown")
        return

    # Check if user has an active loan
    user_data = await user_collection.find_one({"user_id": user_id}) or {}
    loan = user_data.get("loan")

    if not loan or loan["status"] != "approved":
        await update.message.reply_text("❌ You don't have an active loan.")
        return

    if currency != loan["currency"]:
        await update.message.reply_text(f"❌ You must repay in {loan['currency'].capitalize()}!")
        return

    total_repay = loan["total_repay"]
    due_date = loan["due_date"]

    if amount < total_repay:
        await update.message.reply_text(f"❌ You must repay **{total_repay} {currency.capitalize()}**.")
        return

    # Deduct amount from user balance
    if currency == "zeni":
        if user_data.get("coins", 0) < amount:
            await update.message.reply_text("❌ You don't have enough Zeni!")
            return
        await user_collection.update_one({"user_id": user_id}, {"$inc": {"coins": -amount}})
    else:
        if user_data.get("cc", 0) < amount:
            await update.message.reply_text("❌ You don't have enough Chrono Crystals!")
            return
        await user_collection.update_one({"user_id": user_id}, {"$inc": {"chrono_crystals": -amount}})

    # Check if repaid on time
    if datetime.utcnow() <= due_date:
        credit_score_increase = 5
        await update.message.reply_text(f"✅ Loan repaid successfully! Your credit score increased by {credit_score_increase} points.")
        await user_collection.update_one({"user_id": user_id}, {"$inc": {"credit_score": credit_score_increase}})
    else:
        await update.message.reply_text("✅ Loan repaid successfully!")

    # Remove loan data
    await user_collection.update_one({"user_id": user_id}, {"$unset": {"loan": ""}})

application.add_handler(CommandHandler("repay", repay_loan, block=False))
