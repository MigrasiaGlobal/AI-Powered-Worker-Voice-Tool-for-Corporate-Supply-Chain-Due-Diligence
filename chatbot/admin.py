from django.contrib import admin
from .models import ChatSession, ChatMessage, BuyerCompany, PolicyViolation

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'factory_name', 'location', 'case_type', 'created_at')
    list_filter = ('case_type', 'created_at')
    search_fields = ('factory_name', 'location', 'case_type')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'timestamp')
    list_filter = ('role', 'timestamp')
    search_fields = ('content',)

@admin.register(BuyerCompany)
class BuyerCompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'name')
    search_fields = ('name',)

@admin.register(PolicyViolation)
class PolicyViolationAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'buyer_company')
    search_fields = ('buyer_company', 'violation_text')
