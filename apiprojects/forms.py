from django import forms
from django.utils import timezone

from .models import Appointment, Review, Branch

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class AppointmentForm(forms.ModelForm):
    appointment_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Appointment
        fields = ["name","phone_number", "branch", "staff", "service", "appointment_date", "note"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "phone_number": forms.TextInput(attrs={
                "placeholder": "09123456789",
                "inputmode": "numeric",
                "pattern": "[0-9]{11}",
                "maxlength": "11",
                "title": "Enter exactly 11 digits",
            }),
            "note": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Anything we should know? (optional)"}
            ),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        self.fields["branch"].required = True
        self.fields["branch"].empty_label = "Select a branch"


    # These two are OUTSIDE Meta, at the same indentation level as Meta
    def clean_appointment_date(self):
        date = self.cleaned_data["appointment_date"]
        if date <= timezone.now():
            raise forms.ValidationError("Please choose a date and time in the future.")
        return date

    def clean(self):
        cleaned = super().clean()
        staff = cleaned.get("staff")
        date = cleaned.get("appointment_date")

        # Prevent double-booking the same staff member at the same time
        if staff and date:
            clash = Appointment.objects.filter(
                staff=staff, appointment_date=date
            ).exclude(status="cancelled")
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise forms.ValidationError(
                    f"{staff} is already booked at that time. Please pick another slot."
                )
        return cleaned


from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, f"{i} ★") for i in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
        label="Your rating",
    )

    class Meta:
        model = Review
        fields = ["rating", "message"]