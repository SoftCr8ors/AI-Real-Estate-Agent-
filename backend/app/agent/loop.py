"""
Main agent conversation loop.
Orchestrates LLM calls, tool execution, validation, and state management.
"""

import json
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.agent.lm_client import LLMClient, RateLimitError
from app.agent.prompts import build_state_summary, get_system_prompt
from app.agent.registry import execute_tool
from app.agent.state import load_conversation_state
from app.agent.validator import (
    build_correction_prompt,
    get_safe_fallback_response,
    should_regenerate,
    validate_response,
)
from app.services.conversation import add_message, get_recent_messages
from app.services.leads import (
    get_lead_by_conversation,
    track_property_view,
    update_lead_requirements,
)

# ============================================================================
# AGENT LOOP
# ============================================================================

async def run_agent_loop(
    db: Session,
    conversation_id: int,
    user_message: str,
) -> AsyncGenerator[dict, None]:
    """
    Main agent conversation loop with streaming.

    Args:
        db: Database session
        conversation_id: Current conversation ID
        user_message: User's message

    Yields:
        SSE events (dict with 'event' and 'data')
    """
    # Load conversation state
    state = load_conversation_state(db, conversation_id)

    # Save user message
    add_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content=user_message,
    )

    # Get recent message history (last 12 messages)
    recent_messages = get_recent_messages(db, conversation_id, count=12)

    # Build messages for LLM
    messages = [
        {"role": "system", "content": get_system_prompt()},
    ]

    # Add state summary
    state_summary = build_state_summary(state.get_all())
    messages.append({
        "role": "system",
        "content": f"## Current Conversation State\n{state_summary}",
    })

    # Add conversation history
    for msg in recent_messages:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    # Initialize LLM client
    try:
        llm_client = LLMClient(db)
    except ValueError as e:
        yield {
            "event": "error",
            "data": {
                "error_type": "configuration_error",
                "message": str(e),
                "recoverable": False,
            }
        }
        return

    # Get tool definitions
    # tools = get_all_tools()  # TEMPORARILY DISABLED FOR TESTING
    tools = None  # Test without tools first

    # Agent loop (max 5 iterations to prevent infinite loops)
    max_iterations = 5
    iteration = 0
    validation_attempts = 0

    while iteration < max_iterations:
        iteration += 1

        try:
            # Call LLM
            response = llm_client.generate(
                messages=messages,
                tools=tools,
                temperature=0.7,
                max_tokens=1000,
            )

            # Check if LLM wants to use tools
            if response["tool_calls"]:
                # Execute tools and continue loop
                for tool_call in response["tool_calls"]:
                    async for event in handle_tool_call(
                        db=db,
                        state=state,
                        conversation_id=conversation_id,
                        tool_call=tool_call,
                        messages=messages,
                    ):
                        yield event

                # Continue loop to get final response
                continue

            # No tool calls - validate response
            assistant_message = response["content"]

            is_valid, error_message = validate_response(
                db=db,
                response_text=assistant_message,
                conversation_id=conversation_id,
            )

            if not is_valid:
                # Validation failed
                validation_attempts += 1

                if should_regenerate(validation_attempts):
                    # Try regenerating once
                    correction_prompt = build_correction_prompt(error_message)
                    messages.append({
                        "role": "system",
                        "content": correction_prompt,
                    })
                    continue  # Retry loop
                else:
                    # Use safe fallback
                    assistant_message = get_safe_fallback_response("general")

            # Valid response - save and stream
            token_count = response["usage"].get("total_tokens", 0)

            add_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                token_count=token_count,
            )

            # Save state
            state.save()

            # Stream text response
            yield {
                "event": "text",
                "data": {
                    "text": assistant_message,
                    "is_final": True,
                }
            }

            # Done
            yield {
                "event": "done",
                "data": {}
            }

            return

        except RateLimitError:
            yield {
                "event": "error",
                "data": {
                    "error_type": "rate_limit",
                    "message": "I'm receiving a high volume of requests right now. Please try again in a moment.",
                    "recoverable": True,
                }
            }
            return

        except Exception as e:
            yield {
                "event": "error",
                "data": {
                    "error_type": "service_unavailable",
                    "message": "I'm having trouble processing your request. Please try again.",
                    "recoverable": True,
                }
            }
            # DEBUG: Print the actual error
            print(f"❌ EXCEPTION in agent loop: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return

    # Max iterations reached
    yield {
        "event": "error",
        "data": {
            "error_type": "max_iterations",
            "message": "I'm having trouble completing this request. Let me connect you with a human agent.",
            "recoverable": True,
        }
    }


# ============================================================================
# TOOL HANDLING
# ============================================================================

async def handle_tool_call(
    db: Session,
    state,
    conversation_id: int,
    tool_call: dict,
    messages: list,
) -> AsyncGenerator[dict, None]:
    """
    Execute a tool and update state/messages.

    Args:
        db: Database session
        state: Conversation state
        conversation_id: Conversation ID
        tool_call: Tool call from LLM
        messages: Message list to append to

    Yields:
        SSE events for tool execution
    """
    tool_name = tool_call["name"]

    try:
        # Parse arguments
        if isinstance(tool_call["arguments"], str):
            params = json.loads(tool_call["arguments"])
        else:
            params = tool_call["arguments"]

        # Execute tool
        result = execute_tool(db, tool_name, params)

        # Update state based on tool
        update_state_from_tool(state, conversation_id, tool_name, params, result, db)

        # Send appropriate SSE event
        async for event in format_tool_result(tool_name, params, result):
            yield event

        # Add tool result to messages
        messages.append({
            "role": "assistant",
            "content": f"[Used tool: {tool_name}]",
        })
        messages.append({
            "role": "system",
            "content": f"Tool result: {json.dumps(result.dict() if hasattr(result, 'dict') else result)}",
        })

    except Exception as e:
        # Tool execution failed
        error_message = f"Tool {tool_name} failed: {str(e)}"
        messages.append({
            "role": "system",
            "content": error_message,
        })


# ============================================================================
# STATE UPDATES FROM TOOLS
# ============================================================================

def update_state_from_tool(state, conversation_id, tool_name, params, result, db):
    """Update conversation state based on tool execution."""

    # 1. SEARCH PROPERTIES - extract and save search criteria
    if tool_name == "search_properties":
        if params.get("listing_type"):
            state.set_listing_type(params["listing_type"])

        if params.get("location"):
            state.set_location(params["location"])

        if params.get("max_price"):
            state.set_budget(params["max_price"])

        if params.get("bedrooms") is not None:
            state.set_bedrooms(params["bedrooms"])

        if params.get("property_type"):
            state.set_property_type(params["property_type"])

        # Save last search query
        query_summary = getattr(result, "query_understood", "")
        if query_summary:
            state.set_last_search(query_summary)

    # 2. GET PROPERTY DETAILS - track property views
    elif tool_name == "get_property_details":
        state.increment_properties_viewed()
        property_id = params.get("property_id")
        if property_id:
            state.set_selected_property(property_id)

            # Track in lead if exists
            lead = get_lead_by_conversation(db, conversation_id)
            if lead:
                track_property_view(db, lead.id, property_id)

    # 3. CREATE LEAD - mark lead created
    elif tool_name == "create_lead":
        # Lead created - state will be updated via update_lead_requirements
        lead = get_lead_by_conversation(db, conversation_id)
        if lead:
            update_lead_requirements(db, lead.id, state.get_all())

    # 4. UPDATE LEAD - sync state with lead
    elif tool_name == "update_lead":
        lead = get_lead_by_conversation(db, conversation_id)
        if lead:
            update_lead_requirements(db, lead.id, state.get_all())

            # Extract timeline if provided
            if params.get("expected_timeline"):
                state.set_timeline(params["expected_timeline"])

    # 5. BOOK VIEWING - mark appointment booked
    elif tool_name == "book_viewing":
        state.set_appointment_booked(True)
        state.set_requested_viewing(False)  # Clear viewing request flag

        # Extract contact info from params
        if params.get("customer_name"):
            state.set_contact_info(name=params["customer_name"])

        if params.get("customer_phone"):
            state.set_contact_info(phone=params["customer_phone"])

        if params.get("customer_email"):
            state.set_contact_info(email=params["customer_email"])

    # 6. GET AVAILABLE SLOTS - mark viewing requested
    elif tool_name == "get_available_slots":
        state.set_requested_viewing(True)

    # 7. NOTIFY SALES TEAM - mark handoff requested
    elif tool_name == "notify_sales_team":
        state.set_requested_handoff(True)


# ============================================================================
# FORMAT TOOL RESULTS AS SSE EVENTS
# ============================================================================

async def format_tool_result(tool_name: str, params: dict, result) -> AsyncGenerator[dict, None]:
    """Format tool result as appropriate SSE event."""

    # 1. SEARCH PROPERTIES
    if tool_name == "search_properties":
        if result.total_found == 0:
            # No results - send suggestions event
            yield {
                "event": "no_match_suggestions",
                "data": {
                    "original_query": result.query_understood,
                    "suggestions": [
                        {
                            "reason": "No exact matches found",
                            "suggestion": "Try increasing your budget or expanding location",
                            "adjusted_criteria": None,
                        }
                    ]
                }
            }
        else:
            # Send property cards
            yield {
                "event": "property_cards",
                "data": {
                    "properties": [
                        {
                            "property_id": p.property_id,
                            "title": p.title,
                            "location": p.location,
                            "price": p.price,
                            "bedrooms": p.bedrooms,
                            "bathrooms": p.bathrooms,
                            "area_sqft": p.area_sqft,
                            "image_url": None,  # Would come from database
                            "relevance_score": p.relevance_score,
                        }
                        for p in result.properties
                    ],
                    "total_found": result.total_found,
                    "query_summary": result.query_understood,
                }
            }

    # 2. GET PROPERTY DETAILS
    elif tool_name == "get_property_details":
        prop = result.property
        yield {
            "event": "property_details",
            "data": {
                "property_id": prop.property_id,
                "title": prop.title,
                "description": prop.description,
                "location": prop.location,
                "price": prop.price,
                "bedrooms": prop.bedrooms,
                "bathrooms": prop.bathrooms,
                "area_sqft": prop.area_sqft,
                "listing_type": prop.listing_type,
                "property_type": prop.property_type,
                "availability": prop.availability,
                "amenities": prop.amenities,
                "images": prop.images,
                "agent_name": prop.agent_name,
                "agent_phone": prop.agent_phone,
            }
        }

    # 3. GET AVAILABLE SLOTS
    elif tool_name == "get_available_slots":
        yield {
            "event": "time_slots",
            "data": {
                "property_id": result.property_id,
                "property_title": f"Property #{result.property_id}",
                "slots": [
                    {
                        "slot_id": slot.slot_id,
                        "datetime": slot.datetime.isoformat(),
                        "available": slot.available,
                        "label": slot.datetime.strftime("%A, %B %d at %I:%M %p"),
                    }
                    for slot in result.slots
                ]
            }
        }

    # 4. BOOK VIEWING
    elif tool_name == "book_viewing":
        yield {
            "event": "appointment",
            "data": {
                "booking_id": result.booking_id,
                "property_id": params.get("property_id"),
                "property_title": f"Property #{params.get('property_id')}",
                "slot_datetime": result.slot_datetime.isoformat(),
                "customer_name": params.get("customer_name"),
                "confirmation_sent": result.confirmation_sent,
            }
        }

    # 5. CREATE LEAD - check if contact info needed
    elif tool_name == "create_lead":
        # If lead created but missing contact info, request it
        if result.created and not params.get("customer_name"):
            yield {
                "event": "contact_form_request",
                "data": {
                    "reason": "To help you better, I'll need your contact information",
                    "fields": [
                        {
                            "field_name": "name",
                            "label": "Full Name",
                            "required": True,
                            "current_value": None,
                        },
                        {
                            "field_name": "phone",
                            "label": "Phone Number",
                            "required": True,
                            "current_value": None,
                        },
                        {
                            "field_name": "email",
                            "label": "Email Address",
                            "required": False,
                            "current_value": None,
                        },
                    ],
                    "lead_id": result.lead_id,
                }
            }

    # 6. NOTIFY SALES TEAM - handoff event
    elif tool_name == "notify_sales_team":
        yield {
            "event": "handoff",
            "data": {
                "reason": "Connecting you with our sales team for personalized assistance",
                "urgency": params.get("urgency", "normal"),
                "estimated_wait_time": "A team member will contact you within 1 hour",
                "lead_id": params.get("lead_id"),
            }
        }

    # Other tools (check_property_availability, update_lead, get_customer_history)
    # Results are used internally by the agent, no special SSE events needed
