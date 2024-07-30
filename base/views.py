from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from .models import *
from .forms import *
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import Http404

def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username OR password does not exist')

    context = {'page': page}
    return render(request, 'base/login_register.html', context)


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
    chat_messages = chat_group.chat_messages.all()[:30]
    form = ChatmessageCreateForm()
    
    other_user = None
    if chat_group.is_private:
        if request.user not in chat_group.members.all():
            raise Http404()
        for member in chat_group.members.all():
            if member != request.user:
                other_user = member
                break
            
    # if chat_group.groupchat_name:
    #     if request.user not in chat_group.members.all():
    #         if request.user.emailaddress_set.exists():
    #             chat_group.members.add(request.user)
    #         else:
    #             messages.warning(request, 'You need to verify your email to join the chat!')
    #             return redirect('profile-settings')
    
    context = {
        'chat_messages' : chat_messages, 
        'form' : form,
        'other_user' : other_user,
        'chatroom_name' : chatroom_name,
        'chat_group' : chat_group,
    }

    if request.htmx:
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid:
            message = form.save(commit=False)
            message.author = request.user
            message.group = chat_group
            message.save()
            context = {
                'message' : message,
                'user' : request.user
            }
            return render(request, 'chat/partials/chat_message_p.html', context)
    
    # return render(request, 'a_rtchat/chat.html', context)
    q = request.GET.get('q') if request.GET.get('q') else ''

    rooms = Room.objects.filter(
        Q(name__icontains=q) |
        Q(description__icontains=q) |
        Q(points__icontains=q)
    )

    room_count = Room.objects.filter(is_expired=False).count()

    context = {
        'chat_messages' : chat_messages, 
        'form' : form,
        'other_user' : other_user,
        'chatroom_name' : chatroom_name,
        'chat_group' : chat_group,
        'rooms': rooms,
        'room_count': room_count,
        'user': request.user,
    }
    # context = {
    #     'rooms': rooms,
    #     'room_count': room_count,
    #     'user': request.user,
    # }
    return render(request, 'base/home.html', context)




@login_required(login_url='login')
def room(request, pk):
    room = Room.objects.get(id=pk)
    # room_messages = room.message_set.all()
    participants = room.participants.all()
    chat_group = get_object_or_404(ChatGroup, room=room)
    chat_messages = chat_group.chat_messages.all()[:30]
    form = ChatmessageCreateForm()
    
    other_user = None
    if chat_group.is_private:
        if request.user not in chat_group.members.all():
            raise Http404()
        for member in chat_group.members.all():
            if member != request.user:
                other_user = member
                break

    chatroom_name = room.name
            
    # if chat_group.groupchat_name:
    #     if request.user not in chat_group.members.all():
    #         if request.user.emailaddress_set.exists():
    #             chat_group.members.add(request.user)
    #         else:
    #             messages.warning(request, 'You need to verify your email to join the chat!')
    #             return redirect('profile-settings')
    
    context = {
        'chat_messages' : chat_messages, 
        'form' : form,
        'other_user' : other_user,
        'chatroom_name' : chatroom_name,
        'chat_group' : chat_group,
    }

    if request.htmx:
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid:
            message = form.save(commit=False)
            message.author = request.user
            message.group = chat_group
            message.save()
            context = {
                'message' : message,
                'user' : request.user
            }
            return render(request, 'chat/partials/chat_message_p.html', context)

    if request.method == 'POST':
        if 'join' in request.POST:
            if request.user not in room.participants.all():
                room.participants.add(request.user)

                # Check if the participant is the opponent
                if room.participants.count() == 2:  # Assuming the room is now full
                    # Set opponent_ready to False
                    if room.host != request.user:
                        room.opp_ready = False
                    else:
                        room.host_ready = False
                    room.save()

            return redirect('room', pk=room.id)
        elif request.POST.get('body'):
            message = Message.objects.create(
                user=request.user,
                room=room,
                body=request.POST.get('body')
            )
            return redirect('room', pk=room.id)
        elif 'host_ready' in request.POST:
            room.host_ready = True
            room.save()
            return redirect('room', pk=room.id)
        elif 'opp_ready' in request.POST:
            room.opp_ready = True
            room.save()
            return redirect('room', pk=room.id)

    context = {
            'room': room,
            'participants': participants,
            'chat_messages' : chat_messages, 
            'form' : form,
            'chatroom_name' : chatroom_name,
            'chat_group' : chat_group,
        }
    return render(request, 'base/room.html', context)



def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    # room_messages = user.message_set.all()
    context = {'user': user, 'rooms': rooms}
    return render(request, 'base/profile.html', context)


@login_required(login_url='login')
def createRoom(request):
    form = RoomForm()
    if request.method == 'POST':
        if request.POST.get('opponent_type') == 'vs Player':
            room = Room.objects.create(
                host=request.user,
                name=request.POST.get('name'),
                points=request.POST.get('points'),
                opponent_type= request.POST.get('opponent_type'),
                is_2player=True,
                description=request.POST.get('description'),
            )
            new_groupchat = ChatGroup.objects.create(
                admin = request.user,
                group_name = request.POST.get('name'),
                groupchat_name = request.POST.get('name'),
                room = room,
            )
            new_groupchat.members.add(request.user)
            room.participants.add(request.user)
            return redirect('home')
        else:
            room = Room.objects.create(
                host=request.user,
                name=request.POST.get('name'),
                points=request.POST.get('points'),
                opponent_type= request.POST.get('opponent_type'),
                is_2player=False,
                description=request.POST.get('description'),
            )
            room.participants.add(request.user)
            return redirect('home')
    context = {'form': form}
    return render(request, 'base/room_form.html', context)


@login_required(login_url='login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        room.name = request.POST.get('name')
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')

    context = {'form': form, 'room': room}
    return render(request, 'base/room_form.html', context)


@login_required(login_url='login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': room})


@login_required(login_url='login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': message})


@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    return render(request, 'base/update-user.html', {'form': form})


def topicsPage(request):
    return redirect('home')


def activityPage(request):
    room_messages = Message.objects.all()
    return render(request, 'base/activity.html', {'room_messages': room_messages})

@login_required(login_url='login')
def pongPage(request, pk):
    room = Room.objects.get(id=pk)

    if request.method == 'POST':
        winner = request.POST.get('winner')
        if winner:
            if room.opponent_type == 'AI':
                if winner == 'AI':
                    room.won_by_ai = True
                    room.is_expired = True
                    room.save()
                    return JsonResponse({'status': 'success'})
                else:
                    room.won_by_user = request.user
                    room.is_expired = True
                    room.save()
                    return JsonResponse({'status': 'success'})
            if room.opponent_type == 'vs Player':
                room.won_by_user = request.user
                room.is_expired = True
                room.save()
                return JsonResponse({'status': 'success'})
            if room.opponent_type == 'Tournament':
                room.won_by_user = request.user
                room.is_expired = True
                room.save()
                return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'failed', 'error': 'No winner specified'})
    
    context = {'room': room}
    return render(request, 'base/pong_ai.html', context)

@login_required(login_url='login')
def get_or_create_chatroom(request, username):
    if request.user.username == username:
        return redirect('home')
    
    other_user = User.objects.get(username = username)
    my_chatrooms = request.user.chat_groups.filter(is_private=True)
    
    
    if my_chatrooms.exists():
        for chatroom in my_chatrooms:
            if other_user in chatroom.members.all():
                chatroom = chatroom
                break
            else:
                chatroom = ChatGroup.objects.create(is_private = True)
                chatroom.members.add(other_user, request.user)
    else:
        chatroom = ChatGroup.objects.create(is_private = True)
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
    
    context = {
        'form': form
    }
    return render(request, 'chat/create_groupchat.html', context)


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
                member = User.objects.get(id=member_id)
                chat_group.members.remove(member)  
                
            return redirect('chatroom', chatroom_name) 
    
    context = {
        'form' : form,
        'chat_group' : chat_group
    }   
    return render(request, 'chat/chatroom_edit.html', context) 


@login_required(login_url='login')
def chatroom_delete_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    if request.user != chat_group.admin:
        raise Http404()
    
    if request.method == "POST":
        chat_group.delete()
        messages.success(request, 'Chatroom deleted')
        return redirect('home')
    
    return render(request, 'chat/chatroom_delete.html', {'chat_group':chat_group})


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
            file = file,
            author = request.user, 
            group = chat_group,
        )
        channel_layer = get_channel_layer()
        event = {
            'type': 'message_handler',
            'message_id': message.id,
        }
        async_to_sync(channel_layer.group_send)(
            chatroom_name, event
        )
    return HttpResponse()