from django.core.management.base import BaseCommand
from booking.models import Lab, Computer


LABS = [
    {
        "name": "Software Engineering Lab",
        "location": "TTU Campus",
        "description": "Laboratory for Software Engineering students and courses.",
        "capacity": 40,
    },
    {
        "name": "Computer Science Lab",
        "location": "TTU Campus",
        "description": "Laboratory for Computer Science students and courses.",
        "capacity": 40,
    },
    {
        "name": "GIS Lab",
        "location": "TTU Campus",
        "description": "Geographic Information Systems laboratory.",
        "capacity": 10,
    },
    {
        "name": "Tech Build Lab",
        "location": "TTU Campus",
        "description": "Innovation and technology build space.",
        "capacity": 0,
    },
]


class Command(BaseCommand):
    help = "Seeds the database with the default TTU laboratories and their computers"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding laboratories..."))

        for lab_data in LABS:
            lab, created = Lab.objects.get_or_create(
                name=lab_data["name"],
                defaults={
                    "location": lab_data["location"],
                    "description": lab_data["description"],
                    "capacity": lab_data["capacity"],
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  [CREATED] {lab.name} (capacity: {lab.capacity})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"  [EXISTS]  {lab.name} — skipped")
                )
                continue

            # Create Computer entries for labs that have computers
            if lab.capacity > 0:
                computers_created = 0
                for i in range(1, lab.capacity + 1):
                    _, comp_created = Computer.objects.get_or_create(
                        lab=lab,
                        computer_number=i,
                        defaults={"status": "available"},
                    )
                    if comp_created:
                        computers_created += 1

                self.stdout.write(
                    f"           -> {computers_created} computer(s) added"
                )
            else:
                self.stdout.write("           -> No computers (Tech Build Lab)")

        self.stdout.write(self.style.SUCCESS("\nDone! Laboratories seeded successfully."))
