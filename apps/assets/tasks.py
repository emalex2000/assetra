from celery import shared_task
from .models import AssetImportSession
from apps.assets.services.import_commit import commit_import_rows
from django.db import transaction

@shared_task(bind=True)
def commit_asset_import_task(self, import_id):
    try:
        import_session = AssetImportSession.objects.get(import_id=import_id)
        if import_session.status != "VALIDATED":
            return{
                "import_id": str(import_session.import_id),
                "status": import_session.status,
                "detail": "import session must be validated before commit",
            }
        
        result = commit_import_rows(import_session)
        return result
    
    except AssetImportSession.DoesNotExist:
        return{
            "import_id": str(import_id),
            "status": "FAILED",
            "detail": "import session not found"
        }
    
    except Exception as exc:
        try:
            with transaction.atomic():
                import_session = AssetImportSession.objects.get(import_id=import_id),
                import_session.status = "FAILED",
                import_session.save(update_fields=["status", "updated_at"])
        except Exception:
            pass

        return{
            "import_id": str(import_id),
            "status": "Failed",
            "detail": str(exc),
        }