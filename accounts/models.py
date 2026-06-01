import hashlib

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import models

from battle.types import SPIN_TYPE_CHOICES, compute_type_from_image


class CustomUser(AbstractUser):
    bio = models.TextField(blank=True)
    is_hidden = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class SpinImage(models.Model):
    MAX_PER_USER = 3
    MAX_SIZE_BYTES = 5 * 1024 * 1024

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="spin_images")
    name = models.CharField(max_length=30)
    image = models.ImageField(upload_to="spins/%Y/%m/%d/")
    hash = models.CharField(max_length=64, unique=True, editable=False)
    spin_type = models.CharField(max_length=10, choices=SPIN_TYPE_CHOICES, default="", editable=False)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    battle_score = models.IntegerField(default=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def clean(self):
        if self.image and self.image.size > self.MAX_SIZE_BYTES:
            raise ValidationError({"image": _("이미지 크기는 5MB 이하이어야 합니다.")})
        try:
            user = self.user
        except CustomUser.DoesNotExist:
            return
        if not self.pk:
            existing = SpinImage.objects.filter(user=user).count()
            if existing >= self.MAX_PER_USER:
                raise ValidationError({"image": _("이미지는 최대 %(count)s개까지 업로드할 수 있습니다.") % {"count": self.MAX_PER_USER}})

    def save(self, *args, **kwargs):
        if self.image and not self.hash:
            self.image.seek(0)
            self.hash = hashlib.sha256(self.image.read()).hexdigest()
            self.image.seek(0)
        if self.image and not self.spin_type:
            self.spin_type = compute_type_from_image(self.image)
        super().save(*args, **kwargs)
