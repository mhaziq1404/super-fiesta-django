from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *


class MyUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['name', 'username', 'email', 'password1', 'password2']


class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = '__all__'
        exclude = ['host', 'participants']


class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['avatar', 'name', 'username', 'email', 'bio']

class ChatmessageCreateForm(ModelForm):
    class Meta:
        model = GroupMessage
        fields = ['body']
        widgets = {
            'body' : forms.TextInput(attrs={'placeholder': 'Add message ...', 'class': 'p-4 text-black', 'maxlength' : '300', 'autofocus': True }),
        }
        
        
class NewGroupForm(ModelForm):
    class Meta:
        model = ChatGroup
        fields = ['groupchat_name']
        widgets = {
            'groupchat_name' : forms.TextInput(attrs={
                'placeholder': 'Add name ...', 
                'class': 'p-4 text-black', 
                'maxlength' : '300', 
                'autofocus': True,
                }),
        }
        
        
class ChatRoomEditForm(ModelForm):
    class Meta:
        model = ChatGroup
        fields = ['groupchat_name']
        widgets = {
            'groupchat_name' : forms.TextInput(attrs={
                'class': 'p-4 text-xl font-bold mb-4', 
                'maxlength' : '300', 
                }),
        }