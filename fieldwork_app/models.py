from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from datetime import datetime

class Employee(models.Model):
    """Модель для сотрудников"""
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('coordinator', 'Координатор'),
        ('engineer', 'Инженер'),
        ('viewer', 'Просмотрщик'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='engineer')
    phone = models.CharField(max_length=20, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


class WorkRequest(models.Model):
    """Модель для заявки на работу"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('planned', 'Запланирована'),
        ('assigned', 'Назначена'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    
    WORK_TYPE_CHOICES = [
        ('inspection', 'Обследование объекта'),
        ('meter_check', 'Проверка коммерческого учета'),
        ('maintenance', 'Техническое обслуживание'),
        ('repair', 'Ремонт'),
        ('emergency', 'Аварийная работа'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('critical', 'Критический'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_requests')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')
    
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Адрес и локация
    object_address = models.CharField(max_length=500)
    object_name = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Описание работы
    description = models.TextField()
    planned_date = models.DateField()
    planned_time_start = models.TimeField(null=True, blank=True)
    planned_time_end = models.TimeField(null=True, blank=True)
    
    # Дополнительные поля
    meter_number = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-planned_date', '-priority']
        verbose_name = "Заявка на работу"
        verbose_name_plural = "Заявки на работу"
    
    def __str__(self):
        return f"{self.get_work_type_display()} - {self.object_address} ({self.get_status_display()})"


class WorkResult(models.Model):
    """Модель для результатов работы"""
    RESULT_STATUS_CHOICES = [
        ('in_progress', 'В процессе'),
        ('completed', 'Завершено'),
        ('issues', 'Обнаружены проблемы'),
        ('rework', 'Требуется переделка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_request = models.OneToOneField(WorkRequest, on_delete=models.CASCADE, related_name='result')
    engineer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='work_results')
    
    # Время выполнения
    actual_start_time = models.DateTimeField()
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Результаты
    status = models.CharField(max_length=20, choices=RESULT_STATUS_CHOICES, default='in_progress')
    work_description = models.TextField()
    findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    
    # Показания счетчиков (если применимо)
    meter_readings = models.TextField(blank=True)  # JSON для хранения показаний
    meter_reading_date = models.DateField(null=True, blank=True)
    
    # Оценка работ
    work_quality = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Синхронизация
    is_synced = models.BooleanField(default=False)
    sync_timestamp = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Результат работы"
        verbose_name_plural = "Результаты работ"
    
    def __str__(self):
        return f"Результат для {self.work_request}"


class WorkPhoto(models.Model):
    """Модель для фотографий работ"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_result = models.ForeignKey(WorkResult, on_delete=models.CASCADE, related_name='photos')
    
    photo = models.ImageField(upload_to='work_photos/%Y/%m/%d/')
    description = models.CharField(max_length=255, blank=True)
    
    # Для offline режима
    local_path = models.CharField(max_length=500, blank=True)
    is_synced = models.BooleanField(default=False)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Фотография работы"
        verbose_name_plural = "Фотографии работ"
        ordering = ['-uploaded_at']


class WorkDocument(models.Model):
    """Модель для документов и файлов"""
    DOCUMENT_TYPE_CHOICES = [
        ('report', 'Отчет'),
        ('receipt', 'Квитанция'),
        ('contract', 'Контракт'),
        ('checklist', 'Чек-лист'),
        ('other', 'Другое'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_result = models.ForeignKey(WorkResult, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='work_documents/%Y/%m/%d/')
    description = models.CharField(max_length=255, blank=True)
    
    # Для offline режима
    local_path = models.CharField(max_length=500, blank=True)
    is_synced = models.BooleanField(default=False)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Документ работы"
        verbose_name_plural = "Документы работ"
        ordering = ['-uploaded_at']


class WorkAct(models.Model):
    """Модель для акта выполненной работы"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('signed', 'Подписан'),
        ('archived', 'В архиве'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_result = models.OneToOneField(WorkResult, on_delete=models.CASCADE, related_name='act')
    
    act_number = models.CharField(max_length=50, unique=True)
    act_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Подписанты
    engineer_signature_required = models.BooleanField(default=True)
    coordinator_signature_required = models.BooleanField(default=False)
    engineer_signature_date = models.DateTimeField(null=True, blank=True)
    coordinator_signature_date = models.DateTimeField(null=True, blank=True)
    
    # Содержание акта
    act_content = models.TextField()
    conclusion = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Акт выполненной работы"
        verbose_name_plural = "Акты выполненных работ"
        ordering = ['-act_date']
    
    def __str__(self):
        return f"Акт {self.act_number}"


class SyncLog(models.Model):
    """Модель для логирования синхронизации"""
    SYNC_STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sync_logs')
    
    entity_type = models.CharField(max_length=50)  # WorkResult, WorkPhoto, WorkDocument
    entity_id = models.CharField(max_length=100)
    
    status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES)
    error_message = models.TextField(blank=True)
    
    attempt_count = models.IntegerField(default=1)
    last_attempt = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Лог синхронизации"
        verbose_name_plural = "Логи синхронизации"
        ordering = ['-last_attempt']
