import asyncio
import re
import os
from urllib.parse import urlparse
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from concurrent.futures import ThreadPoolExecutor
import logging

# ===================== CONFIG =====================
BOT_TOKEN = "8724611311:AAGXnjqJSVR7Q8-S3Tu4cpOD3_n9xjt8SLs"   # ← Put your bot token here

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

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
executor = ThreadPoolExecutor(max_workers=50)

def normalize_url(url: str) -> str:
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
    except Exception as e:
        print(f"[-] Failed {url}: {e}")
    return None

async def process_single_url(url: str, session: aiohttp.ClientSession):
    normalized = normalize_url(url.strip())
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
        "Send me a list of URLs (one per line) and I'll filter only those with payment gateways and <b>NO Captcha/Cloudflare</b>.\n\n"
        "Just paste the URLs now..."
    )

@dp.message()
async def handle_urls(message: types.Message):
    urls = [line.strip() for line in message.text.splitlines() if line.strip() and not line.strip().startswith('#')]

    if not urls:
        await message.answer("❌ No valid URLs found in your message.")
        return

    await message.answer(f"🚀 Processing <b>{len(urls)}</b> URLs... Please wait.")

    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [process_single_url(url, session) for url in urls]
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                results.append(result)

    if not results:
        await message.answer("❌ No clean gateways found (all had captcha/cloudflare or no gateways).")
        return

    # Save to file
    output_file = f"clean_gateways_{message.from_user.id}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in results:
            f.write("--------------------------------------------------\n")
            f.write(f"URL: {entry['url']}\n")
            f.write(f"Gateways: {', '.join(entry['gateways'])}\n")
            f.write(f"Security: Captcha: No | Cloudflare: No\n")
            f.write(f"@Mod_By_Kamal\n\n")

    # Send file
    await message.answer_document(
        document=FSInputFile(output_file),
        caption=f"✅ <b>Found {len(results)} clean payment gateway sites!</b>\n\n"
                f"Filtered by @Mod_By_Kamal"
    )

    # Cleanup
    try:
        os.remove(output_file)
    except:
        pass

async def main():
    print("😈 Gateway Filter Telegram Bot Started (UNRESTRICTED MODE)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
