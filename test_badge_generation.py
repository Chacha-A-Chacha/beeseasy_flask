"""
Badge Generation Script
Creates sample badges for all badge types to test styling and layout
"""

import sys
from io import BytesIO
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.services.badge_service import BadgeService


class MockAttendee:
    """Mock attendee for badge generation"""

    def __init__(
        self,
        reference_number,
        first_name,
        last_name,
        organization,
        job_title,
        ticket_type,
        professional_category=None,
    ):
        self.id = 999
        self.reference_number = reference_number
        self.first_name = first_name
        self.last_name = last_name
        self.organization = organization
        self.job_title = job_title
        self.ticket_type = MockEnum(ticket_type)
        self.professional_category = professional_category


class MockExhibitor:
    """Mock exhibitor for badge generation"""

    def __init__(
        self,
        reference_number,
        first_name,
        last_name,
        job_title,
        company_legal_name,
        package_type,
        booth_number=None,
        exhibitor_badges_needed=1,
    ):
        self.id = 999
        self.reference_number = reference_number
        self.first_name = first_name
        self.last_name = last_name
        self.job_title = job_title
        self.company_legal_name = company_legal_name
        self.package_type = MockEnum(package_type)
        self.booth_number = booth_number
        self.exhibitor_badges_needed = exhibitor_badges_needed


class MockEnum:
    """Mock enum for ticket/package types"""

    def __init__(self, value):
        self.value = value


def generate_qr_code(data):
    """Generate QR code for testing"""
    import qrcode

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    return img_buffer


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def create_attendee_badges():
    """Create sample attendee badges for different ticket types"""
    print_header("GENERATING ATTENDEE BADGES")

    attendee_samples = [
        {
            "reference_number": "BEE20251203A1LAOO",
            "first_name": "John",
            "last_name": "Doe",
            "organization": "African Beekeepers Association",
            "job_title": "Research Scientist",
            "ticket_type": "early_bird",
        },
        {
            "reference_number": "BEE20251203A2XBPP",
            "first_name": "Jane",
            "last_name": "Smith",
            "organization": "Pollination Research Institute",
            "job_title": "Lead Entomologist",
            "ticket_type": "regular",
        },
        {
            "reference_number": "BEE20251203A3YCQQ",
            "first_name": "Michael",
            "last_name": "Johnson",
            "organization": "East Africa Conservation Society",
            "job_title": "Project Manager",
            "ticket_type": "late_registration",
        },
    ]

    results = []

    for sample in attendee_samples:
        print(f"\nCreating badge for: {sample['first_name']} {sample['last_name']}")
        print(f"  Organization: {sample['organization']}")
        print(f"  Ticket Type: {sample['ticket_type']}")

        # Create mock attendee
        attendee = MockAttendee(**sample)

        # Generate QR code
        qr_buffer = generate_qr_code(
            f"POLLINATION2026-999-{sample['reference_number']}"
        )

        # Create badge
        try:
            success, filename = BadgeService._create_attendee_badge(attendee, qr_buffer)
            if success:
                print(f"  ✓ Badge created: {filename}")
                results.append(
                    {"type": "attendee", "status": "success", "file": filename}
                )
            else:
                print(f"  ✗ Failed: {filename}")
                results.append(
                    {"type": "attendee", "status": "failed", "error": filename}
                )
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({"type": "attendee", "status": "failed", "error": str(e)})

    return results


def create_media_badges():
    """Create sample media pass badges"""
    print_header("GENERATING MEDIA PASS BADGES")

    media_samples = [
        {
            "reference_number": "BEE20251203M1DRAA",
            "first_name": "Sarah",
            "last_name": "Williams",
            "organization": "Tanzania Daily News",
            "job_title": "Environmental Journalist",
            "ticket_type": "media_pass",
            "professional_category": "MEDIA_JOURNALIST",
        },
        {
            "reference_number": "BEE20251203M2ESBB",
            "first_name": "David",
            "last_name": "Brown",
            "organization": "East African Broadcasting",
            "job_title": "Senior Reporter",
            "ticket_type": "media_pass",
            "professional_category": "MEDIA_JOURNALIST",
        },
    ]

    results = []

    for sample in media_samples:
        print(
            f"\nCreating media pass for: {sample['first_name']} {sample['last_name']}"
        )
        print(f"  Organization: {sample['organization']}")

        # Create mock attendee (media)
        attendee = MockAttendee(**sample)

        # Generate QR code
        qr_buffer = generate_qr_code(
            f"POLLINATION2026-999-{sample['reference_number']}"
        )

        # Create badge
        try:
            success, filename = BadgeService._create_media_pass(attendee, qr_buffer)
            if success:
                print(f"  ✓ Media pass created: {filename}")
                results.append({"type": "media", "status": "success", "file": filename})
            else:
                print(f"  ✗ Failed: {filename}")
                results.append({"type": "media", "status": "failed", "error": filename})
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({"type": "media", "status": "failed", "error": str(e)})

    return results


def create_exhibitor_badges():
    """Create sample exhibitor badges"""
    print_header("GENERATING EXHIBITOR BADGES")

    exhibitor_samples = [
        {
            "reference_number": "BEE20251203E1FTCC",
            "first_name": "Robert",
            "last_name": "Anderson",
            "job_title": "CEO",
            "company_legal_name": "African Honey Producers Ltd",
            "package_type": "standard_booth",
            "booth_number": "A12",
            "exhibitor_badges_needed": 3,
        },
        {
            "reference_number": "BEE20251203E2GUDD",
            "first_name": "Mary",
            "last_name": "Wilson",
            "job_title": "Sales Director",
            "company_legal_name": "Pollination Equipment International",
            "package_type": "premium_booth",
            "booth_number": "B05",
            "exhibitor_badges_needed": 5,
        },
        {
            "reference_number": "BEE20251203E3HVEE",
            "first_name": "James",
            "last_name": "Taylor",
            "job_title": "Managing Director",
            "company_legal_name": "Sustainable Agriculture Solutions",
            "package_type": "standard_booth",
            "booth_number": None,
            "exhibitor_badges_needed": 2,
        },
    ]

    results = []

    for sample in exhibitor_samples:
        print(
            f"\nCreating exhibitor badge for: {sample['first_name']} {sample['last_name']}"
        )
        print(f"  Company: {sample['company_legal_name']}")
        print(f"  Booth: {sample['booth_number'] or 'Not assigned'}")

        # Create mock exhibitor
        exhibitor = MockExhibitor(**sample)

        # Generate QR code
        qr_buffer = generate_qr_code(
            f"POLLINATION2026-999-{sample['reference_number']}"
        )

        # Create badge
        try:
            success, filename = BadgeService._create_exhibitor_badge(
                exhibitor, qr_buffer
            )
            if success:
                print(f"  ✓ Exhibitor badge created: {filename}")
                results.append(
                    {"type": "exhibitor", "status": "success", "file": filename}
                )
            else:
                print(f"  ✗ Failed: {filename}")
                results.append(
                    {"type": "exhibitor", "status": "failed", "error": filename}
                )
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({"type": "exhibitor", "status": "failed", "error": str(e)})

    return results


def create_team_member_badges():
    """Create sample team member badges"""
    print_header("GENERATING TEAM MEMBER BADGES")

    # Create mock exhibitor
    exhibitor = MockExhibitor(
        reference_number="BEE20251203E1FTCC",
        first_name="Robert",
        last_name="Anderson",
        job_title="CEO",
        company_legal_name="African Honey Producers Ltd",
        package_type="standard_booth",
        booth_number="A12",
        exhibitor_badges_needed=3,
    )

    team_members = [
        {
            "member_name": "Alice Thompson",
            "member_role": "Sales Representative",
            "member_number": 2,
        },
        {
            "member_name": "Peter Martinez",
            "member_role": "Technical Specialist",
            "member_number": 3,
        },
    ]

    results = []

    for member in team_members:
        print(f"\nCreating team badge for: {member['member_name']}")
        print(f"  Company: {exhibitor.company_legal_name}")
        print(f"  Role: {member['member_role']}")
        print(
            f"  Badge: {member['member_number']} of {exhibitor.exhibitor_badges_needed}"
        )

        # Generate QR code
        qr_data = f"POLLINATION2026-999-TEAM-{member['member_number']}"
        qr_buffer = generate_qr_code(qr_data)

        # Create badge
        try:
            success, filename = BadgeService._create_team_member_badge(
                exhibitor=exhibitor,
                member_name=member["member_name"],
                member_role=member["member_role"],
                member_number=member["member_number"],
                qr_buffer=qr_buffer,
                qr_data=qr_data,
            )
            if success:
                print(f"  ✓ Team badge created: {filename}")
                results.append({"type": "team", "status": "success", "file": filename})
            else:
                print(f"  ✗ Failed: {filename}")
                results.append({"type": "team", "status": "failed", "error": filename})
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({"type": "team", "status": "failed", "error": str(e)})

    return results


def print_summary(all_results):
    """Print summary of badge generation"""
    print_header("BADGE GENERATION SUMMARY")

    by_type = {}
    for result in all_results:
        badge_type = result["type"]
        if badge_type not in by_type:
            by_type[badge_type] = {"success": 0, "failed": 0}

        if result["status"] == "success":
            by_type[badge_type]["success"] += 1
        else:
            by_type[badge_type]["failed"] += 1

    total_success = 0
    total_failed = 0

    for badge_type, stats in by_type.items():
        success = stats["success"]
        failed = stats["failed"]
        total = success + failed

        total_success += success
        total_failed += failed

        print(f"\n{badge_type.upper()} BADGES:")
        print(f"  Success: {success}/{total}")
        if failed > 0:
            print(f"  Failed: {failed}/{total}")

    print(f"\nOVERALL:")
    grand_total = total_success + total_failed
    print(f"  Total: {grand_total}")
    print(f"  Success: {total_success}")
    print(f"  Failed: {total_failed}")

    if grand_total > 0:
        success_rate = (total_success / grand_total) * 100
        print(f"  Success Rate: {success_rate:.1f}%")


def main():
    """Main function"""
    print_header("BADGE GENERATION SCRIPT")
    print("\nThis script creates sample badges for all badge types:")
    print("  - Attendee badges (various ticket types)")
    print("  - Media pass badges")
    print("  - Exhibitor badges")
    print("  - Team member badges")

    # Create Flask app context
    app = create_app()

    with app.app_context():
        all_results = []

        # Create all badge types
        all_results.extend(create_attendee_badges())
        all_results.extend(create_media_badges())
        all_results.extend(create_exhibitor_badges())
        all_results.extend(create_team_member_badges())

        # Print summary
        print_summary(all_results)

    print("\n" + "=" * 80)
    print("  Badge generation completed!")
    print("  Check: app/storage/badges/2025/")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
