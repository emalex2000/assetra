from collections import Counter

from django_countries import countries

from apps.assets.constants import SUPPORTED_IMPORT_FIELDS, COUNTRY_ALIASES
from apps.assets.models import Asset, AssetCategories


def normalize_text(value):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        return value or None

    return str(value).strip()


def build_country_lookup():
    """
    Creates two lookups:
    - country code -> country code
    - lowercase country name -> country code
    """
    code_lookup = {}
    name_lookup = {}

    for code, name in countries:
        code_lookup[code.upper()] = code
        name_lookup[name.strip().lower()] = code

    return code_lookup, name_lookup


def resolve_country(value, code_lookup, name_lookup):
    if not value:
        return None, None

    value = str(value).strip()
    if not value:
        return None, None

    upper_value = value.upper()
    lower_value = value.lower()

    if upper_value in code_lookup:
        return code_lookup[upper_value], None

    if lower_value in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[lower_value], None

    if lower_value in name_lookup:
        return name_lookup[lower_value], None

    return None, f"'{value}' is not a valid country."

def validate_import_rows(import_session):
    """
    Validates all staged AssetImportRow rows for an import session.
    Updates rows with:
    - is_valid
    - errors

    Returns a summary dict for the frontend.
    """
    rows = list(import_session.rows.all().order_by("row_number"))

    company = import_session.company

    # Pull serial numbers from file
    serials_in_file = []
    for row in rows:
        data = row.normalized_data or {}
        serial = normalize_text(data.get("serial_number"))
        if serial:
            serials_in_file.append(serial)

    serial_counter = Counter(serials_in_file)
    duplicate_serials_in_file = {
        serial for serial, count in serial_counter.items() if count > 1
    }

    # Existing serial numbers already in DB
    existing_serials = set(
        Asset.objects.filter(company=company, serial_number__in=serials_in_file)
        .values_list("serial_number", flat=True)
    )

    # Categories belonging to this company
    company_categories = {
        category.name.strip().lower(): category
        for category in AssetCategories.objects.filter(company=company)
    }

    code_lookup, name_lookup = build_country_lookup()

    valid_count = 0
    invalid_count = 0
    preview_rows = []

    for row in rows:
        data = row.normalized_data or {}
        errors = []

        # normalize text fields
        name = normalize_text(data.get("name"))
        serial_number = normalize_text(data.get("serial_number"))
        model = normalize_text(data.get("model"))
        category_value = normalize_text(data.get("category"))
        location_country_value = normalize_text(data.get("location_country"))

        # required fields
        for field_name, config in SUPPORTED_IMPORT_FIELDS.items():
            if not config.get("required"):
                continue

            value = normalize_text(data.get(field_name))
            if not value:
                readable = field_name.replace("_", " ").title()
                errors.append(f"{readable} is required.")

        # duplicate in file
        if serial_number and serial_number in duplicate_serials_in_file:
            errors.append("Serial number is duplicated in the uploaded file.")

        # duplicate in database
        if serial_number and serial_number in existing_serials:
            errors.append("Serial number already exists in the database.")

        # category validation
        resolved_category_name = None
        if category_value:
            category_obj = company_categories.get(category_value.lower())
            if not category_obj:
                errors.append(
                    f"Category '{category_value}' does not exist for this organisation."
                )
            else:
                resolved_category_name = category_obj.name

        # country validation
        resolved_country_code = None
        if location_country_value:
            resolved_country_code, country_error = resolve_country(
                location_country_value,
                code_lookup,
                name_lookup,
            )
            if country_error:
                errors.append(country_error)

        # optionally rewrite normalized data into cleaner form
        cleaned_data = {
            "name": name,
            "serial_number": serial_number,
            "model": model,
            "category": resolved_category_name or category_value,
            "location_country": resolved_country_code or location_country_value,
        }

        row.normalized_data = cleaned_data
        row.errors = errors
        row.is_valid = len(errors) == 0

        if row.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
# <================================save in memory later to make logic faster======================================>
        row.save(update_fields=["normalized_data", "errors", "is_valid"])

        if len(preview_rows) < 10:
            preview_rows.append(
                {
                    "row_number": row.row_number,
                    "normalized_data": row.normalized_data,
                    "is_valid": row.is_valid,
                    "errors": row.errors,
                }
            )

    import_session.valid_rows = valid_count
    import_session.invalid_rows = invalid_count
    import_session.status = "VALIDATED"
    import_session.save(update_fields=["valid_rows", "invalid_rows", "status", "updated_at"])

    return {
        "import_id": str(import_session.import_id),
        "status": import_session.status,
        "summary": {
            "total_rows": len(rows),
            "valid_rows": valid_count,
            "invalid_rows": invalid_count,
            "duplicate_rows": len(duplicate_serials_in_file),
        },
        "preview_rows": preview_rows,
    }