from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.register, name="signup"),
    path("my-spins/", views.my_spins, name="my_spins"),
    path("my-spins/preview/", views.upload_preview, name="upload_preview"),
    path("images/<int:pk>/delete/", views.delete_image, name="delete_image"),
    path("images/<int:pk>/rename/", views.rename_image, name="rename_image"),
    path("users/", views.user_list, name="user_list"),
    path("spins/<int:pk>/", views.spin_detail, name="spin_detail"),
    path("friendly-battle/", views.friendly_battle, name="friendly_battle"),
    path("ranked-battle/", views.ranked_battle, name="ranked_battle"),
]
