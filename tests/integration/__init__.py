"""Integration tests: plone-client against a real Plone site.

They need Docker and are skipped by the default test run; ``make
test-integration`` runs them. ``PLONE_IMAGE`` picks another backend image.
"""

USERNAME = "admin"
PASSWORD = "admin"
