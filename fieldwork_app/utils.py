# utils.py - Вспомогательные функции

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime, timedelta
from .models import WorkRequest, WorkResult, WorkAct
import json


class WorkRequestHelper:
    """Помощник для работы с заявками"""
    
    @staticmethod
    def get_pending_requests(engineer):
        """Получить незавершенные заявки для инженера"""
        return WorkRequest.objects.filter(
            assigned_to=engineer,
            status__in=['assigned', 'in_progress']
        ).order_by('-priority', 'planned_date')
    
    @staticmethod
    def get_overdue_requests():
        """Получить просроченные заявки"""
        return WorkRequest.objects.filter(
            status__in=['planned', 'assigned', 'in_progress'],
            planned_date__lt=datetime.now().date()
        )
    
    @staticmethod
    def get_statistics_by_date_range(start_date, end_date):
        """Получить статистику по диапазону дат"""
        requests = WorkRequest.objects.filter(
            planned_date__range=[start_date, end_date]
        )
        
        return {
            'total': requests.count(),
            'by_status': {
                'draft': requests.filter(status='draft').count(),
                'planned': requests.filter(status='planned').count(),
                'assigned': requests.filter(status='assigned').count(),
                'in_progress': requests.filter(status='in_progress').count(),
                'completed': requests.filter(status='completed').count(),
                'cancelled': requests.filter(status='cancelled').count(),
            },
            'by_type': {
                'inspection': requests.filter(work_type='inspection').count(),
                'meter_check': requests.filter(work_type='meter_check').count(),
                'maintenance': requests.filter(work_type='maintenance').count(),
                'repair': requests.filter(work_type='repair').count(),
                'emergency': requests.filter(work_type='emergency').count(),
            }
        }


class WorkResultHelper:
    """Помощник для работы с результатами"""
    
    @staticmethod
    def calculate_completion_time(work_result):
        """Расчет времени выполнения работы"""
        if work_result.actual_end_time and work_result.actual_start_time:
            duration = work_result.actual_end_time - work_result.actual_start_time
            return {
                'hours': int(duration.total_seconds() // 3600),
                'minutes': int((duration.total_seconds() % 3600) // 60),
                'total_minutes': int(duration.total_seconds() // 60)
            }
        return None
    
    @staticmethod
    def get_engineer_statistics(engineer, start_date=None, end_date=None):
        """Получить статистику работ инженера"""
        results = WorkResult.objects.filter(engineer=engineer)
        
        if start_date and end_date:
            results = results.filter(
                created_at__range=[start_date, end_date]
            )
        
        completed = results.filter(status='completed')
        
        stats = {
            'total_works': results.count(),
            'completed_works': completed.count(),
            'completion_rate': (completed.count() / results.count() * 100) if results.count() > 0 else 0,
            'average_quality': 0,
            'average_duration': 0
        }
        
        if completed.exists():
            avg_quality = sum(r.work_quality or 0 for r in completed) / completed.count()
            stats['average_quality'] = avg_quality
            
            durations = []
            for result in completed:
                duration = WorkResultHelper.calculate_completion_time(result)
                if duration:
                    durations.append(duration['total_minutes'])
            
            if durations:
                stats['average_duration'] = sum(durations) / len(durations)
        
        return stats


class ActHelper:
    """Помощник для работы с актами"""
    
    @staticmethod
    def generate_act_number(work_result):
        """Генерировать уникальный номер акта"""
        date_str = datetime.now().strftime('%Y%m%d')
        id_str = str(work_result.id)[:8].upper()
        return f"АКТ-{date_str}-{id_str}"
    
    @staticmethod
    def generate_act_content(work_result):
        """Генерировать содержание акта"""
        request = work_result.work_request
        duration = WorkResultHelper.calculate_completion_time(work_result)
        
        duration_str = ''
        if duration:
            duration_str = f"{duration['hours']}ч. {duration['minutes']}мин."
        
        content = f"""
        АКТ ВЫПОЛНЕННОЙ РАБОТЫ
        
        Номер акта: {ActHelper.generate_act_number(work_result)}
        Дата: {datetime.now().strftime('%d.%m.%Y')}
        
        ИНФОРМАЦИЯ О ЗАЯВКЕ:
        Тип работы: {request.get_work_type_display()}
        Адрес объекта: {request.object_address}
        Описание: {request.description}
        
        ИНФОРМАЦИЯ О ВЫПОЛНЕНИИ:
        Инженер: {work_result.engineer.get_full_name()}
        Время начала: {work_result.actual_start_time.strftime('%d.%m.%Y %H:%M')}
        Время окончания: {work_result.actual_end_time.strftime('%d.%m.%Y %H:%M') if work_result.actual_end_time else '—'}
        Продолжительность: {duration_str}
        
        ОПИСАНИЕ ВЫПОЛНЕННЫХ РАБОТ:
        {work_result.work_description}
        
        ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ:
        {work_result.findings}
        
        РЕКОМЕНДАЦИИ:
        {work_result.recommendations}
        
        КАЧЕСТВО РАБОТЫ: {work_result.work_quality}/5
        """
        
        return content.strip()
    
    @staticmethod
    def get_unsigned_acts():
        """Получить неподписанные акты"""
        return WorkAct.objects.filter(
            status='draft'
        ).select_related('work_result__engineer')


class EmailNotifications:
    """Отправка уведомлений по email"""
    
    @staticmethod
    def send_request_assigned(work_request):
        """Отправить уведомление об назначении заявки"""
        if not work_request.assigned_to or not work_request.assigned_to.email:
            return False
        
        subject = f"Вам назначена новая заявка: {work_request.object_address}"
        
        context = {
            'engineer': work_request.assigned_to.get_full_name(),
            'request': work_request,
            'date': work_request.planned_date,
            'time': work_request.planned_time_start,
        }
        
        message = f"""
        Вам назначена новая заявка на выполнение работы
        
        Адрес: {work_request.object_address}
        Тип: {work_request.get_work_type_display()}
        Дата: {work_request.planned_date}
        Время: {work_request.planned_time_start}
        Приоритет: {work_request.get_priority_display()}
        
        Описание: {work_request.description}
        """
        
        return send_mail(
            subject,
            message,
            'noreply@fieldwork.com',
            [work_request.assigned_to.email],
            fail_silently=True
        )
    
    @staticmethod
    def send_work_completed(work_result):
        """Отправить уведомление о завершении работы"""
        coordinator_email = 'coordinator@fieldwork.com'
        
        subject = f"Работа завершена: {work_result.work_request.object_address}"
        
        message = f"""
        Работа успешно завершена и готова к проверке
        
        Инженер: {work_result.engineer.get_full_name()}
        Адрес: {work_result.work_request.object_address}
        Время начала: {work_result.actual_start_time.strftime('%d.%m.%Y %H:%M')}
        Время окончания: {work_result.actual_end_time.strftime('%d.%m.%Y %H:%M') if work_result.actual_end_time else '—'}
        
        Описание: {work_result.work_description}
        """
        
        return send_mail(
            subject,
            message,
            'noreply@fieldwork.com',
            [coordinator_email],
            fail_silently=True
        )
    
    @staticmethod
    def send_act_ready_for_signature(act):
        """Отправить уведомление что акт готов к подписи"""
        engineer = act.work_result.engineer
        
        if not engineer.email:
            return False
        
        subject = f"Акт готов к подписи: {act.act_number}"
        
        message = f"""
        Акт выполненной работы готов к вашей подписи
        
        Номер акта: {act.act_number}
        Работа: {act.work_result.work_request.object_address}
        Дата: {act.act_date}
        
        Пожалуйста, подпишите акт в системе.
        """
        
        return send_mail(
            subject,
            message,
            'noreply@fieldwork.com',
            [engineer.email],
            fail_silently=True
        )


class DataExporter:
    """Экспорт данных"""
    
    @staticmethod
    def export_requests_to_csv(start_date, end_date):
        """Экспортировать заявки в CSV"""
        import csv
        from io import StringIO
        
        requests = WorkRequest.objects.filter(
            planned_date__range=[start_date, end_date]
        )
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'ID', 'Адрес', 'Тип работы', 'Статус', 'Приоритет',
            'Дата', 'Инженер', 'Описание', 'Контакт', 'Телефон'
        ])
        
        for req in requests:
            writer.writerow([
                str(req.id),
                req.object_address,
                req.get_work_type_display(),
                req.get_status_display(),
                req.get_priority_display(),
                req.planned_date,
                req.assigned_to.get_full_name() if req.assigned_to else '—',
                req.description,
                req.contact_person,
                req.contact_phone
            ])
        
        return output.getvalue()
    
    @staticmethod
    def export_results_to_json(start_date, end_date):
        """Экспортировать результаты в JSON"""
        results = WorkResult.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        data = []
        for result in results:
            duration = WorkResultHelper.calculate_completion_time(result)
            
            data.append({
                'id': str(result.id),
                'engineer': result.engineer.get_full_name(),
                'work_type': result.work_request.get_work_type_display(),
                'address': result.work_request.object_address,
                'description': result.work_description,
                'findings': result.findings,
                'quality': result.work_quality,
                'duration_minutes': duration['total_minutes'] if duration else None,
                'start_time': result.actual_start_time.isoformat(),
                'end_time': result.actual_end_time.isoformat() if result.actual_end_time else None,
                'status': result.get_status_display(),
            })
        
        return json.dumps(data, ensure_ascii=False, indent=2)
