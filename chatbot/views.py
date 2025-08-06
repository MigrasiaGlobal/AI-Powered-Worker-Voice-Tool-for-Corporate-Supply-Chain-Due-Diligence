import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages

from .models import ChatSession, ChatMessage, BuyerCompany, PolicyViolation
from .session_manager import SessionManager
from .utils import UtilsManager
import textwrap
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class BaseViewManager:
    """Base class for view managers"""
    def __init__(self):
        self.utils_manager = UtilsManager()


class PageViewManager(BaseViewManager):
    """Manager for basic page views"""
    
    def index(self, request):
        """Render the index page"""
        return render(request, 'chatbot/index.html')
    
    def about(self, request):
        """Render the about page"""
        return render(request, 'chatbot/about.html')
    
    def dashboard(self, request):
        """Render the dashboard page with metrics"""
        sessions = ChatSession.objects.all().order_by('-created_at')
        
        # Calculate metrics properly in Python
        total_violations = sum(session.violations.count() for session in sessions)
        total_incidents = 0
        
        for session in sessions:
            for violation in session.violations.all():
                incidents_list = violation.get_incidents_list()
                total_incidents += len(incidents_list)
        
        # Calculate unique factories
        unique_factories = sessions.values('factory_name').distinct().count()
        
        context = {
            'sessions': sessions,
            'total_violations': total_violations,
            'total_incidents': total_incidents,
            'unique_factories': unique_factories,
        }
        
        return render(request, 'chatbot/dashboard.html', context)
    
    def session_detail(self, request, session_id):
        """Render the session detail page"""
        session = ChatSession.objects.get(id=session_id)
        messages = session.messages.all()
        violations = session.violations.all()
        buyer_companies = session.buyer_companies.all()
        
        return render(request, 'chatbot/session_detail.html', {
            'session': session,
            'messages': messages,
            'violations': violations,
            'buyer_companies': buyer_companies
        })

class ChatViewManager(BaseViewManager):
    """Manager for chat-related views and handlers"""
    
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
    
    @csrf_exempt
    @require_POST
    def chat_message(self, request):
        """Handle incoming chat messages"""
        # Parse request data
        data = json.loads(request.body)
        user_message = data.get('message', '')
        new_session = data.get('new_session', False)
        
        print(f"User message: {user_message}")
        print(f"Session ID: {request.session.get('chat_session_id')}")
        print(f"New session: {new_session}")
        
        # Get or create session using session manager
        session = self.session_manager.get_or_create_session(request, user_message, force_new=new_session)
        
        # Handle session creation failure
        if not session:
            return JsonResponse({
                'error': 'Failed to create or retrieve session. Please try again.'
            }, status=500)
        
        # Save user message to the session
        if user_message:
            ChatMessage.objects.create(session=session, role='user', content=user_message)
        
        # If this is a new session (just created), handle language detection
        if new_session or request.session.get('conversation_state') == 'language_detection':
            return self.handle_language_detection(request, session, user_message)
        
        # Get conversation state
        conversation_state = request.session.get('conversation_state', 'language_detection')
        print(f"Current conversation state: {conversation_state}")
        
        # Route to appropriate handler based on conversation state
        if conversation_state == 'location_detection':
            return self.handle_location_detection(request, session, user_message)
        elif conversation_state == 'gender_nationality_detection':
            return self.handle_gender_nationality_detection(request, session, user_message)
        elif conversation_state == 'case_description':
            return self.handle_case_description(request, session, user_message)
        elif conversation_state == 'case_handling':
            return self.handle_case_conversation(request, session, user_message)
        else:
            # Fallback
            return self.handle_fallback(session, user_message)

    def handle_language_detection(self, request, session, user_message):
        """Handle language detection phase"""
        print(f"Handling language detection for message: {user_message}")
        
        # Check if language is already detected
        if session.language:
            print(f"Language already detected: {session.language}")
            # Move to next state
            request.session['conversation_state'] = 'location_detection'
            return self.handle_location_detection(request, session, user_message)
        
        # Try to detect language
        detected_language = self.utils_manager.identify_language(user_message)
        print(f"Detected language: {detected_language}")
        
        if detected_language and detected_language.lower() not in ['none', 'unknown', '']:
            # Save detected language
            session.language = detected_language
            session.save()
            
            # Move to location detection
            request.session['conversation_state'] = 'location_detection'
            
            bot_response = "Thank you! Kindly provide your current location (the country or region where you are currently situated)."
            
            # Translate response if language is not English
            if detected_language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, detected_language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        else:
            # Language detection failed, ask explicitly
            bot_response = "Hello! I am PoBot. I couldn't detect your language. Please tell me which language you prefer to use: English, Bahasa Indonesia, Burmese, Vietnamese, or Thai?"
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})

    def handle_location_detection(self, request, session, user_message):
        """Handle location detection phase"""
        print(f"Handling location detection for message: {user_message}")
        
        # Translate user message to English if needed
        translated_message = user_message
        if session.language and session.language.lower() != 'english':
            translated_message = self.utils_manager.translate_to_English(user_message)
            print(f"Translated message: {translated_message}")
        
        # Check if location is already detected
        if session.location:
            print(f"Location already detected: {session.location}")
            # Move to gender and nationality detection
            request.session['conversation_state'] = 'gender_nationality_detection'
            bot_response = f"Thank you for providing your location in {session.location}! Could you please tell me your gender and nationality?"
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        
        # Try to extract location
        detected_location = self.utils_manager.extract_location(translated_message)
        print(f"Detected location: {detected_location}")
        
        if detected_location and detected_location.lower() not in ['none', 'unknown', '', 'null']:
            # Save detected location
            session.location = detected_location
            session.save()
            
            # Move to gender and nationality detection
            request.session['conversation_state'] = 'gender_nationality_detection'
            
            bot_response = f"Thank you for providing your location in {detected_location}! Could you please tell me your gender and nationality?"
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        else:
            # Location extraction failed, ask again
            bot_response = "I need to know your location to better assist you. Could you please tell me which country you are in? For example: Indonesia, Thailand, Vietnam, etc."
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})

    def handle_gender_nationality_detection(self, request, session, user_message):
        """Handle gender and nationality detection phase"""
        print(f"Handling gender and nationality detection for message: {user_message}")
        
        # Translate user message to English if needed
        translated_message = user_message
        if session.language and session.language.lower() != 'english':
            translated_message = self.utils_manager.translate_to_English(user_message)
            print(f"Translated message: {translated_message}")
        
        # Check if both gender and nationality are already detected
        if session.gender and session.nationality:
            print(f"Gender and nationality already detected: {session.gender}, {session.nationality}")
            # Move to case description
            request.session['conversation_state'] = 'case_description'
            bot_response = f"Thank you for providing your gender ({session.gender}) and nationality ({session.nationality})! How can I help you?"
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        
        # Try to extract gender and nationality
        detected_gender = self.utils_manager.extract_gender(translated_message)
        detected_nationality = self.utils_manager.extract_nationality(translated_message)
        print(f"Detected gender: {detected_gender}")
        print(f"Detected nationality: {detected_nationality}")
        
        # Update session with any detected information
        updated = False
        if detected_gender and detected_gender.lower() not in ['none', 'unknown', '', 'null']:
            session.gender = detected_gender
            updated = True
        
        if detected_nationality and detected_nationality.lower() not in ['none', 'unknown', '', 'null']:
            session.nationality = detected_nationality
            updated = True
        
        if updated:
            session.save()
        
        # Check if we have both gender and nationality now
        if session.gender and session.nationality:
            # Move to case description
            request.session['conversation_state'] = 'case_description'
            
            bot_response = f"Thank you for providing your gender ({session.gender}) and nationality ({session.nationality})! How can I help you?"
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        else:
            # Still missing some information, ask again
            missing_info = []
            if not session.gender:
                missing_info.append("gender")
            if not session.nationality:
                missing_info.append("nationality")
            
            missing_str = " and ".join(missing_info)
            bot_response = f"Could you please tell me your {missing_str}?"
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})

    def handle_case_description(self, request, session, user_message):
        """Handle case description phase"""
        print(f"Handling case description for message: {user_message}")
        
        # Translate user message to English if needed
        translated_message = user_message
        if session.language and session.language.lower() != 'english':
            translated_message = self.utils_manager.translate_to_English(user_message)
            print(f"Translated message: {translated_message}")
        
        # Check if case type is already identified
        case_type = request.session.get('case_type')
        if case_type:
            print(f"Case type already identified: {case_type}")
            # Move to case handling
            request.session['conversation_state'] = 'case_handling'
            return self.handle_case_conversation(request, session, user_message)
        
        # Try to identify case type
        detected_case_type = self.utils_manager.identify_case_type(translated_message)
        print(f"Detected case type: {detected_case_type}")
        
        case_info = self.utils_manager.get_graph_for_case(detected_case_type)
        
        if not case_info:
            bot_response = "I'm sorry, I couldn't identify the type of case you're describing. Could you provide more details about your situation?"
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        
        case_type, G = case_info
        
        # Save case type
        session.case_type = case_type
        session.save()
        
        # Save to session
        request.session['case_type'] = case_type
        request.session['current_node'] = 'start'
        request.session['conversation_state'] = 'case_handling'
        
        # Get message history
        history = []
        for msg in session.messages.all():
            history.append({"role": msg.role, "content": msg.content})
        
        # Generate response for start node
        prompt = self.utils_manager.build_prompt(case_type, 'start', G, history, translated_message)
        messages = [{"role": "user", "content": prompt}]
        bot_response = self.utils_manager.query_ollama(messages)
        
        # Translate response if language is not English
        if session.language and session.language.lower() != 'english':
            bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
        
        ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
        return JsonResponse({'message': bot_response})

class PDFManager(BaseViewManager):
    """Manager for PDF-related functionality"""
    
    def __init__(self):
        super().__init__()
    
    def download_session_pdf(self, request, session_id):
        """Download PDF report for a specific session"""
        try:
            # Generate PDF
            pdf_response = self.utils_manager.generate_session_pdf(session_id)
            
            if pdf_response:
                return pdf_response
            else:
                # Return error response
                return JsonResponse({'error': 'Failed to generate PDF report'}, status=500)
                
        except Exception as e:
            return JsonResponse({'error': f'Error generating PDF: {str(e)}'}, status=500)




        
        # Get message history
        history = []
        for msg in session.messages.all():
            history.append({"role": msg.role, "content": msg.content})
        
        # Extract industrial_sector if we're in the collect_basic_info node
        if current_node == 'collect_basic_info':
            industrial_sector = self.utils_manager.extract_industrial_sector(translated_message)
            if industrial_sector:
                session.industrial_sector = industrial_sector
                session.save()
                print(f"Extracted industrial sector: {industrial_sector}")
        
        # Check if we should navigate to next state
        is_navigate = self.utils_manager.check_navigation_to_next_state(history, current_node, G)
        
        # If navigation is approved, move to next node and create a cohesive response
        if is_navigate == "Yes":
            next_steps = list(G.successors(current_node))
            if next_steps:
                next_node = next_steps[0]
                print(f"Moving from {current_node} to {next_node}")
                request.session['current_node'] = next_node
                
                # Special handling for report generation
                if next_node == "generate_report":
                    # Generate acknowledgment response for current node
                    prompt = self.utils_manager.build_prompt(case_type, current_node, G, history, translated_message)
                    messages = [{"role": "user", "content": prompt}]
                    bot_response = self.utils_manager.query_ollama(messages)
                    
                    # Translate response if language is not English
                    if session.language and session.language.lower() != 'english':
                        bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
                    
                    ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
                    return self.handle_report_generation(request, session, history)
                
                # For other nodes, create a cohesive response that acknowledges and transitions
                current_info = G.nodes[current_node]["text"]
                next_info = G.nodes[next_node]["text"]
                
                # Build a cohesive prompt that combines acknowledgment and next question
                cohesive_prompt = f"""
You are a helpful legal assistant chatbot. The user has provided information for the current step and you need to acknowledge it and smoothly transition to ask for the next required information.

Current step that was completed: {current_info}
Next step requirements: {next_info}

Chat history: {history}
User's latest message: {translated_message}

Create a single, cohesive response that:
1. Acknowledges and thanks the user for the information they provided
2. Smoothly transitions to ask for the next required information
3. Maintains a professional and empathetic tone
4. Flows naturally as one conversation turn

Make the transition feel natural and connected, not like two separate responses.
"""
                messages = [{"role": "user", "content": cohesive_prompt}]
                bot_response = self.utils_manager.query_ollama(messages)
            else:
                # No next steps, just acknowledge
                prompt = self.utils_manager.build_prompt(case_type, current_node, G, history, translated_message)
                messages = [{"role": "user", "content": prompt}]
                bot_response = self.utils_manager.query_ollama(messages)
        else:
            # Stay on current node, just respond to user input
            prompt = self.utils_manager.build_prompt(case_type, current_node, G, history, translated_message)
            messages = [{"role": "user", "content": prompt}]
            bot_response = self.utils_manager.query_ollama(messages)
        
        # Translate response if language is not English
        if session.language and session.language.lower() != 'english':
            bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
        
        ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
        print("Chat history: ", history)
        return JsonResponse({'message': bot_response})

    def handle_legal_rights_inquiry(self, request, session, user_message, translated_message):
        """Handle legal rights inquiry using RAG approach"""
        print(f"Handling legal rights inquiry for message: {translated_message}")
        
        current_node = request.session.get('current_node')
        
        # Get message history for context
        history = []
        for msg in session.messages.all():
            history.append({"role": msg.role, "content": msg.content})
        
        if current_node == 'start':
            # Move to RAG response node
            request.session['current_node'] = 'rag_response'
            
            # Use the RAG approach to generate response
            bot_response = self.utils_manager.respond_based_on_the_context_agent(translated_message, history)
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        
        elif current_node == 'rag_response':
            # Continue using RAG for follow-up questions
            bot_response = self.utils_manager.respond_based_on_the_context_agent(translated_message, history)
            
            # Translate response if language is not English
            if session.language and session.language.lower() != 'english':
                bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
            
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            return JsonResponse({'message': bot_response})
        
        else:
            # Fallback to regular handling
            return self.handle_fallback(session, user_message)

    def handle_report_generation(self, request, session, history):
        """Handle report generation"""
        print("Handling report generation")
        
        # Extract factory name
        factory_name = self.utils_manager.extract_factory_name(history)
        session.factory_name = factory_name
        session.save()
        print("The factory name: ", factory_name)
        
        # Get buyer companies
        buyer_companies = self.utils_manager.search_buyer_company_from_factory(factory_name)
        print("The buyer companies: ", buyer_companies)
        
        # Save buyer companies
        for buyer in buyer_companies:
            BuyerCompany.objects.create(session=session, name=buyer)
        
        # Collect incident description
        incident_description_chat = "\n".join(
            [msg["content"] for msg in history if msg["role"] == "user"]
        )
        incident_description = self.utils_manager.extract_incident(incident_description_chat)
        print("Incident summary: ", incident_description)
        session.incident_description = incident_description
        session.save()
        
        # Generate reports
        reports = []
        for buyer in buyer_companies:
            result_json = self.utils_manager.get_company_policy_report(buyer, incident_description)
            reports.append(f"Policy Analysis for {buyer}:\n{result_json}")
            
            # Parse the JSON result
            try:
                result_data = json.loads(result_json)
                
                # Extract structured data
                complaint_summary = result_data.get('complaint_summary', '')
                incidents = result_data.get('incidents', [])
                policy_violations = result_data.get('policy_violations', [])
                
                # Save violation with structured data
                PolicyViolation.objects.create(
                    session=session,
                    buyer_company=buyer,
                    violation_text=result_json,
                    complaint_summary=complaint_summary,
                    incidents=json.dumps(incidents),
                    policy_violations=json.dumps(policy_violations)
                )
            except json.JSONDecodeError:
                # Fallback for non-JSON responses
                PolicyViolation.objects.create(
                    session=session,
                    buyer_company=buyer,
                    violation_text=result_json
                )
        
        # Combine reports
        if reports:
            bot_response = "\n\nThank you for sharing your case. We will analyze the policy violations and will follow-up with you very soon!!"
        else:
            bot_response = "I couldn't find any buyer companies associated with this factory. Please check the factory name or provide more details."
        
        # Translate response if language is not English
        if session.language and session.language.lower() != 'english':
            bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
        
        ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
        return JsonResponse({'message': bot_response, 'complete': True})

    def handle_fallback(self, session, user_message):
        """Handle fallback responses"""
        print(f"Handling fallback for message: {user_message}")
        
        bot_response = "I'm sorry, I'm having trouble understanding. Could you please provide more details about your situation?"
        
        # Translate response if language is not English
        if session.language and session.language.lower() != 'english':
            bot_response = self.utils_manager.translation_from_English(bot_response, session.language)
        
        ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
        return JsonResponse({'message': bot_response})

class SessionViewManager(BaseViewManager):
    """Manager for session-related functionality"""
    
    def __init__(self):
        super().__init__()
    
    def delete_session(self, request, session_id):
        """Delete a specific session and redirect to dashboard"""
        session = get_object_or_404(ChatSession, id=session_id)
        
        if request.method == 'POST':
            session_info = f"Session {session.id} - {session.factory_name or 'Unknown Factory'}"
            session.delete()
            messages.success(request, f"Successfully deleted {session_info}")
            return redirect('dashboard')
        
        # If GET request, show confirmation page or redirect
        return redirect('session_detail', session_id=session_id)
