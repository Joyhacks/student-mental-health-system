from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from records.models import MentalHealthRecord

TABLE = MentalHealthRecord._meta.db_table


class Command(BaseCommand):
    help = 'Demonstrate encryption at rest by comparing the decrypted value with the raw stored ciphertext.'

    def handle(self, *args, **options):
        record = MentalHealthRecord.objects.order_by('id').first()
        if record is None:
            raise CommandError('No records found. Run "manage.py seed_demo" first.')

        # Read the raw column straight from the database, bypassing the field's
        # decryption, so we see exactly what is persisted on disk.
        with connection.cursor() as cursor:
            # The table name is a trusted constant from the model's own metadata,
            # not user input, and the id is passed as a bound parameter, so this
            # cannot be an injection vector.
            cursor.execute(
                f'SELECT content FROM {TABLE} WHERE id = %s',  # nosec B608
                [record.id],
            )
            raw_value = cursor.fetchone()[0]

        self.stdout.write(f'Record #{record.id}: {record}')
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Read through Django (decrypted plaintext):'))
        self.stdout.write(f'  {record.content}')
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Raw value stored in the database column (ciphertext):'))
        self.stdout.write(f'  {raw_value}')
        self.stdout.write('')
        if record.content != raw_value:
            self.stdout.write(self.style.SUCCESS(
                'Confirmed: the stored value differs from the plaintext and is unreadable ciphertext.'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                'Warning: the stored value matches the plaintext. Content is NOT encrypted.'
            ))
