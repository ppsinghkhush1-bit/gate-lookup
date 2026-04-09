import asyncio
import re
import os
from urllib.parse import urlparse
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ===================== CONFIG =====================
BOT_TOKEN = "8724611311:AAGXnjqJSVR7Q8-S3Tu4cpOD3_n9xjt8SLs"   # ← Change this

PAYMENT_GATEWAYS = [
    "PayPal", "Stripe", "Braintree", "Square", "magento", "Convergepay",
    "PaySimple", "oceanpayments", "eProcessing", "hipay", "worldpay", "cybersourse",
    "payjunction", "Authorize.Net", "2Checkout", "Adyen", "Checkout.com", "PayFlow",
    "Payeezy", "usaepay", "creo", "SquareUp", "Authnet", "ebizcharge", "cpay",
    "Moneris", "recurly", "cardknox", "payeezy", "ebizcharge", "Chargify", "Paytrace",
    "hostedpayments", "securepay", "eWay", "blackbaud", "LawPay", "clover", "cardconnect",
    "bluepay", "fluidpay", "Worldpay", "Ebiz", "chasepaymentech", "Auruspay", "sagepayments",
    "paycomet", "geomerchant", "realexpayments", "Rocketgateway", "Rocketgate", "Shopify",
    "WooCommerce", "BigCommerce", "Magento Payments", "Razorpay"
]

SECURITY_INDICATORS = {
    'captcha': ['captcha', 'protected by recaptcha', "i'm not a robot", 'recaptcha/api.js'],
    'cloudflare': ['cloudflare', 'cdnjs.cloudflare.com', 'challenges.cloudflare.com']
}

# =================================================

# FIXED: Using DefaultBotProperties for aiogram 3.7+
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

async def normalize_url(url: str) -> str:
    if not re.match(r'^https?://', url, re.I):
        return 'http://' + url
    return url

def find_payment_gateways(content: str):
    detected = set()
    for gateway in PAYMENT_GATEWAYS:
        if re.search(r'\b' + re.escape(gateway) + r'\b', content, re.I):
            detected.add(gateway)
    return list(detected)

def check_security(content: str):
    captcha = any(re.search(ind, content, re.I) for ind in SECURITY_INDICATORS['captcha'])
    cloudflare = any(re.search(ind, content, re.I) for ind in SECURITY_INDICATORS['cloudflare'])
    return captcha, cloudflare

async def fetch_content(url: str, session: aiohttp.ClientSession):
    try:
        async with session.get(url, timeout=15, ssl=False) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        pass
    return None

async def process_single_url(url: str, session: aiohttp.ClientSession):
    normalized = await normalize_url(url.strip())
    content = await fetch_content(normalized, session)
    if not content:
        return None

    gateways = find_payment_gateways(content)
    if not gateways:
        return None

    captcha, cloudflare = check_security(content)

    if not captcha and not cloudflare:
        return {
            'url': normalized,
            'gateways': gateways,
            'captcha': captcha,
            'cloudflare': cloudflare
        }
    return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🔥 <b>Gateway Filter Bot</b> 🔥\n\n"
        "Send me URLs (one per line) and I'll return only clean sites with payment gateways and <b>NO Captcha / NO Cloudflare</b>.\n\n"
        "<i>Paste your list now...</i>"
    )

@dp.message()
async def handle_urls(message: types.Message):
    urls = [line.strip() for line in message.text.splitlines() if line.strip() and not line.strip().startswith('#')]

    if not urls:
        await message.answer("❌ No valid URLs found.")
        return

    await message.answer(f"🚀 Processing <b>{len(urls)}</b> URLs... This may take a while.")

    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [process_single_url(url, session) for url in urls]
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                results.append(result)

    if not results:
        await message.answer("❌ No clean gateways found.")
        return

    # Save results
    output_file = f"clean_gateways_{message.from_user.id}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in results:
            f.write("--------------------------------------------------\n")
            f.write(f"URL: {entry['url']}\n")
            f.write(f"Gateways: {', '.join(entry['gateways'])}\n")
            f.write("Security: Captcha: No | Cloudflare: No\n")
            f.write("@Mod_By_Kamal\n\n")

    await message.answer_document(
        document=FSInputFile(output_file),
        caption=f"✅ <b>Found {len(results)} clean payment gateway sites!</b>\n\nFiltered by @Mod_By_Kamal"
    )

    # Cleanup
    try:
        os.remove(output_file)
    except:
        pass

async def main():
    print("😈 Gateway Filter Telegram Bot Started Successfully (UNRESTRICTED MODE)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
