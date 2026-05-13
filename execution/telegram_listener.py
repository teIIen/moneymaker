import asyncio
import aiohttp
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_TRADER_ID, TELEGRAM_OWNER_ID

class TelegramListener:
    """
    Фоновый процесс, который опрашивает Telegram API (getUpdates)
    в поиске нажатий на инлайн-кнопки (callback_query).
    """
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.trader_id = str(TELEGRAM_TRADER_ID)
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0 # Для отслеживания прочитанных сообщений

    async def _send_to_owner(self, text: str):
        payload = {"chat_id": TELEGRAM_OWNER_ID, "text": text, "parse_mode": "HTML"}
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

        print("[Listener] Запущен слушатель кнопок Telegram...")
        
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    # long polling (ждем ответа до 10 секунд)
                    url = f"{self.base_url}/getUpdates?offset={self.offset}&timeout=10"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for update in data.get("result", []):
                                self.offset = update["update_id"] + 1
                                
                                # Ищем нажатия на кнопки
                                if "callback_query" in update:
                                    cb = update["callback_query"]
                                    user_id = str(cb["from"]["id"])
                                    data_text = cb.get("data", "")
                                    cb_id = cb["id"]
                                    
                                    # Проверяем, что нажал именно Трейдер
                                    if user_id == self.trader_id:
                                        if data_text.startswith("approve_"):
                                            signal_id = data_text.split("_")[1]
                                            
                                            # 1. Отвечаем трейдеру, что приняли
                                            await self._answer_callback(cb_id, "✅ Сигнал подтвержден!")
                                            
                                            # 2. Отправляем уведомление Тебе (Архитектору)
                                            await self._send_to_owner(f"👤 <b>Трейдер подтвердил сигнал!</b>\nID: {signal_id}")
                                            
                                            print(f"[Listener] Трейдер подтвердил сигнал {signal_id}!")
                                    else:
                                        # Нажал кто-то чужой
                                        await self._answer_callback(cb_id, "🚫 У вас нет прав.")
                                        
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    print(f"[Listener] Ошибка: {e}")
                    await asyncio.sleep(5)
                
                await asyncio.sleep(1) # Небольшая пауза между запросами
