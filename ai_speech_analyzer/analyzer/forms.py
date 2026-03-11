from django import forms
from .models import SpeechAnalysis

class UploadSpeechForm(forms.ModelForm):
    class Meta:
        model = SpeechAnalysis
        fields = ['uploaded_file']
        widgets = {
            'uploaded_file': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': '.wav,.weba,.webm,.mp3,.ogg,.flac,.m4a,.aac,.mp4'
            })
        }
