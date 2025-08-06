import json
import logging
from typing import Optional, Dict, Any
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from .models import ChatSession, ChatMessage

# Configure logging
logger = logging.getLogger(__name__)

# Session key constants
SESSION_KEYS = {
    'CHAT_SESSION_ID': 'chat_session_id',
    'CURRENT_NODE': 'current_node',
    'CASE_TYPE': 'case_type',
    'CONVERSATION_STATE': 'conversation_state',
    'INITIALIZED': 'initialized',
    'GENDER_NATIONALITY': 'gender_nationality'
}

class SessionManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize_session(self, request: HttpRequest) -> None:
        """Initialize session with default values if not already initialized"""
        try:
            if not request.session.get(SESSION_KEYS['INITIALIZED'], False):
                # Default session data
                session_data = {
                    SESSION_KEYS['CHAT_SESSION_ID']: None,
                    SESSION_KEYS['CURRENT_NODE']: 'start',
                    SESSION_KEYS['CASE_TYPE']: None,
                    SESSION_KEYS['CONVERSATION_STATE']: 'language_detection',
                    SESSION_KEYS['INITIALIZED']: True
                }
                
                # Set session data
                for key, value in session_data.items():
                    request.session[key] = value
                    
                logger.info("Session initialized with default values")
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            raise
    
    def get_or_create_session(self, request: HttpRequest, user_message: str, force_new: bool = False) -> Optional[ChatSession]:
        """Get existing session or create a new one"""
        try:
            # Initialize session if needed
            self.initialize_session(request)
            
            # Get current session ID
            session_id = request.session.get(SESSION_KEYS['CHAT_SESSION_ID'])
            logger.info(f"Found session ID: {session_id}")
            
            if force_new:
                logger.info(f"Force New session requested! Clearing existing session: {session_id}")
                self.clear_session_data(request)
                session_id = None
                # Set initialized flag after clearing
                request.session[SESSION_KEYS['INITIALIZED']] = True
                request.session.save()
            
            # Try to get existing session
            chat_session = None
            if session_id:
                try:
                    chat_session = ChatSession.objects.get(id=session_id)
                    logger.info(f"Continuing with existing session: {session_id}")
                except ChatSession.DoesNotExist:
                    logger.warning(f"Session {session_id} not found in database, creating new one")
                    chat_session = None
            
            # Create new session if needed
            if not chat_session:
                chat_session = ChatSession.objects.create()
                request.session[SESSION_KEYS['CHAT_SESSION_ID']] = chat_session.id
                request.session.save()
                logger.info(f"Created new session: {chat_session.id}")
            
            return chat_session
            
        except Exception as e:
            logger.error(f"Error in get_or_create_session: {e}")
            # Return None to indicate failure, let calling code handle it
            return None
    
    def clear_session_data(self, request: HttpRequest) -> None:
        """Clear session data but preserve Django's authentication data and initialized flag"""
        try:
            # Keys to preserve (authentication related and session state)
            keys_to_preserve = ['_auth_user_id', '_auth_user_backend', '_auth_user_hash', SESSION_KEYS['INITIALIZED']]
            preserved_data = {key: request.session[key] for key in keys_to_preserve if key in request.session}
            
            # Session keys to clear
            session_keys_to_clear = [
                SESSION_KEYS['CHAT_SESSION_ID'], 
                SESSION_KEYS['CURRENT_NODE'], 
                SESSION_KEYS['CASE_TYPE'], 
                SESSION_KEYS['CONVERSATION_STATE']
            ]
            
            # Clear specific session keys
            for key in session_keys_to_clear:
                if key in request.session:
                    del request.session[key]
            
            # Restore preserved data
            for key, value in preserved_data.items():
                request.session[key] = value
                
            # Ensure session is saved
            request.session.save()
            logger.info("Session data cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing session data: {e}")
            raise
    
    @csrf_exempt
    def clear_session(self, request):
        """API endpoint to clear the session"""
        self.clear_session_data(request)
        return JsonResponse({'status': 'session cleared'})