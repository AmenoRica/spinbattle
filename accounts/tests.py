import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from PIL import Image

from battle.engine import _accel_turn_multiplier

from .models import CustomUser, SpinImage
from .views import PLACEMENT_ROUNDS, _run_placement


TEST_MEDIA_ROOT = tempfile.mkdtemp()


class EngineAccelerationTests(TestCase):
    def test_turn_start_acceleration_fades_after_turn_twenty_and_stops_after_twenty_five(self):
        self.assertEqual(_accel_turn_multiplier(20), 1.0)
        self.assertAlmostEqual(_accel_turn_multiplier(21), 5 / 6)
        self.assertAlmostEqual(_accel_turn_multiplier(25), 1 / 6)
        self.assertEqual(_accel_turn_multiplier(26), 0.0)


@override_settings(
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    },
)
class PlacementTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def _image_file(self, name, color):
        image = Image.new("RGB", (10, 10), color)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def test_placement_runs_ten_matches_and_returns_all_results(self):
        user = CustomUser.objects.create_user(username="player", password="pw")
        opponent_user = CustomUser.objects.create_user(username="opponent", password="pw")
        spin = SpinImage.objects.create(user=user, name="새팽이", image=self._image_file("spin.png", (255, 0, 0)))
        opponent = SpinImage.objects.create(user=opponent_user, name="상대팽이", image=self._image_file("opp.png", (0, 0, 255)))

        log = [{"text": "끝", "effects": [{"type": "battle_end", "winner": "a"}]}]
        with patch("accounts.views.simulate", return_value=log):
            results = _run_placement(spin)

        spin.refresh_from_db()
        opponent.refresh_from_db()

        self.assertEqual(PLACEMENT_ROUNDS, 10)
        self.assertEqual(len(results), 10)
        self.assertEqual([r["round"] for r in results], list(range(1, 11)))
        self.assertEqual(spin.wins, 10)
        self.assertEqual(spin.losses, 0)
        self.assertEqual(opponent.wins, 0)
        self.assertEqual(opponent.losses, 10)
