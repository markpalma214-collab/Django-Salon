from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import ServiceCategory


class StaticViewSitemap(Sitemap):
    priority = 1.0          # 1.0 = highest importance on your site (your homepage)
    changefreq = "weekly"   # Hints to Google how often to re-check for updates

    def items(self):
        # Returns a list of URL names from your urls.py
        return ["homepage"]

    def location(self, item):
        # Converts "homepage" into "/"
        return reverse(item)


class ServiceCategorySitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        # Queries Supabase for every service category you created in Admin
        return ServiceCategory.objects.all()

    def location(self, obj):
        # Points Google to the services section on your homepage
        return f"{reverse('homepage')}#services"