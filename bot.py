import asyncio
import os
import tempfile
import re
import requests
from typing import Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from agent import AISellerAgent
from logger_config import get_logger

# Load environment variables
load_dotenv()

class TelegramBot:
    def __init__(self):
        self.logger = get_logger("bot")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "en")
        
        if not self.bot_token or not self.openai_api_key:
            self.logger.error("Missing required environment variables: TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
            raise ValueError("Missing required environment variables: TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
        
        try:
            # Initialize bot and dispatcher
            self.bot = Bot(token=self.bot_token)
            self.dp = Dispatcher()
            
            # Initialize AI agent
            self.agent = AISellerAgent(self.openai_api_key, self.default_language)
            
            # Register handlers
            self.register_handlers()
            self.logger.info("TelegramBot initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize TelegramBot: {e}", exc_info=True)
            raise
    
    def register_handlers(self):
        """Register all bot handlers."""
        
        @self.dp.message(Command("start"))
        async def start_handler(message: Message):
            """Handle /start command."""
            try:
                self.logger.info(f"User {message.from_user.id} started the bot")
                welcome_text = """🌸 Welcome to our AI Flower Shop! 🌸

I'm your personal flower consultant, here to help you find the perfect bouquet for any occasion. I can:

• Search for bouquets by describing what you're looking for
• Find similar bouquets by uploading a photo
• Help you choose based on occasion, budget, or preferences
• Answer questions about our beautiful arrangements

Just tell me what you need, or send me a photo of a bouquet you like, and I'll help you find the perfect match!

What can I help you with today? 💐"""
                
                await message.answer(welcome_text)
                self.logger.info(f"Welcome message sent to user {message.from_user.id}")
            except Exception as e:
                self.logger.error(f"Error in start handler: {e}", exc_info=True)
                await message.answer("Welcome! I'm here to help you find the perfect bouquet. How can I assist you today?")
        
        @self.dp.message(Command("help"))
        async def help_handler(message: Message):
            """Handle /help command."""
            try:
                self.logger.info(f"User {message.from_user.id} requested help")
                help_text = """🆘 How to use our AI Flower Shop:

**Text Search:**
Just describe what you're looking for! For example:
• "I need a romantic bouquet for my girlfriend"
• "Show me white roses under $50"
• "I want something for a birthday party"

**Photo Search:**
Upload a photo of a bouquet you like, and I'll find similar ones in our collection.

**Price Filters:**
I can help you find bouquets within your budget. Just mention your price range!

**Occasions:**
I know about all kinds of occasions - birthdays, anniversaries, apologies, congratulations, and more!

Need more help? Just ask! 😊"""
                
                await message.answer(help_text)
                self.logger.info(f"Help message sent to user {message.from_user.id}")
            except Exception as e:
                self.logger.error(f"Error in help handler: {e}", exc_info=True)
                await message.answer("I'm here to help! You can search for bouquets by describing what you want or by uploading a photo.")
        
        @self.dp.message(Command("clear"))
        async def clear_handler(message: Message):
            """Handle /clear command to reset conversation context."""
            try:
                user_id = message.from_user.id
                self.logger.info(f"User {user_id} cleared conversation context")
                self.agent.clear_context(user_id)
                await message.answer("🔄 Our conversation has been reset. How can I help you find the perfect bouquet?")
                self.logger.info(f"Context cleared for user {user_id}")
            except Exception as e:
                self.logger.error(f"Error in clear handler: {e}", exc_info=True)
                await message.answer("I've reset our conversation. How can I help you find the perfect bouquet?")
        
        @self.dp.message(F.photo)
        async def photo_handler(message: Message):
            """Handle photo messages."""
            user_id = message.from_user.id
            temp_path = None
            try:
                self.logger.info(f"User {user_id} uploaded a photo")
                
                # Get the highest resolution photo
                photo = message.photo[-1]
                self.logger.debug(f"Photo file_id: {photo.file_id}, size: {photo.file_size}")
                
                # Download photo
                file_info = await self.bot.get_file(photo.file_id)
                file_path = file_info.file_path
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_path = temp_file.name
                
                # Download photo to temporary file
                await self.bot.download_file(file_path, temp_path)
                self.logger.debug(f"Photo downloaded to: {temp_path}")
                
                # Process with AI agent
                user_message = message.caption or "I uploaded a photo, please find similar bouquets"
                self.logger.info(f"Processing photo search for user {user_id}: {user_message}")
                
                # Send typing indicator
                await self.bot.send_chat_action(user_id, "typing")
                
                response = await self.agent.process_message(user_id, user_message, temp_path)
                self.logger.info(f"AI response generated for user {user_id}")
                
                # Check if response contains photo URLs and send them
                await self.send_response_with_photos(message, response)
                
            except Exception as e:
                self.logger.error(f"Error processing photo from user {user_id}: {e}", exc_info=True)
                # Try HTML first, then plain text for error message
                try:
                    await message.answer("I apologize, but I had trouble processing your photo. Please try uploading it again or describe what you're looking for in text.", parse_mode="HTML")
                except Exception as html_error:
                    self.logger.warning(f"HTML formatting failed for error message: {html_error}")
                    await message.answer("I apologize, but I had trouble processing your photo. Please try uploading it again or describe what you're looking for in text.")
            finally:
                # Clean up temporary file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                        self.logger.debug(f"Cleaned up temporary file: {temp_path}")
                    except Exception as cleanup_error:
                        self.logger.warning(f"Failed to clean up temporary file {temp_path}: {cleanup_error}")
        
        @self.dp.message()
        async def text_handler(message: Message):
            """Handle text messages."""
            user_id = message.from_user.id
            try:
                user_message = message.text
                self.logger.info(f"User {user_id} sent text message: {user_message[:100]}...")
                
                # Send typing indicator
                await self.bot.send_chat_action(user_id, "typing")
                
                # Process with AI agent
                response = await self.agent.process_message(user_id, user_message)
                self.logger.info(f"AI response generated for user {user_id}")
                
                # Check if response contains photo URLs and send them
                await self.send_response_with_photos(message, response)
                
            except Exception as e:
                self.logger.error(f"Error processing text message from user {user_id}: {e}", exc_info=True)
                # Try HTML first, then plain text for error message
                try:
                    await message.answer("I apologize, but I encountered an error. Please try again or use /help for assistance.", parse_mode="HTML")
                except Exception as html_error:
                    self.logger.warning(f"HTML formatting failed for error message: {html_error}")
                    await message.answer("I apologize, but I encountered an error. Please try again or use /help for assistance.")
    
    def strip_html_formatting(self, text: str) -> str:
        """Strip HTML formatting and return plain text."""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode common HTML entities
        html_entities = {
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' '
        }
        
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        # Clean up extra whitespace but preserve intentional spaces
        text = re.sub(r'[ \t]+', ' ', text)  # Replace multiple spaces/tabs with single space
        text = re.sub(r'\n\s*\n', '\n', text)  # Replace multiple newlines with single newline
        text = text.strip()
        
        return text

    def create_payment_keyboard(self, payment_url: str) -> InlineKeyboardMarkup:
        """Create inline keyboard with payment button."""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Pay Now", url=payment_url)]
        ])
        return keyboard

    def extract_payment_url(self, text: str) -> Optional[str]:
        """Extract payment URL from text if present."""
        # Look for Click payment URLs - more precise pattern to avoid HTML artifacts
        payment_pattern = r'https://my\.click\.uz/services/pay/\?service_id=\d+&merchant_id=\d+&amount=[\d.]+&transaction_param=[a-f0-9\-]+&return_url=https://t\.me/[a-zA-Z0-9_]+'
        match = re.search(payment_pattern, text)
        return match.group(0) if match else None

    async def send_response_with_photos(self, message: Message, response: str):
        """Send response with photos if URLs are found."""
        user_id = message.from_user.id
        try:
            # Check for payment URL first
            payment_url = self.extract_payment_url(response)
            keyboard = self.create_payment_keyboard(payment_url) if payment_url else None
            
            # Extract photo URLs from response - more precise regex to avoid HTML tags
            photo_urls = re.findall(r'https://imagedelivery\.net/[a-zA-Z0-9\-]+/[a-zA-Z0-9\-]+/public', response)
            self.logger.debug(f"Found {len(photo_urls)} photo URLs for user {user_id}")
            
            # Clean up any URLs that might have extra characters
            cleaned_urls = []
            for url in photo_urls:
                # First, try to extract just the URL part using a more precise regex
                url_match = re.search(r'(https://imagedelivery\.net/[a-zA-Z0-9\-]+/[a-zA-Z0-9\-]+/public)', url)
                if url_match:
                    clean_url = url_match.group(1)
                else:
                    # Fallback: remove trailing characters that aren't part of the URL
                    clean_url = re.sub(r'[^a-zA-Z0-9\-/\.:]+$', '', url)
                    # Additional cleanup for common HTML artifacts
                    clean_url = clean_url.replace('">', '').replace('>', '').replace('"', '')
                
                # Validate the URL format
                if (clean_url.startswith('https://imagedelivery.net/') and 
                    clean_url.endswith('/public') and 
                    len(clean_url.split('/')) == 6):  # Should have 6 parts when split by /
                    cleaned_urls.append(clean_url)
                else:
                    self.logger.warning(f"Invalid photo URL format: {url} -> {clean_url}")
            
            photo_urls = cleaned_urls
            self.logger.debug(f"Cleaned photo URLs: {photo_urls}")
            
            if photo_urls:
                try:
                    if len(photo_urls) == 1:
                        # Single photo with caption
                        self.logger.info(f"Sending single photo to user {user_id}")
                        await message.answer_photo(
                            photo=photo_urls[0],
                            caption=response,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                    else:
                        # Multiple photos in media group
                        self.logger.info(f"Sending media group with {len(photo_urls)} photos to user {user_id}")
                        media_group = []
                        for i, photo_url in enumerate(photo_urls[:10]):  # Limit to 10 photos
                            if i == 0:
                                # First photo gets the caption
                                media_group.append(InputMediaPhoto(
                                    media=photo_url,
                                    caption=response,
                                    parse_mode="HTML"
                                ))
                            else:
                                # Other photos without caption
                                media_group.append(InputMediaPhoto(media=photo_url))
                        
                        await message.answer_media_group(media=media_group)
                        
                        # Send payment button separately if there's a payment URL
                        if payment_url:
                            await message.answer(
                                "💳 Click the button below to complete your purchase:",
                                reply_markup=keyboard
                            )
                    
                    self.logger.info(f"Successfully sent photos to user {user_id}")
                    
                except Exception as photo_error:
                    self.logger.warning(f"Failed to send photos to user {user_id}: {photo_error}")
                    # If photos fail, try HTML formatting first, then plain text
                    try:
                        await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
                    except Exception as html_error:
                        self.logger.warning(f"HTML formatting failed, sending plain text: {html_error}")
                        # If HTML fails, send plain text
                        plain_text = self.strip_html_formatting(response)
                        await message.answer(plain_text, reply_markup=keyboard)
            else:
                # No photos found, try HTML formatting first, then plain text
                self.logger.debug(f"No photos found, sending text only to user {user_id}")
                try:
                    await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
                except Exception as html_error:
                    self.logger.warning(f"HTML formatting failed, sending plain text: {html_error}")
                    # If HTML fails, send plain text
                    plain_text = self.strip_html_formatting(response)
                    await message.answer(plain_text, reply_markup=keyboard)
                
        except Exception as e:
            self.logger.error(f"Error in send_response_with_photos for user {user_id}: {e}", exc_info=True)
            # Last resort: try HTML first, then plain text
            try:
                payment_url = self.extract_payment_url(response)
                keyboard = self.create_payment_keyboard(payment_url) if payment_url else None
                await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
            except Exception as html_error:
                self.logger.warning(f"HTML formatting failed in fallback, sending plain text: {html_error}")
                # If HTML fails, send plain text
                plain_text = self.strip_html_formatting(response)
                payment_url = self.extract_payment_url(plain_text)
                keyboard = self.create_payment_keyboard(payment_url) if payment_url else None
                await message.answer(plain_text, reply_markup=keyboard)
    
    async def start_polling(self):
        """Start the bot polling."""
        self.logger.info("🤖 AI Seller Bot is starting...")
        print("🤖 AI Seller Bot is starting...")
        print("🌸 Ready to help customers find perfect bouquets!")
        
        try:
            self.logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.logger.error(f"Error during bot polling: {e}", exc_info=True)
            print(f"Error starting bot: {e}")
        finally:
            self.logger.info("Stopping bot...")
            await self.bot.session.close()
    
    async def stop(self):
        """Stop the bot gracefully."""
        self.logger.info("Stopping bot gracefully...")
        await self.bot.session.close()
