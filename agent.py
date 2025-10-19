import litellm
import json
import os
from typing import Dict, List, Any, Optional
from search_tools import search_products_by_text, search_products_by_photo, format_price, get_product_name, get_product_description, generate_payment_url
from logger_config import get_logger

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
        
        self.system_prompt = f"""You are an expert flower bouquet sales agent with extensive knowledge of floral arrangements, occasions, and customer preferences. You speak like a real salesperson - friendly, knowledgeable, and persuasive.

FORMATTING RULES:
!!! ALWAYS USE ONLY TELEGRAM SUPPORTED HTML MARKDOWN LISTED BELOW:
<blockquote>quote</blockquote>
<b>bold</b> (do not use **text**, just use <b>text</b>)
<i>italic</i>
<u>underline</u>
<s>strike</s>
<a href="photo_url">photo name</a>
!!! DO NOT USE ANY OTHER MARKDOWN LIKE: **, #, <br> and etc...

Your personality:
- Proactive and helpful - ask clarifying questions to understand customer needs
- Knowledgeable about flowers, occasions, and gift-giving
- Persuasive but not pushy - focus on matching customer needs with perfect products
- Enthusiastic about your products and genuinely want to help customers find the perfect bouquet
- Use natural, conversational language
- Write shortly so user can read it fast and easy.
- Use emojis and telegram supported markdown.

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
5. Present results in an engaging, persuasive way
6. Highlight key features like flower types, colors, price, and why it's perfect for their needs
7. Ask follow-up questions to narrow down choices if needed

When customers upload photos:
1. System will automatically search for similar bouquets based on their photo
2. Present the similar products in an engaging way
3. Explain why each bouquet matches their photo
4. Highlight similarities in colors, flower types, or style
5. Ask if they want to see variations or have specific preferences

When customers want to buy:
2. Provide the payment link with the correct amount
4. Be helpful and reassuring about the purchase

- Always format prices properly and include relevant details like flower types, colors, and occasion appropriateness
- When presenting products, make sure to include the photo URLs so customers can see what they look like

Default language for responses: {default_language}"""

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
            score = result['score']
            
            name = meta.get('name_en', 'Unknown Product')
            description = meta.get('description_en', 'No description available')
            price = meta.get('price', 0)
            
            # Create structured data for AI
            result_text = f"Product {i}: {name} | Description: {description} | Price: {price} uzs | Photo: {meta.get('photo_url')}"

            formatted_results.append(result_text)
        
        return "\n".join(formatted_results)

    async def process_message(self, user_id: int, message: str, photo_path: str = None) -> str:
        """Process a user message and return response."""
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
                        
                        # Make API call without tools since we already have results
                        self.logger.debug(f"Making LLM API call to process photo search results for user {user_id}")
                        response = await litellm.acompletion(
                            model="gpt-4o",
                            messages=messages,
                            api_key=self.openai_api_key
                        )
                        
                        ai_response = response.choices[0].message.content
                        self.logger.info(f"AI processed photo search results for user {user_id}")
                        return ai_response
                    else:
                        self.logger.warning(f"No results found for photo search for user {user_id}")
                        # Continue with normal text processing
                        
                except Exception as photo_error:
                    self.logger.error(f"Photo search failed for user {user_id}: {photo_error}", exc_info=True)
                    # Continue with normal text processing
            
            # Prepare messages for LLM
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.get_conversation_context(user_id))
            
            # Make API call with tools
            self.logger.debug(f"Making LLM API call for user {user_id}")
            response = await litellm.acompletion(
                model="gpt-4o",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                api_key=self.openai_api_key
            )
            
            message_response = response.choices[0].message
            
            # Handle tool calls
            if message_response.tool_calls:
                self.logger.info(f"LLM requested tool calls for user {user_id}: {[tc.function.name for tc in message_response.tool_calls]}")
                
                # Add the assistant's message with tool calls to context
                self.add_to_context(user_id, "assistant", message_response.content, tool_calls=message_response.tool_calls)
                
                # Execute each tool call
                for tool_call in message_response.tool_calls:
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
                
                # Make another API call to get AI's response to the tool results
                self.logger.debug(f"Making follow-up LLM API call for user {user_id}")
                follow_up_messages = [{"role": "system", "content": self.system_prompt}]
                follow_up_messages.extend(self.get_conversation_context(user_id))
                
                follow_up_response = await litellm.acompletion(
                    model="gpt-4o",
                    messages=follow_up_messages,
                    tools=self.tools,
                    api_key=self.openai_api_key
                )
                
                final_response = follow_up_response.choices[0].message.content
                self.add_to_context(user_id, "assistant", final_response)
                self.logger.info(f"Final response generated for user {user_id}")
                return final_response
            
            # Regular response without tool calls
            response_text = message_response.content
            self.add_to_context(user_id, "assistant", response_text)
            self.logger.info(f"Regular response generated for user {user_id}")
            return response_text
            
        except Exception as e:
            self.logger.error(f"Error processing message for user {user_id}: {e}", exc_info=True)
            error_msg = f"I apologize, but I encountered an error while processing your request. Please try again."
            self.add_to_context(user_id, "assistant", error_msg)
            return error_msg

    def clear_context(self, user_id: int):
        """Clear conversation context for a user."""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
