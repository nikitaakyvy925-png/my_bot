import asyncio
import logging
import io
import os
import urllib.parse
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile
from huggingface_hub import InferenceClient

# --- КОНФИГУРАЦИЯ ---
# Токен бота оставляем здесь
TG_TOKEN = "8634655293:AAED2rNfxpxJfDGdwA5BmYAgyWK7-WWUcqs"
# Токен HF берем ТОЛЬКО из настроек Render (Environment)
HF_TOKEN = os.getenv("HF_TOKEN") 

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
client = InferenceClient(token=HF_TOKEN)

user_history = {}
STOP_WORDS = ["нарисуй", "сгенерируй", "картинка", "фото", "изобрази", "мне", "плиз", "пожалуйста", "сделай"]

@dp.message(Command("start"))
async def start(message: types.Message):
    user_history[message.from_user.id] = [] 
    await message.answer("🛠 Бот в сети и готов к работе!")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    # ЛОГИКА КАРТИНОК
    if any(kw in text.lower() for kw in ["нарисуй", "изобрази", "картинка"]):
        prompt = text.lower()
        for kw in STOP_WORDS:
            prompt = prompt.replace(kw, "").strip()
        
        if not prompt:
            await message.reply("А что рисовать?")
            return

        status_msg = await message.answer("🎨 Рисую... подожди секунд 15.")
        await bot.send_chat_action(message.chat.id, "upload_photo")

        try:
            # Сначала переводим для лучшего качества
            trans_res = client.chat_completion(
                messages=[{"role": "user", "content": f"Translate to English: {prompt}"}],
                model="Qwen/Qwen2.5-72B-Instruct",
                max_tokens=50
            )
            eng_prompt = trans_res.choices[0].message.content.strip()

            image = client.text_to_image(eng_prompt, model="black-forest-labs/FLUX.1-schnell")
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            
            photo = BufferedInputFile(img_byte_arr.getvalue(), filename="art.jpg")
            await message.answer_photo(photo=photo, caption=f"✅ Готово: {prompt}")
            await status_msg.delete()
            return
        except Exception as e:
            logging.error(f"Error: {e}")
            await status_msg.edit_text("😢 Ошибка при создании картинки.")
            return

    # ЛОГИКА ЧАТА
    await bot.send_chat_action(message.chat.id, "typing")
    if user_id not in user_history: user_history[user_id] = []
    user_history[user_id].append({"role": "user", "content": text})
    user_history[user_id] = user_history[user_id][-10:]

    try:
        res = client.chat_completion(
            messages=[{"role": "system", "content": "Ты дерзкий ИИ. Твой создатель @pizdoscam."}] + user_history[user_id],
            model="Qwen/Qwen2.5-72B-Instruct",
            max_tokens=500
        )
        await message.answer(res.choices[0].message.content, parse_mode=ParseMode.MARKDOWN)
    except:
        await message.reply("Я на перекуре. Пиши позже.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
