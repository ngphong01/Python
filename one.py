import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import requests
import os
import random
from datetime import datetime, timedelta
import google.generativeai as genai

TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PERPLEXITY_API_KEYS = os.getenv('PERPLEXITY_API_KEYS').split(',') if os.getenv('PERPLEXITY_API_KEYS') else []


genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_models = {}
DEFAULT_MODEL = "sonar-pro"

api_key_usage = {key: {'count': 0, 'last_used': datetime.now() - timedelta(minutes=5)} for key in PERPLEXITY_API_KEYS}

MODEL_GROUPS = {
    "perplexity": {
        "name": "Perplexity",
        "models": {
            "sonar-pro": {"name": "Sonar Pro", "api_id": "sonar-pro", "api_type": "perplexity"}
        }
    },
    "gemini": {
        "name": "Google Gemini",
        "models": {
            "gemini-flash": {"name": "Gemini Advanced 2.0 Flash", "api_id": "gemini-1.5-flash", "api_type": "gemini"}
        }
    }
}

AVAILABLE_MODELS = {}
for group in MODEL_GROUPS.values():
    AVAILABLE_MODELS.update(group["models"])

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_models[user_id] = DEFAULT_MODEL
    
    update.message.reply_text(
        'Chào bạn! Đây là mô hình AI của Mr.Phong.\n\n'
        'Bạn có thể gửi câu hỏi trực tiếp hoặc chọn mô hình AI bằng lệnh /model.\n'
        'Để xem các mô hình theo nhóm, sử dụng lệnh /groups.\n\n'
        'Mô hình mặc định: ' + AVAILABLE_MODELS[DEFAULT_MODEL]["name"]
    )

def show_model_groups(update: Update, context: CallbackContext) -> None:
    keyboard = []
    for group_id, group_info in MODEL_GROUPS.items():
        keyboard.append([InlineKeyboardButton(group_info["name"], callback_data=f"group_{group_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Chọn nhóm mô hình AI:', reply_markup=reply_markup)

def show_models(update: Update, context: CallbackContext) -> None:
    keyboard = []
    for model_id, model_info in AVAILABLE_MODELS.items():
        keyboard.append([InlineKeyboardButton(model_info["name"], callback_data=f"model_{model_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Chọn mô hình AI:', reply_markup=reply_markup)

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    if query.data.startswith("group_"):
        group_id = query.data.replace("group_", "")
        keyboard = []
        for model_id, model_info in MODEL_GROUPS[group_id]["models"].items():
            keyboard.append([InlineKeyboardButton(model_info["name"], callback_data=f"model_{model_id}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data="back_to_groups")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text=f"Mô hình {MODEL_GROUPS[group_id]['name']}:",
            reply_markup=reply_markup
        )
    
    elif query.data == "back_to_groups":
        keyboard = []
        for group_id, group_info in MODEL_GROUPS.items():
            keyboard.append([InlineKeyboardButton(group_info["name"], callback_data=f"group_{group_id}")])
        
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
            if i == 0:
                update.message.reply_text(part)
            else:
                update.message.reply_text(f"(tiếp theo) {part}")
    else:
        update.message.reply_text(reply_text)

def get_api_key():
    now = datetime.now()
    
    for key, data in api_key_usage.items():
        if (now - data['last_used']).total_seconds() > 60:
            data['count'] = 0
            data['last_used'] = now - timedelta(minutes=1)
    
    selected_key = min(api_key_usage.items(), key=lambda x: x[1]['count'])[0]
    
    api_key_usage[selected_key]['count'] += 1
    api_key_usage[selected_key]['last_used'] = now
    
    return selected_key

def get_perplexity_response(query: str, model_key: str) -> str:
    url = 'https://api.perplexity.ai/chat/completions'
    api_key = get_api_key()
    model_info = AVAILABLE_MODELS[model_key]
    model_id = model_info["api_id"]
    system_prompt = model_info.get("system_prompt", "Bạn là trợ lý AI hữu ích. Hãy trả lời người dùng một cách chính xác và hữu ích.")
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get('choices')[0].get('message').get('content')
        elif response.status_code == 429:
            logger.warning(f"API key {api_key} đã đạt giới hạn tốc độ. Thử lại với key khác.")
            api_key_usage[api_key]['count'] += 10
            return get_perplexity_response(query, model_key)
        else:
            error_message = f'Có lỗi xảy ra khi gọi API Perplexity. Mã lỗi: {response.status_code}'
            try:
                error_detail = response.json()
                error_message += f', Chi tiết: {error_detail}'
            except:
                error_message += f', Chi tiết: {response.text}'
            logger.error(error_message)
            return error_message
    except Exception as e:
        error_message = f'Có lỗi xảy ra với Perplexity API: {str(e)}'
        logger.error(error_message)
        return error_message

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
        error_message = f'Có lỗi xảy ra với Gemini API: {str(e)}'
        logger.error(error_message)
        return error_message

def test_gemini(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Đang kiểm tra kết nối với API Gemini...")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Xin chào, đây là tin nhắn kiểm tra.")
        update.message.reply_text(f"Kết nối thành công! Phản hồi: {response.text}")
    except Exception as e:
        update.message.reply_text(f"Lỗi kết nối: {str(e)}")

def main() -> None:
    updater = Updater(TELEGRAM_API_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("model", show_models))
    dispatcher.add_handler(CommandHandler("groups", show_model_groups))
    dispatcher.add_handler(CommandHandler("test_gemini", test_gemini))
    dispatcher.add_handler(CallbackQueryHandler(button_callback))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    logger.info("Bot đã khởi động")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
