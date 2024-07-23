from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from .models import Room, Message, User, Home_Message
from .forms import RoomForm, UserForm, MyUserCreationForm
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

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


def home(request):

    q = request.GET.get('q') if request.GET.get('q') else ''

    rooms = Room.objects.filter(
        Q(name__icontains=q) |
        Q(description__icontains=q) |
        Q(points__icontains=q)
    )

    room_count = Room.objects.filter(is_expired=False).count()
    home_messages = Home_Message.objects.all()[0:8]

    context = {'rooms': rooms, 'room_count': room_count, 'room_messages': home_messages}
    if request.method == 'POST':
        message = Home_Message.objects.create(
            user=request.user,
            body=request.POST.get('body')
        )
        return redirect('home')
    return render(request, 'base/home.html', context)

@login_required(login_url='login')
def room(request, pk):
    room = Room.objects.get(id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()

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

    context = {'room': room, 'room_messages': room_messages, 'participants': participants}
    return render(request, 'base/room.html', context)



def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    context = {'user': user, 'rooms': rooms, 'room_messages': room_messages}
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