import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = "8221867831:AAGUULzOPowvPpkGNRQpEylmmcTIjvbtcuE"  # Replace with your BotFather token
# ===========================================

# Game storage
user_games = {}

# --- Command: Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 Welcome to Mini Game Bot!\n\n"
        "Available games:\n"
        "/guess - Guess the Number 🎯\n"
        "/hangman - Hangman 🔠\n"
        "/wyr - Would You Rather 🤔\n\n"
        "Type a command to start!"
    )

# --- Game: Guess the Number ---
async def guess_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = random.randint(1, 20)
    user_games[update.effective_user.id] = {"game": "guess", "number": number, "tries": 0}
    await update.message.reply_text("🎯 Guess the number between 1 and 20!")

# --- Game: Hangman ---
async def hangman_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = ["python", "telegram", "banana", "hangman", "developer"]
    word = random.choice(words)
    hidden = "_ " * len(word)
    user_games[update.effective_user.id] = {
        "game": "hangman",
        "word": word,
        "hidden": list(hidden.replace(" ", "")),
        "guessed": set()
    }
    await update.message.reply_text(f"🔠 Hangman started!\n{hidden}")

# --- Game: Would You Rather ---
async def wyr_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = [
        ("Have the ability to fly", "Be invisible"),
        ("Live without music", "Live without movies"),
        ("Eat only pizza", "Eat only burgers"),
        ("Never use the internet again", "Never watch TV again"),
    ]
    choice = random.choice(questions)
    await update.message.reply_text(f"🤔 Would you rather...\n1️⃣ {choice[0]}\n2️⃣ {choice[1]}")

# --- Handle user responses ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if user_id not in user_games:
        return

    game_data = user_games[user_id]
    game = game_data["game"]

    if game == "guess":
        try:
            guess = int(text)
        except ValueError:
            await update.message.reply_text("❌ Please enter a number!")
            return

        game_data["tries"] += 1
        if guess == game_data["number"]:
            await update.message.reply_text(f"✅ Correct! You guessed it in {game_data['tries']} tries.")
            del user_games[user_id]
        elif guess < game_data["number"]:
            await update.message.reply_text("⬆️ Higher!")
        else:
            await update.message.reply_text("⬇️ Lower!")

    elif game == "hangman":
        word = game_data["word"]
        if len(text) != 1 or not text.isalpha():
            await update.message.reply_text("❌ Guess one letter at a time!")
            return

        if text in game_data["guessed"]:
            await update.message.reply_text("⚠️ You already guessed that letter.")
            return

        game_data["guessed"].add(text)
        if text in word:
            for i, letter in enumerate(word):
                if letter == text:
                    game_data["hidden"][i] = text
            hidden_word = " ".join(game_data["hidden"])
            await update.message.reply_text(hidden_word)
            if "_" not in game_data["hidden"]:
                await update.message.reply_text(f"🎉 You won! The word was '{word}'.")
                del user_games[user_id]
        else:
            await update.message.reply_text(f"❌ No '{text}' in the word.")

# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("guess", guess_game))
    app.add_handler(CommandHandler("hangman", hangman_game))
    app.add_handler(CommandHandler("wyr", wyr_game))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
