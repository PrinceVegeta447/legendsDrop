import asyncio
import time
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, collection, OWNER_ID, auction_collection

# ✅ Auction Duration & Settings
AUCTION_DURATION = 600  # 10 minutes
MIN_BID_INCREMENT = 200  # Minimum bid increment in CC

async def start_auction(update: Update, context: CallbackContext) -> None:
    """Allows owners to start an auction in the designated channel."""
    if update.effective_user.id != int(OWNER_ID):
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

    # ✅ Check if an auction is already running
    active_auction = await auction_collection.find_one({"status": "ongoing"})
    if active_auction:
        await update.message.reply_text("❌ **An auction is already active!** Please wait for it to end.")
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
        "highest_bidder_name": "No Bids Yet",
        "end_time": time.time() + AUCTION_DURATION,
        "channel_id": channel_id,
        "message_id": None,
        "status": "ongoing"
    }
    auction_doc = await auction_collection.insert_one(auction_data)

    # ✅ Send Auction Message in Channel
    keyboard = [
        [InlineKeyboardButton("💎 Bid +200 CC", callback_data=f"bid:{auction_doc.inserted_id}:200")],
        [InlineKeyboardButton("💰 Bid +500 CC", callback_data=f"bid:{auction_doc.inserted_id}:500")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await context.bot.send_photo(
        chat_id=channel_id,
        photo=character.get("file_id", None) or character.get("img_url", None),
        caption=(
            f"⚔ 𝘼𝙪𝙘𝙩𝙞𝙤𝙣 𝙎𝙩𝙖𝙧𝙩𝙚𝙙!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎴 𝘾𝙝𝙖𝙧𝙖𝙘𝙩𝙚𝙧: {character['name']}\n"
            f"🎖 𝙍𝙖𝙧𝙞𝙩𝙮: {character.get('rarity', 'Unknown')}\n"
            f"💰 𝙎𝙩𝙖𝙧𝙩𝙞𝙣𝙜 𝘽𝙞𝙙: {starting_bid} CC\n"
            f"👤 𝙃𝙞𝙜𝙝𝙚𝙨𝙩 𝘽𝙞𝙙𝙙𝙚𝙧: {auction_data['highest_bidder_name']}\n"
            f"📌 𝘿𝙪𝙧𝙖𝙩𝙞𝙤𝙣: 10 minutes\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 𝘽𝙞𝙙 𝙪𝙨𝙞𝙣𝙜 𝙩𝙝𝙚 𝙗𝙪𝙩𝙩𝙤𝙣𝙨 𝙗𝙚𝙡𝙤𝙬!"
        ),
        parse_mode="HTML",
        reply_markup=reply_markup
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


async def handle_bid(update: Update, context: CallbackContext) -> None:
    """Processes user bids in the auction."""
    query = update.callback_query
    _, auction_id, bid_increment = query.data.split(":")
    bid_increment = int(bid_increment)
    user_id = query.from_user.id
    user_first_name = query.from_user.first_name

    # ✅ Fetch auction details
    auction = await auction_collection.find_one({"_id": ObjectId(auction_id), "status": "ongoing"})
    if not auction:
        await query.answer("❌ Auction has ended!", show_alert=True)
        return

    # ✅ Prevent self-bidding if already highest bidder
    if auction["highest_bidder"] == user_id:
        await query.answer("⚠ You are already the highest bidder!", show_alert=True)
        return

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
        {"$set": {"highest_bid": new_bid, "highest_bidder": user_id, "highest_bidder_name": user_first_name}}
    )

    # ✅ Edit auction message without losing inline buttons
    keyboard = [
        [InlineKeyboardButton("💎 Bid +200 CC", callback_data=f"bid:{auction_id}:200")],
        [InlineKeyboardButton("💰 Bid +500 CC", callback_data=f"bid:{auction_id}:500")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_caption(
        caption=(
            f"⚔ 𝗔𝘂𝗰𝘁𝗶𝗼𝗻 𝗢𝗻𝗴𝗼𝗶𝗻𝗴!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎴 <b>Character:</b> {auction['character']['name']}\n"
            f"🎖 <b>Rarity:</b> {auction['character'].get('rarity', 'Unknown')}\n"
            f"💰 <b>Highest Bid:</b> {new_bid} CC\n"
            f"👤 <b>Highest Bidder:</b> {user_first_name}\n"
            f"📌 <b>Auction Ending Soon!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 <b>Bid using the buttons below!</b>"
        ),
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    await query.answer(f"✅ You bid {new_bid} CC!")


async def end_auction(auction_id, context: CallbackContext) -> None:
    """Ends the auction and gives the character to the highest bidder."""
    auction = await auction_collection.find_one({"_id": ObjectId(auction_id)})
    if not auction or auction["status"] != "ongoing":
        return

    highest_bidder = auction["highest_bidder"]
    highest_bid = auction["highest_bid"]
    character = auction["character"]

    await auction_collection.update_one({"_id": ObjectId(auction_id)}, {"$set": {"status": "ended"}})

    if highest_bidder:
        await user_collection.update_one(
            {"id": highest_bidder},
            {"$inc": {"chrono_crystals": -highest_bid}, "$push": {"characters": character}}
        )
        
        try:
            await context.bot.send_message(
                chat_id=highest_bidder,
                text=f"🏆 Congratulations {auction['highest_bidder_name']}! You won {character['name']} for {highest_bid} CC!",
                parse_mode="HTML"
            )
        except Exception:
            pass  

# ✅ Register Handlers
application.add_handler(CommandHandler("auction", start_auction, block=False))
application.add_handler(CallbackQueryHandler(handle_bid, pattern="^bid:", block=False))
