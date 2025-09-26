#!/usr/bin/env python3
"""
Simple Nike Monitor Bot
Monitors Nike for Air Force 1 City Pack Paris (Patent) availability
"""

import json
import logging
import os
import re
import requests
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class NikeMonitor:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
    def load_config(self, config_file):
        """Load configuration from file or create default"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default config
            return {
                "search_terms": ["Nike Air Force 1 Low", "City Pack Paris", "Patent"],
                "nike_search_url": "https://www.nike.com/w/air-force-1-aq0113",
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "check_interval": 30,
                "single_run": False,
                "telegram": {
                    "enabled": True,
                    "bot_token": os.getenv('TELEGRAM_BOT_TOKEN'),
                    "chat_id": os.getenv('TELEGRAM_CHAT_ID')
                }
            }
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('nike_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def check_nike_availability(self):
        """Check Nike website for product availability"""
        try:
            headers = {'User-Agent': self.config['user_agent']}
            response = requests.get(self.config['nike_search_url'], headers=headers, timeout=15)
            
            if response.status_code != 200:
                self.logger.error(f"HTTP {response.status_code} from Nike")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products = []
            
            # Find product cards
            product_cards = soup.find_all('div', class_=re.compile(r'product-card'))
            if not product_cards:
                # Alternative selector
                product_cards = soup.find_all('a', href=re.compile(r'/t/'))
            
            for card in product_cards:
                try:
                    # Extract product info
                    product_name = ''
                    product_link = ''
                    product_price = ''
                    
                    # Get product name
                    name_elem = card.find(['h3', 'h4', 'span'], class_=re.compile(r'product-card__title|card-title'))
                    if not name_elem:
                        name_elem = card.find(text=re.compile(r'Air Force|AF1'))
                        if name_elem:
                            product_name = name_elem.strip()
                    else:
                        product_name = name_elem.get_text(strip=True)
                    
                    # Get product link
                    link_elem = card if card.name == 'a' else card.find('a')
                    if link_elem:
                        href = link_elem.get('href', '')
                        product_link = urljoin('https://www.nike.com', href)
                    
                    # Get price
                    price_elem = card.find(class_=re.compile(r'price|product-price'))
                    if price_elem:
                        product_price = price_elem.get_text(strip=True)
                    
                    # Check if this matches our search terms
                    if self.matches_search_terms(product_name):
                        # Get detailed product info
                        detailed_info = self.get_product_details(product_link)
                        
                        product_info = {
                            'name': product_name,
                            'price': product_price or detailed_info.get('price', 'N/A'),
                            'link': product_link,
                            'sizes': detailed_info.get('sizes', []),
                            'in_stock': detailed_info.get('in_stock', False)
                        }
                        
                        if product_info['in_stock'] or product_info['sizes']:
                            products.append(product_info)
                            self.logger.info(f"Found matching product: {product_name}")
                
                except Exception as e:
                    self.logger.debug(f"Error parsing product card: {e}")
                    continue
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error checking Nike: {e}")
            return []
    
    def get_product_details(self, product_url):
        """Get detailed product information from product page"""
        try:
            headers = {'User-Agent': self.config['user_agent']}
            response = requests.get(product_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            details = {}
            
            # Get price
            price_elem = soup.find(class_=re.compile(r'product-price|current-price'))
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\$£€¥][\d,]+(?:\.\d{2})?', price_text)
                if price_match:
                    details['price'] = price_match.group(0)
            
            # Get available sizes
            sizes = []
            size_buttons = soup.find_all('button', class_=re.compile(r'size|btn-size'))
            for btn in size_buttons:
                if not btn.get('disabled') and btn.get_text(strip=True):
                    sizes.append(btn.get_text(strip=True))
            
            details['sizes'] = sizes
            details['in_stock'] = len(sizes) > 0
            
            # Check for "Add to Bag" button
            add_to_bag = soup.find('button', text=re.compile(r'Add to Bag|Add to Cart', re.I))
            if add_to_bag and not add_to_bag.get('disabled'):
                details['in_stock'] = True
            
            return details
            
        except Exception as e:
            self.logger.debug(f"Error getting product details: {e}")
            return {}
    
    def matches_search_terms(self, product_name):
        """Check if product matches search terms"""
        if not product_name:
            return False
        
        product_lower = product_name.lower()
        search_terms = self.config.get('search_terms', [])
        
        # All terms must be present (AND logic)
        for term in search_terms:
            if term.lower() not in product_lower:
                return False
        
        return True
    
    def send_telegram_message(self, message):
        """Send message via Telegram"""
        try:
            telegram_config = self.config.get('telegram', {})
            if not telegram_config.get('enabled', False):
                return False
            
            bot_token = telegram_config.get('bot_token')
            chat_id = telegram_config.get('chat_id')
            
            if not bot_token or not chat_id:
                self.logger.error("Telegram bot token or chat ID not configured")
                return False
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("Telegram message sent successfully")
                return True
            else:
                self.logger.error(f"Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_email_notification(self, subject, message):
        """Send email notification"""
        try:
            email_config = self.config.get('email_notifications', {})
            if not email_config.get('enabled', False):
                return False
            
            msg = MIMEMultipart()
            msg['From'] = email_config['sender_email']
            msg['To'] = email_config['recipient_email']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            
            text = msg.as_string()
            server.sendmail(email_config['sender_email'], email_config['recipient_email'], text)
            server.quit()
            
            self.logger.info("Email notification sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
    
    def send_discord_message(self, message):
        """Send Discord webhook message"""
        try:
            discord_config = self.config.get('discord_webhook', {})
            if not discord_config.get('enabled', False):
                return False
            
            webhook_url = discord_config.get('webhook_url')
            if not webhook_url:
                return False
            
            payload = {'content': message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                self.logger.info("Discord message sent successfully")
                return True
            else:
                self.logger.error(f"Discord webhook error: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Discord message: {e}")
            return False
    
    def format_notification(self, products):
    """Format notification message"""
    if not products:
        return f"🔍 **Nike Monitor Status**\n\n**Status:** No AF1 City Pack Paris found\n**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n**Next check:** 5 minutes"
        
        message_lines = ["🚨 **NIKE ALERT — AF1 City Pack Paris (Patent)**\n"]
        
        for product in products:
            message_lines.append(f"**Product:** {product['name']}")
            message_lines.append(f"**Price:** {product['price']}")
            
            if product['sizes']:
                sizes_str = ", ".join(product['sizes'])
                message_lines.append(f"**Available Sizes:** {sizes_str}")
            else:
                message_lines.append("**Sizes:** Check website")
            
            message_lines.append(f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            message_lines.append(f"🛒 **BUY NOW:** {product['link']}")
            message_lines.append("")  # Empty line between products
        
        return "\n".join(message_lines)
    
    def should_notify(self, products):
    """Check if we should send notification (simple deduplication)"""
    if not products:
        return True
        
        # Load previous state
        try:
            with open('last_notification.json', 'r') as f:
                last_state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            last_state = {}
        
        # Create current state
        current_state = {}
        for product in products:
            product_id = product['link'].split('/')[-1] if product['link'] else product['name']
            current_state[product_id] = {
                'name': product['name'],
                'price': product['price'],
                'sizes': sorted(product['sizes']),
                'in_stock': product['in_stock']
            }
        
        # Compare states
        if current_state != last_state:
            # Save new state
            try:
                with open('last_notification.json', 'w') as f:
                    json.dump(current_state, f, indent=2)
            except Exception as e:
                self.logger.error(f"Error saving state: {e}")
            
            return True
        
        return False
    
    def run(self):
        """Main run loop"""
        self.logger.info("Starting Nike Monitor")
        
        single_run = self.config.get('single_run', False)
        check_interval = self.config.get('check_interval', 30)
        
        while True:
            try:
                self.logger.info("Checking Nike for availability...")
                products = self.check_nike_availability()
                
                if self.should_notify(products):
                    notification_message = self.format_notification(products)
                    
                    if notification_message:
                        self.logger.info("Sending notifications...")
                        
                        # Send notifications
                        self.send_telegram_message(notification_message)
                        
                        # Optional notifications
                        self.send_email_notification(
                            "Nike AF1 City Pack Paris Available!", 
                            notification_message.replace('**', '').replace('🚨', '').replace('🛒', '')
                        )
                        self.send_discord_message(notification_message)
                
                else:
                    self.logger.info("No new products found or no changes detected")
                
                if single_run:
                    self.logger.info("Single run completed")
                    break
                
                self.logger.info(f"Waiting {check_interval} seconds before next check...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                if single_run:
                    break
                time.sleep(min(check_interval, 300))  # Max 5 minutes on error


if __name__ == '__main__':
    monitor = NikeMonitor()
    monitor.run()
