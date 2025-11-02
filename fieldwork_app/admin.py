# admin.py - Регистрация моделей в админ-панели

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Employee, WorkRequest, WorkResult, WorkPhoto, 
    WorkDocument, WorkAct, SyncLog
)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'role', 'phone', 'organization', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__username', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Информация', {
            'fields': ('role', 'phone', 'organization', 'specialization', 'is_active')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'ФИО'


@admin.register(WorkRequest)
class WorkRequestAdmin(admin.ModelAdmin):
    list_display = ['object_address', 'work_type', 'status', 'priority', 'planned_date', 'assigned_to_name']
    list_filter = ['status', 'work_type', 'priority', 'planned_date', 'created_at']
    search_fields = ['object_address', 'object_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'planned_date'

    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'work_type', 'status', 'priority', 'created_by', 'assigned_to')
        }),
        ('Объект', {
            'fields': ('object_address', 'object_name', 'latitude', 'longitude')
        }),
        ('Описание работ', {
            'fields': ('description', 'notes')
        }),
        ('Счетчик', {
            'fields': ('meter_number', 'account_number'),
            'classes': ('collapse',)
        }),
        ('Контакты', {
            'fields': ('contact_person', 'contact_phone'),
            'classes': ('collapse',)
        }),
        ('График', {
            'fields': ('planned_date', 'planned_time_start', 'planned_time_end')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else '—'
    assigned_to_name.short_description = 'Назначено'


@admin.register(WorkResult)
class WorkResultAdmin(admin.ModelAdmin):
    list_display = ['work_request', 'engineer_name', 'status', 'actual_start_time', 'is_synced_display']
    list_filter = ['status', 'is_synced', 'actual_start_time', 'created_at']
    search_fields = ['work_request__object_address', 'engineer__first_name', 'engineer__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'is_synced', 'sync_timestamp']

    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'work_request', 'engineer', 'status')
        }),
        ('Время выполнения', {
            'fields': ('actual_start_time', 'actual_end_time')
        }),
        ('Результаты', {
            'fields': ('work_description', 'findings', 'recommendations')
        }),
        ('Показания счетчиков', {
            'fields': ('meter_readings', 'meter_reading_date'),
            'classes': ('collapse',)
        }),
        ('Оценка', {
            'fields': ('work_quality',)
        }),
        ('Синхронизация', {
            'fields': ('is_synced', 'sync_timestamp'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def engineer_name(self, obj):
        return obj.engineer.get_full_name()
    engineer_name.short_description = 'Инженер'

    def is_synced_display(self, obj):
        if obj.is_synced:
            return format_html('<span style="color: green;">✓ Синхронизирован</span>')
        return format_html('<span style="color: orange;">⧗ Не синхронизирован</span>')
    is_synced_display.short_description = 'Синхронизация'


class WorkPhotoInline(admin.TabularInline):
    model = WorkPhoto
    extra = 0
    readonly_fields = ['id', 'uploaded_at', 'is_synced']
    fields = ['photo', 'description', 'is_synced', 'uploaded_at']


class WorkDocumentInline(admin.TabularInline):
    model = WorkDocument
    extra = 0
    readonly_fields = ['id', 'uploaded_at', 'is_synced']
    fields = ['file', 'document_type', 'description', 'is_synced', 'uploaded_at']


@admin.register(WorkAct)
class WorkActAdmin(admin.ModelAdmin):
    list_display = ['act_number', 'work_result', 'status', 'act_date', 'engineer_signed', 'coordinator_signed']
    list_filter = ['status', 'act_date', 'engineer_signature_date', 'coordinator_signature_date']
    search_fields = ['act_number', 'work_result__work_request__object_address']
    readonly_fields = ['id', 'created_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'work_result', 'act_number', 'act_date', 'status')
        }),
        ('Содержание', {
            'fields': ('act_content', 'conclusion')
        }),
        ('Подписи', {
            'fields': ('engineer_signature_required', 'engineer_signature_date', 
                      'coordinator_signature_required', 'coordinator_signature_date')
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def engineer_signed(self, obj):
        if obj.engineer_signature_date:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    engineer_signed.short_description = 'Подпись инженера'

    def coordinator_signed(self, obj):
        if obj.coordinator_signature_date:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    coordinator_signed.short_description = 'Подпись координатора'


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'entity_type', 'status', 'attempt_count', 'last_attempt']
    list_filter = ['status', 'entity_type', 'last_attempt']
    search_fields = ['user__username', 'entity_id', 'error_message']
    readonly_fields = ['id', 'created_at']

    fieldsets = (
        ('Информация о синхронизации', {
            'fields': ('id', 'user', 'entity_type', 'entity_id', 'status')
        }),
        ('Попытки', {
            'fields': ('attempt_count', 'last_attempt')
        }),
        ('Ошибки', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
