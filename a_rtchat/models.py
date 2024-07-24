from django.db import models
from django.contrib.auth.models import User
import shortuuid
from PIL import Image
import os

class ChatGroup(models.Model):
    group_name = models.CharField(max_length=128, unique=True, blank=True)
    groupchat_name = models.CharField(max_length=128, null=True, blank=True)
    admin = models.ForeignKey(User, related_name='groupchats', blank=True, null=True, on_delete=models.SET_NULL)
    users_online = models.ManyToManyField(User, related_name='online_in_groups', blank=True)
    members = models.ManyToManyField(User, related_name='chat_groups', blank=True)
    is_private = models.BooleanField(default=False)
    
    def __str__(self):
        return self.group_name

    def save(self, *args, **kwargs):
        if not self.group_name:
            self.group_name = shortuuid.uuid()
        super().save(*args, **kwargs)
    
    
class GroupMessage(models.Model):
    group = models.ForeignKey(ChatGroup, related_name='chat_messages', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.CharField(max_length=300, blank=True, null=True)
    file = models.FileField(upload_to='files/', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    
    @property
    def filename(self):
        if self.file:
            return os.path.basename(self.file.name)
        else:
            return None
    
    def __str__(self):
        if self.body:
            return f'{self.author.username} : {self.body}'
        elif self.file:
            return f'{self.author.username} : {self.filename}'
    
    class Meta:
        ordering = ['-created']
        
    @property    
    def is_image(self):
        try:
            image = Image.open(self.file) 
            image.verify()
            return True 
        except:
            return False


# class Room(models.Model):
#     host = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     name = models.CharField(max_length=200)
#     description = models.TextField(null=True, blank=True)
#     participants = models.ManyToManyField(User, related_name='participants', blank=True)
#     updated = models.DateTimeField(auto_now=True)
#     created = models.DateTimeField(auto_now_add=True)
#     points = models.IntegerField(default=0)

#     OPPONENT_TYPE_CHOICES = (
#         ('vs Player', 'vs Player'),
#         ('Tournament', 'Tournament'),
#         ('AI', 'AI'),
#     )
#     opponent_type = models.CharField(max_length=10, choices=OPPONENT_TYPE_CHOICES, default='ai')

#     won_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_by_user')
#     won_by_ai = models.BooleanField(default=False)
#     is_expired = models.BooleanField(default=False)
#     host_ready = models.BooleanField(default=False)
#     opp_ready = models.BooleanField(default=False)
#     is_2player = models.BooleanField(default=False)

#     class Meta:
#         ordering = ['-updated', '-created']

#     def __str__(self):
#         return self.name
