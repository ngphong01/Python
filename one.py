import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import requests
import os
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PERPLEXITY_API_KEYS = os.getenv('PERPLEXITY_API_KEYS').split(',') if os.getenv('PERPLEXITY_API_KEYS') else []

genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

updater = Updater(TELEGRAM_API_TOKEN, use_context=True)
dp = updater.dispatcher

user_models = {}
DEFAULT_MODEL = "sonar-pro"

MODEL_GROUPS = {
    "perplexity": {"name": "Perplexity", "models": {"sonar-pro": {"name": "Sonar Pro", "api_id": "sonar-pro", "api_type": "perplexity"}}},
    "gemini": {"name": "Google Gemini", "models": {"gemini-flash": {"name": "Gemini Advanced 2.0 Flash", "api_id": "gemini-1.5-flash", "api_type": "gemini"}}}
}

AVAILABLE_MODELS = {}
for group in MODEL_GROUPS.values():
    AVAILABLE_MODELS.update(group["models"])

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_models[user_id] = DEFAULT_MODEL
    update.message.reply_text('Chào bạn! Hiện tại chưa có tin nhắn nào. Gửi câu hỏi bất kỳ để bắt đầu!')

def show_model_groups(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton(group_info["name"], callback_data=f"group_{group_id}")] for group_id, group_info in MODEL_GROUPS.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Chọn nhóm mô hình AI:', reply_markup=reply_markup)

def show_models(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton(model_info["name"], callback_data=f"model_{model_id}")] for model_id, model_info in AVAILABLE_MODELS.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Chọn mô hình AI:', reply_markup=reply_markup)

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data.startswith("group_"):
        group_id = query.data.replace("group_", "")
        keyboard = [[InlineKeyboardButton(model_info["name"], callback_data=f"model_{model_id}")] for model_id, model_info in MODEL_GROUPS[group_id]["models"].items()]
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data="back_to_groups")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=f"Mô hình {MODEL_GROUPS[group_id]['name']}:", reply_markup=reply_markup)
    elif query.data == "back_to_groups":
        keyboard = [[InlineKeyboardButton(group_info["name"], callback_data=f"group_{group_id}")] for group_id, group_info in MODEL_GROUPS.items()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text='Chọn nhóm mô hình AI:', reply_markup=reply_markup)
    elif query.data.startswith("model_"):
        model_id = query.data.replace("model_", "")
        user_id = update.effective_user.id
        user_models[user_id] = model_id
        query.edit_message_text(text=f"Đã chọn mô hình: {AVAILABLE_MODELS[model_id]['name']}")

def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    model = user_models.get(user_id, DEFAULT_MODEL)
    model_info = AVAILABLE_MODELS[model]
    model_name = model_info["name"]
    api_type = model_info["api_type"]
    processing_message = update.message.reply_text(f"Đang xử lý yêu cầu của bạn với {model_name}...")
    if api_type == "perplexity":
        response = get_perplexity_response(user_message, model)
    elif api_type == "gemini":
        response = get_gemini_response(user_message, model)
    else:
        response = "Loại API không được hỗ trợ."
    processing_message.delete()
    reply_text = f"🤖 {model_name}:\n\n{response}"
    if len(reply_text) > 4000:
        parts = [reply_text[i:i+4000] for i in range(0, len(reply_text), 4000)]
        for i, part in enumerate(parts):
            update.message.reply_text(part if i == 0 else f"(tiếp theo) {part}")
    else:
        update.message.reply_text(reply_text)

def get_perplexity_response(query: str, model_key: str) -> str:
    # (Giữ nguyên hàm này từ mã gốc của bạn)
    url = 'https://api.perplexity.ai/chat/completions'
    api_key = PERPLEXITY_API_KEYS[0]  # Dùng key đầu tiên để đơn giản
    model_info = AVAILABLE_MODELS[model_key]
    model_id = model_info["api_id"]
    system_prompt = model_info.get("system_prompt", "Bạn là trợ lý AI hữu ích. Hãy trả lời người dùng một cách chính xác và hữu ích.")
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    data = {"model": model_id, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]}
    response = requests.post(url, headers=headers, json=data)
    return response.json().get('choices')[0].get('message').get('content') if response.status_code == 200 else "Lỗi Perplexity API"

def get_gemini_response(query: str, model_key: str) -> str:
    model_info = AVAILABLE_MODELS[model_key]
    model_id = model_info["api_id"]
    system_prompt = model_info.get("system_prompt", "Bạn là trợ lý AI hữu ích. Hãy trả lời người dùng một cách chính xác và hữu ích.")
    try:
        model = genai.GenerativeModel(model_id)
        full_prompt = f"{system_prompt}\n\nUser: {query}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f'Có lỗi xảy ra với Gemini API: {str(e)}'

# Thêm handlers
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("model", show_models))
dp.add_handler(CommandHandler("groups", show_model_groups))
dp.add_handler(CallbackQueryHandler(button_callback))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dp.process_update(update)
    return 'OK'

def main():
    # Cấu hình webhook
    PORT = int(os.environ.get('PORT', 8443))
    WEBHOOK_URL = f"https://your-render-app.onrender.com/webhook"  # Thay bằng URL thật từ Render
    updater.bot.setWebhook(WEBHOOK_URL)
    app.run(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    main()
