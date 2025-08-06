# Generated manually

import uuid
from django.db import migrations

def convert_ids_to_uuid(apps, schema_editor):
    # Get the historical version of the PolicyViolation model
    PolicyViolation = apps.get_model('chatbot', 'PolicyViolation')
    db_alias = schema_editor.connection.alias
    
    # Get all policy violations
    policy_violations = PolicyViolation.objects.using(db_alias).all()
    
    # Create a temporary table to store old_id -> new_uuid mappings
    id_mappings = {}
    
    # First pass: generate new UUIDs for each record
    for violation in policy_violations:
        # Store the old ID and generate a new UUID
        old_id = violation.id
        new_id = uuid.uuid4()
        id_mappings[old_id] = new_id
    
    # Second pass: update the records with new UUIDs
    # We need to use raw SQL because Django ORM will try to validate UUIDs
    for old_id, new_id in id_mappings.items():
        schema_editor.execute(
            f"UPDATE chatbot_policyviolation SET id = '{new_id}' WHERE id = '{old_id}'"
        )

class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0004_auto_20250715_2129'),
    ]

    operations = [
        migrations.RunPython(convert_ids_to_uuid),
    ]