from pathlib import Path

from django.conf import settings
from django.core.files.base import File
from django.core.management.base import BaseCommand

from accounts.models import SpinImage


class Command(BaseCommand):
    help = "기존 로컬 media 파일을 현재 default storage(R2)로 업로드합니다."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        if not getattr(settings, "USE_R2_STORAGE", False):
            self.stdout.write(self.style.ERROR("USE_R2_STORAGE=True 상태에서 실행해주세요."))
            return

        queryset = SpinImage.objects.exclude(image="").order_by("pk")
        if limit > 0:
            queryset = queryset[:limit]

        total = 0
        uploaded = 0
        missing = 0
        skipped = 0

        for spin in queryset:
            total += 1
            image_name = spin.image.name
            if not image_name:
                skipped += 1
                continue

            local_path = Path(settings.MEDIA_ROOT) / image_name
            if not local_path.exists():
                missing += 1
                self.stdout.write(self.style.WARNING(f"[누락] pk={spin.pk} {image_name}"))
                continue

            if dry_run:
                self.stdout.write(f"[DRY] pk={spin.pk} {image_name}")
                uploaded += 1
                continue

            if spin.image.storage.exists(image_name):
                skipped += 1
                continue

            with local_path.open("rb") as f:
                spin.image.storage.save(image_name, File(f))
            uploaded += 1
            self.stdout.write(self.style.SUCCESS(f"[업로드] pk={spin.pk} {image_name}"))

        self.stdout.write("")
        self.stdout.write(f"대상: {total}")
        self.stdout.write(f"업로드: {uploaded}")
        self.stdout.write(f"건너뜀: {skipped}")
        self.stdout.write(f"누락: {missing}")
