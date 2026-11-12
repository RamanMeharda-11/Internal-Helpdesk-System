from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Ticket, TicketComment, Task, EmployeeProfile, Notification

class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    class Meta:
        model = TicketComment
        fields = ['id','author_name','body','internal','created_at']
        read_only_fields = ['id','author_name','created_at']

class TicketSerializer(serializers.ModelSerializer):
    ticket_id = serializers.SerializerMethodField()
    comments = TicketCommentSerializer(many=True, read_only=True)
    class Meta:
        model = Ticket
        fields = ['id','ticket_id','title','description','category','priority','status','created_by','assigned_to','department','attachment','created_at','updated_at','comments']
        read_only_fields = ['id','ticket_id','created_by','created_at','updated_at']
    def validate_attachment(self,file):
        if file:
            import os
            if os.path.splitext(file.name)[1].lower() not in {'.pdf','.png','.jpg','.jpeg','.txt','.doc','.docx','.xlsx','.zip'}:
                raise serializers.ValidationError('Unsupported attachment type.')
            if file.size > 10 * 1024 * 1024:
                raise serializers.ValidationError('Attachment must be 10 MB or smaller.')
        return file
    def get_ticket_id(self,obj) -> str: return f'HD-{obj.pk:04d}'

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['id','created_by','created_at']

class EmployeeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    is_active = serializers.BooleanField(source='user.is_active', required=False)
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    def validate(self,attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password':'This field is required when creating an employee.'})
        return attrs
    class Meta:
        model = EmployeeProfile
        fields = ['id','username','email','first_name','last_name','is_active','password','full_name','role','department','phone','designation']
    def create(self,validated_data):
        user_data=validated_data.pop('user'); password=validated_data.pop('password')
        user=User.objects.create_user(password=password,**user_data)
        return EmployeeProfile.objects.create(user=user,**validated_data)
    def update(self,instance,validated_data):
        user_data=validated_data.pop('user',{})
        password=validated_data.pop('password',None)
        for key,value in user_data.items(): setattr(instance.user,key,value)
        if password: instance.user.set_password(password)
        instance.user.save()
        return super().update(instance,validated_data)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id','message','read','created_at']
        read_only_fields = ['id','message','created_at']
