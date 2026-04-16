import factory

from apps.enrollments.models import Enrollment
from apps.events.tests.factories import EventFactory
from apps.users.tests.factories import VerifiedSeekerFactory


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    event = factory.SubFactory(EventFactory)
    seeker = factory.SubFactory(VerifiedSeekerFactory)
    status = "enrolled"
