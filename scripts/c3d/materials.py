"""Physically plausible material presets (Principled BSDF, exports cleanly to glTF PBR).

Pick the closest preset, then set `color` from the photos. Values follow real measured
ranges: dielectrics (plastic, rubber, paint, glass) have metallic 0; bare metals have
metallic 1. Anything in between is almost always wrong.
"""
import hashlib
import json

import bpy

PRESETS = {
    # plastics
    "abs_matte":        dict(color="#2a2c2f", metallic=0.0, roughness=0.55, specular=0.5),
    "abs_satin":        dict(color="#e9e9e6", metallic=0.0, roughness=0.35, specular=0.5),
    "plastic_glossy":   dict(color="#f2f2ef", metallic=0.0, roughness=0.12, specular=0.5, coat=0.3),
    "plastic_textured": dict(color="#1f2023", metallic=0.0, roughness=0.75, specular=0.4),
    "plastic_frosted":  dict(color="#e8eef0", metallic=0.0, roughness=0.45, alpha=0.7),
    "silicone":         dict(color="#d8d8d4", metallic=0.0, roughness=0.6, specular=0.35),
    "rubber":           dict(color="#151617", metallic=0.0, roughness=0.85, specular=0.3),
    # metals
    "aluminum_brushed": dict(color="#c7c9cc", metallic=1.0, roughness=0.35),
    "aluminum_anodized": dict(color="#3b3e42", metallic=1.0, roughness=0.3),
    "stainless_steel":  dict(color="#b9bcbf", metallic=1.0, roughness=0.22),
    "chrome":           dict(color="#e6e7e8", metallic=1.0, roughness=0.05),
    "painted_metal":    dict(color="#f0f0ee", metallic=0.0, roughness=0.4, specular=0.5, coat=0.2),
    "cast_iron":        dict(color="#3a3a3a", metallic=1.0, roughness=0.7),
    # transparent
    # Alpha is a portable approximation; sorting and lighting still vary by viewer.
    "glass_clear":      dict(color="#f4f8f8", metallic=0.0, roughness=0.03, alpha=0.18, ior=1.5),
    "glass_tinted":     dict(color="#1c2124", metallic=0.0, roughness=0.03, alpha=0.6, ior=1.5),
    "acrylic_smoked":   dict(color="#1d1f22", metallic=0.0, roughness=0.05, alpha=0.55),
    # soft goods and natural
    "fabric_mesh":      dict(color="#202124", metallic=0.0, roughness=0.95, specular=0.2, sheen=0.5),
    "leather":          dict(color="#3b2a20", metallic=0.0, roughness=0.55, specular=0.4),
    "wood_oak":         dict(color="#a77a4c", metallic=0.0, roughness=0.6, specular=0.4),
    "ceramic_glazed":   dict(color="#f4f3ef", metallic=0.0, roughness=0.08, specular=0.5),
    # lights and displays
    "led_lens":         dict(color="#5a1414", metallic=0.0, roughness=0.15, alpha=0.9),
    "display_off":      dict(color="#08090a", metallic=0.0, roughness=0.08, specular=0.5),
    "emissive":         dict(color="#ffffff", metallic=0.0, roughness=0.5, emission=1.0, emission_strength=8.0),
}

_INPUTS = {
    "metallic": "Metallic", "roughness": "Roughness", "ior": "IOR", "alpha": "Alpha",
    "transmission": "Transmission Weight", "coat": "Coat Weight", "sheen": "Sheen Weight",
    "specular": "Specular IOR Level", "emission_strength": "Emission Strength",
}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h):
    h = h.lstrip("#")
    return [srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)] + [1.0]


def get(preset, color=None, name=None, **overrides):
    """Return a material from `preset`; color is an sRGB hex like "#2b2d30".

    Identical specifications share a material. Conflicting explicit names are rejected.
    """
    if preset not in PRESETS:
        raise KeyError(f"unknown material preset {preset!r}; choose from {sorted(PRESETS)}")
    spec = dict(PRESETS[preset])
    if color:
        spec["color"] = color
    spec.update(overrides)
    signature = json.dumps(spec, sort_keys=True)
    name = name or ((preset if not color else f"{preset}_{spec['color'].lstrip('#')}") +
                    ("_" + hashlib.sha256(signature.encode()).hexdigest()[:10] if overrides else ""))
    mat = bpy.data.materials.get(name)
    if mat:
        if mat.get("c3d_material_spec") != signature:
            raise ValueError(f"Material {name!r} already exists with a different specification; use another name")
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rgba = hex_rgba(spec["color"])
    bsdf.inputs["Base Color"].default_value = rgba
    for key, socket in _INPUTS.items():
        if key in spec and socket in bsdf.inputs:
            bsdf.inputs[socket].default_value = spec[key]
    if spec.get("emission"):
        bsdf.inputs["Emission Color"].default_value = rgba
    if spec.get("alpha", 1.0) < 1.0 or spec.get("transmission", 0) > 0:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
        if hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = spec.get("transmission", 0) > 0
    mat.diffuse_color = (*rgba[:3], spec.get("alpha", 1.0))
    mat.metallic = spec.get("metallic", 0.0)
    mat.roughness = spec.get("roughness", 0.5)
    mat["c3d_preset"] = preset
    mat["c3d_material_spec"] = signature
    return mat
