import uuid
import json
from django.db import models

class ChatSession(models.Model):
    user_name = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)
    job_in_factory = models.CharField(max_length=255, null=True, blank=True)
    factory_name = models.CharField(max_length=255, null=True, blank=True)
    factory_product = models.CharField(max_length=255, null=True, blank=True)
    industrial_sector = models.CharField(max_length=255, null=True, blank=True)
    recruitment_agency_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    case_type = models.CharField(max_length=100, null=True, blank=True)
    incident_description = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Session {self.id} - {self.factory_name or 'Unknown'}"

class BuyerCompany(models.Model):
    session = models.ForeignKey(ChatSession, related_name='buyer_companies', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=20)  # 'user' or 'assistant'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

class PolicyViolation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, related_name='violations', on_delete=models.CASCADE)
    buyer_company = models.CharField(max_length=255)
    violation_text = models.TextField()
    complaint_summary = models.TextField(blank=True, null=True)
    incidents = models.TextField(blank=True, null=True)  # JSON string of incidents list
    policy_violations = models.TextField(blank=True, null=True)  # JSON string of policy violations list
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.buyer_company} - {self.session.id}"
    
    def get_incidents_list(self):
        """Parse the incidents JSON string into a Python list"""
        if not self.incidents:
            return []
        try:
            return json.loads(self.incidents)
        except json.JSONDecodeError:
            return []
    
    def get_violations_list(self):
        """Parse the policy_violations JSON string into a Python list"""
        if not self.policy_violations:
            return []
        try:
            return json.loads(self.policy_violations)
        except json.JSONDecodeError:
            return []
