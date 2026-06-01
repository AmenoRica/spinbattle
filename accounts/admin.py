import hashlib
import os

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from .forms import BulkSpinImageForm
from .models import CustomUser, SpinImage
from battle.types import compute_type_from_image
from battle.stats import compute_stats


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "is_staff", "is_active", "is_hidden")
    list_filter = ("is_staff", "is_active", "is_hidden")
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("bio", "is_hidden")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("bio", "is_hidden")}),
    )


class SpinImageAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "spin_type", "battle_score", "wins", "losses", "uploaded_at")
    list_filter = ("spin_type", "user")
    search_fields = ("name", "user__username")
    readonly_fields = ("hash", "spin_type", "uploaded_at")
    ordering = ("-uploaded_at",)
    change_list_template = "admin/spinimage_change_list.html"

    def get_urls(self):
        custom_urls = [
            path("bulk-upload/", self.admin_site.admin_view(self.bulk_upload_view), name="accounts_spinimage_bulk_upload"),
        ]
        return custom_urls + super().get_urls()

    def bulk_upload_view(self, request):
        results = None
        if request.method == "POST":
            form = BulkSpinImageForm(request.POST)
            files = request.FILES.getlist("images")
            if form.is_valid() and files:
                user = form.cleaned_data["user"]
                prefix = form.cleaned_data.get("name_prefix", "")

                created = 0
                skipped_dup = 0
                skipped_size = 0
                errors = []

                for i, f in enumerate(files):
                    if f.size > SpinImage.MAX_SIZE_BYTES:
                        skipped_size += 1
                        continue

                    f.seek(0)
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    f.seek(0)

                    if SpinImage.objects.filter(hash=file_hash).exists():
                        skipped_dup += 1
                        continue

                    if prefix:
                        name = f"{prefix}_{i + 1}"
                    else:
                        name = os.path.splitext(f.name)[0][:30]

                    spin_type = compute_type_from_image(f)
                    f.seek(0)

                    SpinImage.objects.create(
                        user=user,
                        name=name,
                        image=f,
                        hash=file_hash,
                        spin_type=spin_type,
                    )
                    created += 1

                results = {
                    "created": created,
                    "skipped_dup": skipped_dup,
                    "skipped_size": skipped_size,
                    "total": len(files),
                }

                if created > 0:
                    messages.success(request, _("%(count)s개의 팽이 이미지를 생성했습니다.") % {"count": created})
                if skipped_dup > 0:
                    messages.warning(request, _("%(count)s개의 중복 이미지를 건너뛰었습니다.") % {"count": skipped_dup})
                if skipped_size > 0:
                    messages.warning(request, _("%(count)s개의 이미지가 크기 제한(5MB)을 초과하여 건너뛰었습니다.") % {"count": skipped_size})

                if created > 0 or skipped_dup > 0 or skipped_size > 0:
                    return HttpResponseRedirect(reverse("admin:accounts_spinimage_changelist"))

            elif not files:
                messages.error(request, _("이미지 파일을 선택해주세요."))

        else:
            form = BulkSpinImageForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "results": results,
            "title": _("팽이 이미지 대량 업로드"),
            "opts": self.model._meta,
        }
        return render(request, "admin/bulk_upload.html", context)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(SpinImage, SpinImageAdmin)