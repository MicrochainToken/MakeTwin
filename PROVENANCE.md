# Project provenance and dependencies

MakeTwin builds on component-level Blender helpers and a mechanical showcase
viewer developed by the project authors. The reusable skill contains source,
references, tests and synthetic examples. User-supplied product photos, PDF
manuals, credentials and private evaluation records are not part of this release.

The repository also retains the illustrative engine preview in templates/viewer/
and its rendered demonstration in docs/demo.gif. These are generated demo assets,
not validated manufacturer geometry. The preview manifest preserves its partial
status. Some inherited evidence notes refer to a manual that is not distributed;
those references cannot be independently checked from this repository. The
preview is not a service procedure or evidence of an accepted reconstruction.
The MakeTwin logo and wordmark are project branding. Demo media are retained
from 1.0.0; this maintenance release updates tooling and documentation.

The viewer bundles Three.js 0.169.0 and its helpers under MIT. Its core module
includes a port of Mapbox Earcut 2.2.4 under ISC. Preserve THREE-LICENSE.txt,
EARCUT-LICENSE.txt and vendor-sources.json alongside distributed viewer assets.
The source/version records include the upstream license location and hashes of
the locally rewritten modules. Pillow is an installed dependency, not bundled.

Manufacturer photos and manuals supplied for a separate product case retain their
own ownership; keep them separate from the reusable skill and check permission
before publishing a case or a reproduction based on it.
