from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Employee, WorkRequest, WorkResult, WorkPhoto, 
    WorkDocument, WorkAct, SyncLog
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Employee
        fields = ['id', 'user', 'role', 'phone', 'organization', 'specialization', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class WorkRequestSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = WorkRequest
        fields = [
            'id', 'created_by', 'created_by_name', 'assigned_to', 'assigned_to_name',
            'work_type', 'status', 'priority', 'object_address', 'object_name',
            'latitude', 'longitude', 'description', 'planned_date', 'planned_time_start',
            'planned_time_end', 'meter_number', 'account_number', 'contact_person',
            'contact_phone', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkPhotoSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkPhoto
        fields = ['id', 'work_result', 'photo', 'photo_url', 'description', 'local_path', 'is_synced', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'is_synced']
    
    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None


class WorkDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkDocument
        fields = ['id', 'work_result', 'document_type', 'file', 'file_url', 'description', 'local_path', 'is_synced', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'is_synced']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class WorkResultSerializer(serializers.ModelSerializer):
    photos = WorkPhotoSerializer(many=True, read_only=True)
    documents = WorkDocumentSerializer(many=True, read_only=True)
    engineer_name = serializers.CharField(source='engineer.get_full_name', read_only=True)
    work_request_data = WorkRequestSerializer(source='work_request', read_only=True)
    
    class Meta:
        model = WorkResult
        fields = [
            'id', 'work_request', 'work_request_data', 'engineer', 'engineer_name',
            'actual_start_time', 'actual_end_time', 'status', 'work_description',
            'findings', 'recommendations', 'meter_readings', 'meter_reading_date',
            'work_quality', 'photos', 'documents', 'is_synced', 'sync_timestamp',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_synced', 'sync_timestamp']


class WorkActSerializer(serializers.ModelSerializer):
    work_result_data = WorkResultSerializer(source='work_result', read_only=True)
    
    class Meta:
        model = WorkAct
        fields = [
            'id', 'work_result', 'work_result_data', 'act_number', 'act_date', 'status',
            'engineer_signature_required', 'coordinator_signature_required',
            'engineer_signature_date', 'coordinator_signature_date',
            'act_content', 'conclusion', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = ['id', 'user', 'entity_type', 'entity_id', 'status', 'error_message', 'attempt_count', 'last_attempt', 'created_at']
        read_only_fields = ['id', 'created_at']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['full_name'] = user.get_full_name()
        try:
            token['role'] = user.employee_profile.role
        except:
            pass
        return token
