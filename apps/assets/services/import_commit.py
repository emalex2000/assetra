from django.db import transaction

from apps.assets.models import Asset, AssetCategories


def commit_import_rows(import_session):
    """
    Imports all valid rows from an AssetImportSession into real Asset records.

    Returns:
    - imported_count
    - failed_count
    - preview of failed rows
    """
    company = import_session.company

    valid_rows = list(
        import_session.rows.filter(is_valid=True, imported_assets__isnull=True)
        .order_by("row_number")
    )

    imported_count = 0
    failed_count = 0
    failed_rows = []

    # preload categories for this company once
    company_categories = {
        category.name.strip().lower(): category
        for category in AssetCategories.objects.filter(company=company)
    }

    for row in valid_rows:
        data = row.normalized_data or {}

        try:
            with transaction.atomic():
                category_obj = None
                category_name = data.get("category")

                if category_name:
                    category_obj = company_categories.get(str(category_name).strip().lower())

                asset = Asset.objects.create(
                    company=company,
                    name=data.get("name"),
                    serial_number=data.get("serial_number") or None,
                    model=data.get("model") or None,
                    category=category_obj,
                    location_country=data.get("location_country") or "",
                )

                row.imported_assets = asset
                row.save(update_fields=["imported_assets"])

                imported_count += 1

        except Exception as exc:
            failed_count += 1
            failed_rows.append(
                {
                    "row_number": row.row_number,
                    "normalized_data": row.normalized_data,
                    "error": str(exc),
                }
            )

    total_invalid_rows = import_session.rows.filter(is_valid=False).count()

    import_session.status = "COMPLETED"
    import_session.save(update_fields=["status", "updated_at"])

    return {
        "import_id": str(import_session.import_id),
        "status": import_session.status,
        "imported_count": imported_count,
        "failed_count": failed_count + total_invalid_rows,
        "failed_rows_preview": failed_rows[:10],
    }