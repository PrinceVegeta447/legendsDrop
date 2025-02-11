import random, time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
from shivu import user_collection, battle_collection

MAX_HP = 100  # Each character starts with 100 HP

async def make_team(update, context):
    """Allows users to select 3 characters from their collection"""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id})
    
    if not user or "characters" not in user or len(user["characters"]) < 3:
        await update.message.reply_text("❌ You need at least **3 characters** in your collection to form a team!")
        return

    keyboard = []
    for char in user["characters"]:
        keyboard.append([InlineKeyboardButton(char["name"], callback_data=f"select_team:{char['name']}")])

    await update.message.reply_text("🔹 **Select your team (Choose 3 characters):**", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def select_team(update, context):
    """Handles user selection for team formation"""
    query = update.callback_query
    user_id = query.from_user.id
    char_name = query.data.split(":")[1]

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return

    existing_team = await battle_collection.find_one({"user_id": user_id})
    if not existing_team:
        await battle_collection.insert_one({"user_id": user_id, "team": [char_name]})
    else:
        if len(existing_team["team"]) >= 3:
            await query.answer("❌ You can only select **3 characters** in your team!", show_alert=True)
            return

        await battle_collection.update_one({"user_id": user_id}, {"$push": {"team": char_name}})

    updated_team = await battle_collection.find_one({"user_id": user_id})
    await query.answer(f"✅ {char_name} added to your team!")

    if len(updated_team["team"]) == 3:
        await query.edit_message_text(f"✅ **Your team is ready!**\n\n**Team Members:**\n" + 
                                      "\n".join(f"➤ {char}" for char in updated_team["team"]))
    else:
        remaining = 3 - len(updated_team["team"])
        await query.edit_message_text(f"🔹 **Selected:** {char_name}\n\n✅ Choose **{remaining} more**!")

async def battle(update, context):
    """Starts a PvP battle"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/battle @username`")
        return
    
    opponent = update.message.mention_entities
    if not opponent:
        await update.message.reply_text("❌ **Mention a valid opponent!**")
        return

    user_id = update.effective_user.id
    opponent_id = list(opponent.keys())[0]

    user_team = await battle_collection.find_one({"user_id": user_id})
    opponent_team = await battle_collection.find_one({"user_id": opponent_id})

    if not user_team or len(user_team["team"]) < 3:
        await update.message.reply_text("❌ **You must have a 3-character team to battle!** Use `/maketeam`.")
        return

    if not opponent_team or len(opponent_team["team"]) < 3:
        await update.message.reply_text("❌ **Your opponent has not set a team!** Ask them to use `/maketeam`.")
        return

    battle_id = f"{user_id}_{opponent_id}_{int(time.time())}"

    battle_data = {
        "battle_id": battle_id,
        "player1": {"id": user_id, "team": user_team["team"], "hp": [MAX_HP, MAX_HP, MAX_HP]},
        "player2": {"id": opponent_id, "team": opponent_team["team"], "hp": [MAX_HP, MAX_HP, MAX_HP]},
        "turn": user_id,  # Player 1 starts
    }

    await battle_collection.insert_one(battle_data)

    keyboard = [[InlineKeyboardButton("⚔️ Attack", callback_data=f"attack:{battle_id}")]]
    await update.message.reply_text(f"🔥 **PvP Battle Started!** 🔥\n\n🎴 **{update.effective_user.first_name}** vs **{context.bot.get_chat(opponent_id).first_name}**\n\n⚔️ **Turn:** {update.effective_user.first_name}",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def attack(update, context):
    """Handles attack action"""
    query = update.callback_query
    user_id = query.from_user.id
    battle_id = query.data.split(":")[1]

    battle = await battle_collection.find_one({"battle_id": battle_id})
    if not battle:
        await query.answer("❌ Battle not found!", show_alert=True)
        return

    if battle["turn"] != user_id:
        await query.answer("❌ It's not your turn!", show_alert=True)
        return

    opponent_id = battle["player2"]["id"] if battle["player1"]["id"] == user_id else battle["player1"]["id"]
    opponent_hp = battle["player2"]["hp"] if battle["player1"]["id"] == user_id else battle["player1"]["hp"]
    
    damage = random.randint(15, 30)
    opponent_hp[0] -= damage

    if opponent_hp[0] <= 0:
        opponent_hp.pop(0)
    
    if len(opponent_hp) == 0:
        await battle_collection.delete_one({"battle_id": battle_id})
        await query.message.edit_text(f"🏆 **{update.effective_user.first_name} Wins!** 🏆")
        return

    next_turn = opponent_id
    await battle_collection.update_one({"battle_id": battle_id}, {"$set": {"turn": next_turn}})
    
    keyboard = [[InlineKeyboardButton("⚔️ Attack", callback_data=f"attack:{battle_id}")]]
    await query.message.edit_text(f"⚔️ **Turn:** {context.bot.get_chat(next_turn).first_name}\n💥 **Damage Dealt:** {damage}",
                                  reply_markup=InlineKeyboardMarkup(keyboard))

# Register Handlers
application.add_handler(CommandHandler("maketeam", make_team, block=False))
application.add_handler(CommandHandler("battle", battle, block=False))
application.add_handler(CallbackQueryHandler(select_team, pattern="^select_team:", block=False))
application.add_handler(CallbackQueryHandler(attack, pattern="^attack:", block=False))
