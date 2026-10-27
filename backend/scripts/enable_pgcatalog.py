"""Switch the site's catalog to plone.pgcatalog and index all content.

Run after ``create_site.py``, as its own process::

    zconsole run instance/etc/zope.conf scripts/enable_pgcatalog.py

Two reasons it is a separate step:

* plone.exportimport's final import step, which loads the example content,
  calls ``catalog.getAllBrains()``; plone.pgcatalog does not implement it. So
  the site is built on ZCatalog first, then switched over, which is the path
  plone.pgcatalog documents for existing sites: install the profile (it keeps
  the add-ons' indexes), then rebuild.
* plone.pgcatalog builds its index registry from the sites it finds when the
  database opens. In the process that created the site there was none yet,
  and a rebuild there indexes nothing; a fresh process finds the site.

Running it again on a site that already uses plone.pgcatalog does nothing,
unless ``REBUILD=1`` asks for a rebuild.
"""

from AccessControl.SecurityManagement import newSecurityManager
from Testing.makerequest import makerequest
from zope.component.hooks import setSite

import os
import transaction


SITE_ID = os.getenv("SITE_ID", "Plone")
PROFILE = "profile-plone.pgcatalog:default"
REBUILD = os.getenv("REBUILD", "").lower() in ("1", "true", "yes", "on")

app = makerequest(globals()["app"])
admin = app.acl_users.getUserById("admin").__of__(app.acl_users)
newSecurityManager(None, admin)

site = app[SITE_ID]
setSite(site)

setup_tool = site.portal_setup
installed = setup_tool.getLastVersionForProfile(PROFILE) != "unknown"
if not installed:
    setup_tool.runAllImportStepsFromProfile(PROFILE)
    transaction.commit()

catalog = site.portal_catalog
if not installed or REBUILD:
    catalog.clearFindAndRebuild()
    transaction.commit()
print(f"{SITE_ID}: {len(catalog.unrestrictedSearchResults())} objects in the catalog")
