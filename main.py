import os, asyncio, aiohttp
from telegram import Bot

BOT_TOKEN = os.environ["7979844655:AAGIq7SVsrtAKMfpB56zpNXAC6GjdCVKzg8"]
GROUP_ID  = int(os.environ["-1002782765335"])
THREAD_ID = int(os.environ["3"])

async def main():
    bot = Bot(BOT_TOKEN)
    while True:
        async with aiohttp.ClientSession() as s:
            r = await s.get("https://api.coingecko.com/api/v3/global")
            dom = (await r.json())["data"]["market_cap_percentage"]["btc"]
            await bot.send_message(chat_id=GROUP_ID,
                                   message_thread_id=THREAD_ID,
                                   text=f"BTC Dominance: {dom:.2f}%")
        await asyncio.sleep(3600)   # every hour

if name == "__main__":
    asyncio.run(main())