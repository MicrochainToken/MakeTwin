# Reusable model and part semantics

The model and its meaning are the product; animation is a demonstration. Deliver independently addressable named parts in Blender and GLB, with stable IDs shared by parts.json, explorer.json and the exported manifest. Preserve physical assembly hierarchy and pivots in the Blender source. GLB exporters may flatten animated transforms; document that representation and preserve the logical assembly graph in parts.json. No chatbot is required.

## parts.json

Use schemaVersion 1, units `metres`, coordinateSystem `glTF-Y-up`, a concise product name, and `parts` with one record per exported part. IDs must exactly match model.manifest.json. `assemblies` declares logical grouping IDs; assembly records need id, label and purpose. A part's assembly must name one of them. `parent` is either null or another part ID; it describes the physical attachment, not the display explosion. Do not create cycles. Each part needs:

- id, label and a specific nonempty function: what it does, retains, seals, supports or encloses. Repeated hardware may share a family description but identifies its actual host.
- evidence: observed, inferred or illustrative; evidenceNote explains the reference or uncertainty without presenting guesses as manufacturer facts.
- assembly, parent and interfaces: an array of {target, type, evidence}, naming valid part IDs and a concrete relation such as seals, fastens, supports, encloses, drives or mates.
- motion: {kind: fixed|unknown|rotation|translation}. Use unknown for undocumented movement. For a supported rotation/translation include space (`model` or `parent`), a unit-length axis, pivot in metres and range [min,max]; unit is `radians` for rotation and `metres` for translation. Explain the basis in motion.note. A display explosion offset alone does not establish a physical removal axis or permitted range.

Keep descriptions concise and product-specific. A screw secures a named cover; a washer distributes the fastening load; a ring seals a declared interface. Avoid empty descriptions such as 'engine part'. Document inference rather than withholding useful approximate geometry. Do not invent hidden gearing or divide castings merely to increase count.

## Delivery checks

Run `python scripts/validate_parts.py --manifest model.manifest.json --parts parts.json --out parts-audit.json` after final export. The supervisor also validates coverage. Review a representative mechanism, a seal and repeated hardware against the model. Exported IDs, function records and viewer selections must agree. Check separately whether geometry, motion, semantic coverage, explosion metadata and browser interaction passed; a schema pass does not prove functional correctness.
