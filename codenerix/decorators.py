from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied


def restrict_access_to_groups(groups: list, raise_exception: bool = False):
    """
    Decorator for views that requires the user to be part of a group,
    if they are not the user is not allowed into the page.
    If the raise_exception parameter is given the PermissionDenied exception
    is raised returning a 403 status code

    Usage:

    @method_decorator(
        restrict_access_to_groups(
            ["admin", "sales"],
            True
        ),
        name="dispatch"
    )

    Author: Ben Cleary (https://github.com/bencleary)
    """

    def in_groups(user):
        # checks if the user is authenticated, if not returns False
        if not user.is_authenticated:
            return False

        # checks if the user is a superuser or is part of the given groups
        if user.groups.filter(name__in=groups).exists() | user.is_superuser:
            return True

        # if raise_exception is given raise the 403 error
        if raise_exception:
            raise PermissionDenied

        # return False otherwise
        return False

    return user_passes_test(in_groups)
