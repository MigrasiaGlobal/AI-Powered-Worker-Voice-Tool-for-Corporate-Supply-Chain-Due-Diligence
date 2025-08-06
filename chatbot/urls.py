from django.urls import path
from . import views
from .session_manager import SessionManager
from .views import PageViewManager, ChatViewManager, PDFManager, SessionViewManager

# Initialize managers
session_manager = SessionManager()
page_view_manager = PageViewManager()
chat_view_manager = ChatViewManager()
pdf_manager = PDFManager()
session_view_manager = SessionViewManager()

urlpatterns = [
    path('', page_view_manager.index, name='index'),
    path('about/', page_view_manager.about, name='about'),
    path('dashboard/', page_view_manager.dashboard, name='dashboard'),
    path('session/<int:session_id>/', page_view_manager.session_detail, name='session_detail'),
    path('session/<int:session_id>/download-pdf/', pdf_manager.download_session_pdf, name='download_session_pdf'),
    path('session/<int:session_id>/delete/', session_view_manager.delete_session, name='delete_session'),
    path('chat/message/', chat_view_manager.chat_message, name='chat_message'),
    path('chat/clear-session/', session_manager.clear_session, name='clear_session'),
]