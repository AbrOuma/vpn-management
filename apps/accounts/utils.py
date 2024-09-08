def log_action(request, action, target, detail=''):
    from .models import AuditLog
    AuditLog.objects.create(
        actor=request.user,
        action=action,
        target=target,
        detail=detail,
    )