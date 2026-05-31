from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, SpinImage


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("username", "email")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("username", "email", "bio")


class SpinImageForm(forms.ModelForm):
    class Meta:
        model = SpinImage
        fields = ("name", "image",)
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("팽이 이름"), "maxlength": "30"}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }


class SpinImageRenameForm(forms.ModelForm):
    class Meta:
        model = SpinImage
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("팽이 이름"), "maxlength": "30"}),
        }
