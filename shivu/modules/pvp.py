import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, collection, battle_collection, OWNER_ID

BATTLE_TIMEOUT = 120  # 2 minutes per turn

# ✅ **Team Selection**
async def maketeam(update: Update, context: CallbackContext) -> None:
    """Allows users to select a 3-character team before battle."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id})

    if not user or "characters" not in user or len(user["characters"]) < 3:
        await update.message.reply_text("❌ You need at least 3 characters in your collection to make a team!")
        return

    character_list = "\n".join([f"{char['id']} - {char['name']} ({char['rarity']})" for char in user["characters"]])
    await update.message.reply_text(
        f"🔹 **Your Collection:**\n{character_list}\n\n"
        "🛡 Choose 3 characters for battle using:\n"
        "`/maketeam <id1> <id2> <id3>`",
        parse_mode="Markdown"
    )

    if len(context.args) != 3:
        return

    team = [char for char in user["characters"] if char["id"] in context.args]
    if len(team) != 3:
        await update.message.reply_text("❌ Invalid selection! Make sure all 3 IDs are from your collection.")
        return

    await user_collection.update_one({"id": user_id}, {"$set": {"battle_team": team}})
    await update.message.reply_text("✅ Team selected successfully! Use `/challenge @username` to start a battle.")

# ✅ **Challenge a Player**
async def challenge(update: Update, context: CallbackContext) -> None:
    """Allows users to challenge others to a PvP battle."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id})
    
    if not user or "battle_team" not in user or len(user["battle_team"]) != 3:
        await update.message.reply_text("❌ You need to select a team first! Use `/maketeam`.")
        return

    if len(context.args) != 1 or not context.args[0].startswith("@"):
        await update.message.reply_text("❌ Usage: `/challenge @username`")
        return

    opponent_username = context.args[0][1:]
    opponent = await user_collection.find_one({"username": opponent_username})

    if not opponent:
        await update.message.reply_text("❌ Opponent not found or they haven't played yet.")
        return

    if "battle_team" not in opponent or len(opponent["battle_team"]) != 3:
        await update.message.reply_text("❌ Your opponent hasn't selected a team yet!")
        return

    battle_id = f"{user_id}_{opponent['id']}_{random.randint(1000, 9999)}"
    
    # ✅ Create battle entry
    battle_data = {
        "battle_id": battle_id,
        "players": {str(user_id): user, str(opponent["id"]): opponent},
        "turn": user_id,
        "status": "ongoing",
        "actions": [],
    }
    await battle_collection.insert_one(battle_data)

    keyboard = [[InlineKeyboardButton("✅ Accept Challenge", callback_data=f"accept:{battle_id}")]]
    await update.message.reply_text(
        f"⚔️ **Battle Challenge!**\n\n"
        f"👑 **{update.effective_user.first_name}** challenges **{opponent['username']}** to a 3v3 battle!\n"
        "🔹 Opponent, click below to accept:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ✅ **Accept Challenge**
async def accept_challenge(update: Update, context: CallbackContext) -> None:
    """Handles challenge acceptance."""
    query = update.callback_query
    _, battle_id = query.data.split(":")
    battle = await battle_collection.find_one({"battle_id": battle_id, "status": "ongoing"})

    if not battle:
        await query.answer("❌ Battle not found or already started!", show_alert=True)
        return

    players = list(battle["players"].keys())
    if str(query.from_user.id) not in players:
        await query.answer("❌ You are not part of this battle!", show_alert=True)
        return

    await query.message.edit_text("⚔️ **Battle Started!** Turns will be taken automatically.")

    await start_battle(battle_id, context)

# ✅ **Start Battle**
async def start_battle(battle_id, context: CallbackContext):
    """Initiates the battle sequence."""
    battle = await battle_collection.find_one({"battle_id": battle_id, "status": "ongoing"})
    if not battle:
        return

    turn = battle["turn"]
    await send_turn_prompt(battle_id, turn, context)

# ✅ **Send Turn Prompt**
async def send_turn_prompt(battle_id, player_id, context: CallbackContext):
    """Sends turn options to the active player."""
    battle = await battle_collection.find_one({"battle_id": battle_id, "status": "ongoing"})
    if not battle:
        return

    keyboard = [
        [InlineKeyboardButton("⚔ Attack", callback_data=f"attack:{battle_id}"),
         InlineKeyboardButton("🛡 Defend", callback_data=f"defend:{battle_id}")],
        [InlineKeyboardButton("🔥 Special Move", callback_data=f"special:{battle_id}"),
         InlineKeyboardButton("🔄 Swap", callback_data=f"swap:{battle_id}")]
    ]
    player = battle["players"][str(player_id)]

    await context.bot.send_message(
        chat_id=player["id"],
        text=f"🎮 **Your Turn!**\n\n"
        f"🆚 **Battle:** {battle_id}\n"
        "Choose an action:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ✅ **Handle Actions**
async def handle_action(update: Update, context: CallbackContext) -> None:
    """Handles attack, defend, swap, and special moves."""
    query = update.callback_query
    action, battle_id = query.data.split(":")

    battle = await battle_collection.find_one({"battle_id": battle_id, "status": "ongoing"})
    if not battle:
        await query.answer("❌ Battle ended!", show_alert=True)
        return

    turn_player = battle["turn"]
    if query.from_user.id != turn_player:
        await query.answer("❌ Not your turn!", show_alert=True)
        return

    # Simulate action effects (for now, just random)
    damage = random.randint(10, 30)
    next_turn = next(iter(battle["players"].keys())) if str(turn_player) != next(iter(battle["players"].keys())) else next(iter(battle["players"].values()))

    await battle_collection.update_one({"battle_id": battle_id}, {"$set": {"turn": int(next_turn)}})

    await query.message.edit_text(f"✅ {query.from_user.first_name} used {action.upper()}! ({damage} Damage)")

    # Next turn
    await asyncio.sleep(2)
    await send_turn_prompt(battle_id, next_turn, context)

# ✅ **Register Handlers**
application.add_handler(CommandHandler("maketeam", maketeam, block=False))
application.add_handler(CommandHandler("challenge", challenge, block=False))
application.add_handler(CallbackQueryHandler(accept_challenge, pattern="^accept:", block=False))
application.add_handler(CallbackQueryHandler(handle_action, pattern="^(attack|defend|special|swap):", block=False))
