from django import forms
from django.utils import timezone

from .models import Appointment, Review


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
        fields = ["name", "staff", "appointment_date", "note"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "note": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Anything we should know? (optional)"}
            ),
        }

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
            if Appointment.objects.filter(staff=staff, appointment_date=date).exists():
                raise forms.ValidationError(
                    f"{staff} is already booked at that time. Please pick another slot."
                )
        return cleaned


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, f"{i} ★") for i in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ["rating"]