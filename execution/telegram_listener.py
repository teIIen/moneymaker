import asyncio
from datetime import datetime

import aiohttp

from config.secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID, TELEGRAM_TRADER_ID
from config.settings import TIMEFRAME, TRADING_PAIRS


class TelegramListener:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.trader_id = str(TELEGRAM_TRADER_ID)
        self.owner_id = str(TELEGRAM_OWNER_ID)
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.pairs_list = ", ".join(TRADING_PAIRS)

    async def _send_text(self, chat_id: str, text: str):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        async with aiohttp.ClientSession() as session:
            await session.post(f"{self.base_url}/sendMessage", json=payload)

    async def _answer_callback(self, callback_query_id: str, text: str):
        payload = {"callback_query_id": callback_query_id, "text": text}
        async with aiohttp.ClientSession() as session:
            await session.post(f"{self.base_url}/answerCallbackQuery", json=payload)

    async def listen(self):
        if not self.token or self.token.startswith("YOUR_"):
            print("[Listener] Telegram token is not configured. Listener disabled.")
            return

        print("[Listener] Telegram command/callback listener started.")

        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    url = f"{self.base_url}/getUpdates?offset={self.offset}&timeout=10"
                    async with session.get(url) as response:
                        if response.status != 200:
                            await asyncio.sleep(5)
                            continue

                        data = await response.json()
                        for update in data.get("result", []):
                            self.offset = update["update_id"] + 1

                            if "message" in update:
                                await self._handle_message(update["message"])
                            elif "callback_query" in update:
                                await self._handle_callback(update["callback_query"])

                except asyncio.TimeoutError:
                    pass
                except Exception as exc:
                    print(f"[Listener] Error: {exc}")
                    await asyncio.sleep(5)

                await asyncio.sleep(1)

    async def _handle_message(self, message: dict):
        text = message.get("text", "")
        chat_id = str(message["chat"]["id"])

        if text != "/start":
            return

        current_time = datetime.now().strftime("%H:%M:%S")
        reply = (
            "<b>Moneymaker2 is running.</b>\n\n"
            f"<i>Last bot ping: {current_time}</i>\n"
            f"<i>Pairs: {self.pairs_list}</i>\n"
            f"<i>Timeframe: {TIMEFRAME}</i>\n\n"
            "The scanner checks every pair from TRADING_PAIRS once per cycle."
        )
        await self._send_text(chat_id, reply)
        print(f"[Listener] Replied to /start for chat {chat_id}")

    async def _handle_callback(self, callback_query: dict):
        user_id = str(callback_query["from"]["id"])
        data_text = callback_query.get("data", "")
        callback_id = callback_query["id"]

        if user_id != self.trader_id:
            await self._answer_callback(callback_id, "Access denied.")
            return

        if data_text.startswith("approve_"):
            signal_id = data_text.removeprefix("approve_")
            await self._answer_callback(callback_id, "Signal approved.")
            await self._send_text(
                self.owner_id,
                f"<b>Trader approved signal.</b>\nID: {signal_id}",
            )
            print(f"[Listener] Trader approved signal {signal_id}.")
