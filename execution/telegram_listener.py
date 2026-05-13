import asyncio
import aiohttp
from datetime import datetime
from config.secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_TRADER_ID, TELEGRAM_OWNER_ID
from config.settings import TRADING_SYMBOL, TIMEFRAME

class TelegramListener:
    """
    Фоновый процесс, который опрашивает Telegram API (getUpdates).
    Слушает команды (например, /start) и нажатия на инлайн-кнопки (callback_query).
    """
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.trader_id = str(TELEGRAM_TRADER_ID)
        self.owner_id = str(TELEGRAM_OWNER_ID)
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0

    async def _send_text(self, chat_id: str, text: str):
        """Универсальный метод отправки сообщений по Chat ID"""
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        async with aiohttp.ClientSession() as session:
            await session.post(f"{self.base_url}/sendMessage", json=payload)

    async def _answer_callback(self, callback_query_id: str, text: str):
         """Убирает 'часики' с кнопки в Телеграме после нажатия"""
         payload = {"callback_query_id": callback_query_id, "text": text}
         async with aiohttp.ClientSession() as session:
            await session.post(f"{self.base_url}/answerCallbackQuery", json=payload)

    async def listen(self):
        """Бесконечный цикл прослушивания обновлений"""
        if not self.token or self.token.startswith("YOUR_"):
            print("[Listener] Токен не настроен. Слушатель отключен.")
            return

        print("[Listener] Запущен слушатель команд и кнопок Telegram...")
        
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    url = f"{self.base_url}/getUpdates?offset={self.offset}&timeout=10"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for update in data.get("result", []):
                                self.offset = update["update_id"] + 1
                                
                                # 1. Обработка обычных текстовых сообщений
                                if "message" in update:
                                    msg = update["message"]
                                    text = msg.get("text", "")
                                    chat_id = str(msg["chat"]["id"])
                                    
                                    # Проверяем команду /start
                                    if text == "/start":
                                        current_time = datetime.now().strftime("%H:%M:%S")
                                        reply = (
                                            "🤖 <b>Да, Никитос, я живой!</b>\n\n"
                                            "Прямо сейчас я нахожусь в поиске торговых ситуаций.\n"
                                            "<b>Доказательство:</b>\n"
                                            f"⏳ <i>Последний пинг биржи: {current_time}</i>\n"
                                            f"📊 <i>Анализирую пару: {TRADING_SYMBOL}</i>\n"
                                            f"📈 <i>Таймфрейм: {TIMEFRAME}</i>\n\n"
                                            "Я ищу VSA кульминации (TrueVolume) на уровнях ликвидности (PROfile) с подтверждением по краям (Kraya). Жди сигнала!"
                                        )
                                        await self._send_text(chat_id, reply)
                                        print(f"[Listener] Ответил на команду /start пользователю {chat_id}")

                                # 2. Обработка нажатий на инлайн-кнопки
                                elif "callback_query" in update:
                                    cb = update["callback_query"]
                                    user_id = str(cb["from"]["id"])
                                    data_text = cb.get("data", "")
                                    cb_id = cb["id"]
                                    
                                    if user_id == self.trader_id:
                                        if data_text.startswith("approve_"):
                                            signal_id = data_text.split("_")[1]
                                            await self._answer_callback(cb_id, "✅ Сигнал подтвержден!")
                                            await self._send_text(self.owner_id, f"👤 <b>Трейдер подтвердил сигнал!</b>\nID: {signal_id}")
                                            print(f"[Listener] Трейдер подтвердил сигнал {signal_id}!")
                                    else:
                                        await self._answer_callback(cb_id, "🚫 У вас нет прав.")
                                        
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    print(f"[Listener] Ошибка: {e}")
                    await asyncio.sleep(5)
                
                await asyncio.sleep(1)
