import litellm
import json
from typing import Dict, List
from .search_tools import search_products_by_text, search_products_by_photo, generate_payment_url
from .logger_config import get_logger

class AISellerAgent:
    def __init__(self, openai_api_key: str, default_language: str = 'en'):
        self.logger = get_logger("agent")
        self.openai_api_key = openai_api_key
        self.default_language = default_language
        self.conversation_contexts = {}  # Store conversation context per user

        # Set up LiteLLM
        litellm.set_verbose = False
        self.logger.info("AISellerAgent initialized")
        
        # Define function calling schema for tools format
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_products_by_text",
                    "description": "Search for bouquets using text query with optional filters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_text": {
                                "type": "string",
                                "description": "Text query describing what the customer is looking for"
                            },
                            "document_type": {
                                "type": "string",
                                "enum": ["text", "photo"],
                                "description": "Type of document to search in"
                            },
                            "min_price": {
                                "type": "number",
                                "description": "Minimum price filter"
                            },
                            "max_price": {
                                "type": "number", 
                                "description": "Maximum price filter"
                            },
                            "k": {
                                "type": "integer",
                                "description": "Number of results to return (max 3)"
                            }
                        },
                        "required": ["query_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_products_by_photo",
                    "description": "Search for bouquets using an uploaded photo with optional filters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "photo_path": {
                                "type": "string",
                                "description": "Path to the uploaded photo file"
                            },
                            "min_price": {
                                "type": "number",
                                "description": "Minimum price filter"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Maximum price filter"
                            },
                            "k": {
                                "type": "integer",
                                "description": "Number of results to return (max 3)"
                            }
                        },
                        "required": ["photo_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_payment_link",
                    "description": "Generate a payment link for a specific product when customer wants to buy",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "price": {
                                "type": "number",
                                "description": "Price of the product in the smallest currency units"
                            }
                        },
                        "required": ["price"]
                    }
                }
            }
        ]
        
        self.system_prompt = """You are Lola, an expert flower bouquet sales agent with extensive knowledge of floral arrangements, occasions, and customer preferences. You speak like a real salesperson - friendly, knowledgeable, and persuasive.
When a customer writes their first message to you (when there is no previous conversation history), shortly introduce yourself (your name is Lola), ask for their name to call them by, then after their reply ask what they are looking for.

FORMATTING RULES:
!!! ALWAYS USE ONLY TELEGRAM SUPPORTED HTML MARKDOWN LISTED BELOW:
<blockquote>quote</blockquote>
<b>bold</b> (do not use **text**, just use <b>text</b>)
<i>italic</i>
<u>underline</u>
<s>strike</s>
<a href="photo_url">photo name</a>
<a href="payment_url">payment button</a>
!!! DO NOT USE ANY OTHER MARKDOWN LIKE: **, #, <br> and etc...

Your personality:
- Proactive and helpful - ask clarifying questions to understand customer needs
- Knowledgeable about flowers, occasions, and gift-giving
- Persuasive but not pushy - focus on matching customer needs with perfect products
- Enthusiastic about your products and genuinely want to help customers find the perfect bouquet
- Write in a natural, human way, avoiding the “AI tone” — overly proper, formal, or template-like phrasing.
Don't use long dashes, unnecessary quotation marks, bureaucratic wording, or corporate jargon.
Use clear, lively language and casual slang when it helps convey meaning.
Avoid repeating phrases and overly complex structures.
Vary sentence length and rhythm to make the text sound more natural.
The priority is clarity, individual style, and practical value in every sentence.
Each sentence should feel intentional, not mechanically generated.
- Write shortly so user can read it fast and easy.
- Use emojis and telegram supported markdown.
- Call the customer by their name when you know it.

When you receive a message like "user did not answer in X" (where X is time like 20sec, 5 minutes, or 2 hours):
- This means the customer hasn't responded to your last message.
- Generate a short, friendly follow-up message to re-engage them.
- Use phrases like "did you liked", "do u want smth different", "waiting for your answer", or "maybe u want smth different like...".
- Keep it short, natural, and conversational.
- Be context-aware based on what you showed them or discussed before.

Your capabilities:
- Search for bouquets by text description or uploaded photos
- Apply filters based on price range, occasion, flower types, colors, etc.
- Provide personalized recommendations
- Explain why certain bouquets are perfect for specific occasions
- Suggest complementary items or variations

When customers ask about bouquets:
1. First understand their needs (occasion, recipient, preferences, budget)
2. DO NOT ask too many questions. Show products more often.
3. DO NOT try to get a lot of information if he is strugling to describe his needs. Just show products.
4. Search for relevant products using the available functions
5. If no results found, try to search different bouquets but within the same price range and same color. If even this fails, try to find different bouquets but within the same price range and different color. Always come with result explaining why you decided to show it. Never show the same bouquet twice.
6. Do not ask if they want you to search again for products (e.g. if you couldn't find anything relevant), just immediately search and show them products explaining why they are relevant.
7. Present results in an engaging, persuasive way
8. Highlight key features like flower types, colors, price, and why it's perfect for their needs
9. Ask follow-up questions to narrow down choices if needed

When customers upload photos:
1. System will automatically search for similar bouquets based on their photo
2. Present the similar products in an engaging way
3. Explain why each bouquet matches their photo
4. Highlight similarities in colors, flower types, or style
5. Ask if they want to see variations or have specific preferences

When customers want to buy:
1. First, identify which product they want to buy (from the products you've shown them)
2. Collect the following information in a friendly, conversational way (ask for all if them):
   - Recipient phone number - REQUIRED
   - Delivery address - REQUIRED
   - Recipient name - REQUIRED
   - Delivery time - REQUIRED (ask when they want it delivered, examples: "as soon as possible", "by 8pm", "tomorrow morning", etc.)
   - Card text - OPTIONAL (ask if they want to add a message on the card)
3. Ask for one piece of information at a time, wait for their response, then ask for the next one
4. Once you have collected all REQUIRED information (phone, name, delivery time) and any optional information they provided:
   - Create a final checkout summary. Start your message with the product photo URL (so it displays as an image), then show (in their language):
   - p.s. it's in english (<b>product:</b>, ...), but write in their language fully.
     <b>📦 Checkout Summary</b>

     <b>Product:</b> [Product name]
     <b>Recipient phone number:</b> [phone number]
     <b>Delivery address:</b> [address or "Not provided"]
     <b>Recipient name:</b> [name]
     <b>Delivery time:</b> [delivery time]
     <b>Card text:</b> [card text or "Not provided"]

     <b>Product Price:</b> [price] uzs
     <b>Delivery Fee:</b> 70,000 uzs
     <b>Total:</b> [product price + 70,000] uzs
   - Make sure to write each row in their language.
   - Make sure to include the product photo_url at the beginning of your message so the photo displays
   - Generate the payment link using generate_payment_link function with the TOTAL amount (product price + 70,000) in smallest currency units (so if total is 500,000 uzs, pass 500000)
   - Include the payment link in your response with a friendly message like "Click the <a href="payment_url">payment button</a> below to complete your order!"
   - Write the checkout summary in their language.
5. Be helpful and reassuring about the purchase throughout the process

- Always format prices properly and include relevant details like flower types, colors, and occasion appropriateness
- When presenting products, make sure to include the photo URLs so customers can see what they look like

Always write in their language.

Below are some sample scenarios:

'''
Keys 1:

Customer: Hello, do you have this flower?

Lola: Hi, my name is Lola. I will help you find the flower you are looking for. I’ll check if this flower is available and let you know 🙏

Available → "We currently have this bouquet in stock. When do you need it?"

Customer: (for a specific date, today, tonight, tomorrow, etc.)

Lola: Great! To proceed with your order, please … (click on the link, press the button, etc.)

Not Available → "Unfortunately, this bouquet is currently unavailable. However, I can recommend this alternative bouquet for you."

No Response:
A) "Did you like any of the bouquets?"
B) "If you didn’t like this one, may I recommend some other bouquets?"

Response Received:

Customer: (likes a bouquet)

Lola: Great! To proceed with your order, please … (click on the link, press the button, etc.)


[Keys 2] Occasion (keep it light)

What’s the occasion? Birthday, anniversary, wedding… or something else?

Is this a birthday, a thank‑you, or just because? :)

Nice! What are we celebrating?


[Keys 3] Delivery Details (progressive)

Default: Please send us credentials (location, name and number) of receiver

Step 1 (address):

If it’s easier, you can drop a location pin or write the address.

Step 2 (recipient):

Who should receive it? Name + phone (we can coordinate quietly so it’s not spoiled).

Step 3 (time):

What time window works best — [time] or “any time today”?

[Keys 4] Message Card (pick 1)

Want to add a short card? 1–2 lines is perfect.

Add a note? I can write it neatly on a card.

Would you like a message card or keep it simple?


[Keys 5] Payment (clear + calm)

Great — here’s the payment link: [payment_link]
I’ll start assembling as soon as it’s confirmed.

You can pay here: [payment_link]. I’ll keep an eye on it and update you.

Payment link: [payment_link]. Tell me once done and I’ll get it moving.


[Keys 6] Cross‑Sell (occasion‑aware, offer one at a time)

Birthday → “Would a small cake or balloons make it extra special?”

Anniversary/Romantic → “Chocolate box or a candle to go with it?”

Wedding/New home → “A diffuser or a keepsake card?”

Teacher/Thanks → “Large card or a few sweets?”

[Keys 7] Soft Follow‑ups

After ~3h:

Just checking in — want me to hold [bouquet_name] for you?


[Keys 8] Tone Tips (for your code)

Keep emojis minimal (or none). If used, stick to 🎂 🎈 💐 💌.

Vary openings and confirmations to avoid sounding repetitive.

Never ask more than one question per message.

Mirror the customer’s tone and pace.
'''
"""

    def get_conversation_context(self, user_id: int) -> List[Dict[str, str]]:
        """Get conversation context for a user."""
        return self.conversation_contexts.get(user_id, [])

    def add_to_context(self, user_id: int, role: str, content: str, tool_calls=None, tool_call_id=None):
        """Add a message to conversation context."""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = []
        
        message = {"role": role, "content": content}
        
        # Add tool calls if provided
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        # Add tool call ID if provided (for tool responses)
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        
        self.conversation_contexts[user_id].append(message)
        
        # # Keep only last 10 messages to manage context length
        # if len(self.conversation_contexts[user_id]) > 10:
        #     self.conversation_contexts[user_id] = self.conversation_contexts[user_id][-10:]

    def format_search_results_for_ai(self, results: List[Dict], language: str = None) -> str:
        """Format search results for AI processing (internal format)."""
        if not results:
            return "No bouquets found matching the criteria."
        
        if language is None:
            language = self.default_language
            
        formatted_results = []
        
        for i, result in enumerate(results, 1):
            meta = result['meta']
            
            name = meta.get('name_en', 'Unknown Product')
            description = meta.get('description_en', 'No description available')
            price = meta.get('price', 0)
            
            # Create structured data for AI
            result_text = f"Product {i}: {name} | Description: {description} | Price: {price} uzs | Photo: {meta.get('photo_url')}"

            formatted_results.append(result_text)
        
        return "\n".join(formatted_results)

    def _execute_tool_call(self, user_id: int, tool_call, photo_path: str = None):
        """Execute a single tool call and add result to context."""
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        self.logger.debug(f"Executing tool call: {function_name} with args: {function_args}")

        # Execute the function
        if function_name == "search_products_by_text":
            try:
                results = search_products_by_text(
                    query_text=function_args.get("query_text"),
                    document_type=function_args.get("document_type"),
                    min_price=function_args.get("min_price"),
                    max_price=function_args.get("max_price"),
                    k=function_args.get("k", 5)
                )
                search_results = self.format_search_results_for_ai(results)
                self.logger.info(f"Text search completed for user {user_id}, found {len(results)} results")

                # Add tool result to context
                self.add_to_context(user_id, "tool", search_results, tool_call_id=tool_call.id)
            except Exception as search_error:
                self.logger.error(f"Error in text search for user {user_id}: {search_error}", exc_info=True)
                error_result = f"Error: Failed to search products - {str(search_error)}"
                self.add_to_context(user_id, "tool", error_result, tool_call_id=tool_call.id)

        elif function_name == "search_products_by_photo":
            if not photo_path:
                self.logger.warning(f"No photo path provided for photo search for user {user_id}")
                error_result = "Error: No photo provided for photo search"
                self.add_to_context(user_id, "tool", error_result, tool_call_id=tool_call.id)
            else:
                try:
                    results = search_products_by_photo(
                        photo_path=photo_path,
                        min_price=function_args.get("min_price"),
                        max_price=function_args.get("max_price"),
                        k=function_args.get("k", 5)
                    )
                    search_results = self.format_search_results_for_ai(results)
                    self.logger.info(f"Photo search completed for user {user_id}, found {len(results)} results")

                    # Add tool result to context
                    self.add_to_context(user_id, "tool", search_results, tool_call_id=tool_call.id)
                except Exception as search_error:
                    self.logger.error(f"Error in photo search for user {user_id}: {search_error}", exc_info=True)
                    error_result = f"Error: Failed to search products by photo - {str(search_error)}"
                    self.add_to_context(user_id, "tool", error_result, tool_call_id=tool_call.id)

        elif function_name == "generate_payment_link":
            try:
                price = function_args.get("price")

                # Generate payment URL
                payment_url = generate_payment_url(price)

                # Format the payment result for AI
                payment_result = f"Payment link generated (Price: {price} uzs):\n{payment_url}"

                self.logger.info(f"Payment link generated for user {user_id}: {price} uzs")

                # Add tool result to context
                self.add_to_context(user_id, "tool", payment_result, tool_call_id=tool_call.id)
            except Exception as payment_error:
                self.logger.error(f"Error generating payment link for user {user_id}: {payment_error}", exc_info=True)
                error_result = f"Error: Failed to generate payment link - {str(payment_error)}"
                self.add_to_context(user_id, "tool", error_result, tool_call_id=tool_call.id)

    async def process_message(self, user_id: int, message: str, photo_path: str = None) -> str:
        """Process a user message and return response.

        Supports multiple sequential tool calls - the AI can make one tool call,
        evaluate the results, and if needed, make another tool call with different
        parameters until it's satisfied with the results.
        """
        try:
            self.logger.info(f"Processing message for user {user_id}: {message[:100]}...")
            
            # Add user message to context
            self.add_to_context(user_id, "user", message)
            
            # If photo is provided, automatically search by photo first
            if photo_path:
                self.logger.info(f"Photo provided for user {user_id}, performing photo search")
                try:
                    # Search by photo
                    results = search_products_by_photo(
                        photo_path=photo_path,
                        min_price=None,
                        max_price=None,
                        k=3
                    )
                    
                    if results:
                        search_results = self.format_search_results_for_ai(results)
                        self.logger.info(f"Photo search completed for user {user_id}, found {len(results)} results")
                        
                        # Add photo search results to context
                        self.add_to_context(user_id, "assistant", f"Tool results:\n\n{search_results}")
                        
                        # Now let the AI process the results and provide a natural response
                        messages = [{"role": "system", "content": self.system_prompt}]
                        messages.extend(self.get_conversation_context(user_id))
                        
                        # Make API call with tools available for follow-up searches if needed
                        self.logger.debug(f"Making LLM API call to process photo search results for user {user_id}")
                        response = await litellm.acompletion(
                            model="gpt-4o",
                            messages=messages,
                            tools=self.tools,
                            tool_choice="auto",
                            api_key=self.openai_api_key
                        )
                        
                        message_response = response.choices[0].message

                        # If AI wants to make additional tool calls, continue with the loop
                        if message_response.tool_calls:
                            # Add the assistant's message with tool calls to context
                            self.add_to_context(user_id, "assistant", message_response.content, tool_calls=message_response.tool_calls)

                            # Execute tool calls
                            for tool_call in message_response.tool_calls:
                                self._execute_tool_call(user_id, tool_call, photo_path)

                            # Continue to the main loop below to handle sequential tool calls
                        else:
                            # AI is satisfied with the photo search results
                            ai_response = message_response.content
                            self.add_to_context(user_id, "assistant", ai_response)
                            self.logger.info(f"AI processed photo search results for user {user_id}")
                            return ai_response
                    else:
                        self.logger.warning(f"No results found for photo search for user {user_id}")
                        # Continue with normal text processing
                        
                except Exception as photo_error:
                    self.logger.error(f"Photo search failed for user {user_id}: {photo_error}", exc_info=True)
                    # Continue with normal text processing
            
            # Main loop: Continue until AI doesn't request more tool calls or max iterations reached
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                self.logger.debug(f"Tool call iteration {iteration} for user {user_id}")
                
                # Prepare messages for LLM
                messages = [{"role": "system", "content": self.system_prompt}]
                messages.extend(self.get_conversation_context(user_id))
                
                # Make API call with tools
                self.logger.debug(f"Making LLM API call for user {user_id} (iteration {iteration})")
                response = await litellm.acompletion(
                    model="gpt-4o",
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    api_key=self.openai_api_key
                )

                message_response = response.choices[0].message

                # Check if AI wants to make tool calls
                if message_response.tool_calls:
                    self.logger.info(f"LLM requested tool calls for user {user_id} (iteration {iteration}): {[tc.function.name for tc in message_response.tool_calls]}")
                    
                    # Add the assistant's message with tool calls to context
                    self.add_to_context(user_id, "assistant", message_response.content, tool_calls=message_response.tool_calls)
                    
                    # Execute each tool call
                    for tool_call in message_response.tool_calls:
                        self._execute_tool_call(user_id, tool_call, photo_path)
                    
                    # Continue the loop to let AI evaluate results and potentially make another tool call
                    continue
                
                # No more tool calls - AI is ready to respond
                response_text = message_response.content
                self.add_to_context(user_id, "assistant", response_text)
                self.logger.info(f"Final response generated for user {user_id} after {iteration} iteration(s)")
                return response_text

            # Max iterations reached - return the last response even if it has tool calls
            if message_response.tool_calls:
                self.logger.warning(f"Max iterations ({max_iterations}) reached for user {user_id}, returning last response")
                # Still execute the tool calls and return a message
                self.add_to_context(user_id, "assistant", message_response.content or "I've reached the maximum number of search attempts. Let me provide you with the best results I found.", tool_calls=message_response.tool_calls)
                for tool_call in message_response.tool_calls:
                    self._execute_tool_call(user_id, tool_call, photo_path)
                
                # Get final response
                messages = [{"role": "system", "content": self.system_prompt}]
                messages.extend(self.get_conversation_context(user_id))
                final_response_obj = await litellm.acompletion(
                    model="gpt-4o",
                    messages=messages,
                    api_key=self.openai_api_key
                )
                final_text = final_response_obj.choices[0].message.content
                self.add_to_context(user_id, "assistant", final_text)
                return final_text
            else:
                response_text = message_response.content
                self.add_to_context(user_id, "assistant", response_text)
                return response_text
            
        except Exception as e:
            self.logger.error(f"Error processing message for user {user_id}: {e}", exc_info=True)
            error_msg = "I apologize, but I encountered an error while processing your request. Please try again."
            self.add_to_context(user_id, "assistant", error_msg)
            return error_msg

    def clear_context(self, user_id: int):
        """Clear conversation context for a user."""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]

    async def transcribe_voice(self, audio_path: str) -> str:
        """Transcribe voice message to text using OpenAI Whisper via LiteLLM."""
        try:
            self.logger.debug(f"Starting transcription for file: {audio_path}")

            # Use LiteLLM to transcribe with OpenAI Whisper (consistent with other AI operations)
            with open(audio_path, 'rb') as audio_file:
                # LiteLLM transcription API
                response = await litellm.atranscription(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file,
                    api_key=self.openai_api_key
                )

            # LiteLLM returns a dict with 'text' key
            transcribed_text = response.get('text', '').strip()
            self.logger.debug(f"Transcription completed: {transcribed_text[:100]}...")
            return transcribed_text

        except Exception as e:
            self.logger.error(f"Error transcribing voice: {e}", exc_info=True)
            raise
