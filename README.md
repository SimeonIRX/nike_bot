# Nike Air Force 1 Monitor Bot

🚀 A simple bot that monitors Nike for Air Force 1 City Pack Paris (Patent) availability and sends instant Telegram notifications.

## Quick Setup

### 1. Set up Telegram Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save your **bot token**
4. Message your bot, then visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Find your **chat_id** in the response

### 2. Configure GitHub Secrets
Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:
- `TELEGRAM_BOT_TOKEN` - Your bot token from BotFather
- `TELEGRAM_CHAT_ID` - Your chat ID from the API call

### 3. Enable Actions
1. Go to the **Actions** tab
2. Enable workflows if prompted
3. The bot will run every 5 minutes automatically!

## How it Works

- ✅ Monitors Nike Air Force 1 pages every 5 minutes
- ✅ Detects when City Pack Paris (Patent) becomes available
- ✅ Sends formatted Telegram alerts with product details
- ✅ Only notifies when product status actually changes
- ✅ Includes direct buy links and available sizes

## Notification Example
