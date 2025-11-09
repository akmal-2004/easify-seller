import asyncio
import os
import tempfile
import re
import time
from typing import Optional, Dict, Set
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from .agent import AISellerAgent
from .logger_config import get_logger

# Load environment variables
load_dotenv()

class TelegramBot:
    def __init__(self):
        self.logger = get_logger("bot")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "en")
        
        # Track users who have sent their first message
        self.first_message_sent = set()

        # Track last message time per user (when user sent message)
        self.last_message_time: Dict[int, float] = {}

        # Track last bot response time per user (when bot sent message)
        self.last_bot_response_time: Dict[int, float] = {}

        # Track pending follow-up tasks per user
        self.pending_followups: Dict[int, Dict[str, asyncio.Task]] = {}

        # Track which follow-ups have been sent per user
        self.sent_followups: Dict[int, Set[str]] = {}

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
• Understand voice messages - just speak to me! 🎤
• Help you choose based on occasion, budget, or preferences
• Answer questions about our beautiful arrangements

Just tell me what you need, send me a photo, or record a voice message, and I'll help you find the perfect match!

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

<b>Text Search:</b>
Just describe what you're looking for! For example:
• "I need a romantic bouquet for my girlfriend"
• "Show me white roses under $50"
• "I want something for a birthday party"

<b>Photo Search:</b>
Upload a photo of a bouquet you like, and I'll find similar ones in our collection.

<b>Voice Messages:</b>
Send me a voice message describing what you're looking for, and I'll understand and help you find the perfect bouquet! 🎤

<b>Price Filters:</b>
I can help you find bouquets within your budget. Just mention your price range!

<b>Occasions:</b>
I know about all kinds of occasions - birthdays, anniversaries, apologies, congratulations, and more!

Need more help? Just ask! 😊"""
                
                await message.answer(help_text, parse_mode="HTML")
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
                
                # Check if this is the first message from this user
                is_first_message = user_id not in self.first_message_sent

                if is_first_message:
                    # Mark that this user has sent their first message
                    self.first_message_sent.add(user_id)
                    self.logger.info(f"First message from user {user_id}, waiting 15 seconds before responding...")

                    # Wait 15 seconds to simulate human-like response time
                    await asyncio.sleep(15)
                    self.logger.info(f"15 second delay completed for user {user_id}, processing with AI...")

                # Update last message time and cancel pending follow-ups
                self.update_user_activity(user_id)

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

                # Update bot response time and schedule follow-up messages
                self.update_bot_response_time(user_id)
                self.schedule_followups(user_id)
                
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
        
        @self.dp.message(F.voice | F.video_note)
        async def voice_handler(message: Message):
            """Handle voice messages and video notes."""
            user_id = message.from_user.id
            temp_path = None
            try:
                # Determine if it's a voice message or video note
                if message.voice:
                    audio_file = message.voice
                    self.logger.info(f"User {user_id} sent a voice message")
                elif message.video_note:
                    audio_file = message.video_note
                    self.logger.info(f"User {user_id} sent a video note")
                else:
                    return

                # Check if this is the first message from this user
                is_first_message = user_id not in self.first_message_sent

                if is_first_message:
                    # Mark that this user has sent their first message
                    self.first_message_sent.add(user_id)
                    self.logger.info(f"First message from user {user_id}, waiting 15 seconds before responding...")

                    # Wait 15 seconds to simulate human-like response time
                    await asyncio.sleep(15)
                    self.logger.info(f"15 second delay completed for user {user_id}, processing with AI...")

                # Update last message time and cancel pending follow-ups
                self.update_user_activity(user_id)

                # Send typing indicator
                await self.bot.send_chat_action(user_id, "typing")

                # Download voice file
                file_info = await self.bot.get_file(audio_file.file_id)
                file_path = file_info.file_path

                # Determine file extension based on MIME type or default to ogg
                file_extension = '.ogg'  # Default for Telegram voice messages
                if hasattr(audio_file, 'mime_type') and audio_file.mime_type:
                    if 'mpeg' in audio_file.mime_type or 'mp3' in audio_file.mime_type:
                        file_extension = '.mp3'
                    elif 'ogg' in audio_file.mime_type:
                        file_extension = '.ogg'
                    elif 'wav' in audio_file.mime_type:
                        file_extension = '.wav'

                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    temp_path = temp_file.name

                # Download voice file to temporary file
                await self.bot.download_file(file_path, temp_path)
                self.logger.debug(f"Voice file downloaded to: {temp_path}")

                # Transcribe voice to text using agent
                self.logger.info(f"Transcribing voice message for user {user_id}")
                transcribed_text = await self.agent.transcribe_voice(temp_path)

                if not transcribed_text or not transcribed_text.strip():
                    self.logger.warning(f"Empty transcription for user {user_id}")
                    await message.answer("I couldn't understand the voice message. Could you please try again or send a text message?")
                    return

                self.logger.info(f"Voice transcribed for user {user_id}: {transcribed_text[:100]}...")

                # Process transcribed text with AI agent
                response = await self.agent.process_message(user_id, transcribed_text)
                self.logger.info(f"AI response generated for user {user_id}")

                # Check if response contains photo URLs and send them
                await self.send_response_with_photos(message, response)

                # Update bot response time and schedule follow-up messages
                self.update_bot_response_time(user_id)
                self.schedule_followups(user_id)

            except Exception as e:
                self.logger.error(f"Error processing voice message from user {user_id}: {e}", exc_info=True)
                # Try HTML first, then plain text for error message
                try:
                    await message.answer("I apologize, but I had trouble processing your voice message. Please try sending it again or use text instead.", parse_mode="HTML")
                except Exception as html_error:
                    self.logger.warning(f"HTML formatting failed for error message: {html_error}")
                    await message.answer("I apologize, but I had trouble processing your voice message. Please try sending it again or use text instead.")
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
                
                # Check if this is the first message from this user
                is_first_message = user_id not in self.first_message_sent

                if is_first_message:
                    # Mark that this user has sent their first message
                    self.first_message_sent.add(user_id)
                    self.logger.info(f"First message from user {user_id}, waiting 15 seconds before responding...")

                    # Wait 15 seconds to simulate human-like response time
                    await asyncio.sleep(15)
                    self.logger.info(f"15 second delay completed for user {user_id}, processing with AI...")

                # Update last message time and cancel pending follow-ups
                self.update_user_activity(user_id)

                # Send typing indicator
                await self.bot.send_chat_action(user_id, "typing")
                
                # Process with AI agent
                response = await self.agent.process_message(user_id, user_message)
                self.logger.info(f"AI response generated for user {user_id}")
                
                # Check if response contains photo URLs and send them
                await self.send_response_with_photos(message, response)

                # Update bot response time and schedule follow-up messages
                self.update_bot_response_time(user_id)
                self.schedule_followups(user_id)
                
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

    def update_user_activity(self, user_id: int):
        """Update last message time and cancel pending follow-ups."""
        self.last_message_time[user_id] = time.time()

        # Cancel any pending follow-up tasks
        if user_id in self.pending_followups:
            for followup_type, task in self.pending_followups[user_id].items():
                if not task.done():
                    task.cancel()
                    self.logger.debug(f"Cancelled pending {followup_type} follow-up for user {user_id}")
            self.pending_followups[user_id] = {}

        # Reset sent follow-ups when user is active
        if user_id in self.sent_followups:
            self.sent_followups[user_id] = set()

    def update_bot_response_time(self, user_id: int):
        """Update last bot response time when bot sends a message."""
        self.last_bot_response_time[user_id] = time.time()

    def schedule_followups(self, user_id: int):
        """Schedule follow-up messages for inactive users."""
        # Initialize pending followups dict for user if needed
        if user_id not in self.pending_followups:
            self.pending_followups[user_id] = {}

        # Initialize sent followups set for user if needed
        if user_id not in self.sent_followups:
            self.sent_followups[user_id] = set()

        # Schedule first follow-up: 20 seconds
        if "first" not in self.pending_followups[user_id] or self.pending_followups[user_id]["first"].done():
            task1 = asyncio.create_task(self.send_followup(user_id, "first", 20))
            self.pending_followups[user_id]["first"] = task1

        # Schedule second follow-up: 5 minutes (300 seconds)
        if "second" not in self.pending_followups[user_id] or self.pending_followups[user_id]["second"].done():
            task2 = asyncio.create_task(self.send_followup(user_id, "second", 300))
            self.pending_followups[user_id]["second"] = task2

        # Schedule third follow-up: 5 hours (18000 seconds)
        if "third" not in self.pending_followups[user_id] or self.pending_followups[user_id]["third"].done():
            task3 = asyncio.create_task(self.send_followup(user_id, "third", 18000))
            self.pending_followups[user_id]["third"] = task3

    async def send_followup(self, user_id: int, followup_type: str, delay_seconds: float):
        """Send a follow-up message after delay if user hasn't responded."""
        try:
            # Wait for the delay
            await asyncio.sleep(delay_seconds)

            # Check if user has sent a message since the bot's last response
            if user_id in self.last_bot_response_time:
                bot_response_time = self.last_bot_response_time[user_id]

                # If user responded after bot's last message, don't send follow-up
                if user_id in self.last_message_time:
                    user_message_time = self.last_message_time[user_id]
                    if user_message_time > bot_response_time:
                        self.logger.info(f"Skipping {followup_type} follow-up for user {user_id} - user responded after bot's message")
                        return

            # Check if this follow-up was already sent
            if user_id in self.sent_followups and followup_type in self.sent_followups[user_id]:
                self.logger.debug(f"{followup_type} follow-up already sent for user {user_id}")
                return

            # Mark this follow-up as sent
            if user_id not in self.sent_followups:
                self.sent_followups[user_id] = set()
            self.sent_followups[user_id].add(followup_type)

            self.logger.info(f"Sending {followup_type} follow-up to user {user_id} after {delay_seconds} seconds")

            # Create context message about user not responding
            time_description = self._format_time_description(delay_seconds)
            context_message = f"user did not answer in {time_description}"

            # Use the agent's process_message to generate follow-up response
            # This ensures it uses the same conversation context
            try:
                followup_message = await self.agent.process_message(user_id, context_message)

                if followup_message:
                    # Send the follow-up message
                    await self.bot.send_message(user_id, followup_message, parse_mode="HTML")
                    self.logger.info(f"Follow-up message sent to user {user_id}")
                else:
                    self.logger.warning(f"Failed to generate follow-up message for user {user_id}")
            except Exception as e:
                self.logger.error(f"Error generating follow-up message for user {user_id}: {e}", exc_info=True)
                # Fallback messages based on follow-up type
                fallback_messages = {
                    "first": "Did you like what you saw? 😊",
                    "second": "Do you want something different? I'm here to help! 💐",
                    "third": "Waiting for your answer! Maybe you want something different like... 🌸"
                }
                fallback = fallback_messages.get(followup_type, "How can I help you find the perfect bouquet? 💐")
                await self.bot.send_message(user_id, fallback, parse_mode="HTML")
                # Add fallback to context
                self.agent.add_to_context(user_id, "assistant", fallback)

        except asyncio.CancelledError:
            self.logger.debug(f"Follow-up {followup_type} for user {user_id} was cancelled")
        except Exception as e:
            self.logger.error(f"Error sending {followup_type} follow-up to user {user_id}: {e}", exc_info=True)

    def _format_time_description(self, seconds: float) -> str:
        """Format time description for context messages."""
        if seconds < 60:
            return f"{int(seconds)}sec"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minutes"
        else:
            hours = int(seconds / 3600)
            return f"{hours} hours"


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
