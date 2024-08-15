from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.http import Http404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from uuid import uuid4
from django.utils.text import slugify
import random

from .models import User, ChatGroup, Room, GroupMessage, Match
from .forms import MyUserCreationForm, ChatmessageCreateForm, RoomForm, UserForm, NewGroupForm, ChatRoomEditForm, MatchScoreForm

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
        'chatroom_name_ws': chat_group.groupchat_name,
        'home_chat': "Public",
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

        print("=============here===========")

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

    context = {
        'room': room,
        'participants': room.participants.all(),
        'chat_messages': chat_messages,
        'form': form,
        'other_user': other_user,
        'chatroom_name': room.name,
        'chatroom_name_ws': chat_group.groupchat_name,
        'chat_group': chat_group,
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'leave-room':
            if request.user in room.participants.all():
                room.participants.remove(request.user)
                return redirect('home')
            else:
                # Handle user not being part of the room
                messages.error(request, "You are not a participant of this room.")

        elif action == 'ready':
            if request.user in room.participants.all():
                room.opp_ready = True
                room.save()
                return render(request, 'base/room.html', context)
            else:
                # Handle user not being part of the room
                messages.error(request, "You are not a participant of this room.")

        raise Http404()

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
            
            unique_suffix = uuid4().hex[:6]
            
            # Replace spaces with hyphens
            formatted_name = room.name.replace(' ', '-')

            chat_group = ChatGroup.objects.create(
                admin=request.user,
                group_name=f"{formatted_name}-{unique_suffix}",  # Append unique suffix
                groupchat_name=f"{formatted_name}-{unique_suffix}",  # Append unique suffix
                room=room
            )

            # Assign the user to the group after saving
            chat_group.members.set([request.user])

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
    if request.method == 'POST':
        form = NewGroupForm(request.POST)
        if form.is_valid():
            unique_suffix = uuid4().hex[:6]
            
            formatted_name = slugify(form.cleaned_data['groupchat_name'])
            group_name = f"{formatted_name}-{unique_suffix}"
            
            chat_group = ChatGroup.objects.create(
                admin=request.user,
                group_name=group_name,
                groupchat_name=group_name,
            )
            
            chat_group.members.set([request.user])

            request.user.group_chats.add(chat_group)
            request.user.save()
            
            return redirect('messages')

    else:
        form = NewGroupForm()

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
    # Fetch chat groups for the current user
    chat_groups = request.user.group_chats.all()

    context = {
        'chat_groups': chat_groups,
    }
    
    return render(request, 'base/private_messages.html', context)

@login_required(login_url='login')
def chat_group_detail(request, id):
    group = get_object_or_404(ChatGroup, id=id)
    chat_groups = request.user.group_chats.all()
    chat_messages = group.chat_messages.all()[:30]

    if request.htmx:
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.author = request.user
            message.group = group
            message.room = room
            message.save()
            return render(request, 'private_message/partials/chat_message_p.html', {'message': message, 'user': request.user})

    context = {
        'group': group,
        'chat_groups': chat_groups,
        'selected_group_id': group.id,
        'chatroom_name_ws': group.groupchat_name,
        'chat_messages': chat_messages,
    }
    
    return render(request, 'base/private_messages.html', context)

@login_required(login_url='login')
def tournament_view(request, pk):
    room = Room.objects.get(id=pk)  # Fetch the room object
    participants = list(room.participants.all())
    random.shuffle(participants)
    opp_count = len(participants)

    matches = {
        'quarterfinals': [],
        'semifinals': [],
        'final': None
    }

    if opp_count == 8:
        # Create Quarterfinals
        for i in range(0, 8, 2):
            match = Match(
                player1=participants[i],
                player2=participants[i+1],
                round='Quarterfinal'
            )
            match.save()
            matches['quarterfinals'].append(match)

        # Create Semifinals
        for _ in range(4):
            match = Match(round='Semifinal')
            match.save()
            matches['semifinals'].append(match)

        # Create Final with empty player1 and player2
        final_match = Match(
            round='Final',
            is_final=True
            # Do not set player1 and player2 yet
        )
        final_match.save()
        matches['final'] = final_match

    elif opp_count == 4:
        # Create Semifinals
        for i in range(0, 4, 2):
            match = Match(
                player1=participants[i],
                player2=participants[i+1],
                round='Semifinal'
            )
            match.save()
            matches['semifinals'].append(match)

        # Create Final with empty player1 and player2
        final_match = Match(
            round='Final',
            is_final=True
            # Do not set player1 and player2 yet
        )
        # final_match.save()
        matches['final'] = final_match

    context = {
        'matches': matches,
        'opp_count': opp_count,
        'room': room,
    }

    return render(request, 'tournament/bracket.html', context)


# @login_required(login_url='login')
# def podium_view(request, pk):
#     # Fetch the room object
#     room = Room.objects.get(id=pk)
    
#     # Fetch all matches related to the room and order them by score to get podium positions
#     matches = Match.objects.filter(room=room).order_by('-player1_score', '-player2_score')
    
#     # Get the top 3 matches for podium positions
#     podium_matches = matches[:3]
    
#     context = {
#         'matches': podium_matches,
#     }
    
#     return render(request, 'tournament/podium.html', context)

@login_required(login_url='login')
def podium_view(request, pk):
    # Dummy data for testing
    class DummyPlayer:
        def __init__(self, username, avatar_url):
            self.username = username
            self.avatar_url = avatar_url

    class DummyMatch:
        def __init__(self, player1, player2, player1_score=None, player2_score=None):
            self.player1 = player1
            self.player2 = player2
            self.player1_score = player1_score or 0
            self.player2_score = player2_score or 0

    # Create dummy players
    player1 = DummyPlayer(username="Player One", avatar_url="/static/images/player1.jpg")
    player2 = DummyPlayer(username="Player Two", avatar_url="/static/images/player2.jpg")
    player3 = DummyPlayer(username="Player Three", avatar_url="/static/images/player3.jpg")
    player4 = DummyPlayer(username="Player Four", avatar_url="/static/images/player4.jpg")

    # Create dummy matches
    matches = [
        DummyMatch(player1=player1, player2=player2, player1_score=3, player2_score=1),  # First place
        DummyMatch(player1=player3, player2=player4, player1_score=2, player2_score=2),  # Second place
        DummyMatch(player1=player2, player2=player3, player1_score=1, player2_score=0)   # Third place
    ]

    context = {
        'matches': matches,
    }
    
    return render(request, 'tournament/podium.html', context)
