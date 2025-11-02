from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime, timedelta
import json

from .models import (
    Employee, WorkRequest, WorkResult, WorkPhoto, 
    WorkDocument, WorkAct, SyncLog
)
from .serializers import (
    EmployeeSerializer, WorkRequestSerializer, WorkResultSerializer,
    WorkPhotoSerializer, WorkDocumentSerializer, WorkActSerializer,
    SyncLogSerializer, CustomTokenObtainPairSerializer
)


class IsEngineer(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.employee_profile.role == 'engineer'
        except:
            return False


class IsCoordinator(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.employee_profile.role in ['coordinator', 'admin']
        except:
            return False


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.employee_profile.role == 'admin'
        except:
            return False


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.employee_profile.role == 'admin':
            return Employee.objects.all()
        return Employee.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current_user(self, request):
        """Получить профиль текущего пользователя"""
        employee = get_object_or_404(Employee, user=request.user)
        serializer = self.get_serializer(employee)
        return Response(serializer.data)


class WorkRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WorkRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            role = user.employee_profile.role
        except:
            return WorkRequest.objects.none()
        
        if role == 'admin':
            return WorkRequest.objects.all()
        elif role == 'coordinator':
            return WorkRequest.objects.all()
        elif role == 'engineer':
            return WorkRequest.objects.filter(Q(assigned_to=user) | Q(created_by=user))
        else:
            return WorkRequest.objects.filter(created_by=user)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Получить заявки для текущего пользователя"""
        requests = self.get_queryset()
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_to_me(self, request, pk=None):
        """Назначить заявку себе"""
        work_request = self.get_object()
        work_request.assigned_to = request.user
        work_request.status = 'assigned'
        work_request.save()
        serializer = self.get_serializer(work_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_work(self, request, pk=None):
        """Начать выполнение работы"""
        work_request = self.get_object()
        if work_request.assigned_to != request.user and not request.user.employee_profile.role == 'admin':
            return Response({'error': 'Вы не назначены на эту работу'}, status=status.HTTP_403_FORBIDDEN)
        
        work_request.status = 'in_progress'
        work_request.save()
        
        # Создать результат работы если его нет
        if not hasattr(work_request, 'result'):
            WorkResult.objects.create(
                work_request=work_request,
                engineer=request.user,
                actual_start_time=datetime.now()
            )
        
        serializer = self.get_serializer(work_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete_work(self, request, pk=None):
        """Завершить выполнение работы"""
        work_request = self.get_object()
        work_request.status = 'completed'
        work_request.save()
        
        # Обновить результат
        if hasattr(work_request, 'result'):
            work_request.result.actual_end_time = datetime.now()
            work_request.result.save()
        
        serializer = self.get_serializer(work_request)
        return Response(serializer.data)


class WorkResultViewSet(viewsets.ModelViewSet):
    serializer_class = WorkResultSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            role = user.employee_profile.role
        except:
            return WorkResult.objects.none()
        
        if role == 'admin':
            return WorkResult.objects.all()
        elif role == 'coordinator':
            return WorkResult.objects.all()
        else:
            return WorkResult.objects.filter(engineer=user)
    
    def perform_create(self, serializer):
        serializer.save(engineer=self.request.user)
    
    @action(detail=True, methods=['post'])
    def upload_photo(self, request, pk=None):
        """Загрузить фотографию работы"""
        work_result = self.get_object()
        
        if 'photo' not in request.FILES:
            return Response({'error': 'Photo file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        photo = request.FILES['photo']
        description = request.data.get('description', '')
        local_path = request.data.get('local_path', '')
        
        work_photo = WorkPhoto.objects.create(
            work_result=work_result,
            photo=photo,
            description=description,
            local_path=local_path,
            is_synced=False
        )
        
        serializer = WorkPhotoSerializer(work_photo, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def upload_document(self, request, pk=None):
        """Загрузить документ работы"""
        work_result = self.get_object()
        
        if 'file' not in request.FILES:
            return Response({'error': 'File is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        document_type = request.data.get('document_type', 'other')
        description = request.data.get('description', '')
        local_path = request.data.get('local_path', '')
        
        work_document = WorkDocument.objects.create(
            work_result=work_result,
            file=file,
            document_type=document_type,
            description=description,
            local_path=local_path,
            is_synced=False
        )
        
        serializer = WorkDocumentSerializer(work_document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def complete_result(self, request, pk=None):
        """Завершить результат работы"""
        work_result = self.get_object()
        
        work_result.work_description = request.data.get('work_description', work_result.work_description)
        work_result.findings = request.data.get('findings', work_result.findings)
        work_result.recommendations = request.data.get('recommendations', work_result.recommendations)
        work_result.meter_readings = request.data.get('meter_readings', work_result.meter_readings)
        work_result.work_quality = request.data.get('work_quality', work_result.work_quality)
        work_result.actual_end_time = datetime.now()
        work_result.status = 'completed'
        work_result.save()
        
        # Создать акт выполненной работы
        if not hasattr(work_result, 'act'):
            act_number = f"ACT-{work_result.id.hex[:8].upper()}-{datetime.now().strftime('%Y%m%d')}"
            WorkAct.objects.create(
                work_result=work_result,
                act_number=act_number,
                act_content=f"Акт выполнения работы {work_result.work_request}"
            )
        
        serializer = self.get_serializer(work_result)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def sync_offline_data(self, request):
        """Синхронизировать offline данные"""
        try:
            offline_data = request.data.get('offline_data', [])
            sync_results = []
            
            for item in offline_data:
                entity_type = item.get('entity_type')
                entity_id = item.get('entity_id')
                
                try:
                    SyncLog.objects.create(
                        user=request.user,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        status='success'
                    )
                    sync_results.append({
                        'entity_id': entity_id,
                        'status': 'synced'
                    })
                except Exception as e:
                    SyncLog.objects.create(
                        user=request.user,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        status='failed',
                        error_message=str(e)
                    )
                    sync_results.append({
                        'entity_id': entity_id,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            return Response({
                'sync_results': sync_results,
                'total': len(offline_data),
                'synced': sum(1 for r in sync_results if r['status'] == 'synced')
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WorkActViewSet(viewsets.ModelViewSet):
    serializer_class = WorkActSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            role = user.employee_profile.role
        except:
            return WorkAct.objects.none()
        
        if role == 'admin':
            return WorkAct.objects.all()
        elif role == 'coordinator':
            return WorkAct.objects.all()
        else:
            return WorkAct.objects.filter(work_result__engineer=user)
    
    @action(detail=True, methods=['post'])
    def sign_engineer(self, request, pk=None):
        """Подписать акт инженером"""
        act = self.get_object()
        if act.work_result.engineer != request.user:
            return Response({'error': 'You are not the engineer for this act'}, status=status.HTTP_403_FORBIDDEN)
        
        act.engineer_signature_date = datetime.now()
        act.status = 'signed'
        act.save()
        
        serializer = self.get_serializer(act)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def sign_coordinator(self, request, pk=None):
        """Подписать акт координатором"""
        act = self.get_object()
        try:
            if request.user.employee_profile.role not in ['coordinator', 'admin']:
                return Response({'error': 'Only coordinators can sign'}, status=status.HTTP_403_FORBIDDEN)
        except:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        act.coordinator_signature_date = datetime.now()
        act.status = 'signed'
        act.save()
        
        serializer = self.get_serializer(act)
        return Response(serializer.data)


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            role = user.employee_profile.role
        except:
            return SyncLog.objects.none()
        
        if role == 'admin':
            return SyncLog.objects.all()
        else:
            return SyncLog.objects.filter(user=user)
