from django import forms
from .models import ChatSession

class ChatForm(forms.Form):
    message = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type your message...'}))

class FilterForm(forms.Form):
    case_type = forms.ChoiceField(
        choices=[
            ('', 'All Case Types'),
            ('Lender Harassment', 'Lender Harassment'),
            ('Employer Exploitation', 'Employer Exploitation'),
            ('Excessive Interest Rate', 'Excessive Interest Rate'),
            ('Recruitment Agency Harassment', 'Recruitment Agency Harassment'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    factory_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by factory name'})
    )
    
    buyer_company = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by buyer company'})
    )