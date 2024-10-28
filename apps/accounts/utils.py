def log_action(request, action, target, detail=''):
    from .models import AuditLog
    AuditLog.objects.create(
        actor=request.user,
        action=action,
        target=target,
        detail=detail,
    )
def log_action_system(action, target, detail=''):
    from .models import AuditLog
    AuditLog.objects.create(
        actor=None,
        action=action,
        target=target,
        detail=detail,
    )