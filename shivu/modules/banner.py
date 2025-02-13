from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, banners_collection, OWNER_ID, sudo_users
from bson import ObjectId
import shlex
  # First argument is command itself
# ✅ Create a New Banner
async def create_banner(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 <b>You don't have permission to create banners!</b>", parse_mode="HTML")
        return

    try:
        args = shlex.split(update.message.text)  # ✅ Corrected Indentation
        if len(args) != 3:
            await update.message.reply_text(
                "❌ <b>Usage:</b>\n<code>/createbanner &lt;name&gt; &lt;file_id&gt;</code>",
                parse_mode="HTML"
            )
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

        name, file_id = args
        banner = {"name": name, "file_id": file_id, "characters": []}
        banner_doc = await banners_collection.insert_one(banner)
        banner_id = str(banner_doc.inserted_id)

        keyboard = [[InlineKeyboardButton("📜 View Banners", callback_data="view_banners")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ <b>New Summon Banner Created!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟 <b>Banner Name:</b> <code>{name}</code>\n"
            f"🆔 <b>Banner ID:</b> <code>{banner_id}</code>\n\n"
            f"🔹 <b>Next Steps:</b>\n"
            f"➜ Use <code>/badd</code> to add characters.\n"
            f"➜ Use <code>/banners</code> to view all banners.\n\n"
            f"✨ <b>Good Luck Summoning!</b> 🎉",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"❌ <b>Error Creating Banner:</b> <code>{str(e)}</code>", parse_mode="HTML")


# ✅ List All Active Banners
async def view_banners(update: Update, context: CallbackContext) -> None:
    banners = await banners_collection.find({}).to_list(length=10)  # Limit to 10 banners

    if not banners:
        await update.message.reply_text("❌ <b>No active banners at the moment!</b>", parse_mode="HTML")
        return

    for banner in banners:
        keyboard = [[InlineKeyboardButton("🔄 Refresh List", callback_data="view_banners")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_photo(
            photo=banner["file_id"],
            caption=(
                f"🎟 <b>Summon Banner:</b> <code>{banner['name']}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 <b>Banner ID:</b> <code>{banner['_id']}</code>\n"
                f"📅 <b>Status:</b> 🟢 <i>Active</i>\n\n"
                f"🔹 <b>How to Summon?</b>\n"
                f"➜ Use <code>/bsummon {banner['_id']}</code> to summon characters.\n\n"
                f"✨ <b>Good Luck Summoning!</b> 🎉"
            ),
            parse_mode="HTML",
            reply_markup=reply_markup
        )


# ✅ Delete a Banner (with Confirmation)
async def delete_banner(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 <b>You don't have permission to delete banners!</b>", parse_mode="HTML")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text(
                "❌ <b>Usage:</b>\n<code>/deletebanner &lt;banner_id&gt;</code>",
                parse_mode="HTML"
            )
            return

        banner_id = args[0]

        try:
            banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})
        except Exception:
            await update.message.reply_text("❌ <b>Invalid Banner ID!</b>", parse_mode="HTML")
            return

        if not banner:
            await update.message.reply_text("❌ <b>Banner not found!</b>", parse_mode="HTML")
            return

        keyboard = [
            [InlineKeyboardButton("🗑 Confirm Delete", callback_data=f"confirm_delete:{banner_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"⚠️ <b>Confirm Deletion</b>\n\n"
            f"🎟 <b>Banner Name:</b> <code>{banner['name']}</code>\n"
            f"🆔 <b>Banner ID:</b> <code>{banner_id}</code>\n\n"
            f"❌ <b>This action is irreversible.</b>\n\n"
            f"🔹 Click <b>Confirm Delete</b> to proceed.",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ <b>Error Deleting Banner:</b> <code>{str(e)}</code>", parse_mode="HTML")


# ✅ Handle Banner Deletion Confirmation
async def confirm_delete(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge button press

    try:
        _, banner_id = query.data.split(":")
        banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})

        if not banner:
            await query.message.edit_text("❌ <b>Banner not found!</b>", parse_mode="HTML")
            return

        await banners_collection.delete_one({"_id": ObjectId(banner_id)})
        await query.message.edit_text(
            f"✅ <b>Banner Deleted Successfully!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎟 <b>Banner Name:</b> <code>{banner['name']}</code>\n"
            f"🆔 <b>Banner ID:</b> <code>{banner_id}</code>\n\n"
            f"🔹 <b>Use</b> <code>/createbanner</code> <b>to add a new banner!</b>",
            parse_mode="HTML"
        )
    except Exception:
        await query.message.edit_text("❌ <b>Error deleting banner. Invalid ID.</b>", parse_mode="HTML")


async def cancel_delete(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge button press
    await query.message.edit_text("❌ <b>Deletion Cancelled.</b>", parse_mode="HTML")


# ✅ Add Command Handlers
application.add_handler(CommandHandler("createbanner", create_banner, block=False))
application.add_handler(CommandHandler("banners", view_banners, block=False))
application.add_handler(CommandHandler("deletebanner", delete_banner, block=False))
application.add_handler(CallbackQueryHandler(confirm_delete, pattern="^confirm_delete:", block=False))
application.add_handler(CallbackQueryHandler(cancel_delete, pattern="^cancel_delete$", block=False))
