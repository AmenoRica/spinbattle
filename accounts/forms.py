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


class BulkSpinImageForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.all().order_by("username"),
        label=_("유저"),
        help_text=_("이미지를 등록할 유저를 선택하세요."),
    )
    name_prefix = forms.CharField(
        max_length=20,
        required=False,
        label=_("이름 접두사"),
        help_text=_("비워두면 파일명에서 자동 추출합니다. 입력하면 {접두사}_1, {접두사}_2 ... 형식으로 생성됩니다."),
    )
    name_prefix = forms.CharField(
        max_length=20,
        required=False,
        label=_("이름 접두사"),
        help_text=_("비워두면 파일명에서 자동 추출합니다. 입력하면 {접두사}_1, {접두사}_2 ... 형식으로 생성됩니다."),
    )
