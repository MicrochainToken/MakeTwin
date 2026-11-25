# Validation status — v1.0.0

Main deliverable: a reusable named-part Blender/glTF model plus parts.json with functions, evidence, assemblies, interfaces, physical attachments and supported movement. The viewer demonstrates and inspects those assets. Rich meaningful detail and labeled plausible internals are allowed; there is no mandatory component count or chatbot.

No credentials, product images/manuals or generated product outputs are included.

The default exporter preserves joint-node hierarchy. Optional --fast-transform-export (for dense rigid models) creates model-space animated mesh nodes without repeatedly sampling the exporter per NLA track; it preserves neutral rest and clip-specific held poses. The physical hierarchy remains in the Blender source; metadata records the logical assembly graph. The checker uses rigid BVH caching and AABB broad phase while retaining the same collision tests, thresholds and authored samples. Completed stages write an explicitly incomplete progress report before finalization.

Validation evidence: on a saved 448-part model the original and accelerated checker findings matched exactly (1,321 errors, 58 warnings), with local times of 425.484 and 90.950 seconds. Twelve separate fixtures checked pair/count equivalence, moving-pair filtering, duplicate-report exclusion, modifier changes and mesh replacement. Semantic validation fixtures covered missing IDs, cyclic parents and invalid motion axes. The dense animation exporter was exercised with all named components and clips. These are local implementation checks, not manufacturer accuracy, universal cross-platform certification or acceptance of the generated product. See README.md for known partial-result limitations.

Display-only explosions remain distinct from physical service/removal motion. The full checker still reports display intersections; no exemptions are added merely to improve the pass count. Browser effects and metadata schema validity do not establish collision freedom or functional correctness.
