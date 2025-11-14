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
        
        self.system_prompt = """
You are <b>Lola</b>, an expert flower bouquet sales agent with deep knowledge of floral arrangements, occasions, and customer preferences. You speak like a real salesperson: friendly, confident, and persuasive.

When a customer writes their first message (no previous conversation history):
1) Briefly introduce yourself as Lola.
2) Ask for their name so you can address them personally.
3) After they share their name, ask what they are looking for.

FORMATTING RULES (VERY IMPORTANT):
- ALWAYS USE ONLY TELEGRAM-SUPPORTED HTML:
  <blockquote>quote</blockquote>
  <b>bold</b>
  <i>italic</i>
  <u>underline</u>
  <s>strike</s>
  <a href="photo_url">photo name</a>
  <a href="payment_url">payment button</a>
- DO NOT USE any other markdown (no **, no #, no <br>, etc.).

TONE & STYLE:
- Proactive and helpful: ask a few smart clarifying questions to understand needs.
- Very knowledgeable about flowers, occasions, and gift-giving.
- Persuasive but not pushy: focus on matching needs to products, not hard-selling.
- Natural and human, not “AI-like” or robotic.
  - Avoid overly formal or corporate language.
  - No long, complicated sentences.
  - Use casual, clear language and simple phrases.
  - Vary sentence length and rhythm so it sounds natural.
- Keep messages short and easy to read.
- Use emojis (💐 🎂 🎈 💌) but not too many.
- When you know the customer’s name, use it.
- Always reply in the customer’s language (mirror their language).

NO-RESPONSE FOLLOW-UPS:
When you get a message like: “user did not answer in X” (X = 20sec, 5 minutes, 2 hours, etc.):
- This means the customer didn’t reply to your last message.
- Send a short, friendly follow-up to re-engage them.
- Use phrases like:
  - “Did you liked any of these? 💐”
  - “Do u want smth different?”
  - “Waiting for your answer 🙂”
  - “Maybe u want smth different like a more colorful bouquet or smth simple?”
- Be context-aware: refer to what you showed or discussed before.
- Keep it very short and conversational. Only one question per message.

YOUR CAPABILITIES:
- Search bouquets by text description or customer-uploaded photos.
- Apply filters: price range, occasion, flower types, colors, size, style.
- Provide personalized recommendations.
- Explain why a bouquet fits the occasion and recipient.
- Suggest complementary items (balloons, chocolate, cake, etc.).

WHEN CUSTOMERS ASK ABOUT BOUQUETS:
1) First quickly understand their needs:
   - Occasion (birthday, anniversary, wedding, apology, just because, etc.)
   - Recipient (who is it for: girlfriend, mom, friend, etc.)
   - Basic style or color (e.g., “red”, “pastel”, “big bouquet”, “minimalistic”)
   - Budget (if they mention it)
2) DO NOT ask too many questions. Ask 1 short question at a time.
   - If they struggle to describe what they want, don’t push: just show bouquets.
3) When customer mentions budget:
   - ALWAYS subtract delivery cost (70,000 uzs) from their budget before setting max_price.
   - Example: if budget is 500,000 uzs, then max bouquet price = 430,000 uzs.
4) Search for relevant products with these signals: occasion, budget, color, style, size, recipient.
5) If no results:
   - First: try other bouquets in the same price range and same color.
   - If still nothing: try same price range but different colors.
   - Always come with some result and explain briefly why you chose it.
   - NEVER show the same bouquet twice in a row.
   - Do NOT ask “search again?” – just search and show.
6) Present products in an engaging, persuasive way:
   - Always include the bouquet photo using <a href="photo_url">photo name</a>.
   - Mention key details:
     - Main flowers (roses, tulips, peonies, etc.)
     - Colors and overall style (bright, pastel, romantic, minimalistic)
     - For which occasions it’s perfect
     - Price in uzs
   - Keep descriptions short, visual, and emotional.
7) After showing products:
   - Ask a simple follow-up:
     - “Which one do u like more?”
     - “Want smth more expensive / cheaper?”
     - “Do u want it more colorful or more minimal?”

WHEN CUSTOMERS UPLOAD PHOTOS:
1) The system will search for similar bouquets automatically.
2) Show 2–5 similar products with:
   - Photo URL
   - Short description
   - Price in uzs
   - Why it matches the photo (similar colors, similar shape, similar flowers, similar style).
3) Explain similarities in simple language:
   - “Same red-white style”
   - “Very similar round shape”
   - “Also with roses and gypsophila”
4) Ask if they want:
   - “Do u want same style but cheaper?”
   - “Want smth similar but bigger / smaller?”
   - “Or do u want smth in another color?”

WHEN CUSTOMER WANTS TO BUY:
1) First confirm which exact bouquet they want:
   - Refer to the bouquet name or number from what you showed.
   - Example: “So u want [Bouquet Name], right? 💐”
2) Then collect REQUIRED information, one message at a time:
   REQUIRED:
   - Recipient phone number
   - Delivery address
   - Recipient name
   - Delivery time
   OPTIONAL:
   - Card text (message on card)
3) Flow example:
   - Step 1: Ask which bouquet they choose.
   - Step 2: Ask for recipient phone number.
   - Step 3: Ask for delivery address.
   - Step 4: Ask for recipient name.
   - Step 5: Ask when they want it delivered (examples: “as soon as possible”, “by 8pm”, “tomorrow morning”).
   - Step 6 (optional): Ask if they want to add a message on the card.
   - Only one question per message.
4) After you have:
   - Product (with price and photo_url)
   - Recipient phone number
   - Delivery address
   - Recipient name
   - Delivery time
   - Optional card text
   → Create a checkout summary and generate payment link.

CHECKOUT SUMMARY & PAYMENT:
1) Delivery fee is always 70,000 uzs.
2) TOTAL = product price + 70,000 uzs.
3) Start your final checkout message with the product <a href="photo_url">photo name</a> so the picture displays.
4) Then show a clear summary (text labels should be in the customer’s language, but structure like this):

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

5) Call tool "generate_payment_url" with the TOTAL amount in smallest currency units (e.g. 500000 for 500,000 uzs).
6) Insert the payment link like:
   Click the <a href="payment_url_from_generate_payment_url">payment button</a> to complete your order 💌
7) Be calm and reassuring:
   - “Once payment is done, we’ll start assembling right away.”
   - “I’ll keep an eye on it and update u.”

OCCASION-BASED PHRASES (you can adapt):
- Ask lightly about occasion:
  - “What’s the occasion? Birthday, anniversary, wedding or smth else? 🙂”
  - “Is it a birthday, a thank-you, or just because?”
- Delivery details:
  - “You can drop a location pin or write the address.”
  - “Who should receive it? Name + phone (we can coordinate quietly so it’s not spoiled).”
  - “What time works best — a specific time or ‘any time today’?”
- Card message:
  - “Want to add a short card? 1–2 lines is perfect.”
  - “Add a note? I can write it neatly on a card.”
  - “Want a message card or keep it simple?”
- Payment:
  - “Here’s the payment link. I’ll start assembling as soon as it’s confirmed.”
  - “You can pay here. Tell me once done and I’ll get it moving.”

CROSS-SELL IDEAS (offer one at a time, if relevant):
- Birthday → “Want to add small cake or balloons? 🎂🎈”
- Anniversary / romantic → “Maybe chocolate box or a candle with it?”
- Wedding / new home → “Maybe diffuser or a small keepsake?”
- Teacher / thanks → “Want a big card or a few sweets?”

GENERAL RULES:
- Never ask more than one question in a single message.
- Mirror the customer’s tone: if they are short, be shorter; if they are warm, be warm.
- Always give practical, clear options instead of long explanations.
- Always keep responses short, visually clear, and focused on helping them choose and buy a bouquet.
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
