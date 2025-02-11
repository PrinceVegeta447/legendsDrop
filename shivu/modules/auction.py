import asyncio
import time
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, collection, OWNER_ID, auction_collection

# ✅ Auction Duration (Seconds)
AUCTION_DURATION = 600  # 10 minutes
MIN_BID_INCREMENT = 200  # Minimum bid increment in CC

# ✅ Start an Auction (Only Owners)
async def start_auction(update: Update, context: CallbackContext) -> None:
    """Allows owners to start an auction in the designated channel."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only the bot owner can start an auction!")
        return

    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ **Usage:** `/auction <character_id> <starting_bid> <channel_id>`\n"
            "📌 Example: `/auction 027 500 -1001234567890`",
            parse_mode="Markdown"
        )
        return

    character_id, starting_bid, channel_id = context.args

    try:
        starting_bid = int(starting_bid)
    except ValueError:
        await update.message.reply_text("❌ **Invalid starting bid!** It must be a number.", parse_mode="Markdown")
        return

    # ✅ Fetch character details
    character = await collection.find_one({"id": character_id})
    if not character:
        await update.message.reply_text("❌ **Character not found!**", parse_mode="Markdown")
        return

    # ✅ Store auction details in database
    auction_data = {
        "character_id": character_id,
        "character": character,
        "starting_bid": starting_bid,
        "highest_bid": starting_bid,
        "highest_bidder": None,
        "end_time": time.time() + AUCTION_DURATION,
        "channel_id": channel_id,
        "status": "ongoing"
    }
    auction_doc = await auction_collection.insert_one(auction_data)

    # ✅ Send Auction Message in Channel
    auction_message = (
        f"⚔ <b>Auction Started!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎴 <b>Character:</b> {character['name']}\n"
        f"🎖 <b>Rarity:</b> {character.get('rarity', 'Unknown')}\n"
        f"💰 <b>Starting Bid:</b> {starting_bid} CC\n"
        f"📌 <b>Duration:</b> 10 minutes\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 <b>Bid using the buttons below!</b>"
    )

    keyboard = [
        [InlineKeyboardButton("💎 Bid +200 CC", callback_data=f"bid:{auction_doc.inserted_id}:200")],
        [InlineKeyboardButton("💰 Bid +500 CC", callback_data=f"bid:{auction_doc.inserted_id}:500")]
    ]

    message = await context.bot.send_photo(
        chat_id=channel_id,
        photo=character.get("file_id", None) or character.get("img_url", None),
        caption=auction_message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # ✅ Store message ID for auction tracking
    await auction_collection.update_one(
        {"_id": auction_doc.inserted_id},
        {"$set": {"message_id": message.message_id}}
    )

    await update.message.reply_text("✅ **Auction started in the channel!**")

    # ✅ Schedule auction ending
    await asyncio.sleep(AUCTION_DURATION)
    await end_auction(auction_doc.inserted_id, context)

# ✅ Handle Bids
async def handle_bid(update: Update, context: CallbackContext) -> None:
    """Processes user bids in the auction."""
    query = update.callback_query
    _, auction_id, bid_increment = query.data.split(":")
    bid_increment = int(bid_increment)
    user_id = query.from_user.id

    # ✅ Fetch auction details
    auction = await auction_collection.find_one({"_id": ObjectId(auction_id), "status": "ongoing"})
    if not auction:
        await query.answer("❌ Auction has ended!", show_alert=True)
        return

    # ✅ Ensure bid is higher than current highest bid
    highest_bid = auction["highest_bid"]
    new_bid = highest_bid + bid_increment

    # ✅ Fetch user details
    user = await user_collection.find_one({"id": user_id})
    if not user:
        await query.answer("❌ You need to participate in the bot first!", show_alert=True)
        return

    user_cc = int(user.get("chrono_crystals", 0))

    # ✅ Check if user has enough CC
    if user_cc < new_bid:
        await query.answer(f"❌ Not enough CC! You need {new_bid}, but you have {user_cc}.", show_alert=True)
        return

    # ✅ Update auction with new highest bid
    await auction_collection.update_one(
        {"_id": ObjectId(auction_id)},
        {"$set": {"highest_bid": new_bid, "highest_bidder": user_id}}
    )

    # ✅ Edit auction message
    auction_message = (
        f"⚔ <b>Auction Ongoing!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎴 <b>Character:</b> {auction['character']['name']}\n"
        f"🎖 <b>Rarity:</b> {auction['character'].get('rarity', 'Unknown')}\n"
        f"💰 <b>Highest Bid:</b> {new_bid} CC\n"
        f"👤 <b>Highest Bidder:</b> @{query.from_user.username if query.from_user.username else 'Unknown'}\n"
        f"📌 <b>Auction ends soon!</b>"
    )

    keyboard = [
        [InlineKeyboardButton("💎 Bid +200 CC", callback_data=f"bid:{auction_id}:200")],
        [InlineKeyboardButton("💰 Bid +500 CC", callback_data=f"bid:{auction_id}:500")]
    ]

    await context.bot.edit_message_caption(
        chat_id=auction["channel_id"],
        message_id=auction["message_id"],
        caption=auction_message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await query.answer(f"✅ You bid {new_bid} CC!")

# ✅ End Auction
async def end_auction(auction_id, context: CallbackContext) -> None:
    """Ends the auction and gives the character to the highest bidder."""
    auction = await auction_collection.find_one({"_id": ObjectId(auction_id)})
    if not auction or auction["status"] != "ongoing":
        return

    highest_bidder = auction["highest_bidder"]
    highest_bid = auction["highest_bid"]
    character = auction["character"]

    # ✅ Update auction status
    await auction_collection.update_one({"_id": ObjectId(auction_id)}, {"$set": {"status": "ended"}})

    auction_message = f"❌ **Auction Ended! No bids were placed.**" if not highest_bidder else (
        f"🏆 **Auction Ended!**\n"
        f"🎴 **Winner:** <a href='tg://user?id={highest_bidder}'>User {highest_bidder}</a>\n"
        f"💰 **Winning Bid:** {highest_bid} CC\n"
        f"🎖 **Character:** {character['name']}\n"
        f"📌 **Congratulations to the winner!**"
    )

    await context.bot.edit_message_caption(chat_id=auction["channel_id"], message_id=auction["message_id"], caption=auction_message, parse_mode="HTML")

# ✅ Register Handlers
application.add_handler(CommandHandler("auction", start_auction, block=False))
application.add_handler(CallbackQueryHandler(handle_bid, pattern="^bid:", block=False))
