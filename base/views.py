from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.http import Http404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import User, Notification, ChatGroup, Room, GroupMessage
from .forms import MyUserCreationForm, ChatmessageCreateForm, RoomForm, UserForm, NewGroupForm, ChatRoomEditForm

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')
            return render(request, 'base/login_register.html', {'page': 'login'})

        user = authenticate(request, email=email, password=password)

        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username OR password does not exist')

    return render(request, 'base/login_register.html', {'page': 'login'})

def logoutUser(request):
    logout(request)
    return redirect('home')

def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error occurred during registration')

    return render(request, 'base/login_register.html', {'form': form})

def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications/notifications.html', {'notifications': notifications})

def mark_notification_as_read(request, notification_id):
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required(login_url='login')
def home(request, chatroom_name='public-chat'):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if chat_group.is_private and request.user not in chat_group.members.all():
        raise Http404()

    chat_messages = chat_group.chat_messages.all()[:30]
    form = ChatmessageCreateForm()
    other_user = next((member for member in chat_group.members.all() if member != request.user), None)
    q = request.GET.get('q', '')
    rooms = Room.objects.filter(
        Q(name__icontains=q) |
        Q(description__icontains=q) |
        Q(points__icontains=q)
    )
    room_count = Room.objects.filter(is_expired=False).count()
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    if request.htmx and request.method == 'POST':
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.author = request.user
            message.group = chat_group
            message.save()
            return render(request, 'chat/partials/chat_message_p.html', {'message': message, 'user': request.user})

    context = {
        'chat_messages': chat_messages,
        'form': form,
        'other_user': other_user,
        'chatroom_name': chatroom_name,
        'chat_group': chat_group,
        'rooms': rooms,
        'room_count': room_count,
        'user': request.user,
        'notifications': notifications,
    }

    return render(request, 'base/home.html', context)

def room_list(request):
    rooms = Room.objects.filter(is_expired=False)
    if request.headers.get('HX-Request'):
        return render(request, 'room/partials/room_list.html', {'rooms': rooms})
    return render(request, 'base/home.html', {'rooms': rooms})

def player_list(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    participants = room.participants.all()
    other_player = participants[1] if len(participants) > 1 else None
    context = {
        'other_player': other_player,
        'room': room,
        'participants': participants,
        'participant': request.user,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'room/partials/vsplayer.html', context)
    return render(request, 'base/room.html', {'room': room})

def kick_player(request):
    if request.method == 'POST':
        player_id = request.POST.get('player_id')
        room_id = request.POST.get('room_id')

        if player_id and room_id:
            room = get_object_or_404(Room, id=room_id)
            player = get_object_or_404(User, id=player_id)
            if player in room.participants.all():
                room.participants.remove(player)
                room.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def leave_room(request):
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        if room_id:
            room = get_object_or_404(Room, id=room_id)
            user = request.user
            if user in room.participants.all():
                room.participants.remove(user)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def check_kickout_status(request):
    room_id = request.GET.get('room_id')
    player_id = request.GET.get('player_id')

    if room_id and player_id:
        room = get_object_or_404(Room, id=room_id)
        player = get_object_or_404(User, id=player_id)
        if player not in room.participants.all():
            return JsonResponse({'status': 'kickedout'})
    return JsonResponse({'status': 'still_in_room'})

@login_required(login_url='login')
def room(request, pk):
    room = get_object_or_404(Room, id=pk)
    if room.opponent_type == "AI":
        return render(request, 'base/room.html', {'room': room})

    if request.user not in room.participants.all():
        room.participants.add(request.user)

    chat_group = get_object_or_404(ChatGroup, room=room)
    chat_messages = chat_group.chat_messages.all()[:30]
    form = ChatmessageCreateForm()
    other_user = next((member for member in chat_group.members.all() if member != request.user), None)

    if chat_group.is_private and request.user not in chat_group.members.all():
        raise Http404()

    if request.htmx:
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.author = request.user
            message.group = chat_group
            message.room = room
            message.save()
            return render(request, 'chat/partials/chat_message_p.html', {'message': message, 'user': request.user})

    if request.method == 'POST' and request.user in room.participants.all():
        room.participants.remove(request.user)
        return redirect('home')

    context = {
        'room': room,
        'participants': room.participants.all(),
        'chat_messages': chat_messages,
        'form': form,
        'other_user': other_user,
        'chatroom_name': room.name,
        'chat_group': chat_group,
    }

    return render(request, 'base/room.html', context)

def userProfile(request, pk):
    user = get_object_or_404(User, id=pk)
    rooms = user.room_set.all()
    return render(request, 'base/profile.html', {'user': user, 'rooms': rooms})

@login_required(login_url='login')
def createRoom(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.host = request.user
            room.is_2player = (form.cleaned_data['opponent_type'] == 'vs Player')
            room.save()
            
            ChatGroup.objects.create(
                admin=request.user,
                group_name=room.name,
                groupchat_name=room.name,
                room=room,
                members=[request.user]
            )

            if request.htmx:
                rooms = Room.objects.filter(is_expired=False)
                return render(request, 'room/room_list.html', {'rooms': rooms})
            else:
                return redirect('home')
    else:
        form = RoomForm()

    return render(request, 'base/room_form.html', {'form': form})

@login_required(login_url='login')
def updateRoom(request, pk):
    room = get_object_or_404(Room, id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    form = RoomForm(instance=room)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            return redirect('home')

    return render(request, 'base/room_form.html', {'form': form, 'room': room})

@login_required(login_url='login')
def deleteRoom(request, pk):
    room = get_object_or_404(Room, id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')

    return render(request, 'base/delete.html', {'obj': room})

@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)
        else:
            print(form.errors)

    return render(request, 'base/update-user.html', {'form': form})

@login_required(login_url='login')
def pongPage(request, pk):
    room = get_object_or_404(Room, id=pk)

    if request.method == 'POST':
        winner = request.POST.get('winner')
        if winner:
            if room.opponent_type in ['AI', 'vs Player', 'Tournament']:
                room.won_by_user = request.user if winner != 'AI' else None
                room.won_by_ai = winner == 'AI'
                room.is_expired = True
                room.save()
                return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'failed', 'error': 'No winner specified'})

    return render(request, 'base/pong_ai.html', {'room': room})

@login_required(login_url='login')
def get_or_create_chatroom(request, username):
    if request.user.username == username:
        return redirect('home')
    
    other_user = get_object_or_404(User, username=username)
    chatroom = ChatGroup.objects.filter(is_private=True, members=request.user).first()

    if chatroom and other_user in chatroom.members.all():
        return redirect('chatroom', chatroom.group_name)

    chatroom, created = ChatGroup.objects.get_or_create(is_private=True)
    chatroom.members.add(other_user, request.user)
    return redirect('chatroom', chatroom.group_name)

@login_required(login_url='login')
def create_groupchat(request):
    form = NewGroupForm()

    if request.method == 'POST':
        form = NewGroupForm(request.POST)
        if form.is_valid():
            new_groupchat = form.save(commit=False)
            new_groupchat.admin = request.user
            new_groupchat.save()
            new_groupchat.members.add(request.user)
            return redirect('chatroom', new_groupchat.group_name)

    return render(request, 'chat/create_groupchat.html', {'form': form})

@login_required(login_url='login')
def chatroom_edit_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if request.user != chat_group.admin:
        raise Http404()

    form = ChatRoomEditForm(instance=chat_group)

    if request.method == 'POST':
        form = ChatRoomEditForm(request.POST, instance=chat_group)
        if form.is_valid():
            form.save()
            remove_members = request.POST.getlist('remove_members')
            for member_id in remove_members:
                member = get_object_or_404(User, id=member_id)
                chat_group.members.remove(member)
            return redirect('chatroom', chatroom_name)

    return render(request, 'chat/chatroom_edit.html', {'form': form, 'chat_group': chat_group})

@login_required(login_url='login')
def chatroom_delete_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if request.user != chat_group.admin:
        raise Http404()

    if request.method == "POST":
        chat_group.delete()
        messages.success(request, 'Chatroom deleted')
        return redirect('home')

    return render(request, 'chat/chatroom_delete.html', {'chat_group': chat_group})

@login_required(login_url='login')
def chatroom_leave_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if request.user not in chat_group.members.all():
        raise Http404()

    if request.method == "POST":
        chat_group.members.remove(request.user)
        messages.success(request, 'You left the Chat')
        return redirect('home')

def chat_file_upload(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)

    if request.htmx and request.FILES:
        file = request.FILES['file']
        message = GroupMessage.objects.create(
            file=file,
            author=request.user,
            group=chat_group,
        )
        channel_layer = get_channel_layer()
        event = {'type': 'message_handler', 'message_id': message.id}
        async_to_sync(channel_layer.group_send)(chatroom_name, event)

    return HttpResponse()

@login_required(login_url='login')
def chat_ui(request):
# Fetch chat messages for the current user
    chat_group = get_object_or_404(ChatGroup, group_name='public-chat')
    if chat_group.is_private and request.user not in chat_group.members.all():
        raise Http404()

    chat_messages = chat_group.chat_messages.all()[:30]
    
    context = {
        'chat_messages': chat_messages,
    }
    
    return render(request, 'base/private_messages.html', context)
