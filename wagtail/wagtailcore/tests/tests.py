import unittest

from django.test import TestCase
from django.core.cache import cache

from wagtail.wagtailcore.models import Page, Site
from wagtail.wagtailcore.utils import resolve_model_string
from wagtail.tests.models import SimplePage


class TestPageUrlTags(TestCase):
    fixtures = ['test.json']

    def test_pageurl_tag(self):
        response = self.client.get('/events/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
                            '<a href="/events/christmas/">Christmas</a>')

    def test_slugurl_tag(self):
        response = self.client.get('/events/christmas/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
                            '<a href="/events/">Back to events index</a>')


class TestSiteRootPathsCache(TestCase):
    fixtures = ['test.json']

    def test_cache(self):
        """
        This tests that the cache is populated when building URLs
        """
        # Get homepage
        homepage = Page.objects.get(url_path='/home/')

        # Warm up the cache by getting the url
        _ = homepage.url

        # Check that the cache has been set correctly
        self.assertEqual(cache.get('wagtail_site_root_paths'), [(1, '/home/', 'http://localhost')])

    def test_cache_clears_when_site_saved(self):
        """
        This tests that the cache is cleared whenever a site is saved
        """
        # Get homepage
        homepage = Page.objects.get(url_path='/home/')

        # Warm up the cache by getting the url
        _ = homepage.url

        # Check that the cache has been set
        self.assertTrue(cache.get('wagtail_site_root_paths'))

        # Save the site
        Site.objects.get(is_default_site=True).save()

        # Check that the cache has been cleared
        self.assertFalse(cache.get('wagtail_site_root_paths'))

    def test_cache_clears_when_site_deleted(self):
        """
        This tests that the cache is cleared whenever a site is deleted
        """
        # Get homepage
        homepage = Page.objects.get(url_path='/home/')

        # Warm up the cache by getting the url
        _ = homepage.url

        # Check that the cache has been set
        self.assertTrue(cache.get('wagtail_site_root_paths'))

        # Delete the site
        Site.objects.get(is_default_site=True).delete()

        # Check that the cache has been cleared
        self.assertFalse(cache.get('wagtail_site_root_paths'))

    def test_cache_clears_when_site_root_moves(self):
        """
        This tests for an issue where if a site root page was moved, all
        the page urls in that site would change to None.

        The issue was caused by the 'wagtail_site_root_paths' cache
        variable not being cleared when a site root page was moved. Which
        left all the child pages thinking that they are no longer in the
        site and return None as their url.

        Fix: d6cce69a397d08d5ee81a8cbc1977ab2c9db2682
        Discussion: https://github.com/torchbox/wagtail/issues/7
        """
        # Get homepage, root page and site
        root_page = Page.objects.get(id=1)
        homepage = Page.objects.get(url_path='/home/')
        default_site = Site.objects.get(is_default_site=True)

        # Create a new homepage under current homepage
        new_homepage = SimplePage(title="New Homepage", slug="new-homepage")
        homepage.add_child(instance=new_homepage)

        # Set new homepage as the site root page
        default_site.root_page = new_homepage
        default_site.save()

        # Warm up the cache by getting the url
        _ = homepage.url

        # Move new homepage to root
        new_homepage.move(root_page, pos='last-child')

        # Get fresh instance of new_homepage
        new_homepage = Page.objects.get(id=new_homepage.id)

        # Check url
        self.assertEqual(new_homepage.url, '/')

    def test_cache_clears_when_site_root_slug_changes(self):
        """
        This tests for an issue where if a site root pages slug was
        changed, all the page urls in that site would change to None.

        The issue was caused by the 'wagtail_site_root_paths' cache
        variable not being cleared when a site root page was changed.
        Which left all the child pages thinking that they are no longer in
        the site and return None as their url.

        Fix: d6cce69a397d08d5ee81a8cbc1977ab2c9db2682
        Discussion: https://github.com/torchbox/wagtail/issues/157
        """
        # Get homepage
        homepage = Page.objects.get(url_path='/home/')

        # Warm up the cache by getting the url
        _ = homepage.url

        # Change homepage title and slug
        homepage.title = "New home"
        homepage.slug = "new-home"
        homepage.save()

        # Get fresh instance of homepage
        homepage = Page.objects.get(id=homepage.id)

        # Check url
        self.assertEqual(homepage.url, '/')


class TestResolveModelString(TestCase):
    def test_resolve_from_string(self):
        model = resolve_model_string('wagtailcore.Page')

        self.assertEqual(model, Page)

    def test_resolve_from_string_with_default_app(self):
        model = resolve_model_string('Page', default_app='wagtailcore')

        self.assertEqual(model, Page)

    def test_resolve_from_string_with_different_default_app(self):
        model = resolve_model_string('wagtailcore.Page', default_app='wagtailadmin')

        self.assertEqual(model, Page)

    def test_resolve_from_class(self):
        model = resolve_model_string(Page)

        self.assertEqual(model, Page)

    def test_resolve_from_string_invalid(self):
        self.assertRaises(ValueError, resolve_model_string, 'wagtail.wagtailcore.Page')

    def test_resolve_from_string_with_incorrect_default_app(self):
        self.assertRaises(LookupError, resolve_model_string, 'Page', default_app='wagtailadmin')

    def test_resolve_from_string_with_no_default_app(self):
        self.assertRaises(ValueError, resolve_model_string, 'Page')

    @unittest.expectedFailure # Raising LookupError instead
    def test_resolve_from_class_that_isnt_a_model(self):
        self.assertRaises(ValueError, resolve_model_string, object)

    @unittest.expectedFailure # Raising LookupError instead
    def test_resolve_from_bad_type(self):
        self.assertRaises(ValueError, resolve_model_string, resolve_model_string)
