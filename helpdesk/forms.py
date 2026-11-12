from django import forms
from django.contrib.auth.models import User
from .models import EmployeeProfile, Ticket

class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority', 'attachment']
    def clean_attachment(self):
        file = self.cleaned_data.get('attachment')
        if file:
            allowed = {'.pdf', '.png', '.jpg', '.jpeg', '.txt', '.doc', '.docx', '.xlsx', '.zip'}
            import os
            if os.path.splitext(file.name)[1].lower() not in allowed:
                raise forms.ValidationError('Allowed files: PDF, common images, text, Office documents, ZIP.')
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Attachment must be 10 MB or smaller.')
        return file

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ['role', 'department', 'phone', 'designation']
