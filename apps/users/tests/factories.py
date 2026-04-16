import factory
from django.contrib.auth import get_user_model
from faker import Faker

from apps.users.models import Profile

faker = Faker()
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda o: faker.unique.email())
    username = factory.LazyAttribute(lambda o: o.email)
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)
    role = "seeker"
    is_email_verified = True


class VerifiedSeekerFactory(factory.django.DjangoModelFactory):
    """Creates a User + verified Seeker profile."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.LazyAttribute(lambda o: faker.unique.email())
    username = factory.LazyAttribute(lambda o: o.email)
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        if create:
            ProfileFactory(user=self, role="seeker", is_email_verified=True)


class VerifiedFacilitatorFactory(factory.django.DjangoModelFactory):
    """Creates a User + verified Facilitator profile."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.LazyAttribute(lambda o: faker.unique.email())
    username = factory.LazyAttribute(lambda o: o.email)
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        if create:
            ProfileFactory(user=self, role="facilitator", is_email_verified=True)
