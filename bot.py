import re
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# ==== CONFIG ====
BOT_TOKEN = "7648911646:AAFa2t60QPqmpG-DGxXymUFHPZ2HCd62jA4"  # 🔹 Your bot token from file
MONGO_URI = "mongodb+srv://7261y2y2u2u2u:7261y2y2u2u2u@cluster0.aqmbh9q.mongodb.net/"  # 🔹 Paste your MongoDB URI here
LOG_CHANNEL_ID = -1002330347621
OWNER_IDS = 7055347499, 6222524953

# ==== MONGO CONNECT ====
client = MongoClient(MONGO_URI)
db = client["escrow_bot"]  # Database name
groups_col = db["groups"]
global_col = db["global"]
admins_col = db["admins"]

# Ensure global doc exists
if not global_col.find_one({"_id": "stats"}):
    global_col.insert_one({
        "_id": "stats",
        "total_deals": 0,
        "total_volume": 0,
        "total_fee": 0.0,
        "escrowers": {}
    })

# ==== HELPERS ====
async def is_admin(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        return True
    return admins_col.find_one({"user_id": user_id}) is not None

def init_group(chat_id: str):
    if not groups_col.find_one({"_id": chat_id}):
        groups_col.insert_one({
            "_id": chat_id,
            "deals": {},
            "total_deals": 0,
            "total_volume": 0,
            "total_fee": 0.0,
            "escrowers": {}
        })

def update_escrower_stats(group_id: str, escrower: str, amount: float, fee: float):
    g = groups_col.find_one({"_id": group_id})
    g["total_deals"] += 1
    g["total_volume"] += amount
    g["total_fee"] += fee
    g["escrowers"][escrower] = g["escrowers"].get(escrower, 0) + amount
    groups_col.update_one({"_id": group_id}, {"$set": g})

    global_data = global_col.find_one({"_id": "stats"})
    global_data["total_deals"] += 1
    global_data["total_volume"] += amount
    global_data["total_fee"] += fee
    global_data["escrowers"][escrower] = global_data["escrowers"].get(escrower, 0) + amount
    global_col.update_one({"_id": "stats"}, {"$set": global_data})

# ==== COMMANDS ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✨ <b>Welcome to Escrower Bot!</b> ✨\n\n"
        "• /add – Add a new deal\n"
        "• /complete – Complete a deal\n"
        "• /stats – Group stats\n"
        "• /gstats – Global stats (Admin only)\n"
        "• /addadmin user_id – Owner only\n"
        "• /removeadmin user_id – Owner only"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Only owner can add admins!")
    if len(context.args) != 1 or not context.args[0].isdigit():
        return await update.message.reply_text("Usage: /addadmin <user_id>")
    user_id = int(context.args[0])
    if admins_col.find_one({"user_id": user_id}):
        return await update.message.reply_text("⚠️ Already admin!")
    admins_col.insert_one({"user_id": user_id})
    await update.message.reply_text(f"✅ Added admin: {user_id}")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Only owner can remove admins!")
    if len(context.args) != 1 or not context.args[0].isdigit():
        return await update.message.reply_text("Usage: /removeadmin <user_id>")
    user_id = int(context.args[0])
    admins_col.delete_one({"user_id": user_id})
    await update.message.reply_text(f"✅ Removed admin: {user_id}")

async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        await update.message.delete()
    except:
        pass
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the DEAL INFO message!")

    original_text = update.message.reply_to_message.text
    chat_id = str(update.effective_chat.id)
    reply_id = str(update.message.reply_to_message.message_id)
    init_group(chat_id)

    buyer_match = re.search(r"BUYER\s*:\s*(@\w+)", original_text, re.IGNORECASE)
    seller_match = re.search(r"SELLER\s*:\s*(@\w+)", original_text, re.IGNORECASE)
    amount_match = re.search(r"DEAL AMOUNT\s*:\s*₹?\s*([\d.]+)", original_text, re.IGNORECASE)

    buyer = buyer_match.group(1) if buyer_match else "Unknown"
    seller = seller_match.group(1) if seller_match else "Unknown"
    if not amount_match:
        return await update.message.reply_text("❌ Amount not found!")
    amount = float(amount_match.group(1))

    g = groups_col.find_one({"_id": chat_id})
    deals = g["deals"]
    if reply_id not in deals:
        trade_id = f"TID{random.randint(100000, 999999)}"
        fee = 0.0
        release_amount = round(amount - fee, 2)
        deals[reply_id] = {"trade_id": trade_id, "release_amount": release_amount, "completed": False}
    else:
        trade_id = deals[reply_id]["trade_id"]
        release_amount = deals[reply_id]["release_amount"]
        fee = round(amount - release_amount, 2)

    g["deals"] = deals
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    escrower = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name
    update_escrower_stats(chat_id, escrower, amount, fee)

    msg = (
        "✅ <b>Amount Received!</b>\n"
        "────────────────\n"
        f"👤 Buyer  : {buyer}\n"
        f"👤 Seller : {seller}\n"
        f"💰 Amount : ₹{amount}\n"
        f"💸 Release: ₹{release_amount}\n"
        f"⚖️ Fee    : ₹{fee}\n"
        f"🆔 Trade ID: #{trade_id}\n"
        "────────────────\n"
        f"🛡️ Escrowed by {escrower}"
    )
    await update.effective_chat.send_message(msg, reply_to_message_id=update.message.reply_to_message.message_id, parse_mode="HTML")

async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        await update.message.delete()
    except:
        pass
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the DEAL INFO message!")

    chat_id = str(update.effective_chat.id)
    reply_id = str(update.message.reply_to_message.message_id)
    g = groups_col.find_one({"_id": chat_id})
    deal_info = g["deals"].get(reply_id)

    if not deal_info:
        return await update.message.reply_text("❌ Deal not found!")
    if deal_info["completed"]:
        return await update.message.reply_text("⚠️ Already completed!")

    deal_info["completed"] = True
    g["deals"][reply_id] = deal_info
    groups_col.update_one({"_id": chat_id}, {"$set": g})

    original_text = update.message.reply_to_message.text
    buyer_match = re.search(r"BUYER\s*:\s*(@\w+)", original_text, re.IGNORECASE)
    seller_match = re.search(r"SELLER\s*:\s*(@\w+)", original_text, re.IGNORECASE)
    buyer = buyer_match.group(1) if buyer_match else "Unknown"
    seller = seller_match.group(1) if seller_match else "Unknown"

    escrower = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name
    release_amount = deal_info["release_amount"]
    trade_id = deal_info["trade_id"]

    msg = (
        "✅ <b>Deal Completed!</b>\n"
        "────────────────\n"
        f"👤 Buyer   : {buyer}\n"
        f"👤 Seller  : {seller}\n"
        f"💸 Released: ₹{release_amount}\n"
        f"🆔 Trade ID: #{trade_id}\n"
        "────────────────\n"
        f"🛡️ Escrowed by {escrower}"
    )
    await update.effective_chat.send_message(msg, reply_to_message_id=update.message.reply_to_message.message_id, parse_mode="HTML")

    log_msg = (
        "📜 <b>Deal Completed (Log)</b>\n"
        "────────────────\n"
        f"👤 Buyer   : {buyer}\n"
        f"👤 Seller  : {seller}\n"
        f"💸 Released: ₹{release_amount}\n"
        f"🆔 Trade ID: #{trade_id}\n"
        f"🛡️ Escrowed by {escrower}\n"
        f"📌 Group: {update.effective_chat.title} ({update.effective_chat.id})"
    )
    await context.bot.send_message(LOG_CHANNEL_ID, log_msg, parse_mode="HTML")

async def group_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    init_group(chat_id)
    g = groups_col.find_one({"_id": chat_id})
    escrowers_text = "\n".join([f"{name} = ₹{amt}" for name, amt in g["escrowers"].items()]) or "No deals yet"
    msg = (
        f"📊 Group Stats\n\n"
        f"{escrowers_text}\n\n"
        f"🔹 Total Deals: {g['total_deals']}\n"
        f"💰 Total Volume: ₹{g['total_volume']}\n"
        f"💸 Total Fee: ₹{g['total_fee']}"
    )
    await update.message.reply_text(msg)

async def global_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    g = global_col.find_one({"_id": "stats"})
    escrowers_text = "\n".join([f"{name} = ₹{amt}" for name, amt in g["escrowers"].items()]) or "No deals yet"
    msg = (
        f"🌍 Global Stats\n\n"
        f"{escrowers_text}\n\n"
        f"🔹 Total Deals: {g['total_deals']}\n"
        f"💰 Total Volume: ₹{g['total_volume']}\n"
        f"💸 Total Fee: ₹{g['total_fee']}"
    )
    await update.message.reply_text(msg)

# ==== MAIN ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("stats", group_stats))
    app.add_handler(CommandHandler("gstats", global_stats))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()




