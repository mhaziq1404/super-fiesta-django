# routing.py
from django.urls import path, re_path
from .consumers import *

websocket_urlpatterns = [
    path("ws/chatroom/<chatroom_name>", ChatroomConsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    # path("ws/room/<room_name>", RoomConsumer.as_asgi()),
    # path("ws/online-status/", OnlineStatusConsumer.as_asgi()),
]