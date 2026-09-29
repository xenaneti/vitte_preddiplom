from django import forms

from .models import Ticket


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["subject", "text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 5})}


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["status", "reply"]

    def clean(self):
        data = super().clean()
        if data.get("status") == "closed" and not data.get("reply", "").strip():
            self.add_error("reply", "Перед закрытием обращения напишите ответ.")
        return data
