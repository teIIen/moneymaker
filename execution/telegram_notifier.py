import aiohttp
from config.secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID, TELEGRAM_TRADER_ID

class TelegramNotifier:
    """
    Асинхронный класс для отправки уведомлений в Telegram.
    Поддерживает отправку инлайн-клавиатур.
    """
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.owner_id = TELEGRAM_OWNER_ID
        self.trader_id = TELEGRAM_TRADER_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def _post(self, endpoint: str, payload: dict) -> bool:
        """Базовый метод отправки POST запроса в Telegram API"""
        if not self.token or self.token.startswith("YOUR_"):
            print("[Warning] Telegram токен не настроен.")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/{endpoint}", json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        print(f"[Error] Ошибка Telegram API ({endpoint}): {response.status} - {error_text}")
                        return False
        except Exception as e:
             print(f"[Error] Не удалось отправить запрос в Telegram: {e}")
             return False

    async def send_to_owner(self, text: str) -> bool:
        """Отправляет сообщение тебе (Владельцу/Архитектору)"""
        if not self.owner_id or self.owner_id.startswith("YOUR_"):
            return False
            
        payload = {
            "chat_id": self.owner_id,
            "text": text,
            "parse_mode": "HTML"
        }
        return await self._post("sendMessage", payload)
        
    async def send_to_trader_with_keyboard(self, text: str, signal_id: str) -> bool:
        """
        Отправляет сообщение Трейдеру с инлайн-кнопкой для валидации.
        signal_id - уникальный идентификатор сигнала (например timestamp), 
        чтобы бот понимал, какую именно сделку подтвердил трейдер.
        """
        if not self.trader_id or self.trader_id.startswith("YOUR_"):
            return False
            
        payload = {
            "chat_id": self.trader_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "✅ Согласен с предположением", "callback_data": f"approve_{signal_id}"}
                    ]
                ]
            }
        }
        return await self._post("sendMessage", payload)
