from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shivu import user_collection, shivuu
import asyncio

INTEREST_RATE = 0.02  # 2% daily interest
MIN_DEPOSIT = 500  # Minimum Zeni to deposit
MIN_WITHDRAW = 500  # Minimum Zeni to withdraw
BANK_INTEREST_INTERVAL = 86400  # 24 hours

async def apply_interest():
    while True:
        users = await user_collection.find({"bank_balance": {"$gt": 0}}).to_list(length=1000)
        for user in users:
            interest = int(user["bank_balance"] * INTEREST_RATE)
            await user_collection.update_one(
                {"id": user["id"]}, {"$inc": {"bank_balance": interest}}
            )
        await asyncio.sleep(BANK_INTEREST_INTERVAL)

asyncio.create_task(apply_interest())

@shivuu.on_message(filters.command("bank"))
async def bank_menu(client, message):
    user = await user_collection.find_one({"id": message.from_user.id})
    if not user:
        await message.reply_text("❌ You don’t have an account. Use /openbank to create one.")
        return

    wallet = user.get("coins", 0)
    bank = user.get("bank_balance", 0)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Deposit", callback_data="bank_deposit"),
         InlineKeyboardButton("🏧 Withdraw", callback_data="bank_withdraw")],
        [InlineKeyboardButton("🔄 Transfer", callback_data="bank_transfer")],
    ])

    await message.reply_text(
        f"🏦 **Bank Account**\n"
        f"💵 Wallet: {wallet} Zeni\n"
        f"💳 Bank Balance: {bank} Zeni\n\n"
        f"💲 **Earn 2% daily interest on bank deposits!**",
        reply_markup=keyboard
    )

@shivuu.on_message(filters.command("openbank"))
async def open_bank(client, message):
    user = await user_collection.find_one({"id": message.from_user.id})
    if user and "bank_balance" in user:
        await message.reply_text("✅ You already have a bank account.")
        return

    await user_collection.update_one(
        {"id": message.from_user.id}, 
        {"$set": {"bank_balance": 0}}, 
        upsert=True
    )

    await message.reply_text("🏦 **Bank account created successfully!**\nUse /bank to manage your Zeni.")

@shivuu.on_callback_query(filters.regex("bank_deposit"))
async def deposit_prompt(client, callback_query):
    await callback_query.message.edit_text("💰 Enter the amount you want to deposit:")

    def check(msg):
        return msg.from_user.id == callback_query.from_user.id and msg.text.isdigit()

    response = await client.listen(callback_query.message.chat.id, filters=check, timeout=30)
    amount = int(response.text)

    user = await user_collection.find_one({"id": callback_query.from_user.id})
    if amount < MIN_DEPOSIT or amount > user.get("coins", 0):
        await callback_query.message.reply_text("❌ Invalid amount.")
        return

    await user_collection.update_one(
        {"id": user["id"]}, 
        {"$inc": {"coins": -amount, "bank_balance": amount}}
    )

    await callback_query.message.reply_text(f"✅ Deposited {amount} Zeni to your bank!")

@shivuu.on_callback_query(filters.regex("bank_withdraw"))
async def withdraw_prompt(client, callback_query):
    await callback_query.message.edit_text("🏧 Enter the amount you want to withdraw:")

    def check(msg):
        return msg.from_user.id == callback_query.from_user.id and msg.text.isdigit()

    response = await client.listen(callback_query.message.chat.id, filters=check, timeout=30)
    amount = int(response.text)

    user = await user_collection.find_one({"id": callback_query.from_user.id})
    if amount < MIN_WITHDRAW or amount > user.get("bank_balance", 0):
        await callback_query.message.reply_text("❌ Invalid amount.")
        return

    await user_collection.update_one(
        {"id": user["id"]}, 
        {"$inc": {"coins": amount, "bank_balance": -amount}}
    )

    await callback_query.message.reply_text(f"✅ Withdrawn {amount} Zeni from your bank!")

@shivuu.on_callback_query(filters.regex("bank_transfer"))
async def transfer_prompt(client, callback_query):
    await callback_query.message.edit_text("🔄 Reply to a user and enter the amount to transfer.")

    def check(msg):
        return msg.reply_to_message and msg.from_user.id == callback_query.from_user.id and msg.text.isdigit()

    response = await client.listen(callback_query.message.chat.id, filters=check, timeout=30)
    amount = int(response.text)
    receiver_id = response.reply_to_message.from_user.id

    sender = await user_collection.find_one({"id": callback_query.from_user.id})
    receiver = await user_collection.find_one({"id": receiver_id})

    if not receiver:
        await callback_query.message.reply_text("❌ User does not have a bank account.")
        return
    if amount < 1 or amount > sender.get("bank_balance", 0):
        await callback_query.message.reply_text("❌ Invalid amount.")
        return

    await user_collection.update_one(
        {"id": sender["id"]}, {"$inc": {"bank_balance": -amount}}
    )
    await user_collection.update_one(
        {"id": receiver["id"]}, {"$inc": {"bank_balance": amount}}
    )

    await callback_query.message.reply_text(
        f"✅ Transferred {amount} Zeni to {response.reply_to_message.from_user.mention}!"
    )
