from datetime import timedelta

import factory
from django.utils import timezone
from faker import Faker

from apps.events.models import Event
from apps.users.tests.factories import VerifiedFacilitatorFactory

faker = Faker()


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    title = factory.LazyAttribute(lambda o: faker.sentence(nb_words=4))
    description = factory.LazyAttribute(lambda o: faker.paragraph())
    language = "English"
    location = "Mumbai"
    starts_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    ends_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7, hours=2))
    capacity = 30
    created_by = factory.SubFactory(VerifiedFacilitatorFactory)
