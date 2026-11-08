"""Procedural materials for stylized-realistic environments (snow, snowpack strata, frozen
ground, rock, fur, sea ice), plus two material add-ons used by whole scenes:

- add_section_clip(): hides geometry on the camera side of a section plane (driven by an
  empty, so a cut can be animated without per-frame booleans), or shows a cut face only
  where the cut has passed.
- add_haze(): blends distant surfaces toward a sky color (aerial perspective).

All textures are procedural shader nodes; no image files.
"""

import bpy

from .materials import color


# ---------------------------------------------------------------- node graph helper

class Graph:
    def __init__(self, mat):
        self.mat = mat
        self.nt = mat.node_tree
        self.nodes, self.links = self.nt.nodes, self.nt.links

    def node(self, kind, inputs=None, **props):
        n = self.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        for k, v in (inputs or {}).items():
            self.set(n.inputs[k] if not isinstance(k, str) else _socket(n.inputs, k), v)
        return n

    def set(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, socket)
        elif isinstance(value, bpy.types.Node):
            self.links.new(value.outputs[0], socket)
        elif isinstance(value, str):
            socket.default_value = color(value)
        elif isinstance(value, (int, float)) and socket.type == "VECTOR":
            socket.default_value = (value, value, value)
        else:
            socket.default_value = value

    # Small conveniences -------------------------------------------------
    def coords(self, space="Object", obj=None):
        tc = self.node("ShaderNodeTexCoord")
        if obj is not None:
            tc.object = obj
        return tc.outputs[space]

    def math(self, op, a, b=0.0, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        return n.outputs[0]

    def vmath(self, op, a, b=(0, 0, 0), scale=None):
        n = self.node("ShaderNodeVectorMath", operation=op)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        if scale is not None:
            self.set(n.inputs["Scale"], scale)
        return n.outputs["Value"] if op in ("LENGTH", "DISTANCE", "DOT_PRODUCT") else n.outputs["Vector"]

    def scale_vec(self, vec, s):
        return self.vmath("MULTIPLY", vec, s)

    def noise(self, vec, scale=1.0, detail=4.0, roughness=0.5, distortion=0.0, out="Fac"):
        n = self.node("ShaderNodeTexNoise", {"Scale": scale, "Detail": detail, "Roughness": roughness,
                                             "Distortion": distortion})
        self.set(n.inputs["Vector"], vec)
        return n.outputs[out]

    def voronoi(self, vec, scale=1.0, feature="F1", out="Distance", randomness=1.0, dims="3D"):
        """out=None returns the node (use .outputs["Distance"] and ["Color"] from one evaluation)."""
        n = self.node("ShaderNodeTexVoronoi", {"Scale": scale, "Randomness": randomness},
                      feature=feature, voronoi_dimensions=dims)
        self.set(n.inputs["Vector"], vec)
        return n if out is None else n.outputs[out]

    def ramp(self, fac, stops, interp="LINEAR"):
        n = self.node("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = interp
        for _ in range(len(stops) - 2):
            cr.elements.new(0.5)
        for el, (pos, col) in zip(cr.elements, stops):
            el.position = pos
            el.color = color(col) if isinstance(col, str) else col
        self.set(n.inputs["Fac"], fac)
        return n.outputs["Color"]

    def map_range(self, value, a, b, c=0.0, d=1.0, clamp=True, interp="LINEAR"):
        n = self.node("ShaderNodeMapRange", {"From Min": a, "From Max": b, "To Min": c, "To Max": d},
                      clamp=clamp, interpolation_type=interp)
        self.set(n.inputs["Value"], value)
        return n.outputs["Result"]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self.set(_ident(n.inputs, "Factor_Float"), fac)
        self.set(_ident(n.inputs, "A_Color"), a)
        self.set(_ident(n.inputs, "B_Color"), b)
        return _ident(n.outputs, "Result_Color")

    def mixf(self, fac, a, b):
        n = self.node("ShaderNodeMix", data_type="FLOAT")
        self.set(_ident(n.inputs, "Factor_Float"), fac)
        self.set(_ident(n.inputs, "A_Float"), a)
        self.set(_ident(n.inputs, "B_Float"), b)
        return _ident(n.outputs, "Result_Float")

    def attr(self, name):
        return self.node("ShaderNodeAttribute", attribute_name=name).outputs["Fac"]

    def xyz(self, vec):
        n = self.node("ShaderNodeSeparateXYZ")
        self.set(n.inputs[0], vec)
        return n.outputs

    def bump(self, height, strength=0.3, distance=0.02, normal=None):
        n = self.node("ShaderNodeBump", {"Strength": strength, "Distance": distance})
        self.set(n.inputs["Height"], height)
        if normal is not None:
            self.set(n.inputs["Normal"], normal)
        return n.outputs["Normal"]

    def bsdf(self):
        return self.nodes["Principled BSDF"]

    def output_link(self):
        out = self.nodes["Material Output"]
        return out, out.inputs["Surface"].links[0].from_socket


def _socket(sockets, name):
    for s in sockets:
        if s.name == name and s.enabled:
            return s
    return sockets[name]


def _ident(sockets, identifier):
    for s in sockets:
        if s.identifier == identifier:
            return s
    raise KeyError(identifier)


def new(name):
    mat = bpy.data.materials.new(name)
    return mat, Graph(mat)


def _principled(g, base, roughness, normal=None, **extra):
    b = g.bsdf()
    g.set(b.inputs["Base Color"], base)
    g.set(b.inputs["Roughness"], roughness)
    if normal is not None:
        g.set(b.inputs["Normal"], normal)
    for k, v in extra.items():
        g.set(b.inputs[k.replace("_", " ")], v)
    return b


# ---------------------------------------------------------------- materials

def snow(name="Snow", wind_axis="X", exposed_attr="sdepth", tundra=True):
    """Wind-packed surface snow: sastrugi ripples along the wind, fine grain, faint sparkle,
    slight subsurface. Where the per-vertex attribute `exposed_attr` (snow depth, m) is
    near zero, dry tundra and gravel show through."""
    mat, g = new(name)
    co = g.coords()
    stretch = (0.7, 4.0, 4.0) if wind_axis == "X" else (4.0, 0.7, 4.0)
    sast = g.noise(g.scale_vec(co, stretch), scale=1.3, detail=3, roughness=0.55)
    grain = g.noise(co, scale=70, detail=2)
    height = g.math("ADD", g.math("MULTIPLY", sast, 0.75), g.math("MULTIPLY", grain, 0.25))
    tone = g.noise(co, scale=0.35, detail=2)
    base = g.mix(g.map_range(tone, 0.35, 0.65), "#F1F5F9", "#DCE5EE")
    spark = g.math("LESS_THAN", g.voronoi(co, scale=220), 0.07)
    rough = g.mixf(spark, 0.62, 0.18)
    normal = g.bump(height, strength=0.22, distance=0.03)
    if tundra:
        depth = g.attr(exposed_attr)
        wobble = g.math("MULTIPLY", g.math("SUBTRACT", g.noise(co, scale=2.2, detail=3), 0.5), 0.12)
        bare = g.map_range(g.math("ADD", depth, wobble), 0.07, 0.025)
        tcol = g.ramp(g.noise(co, scale=6.0, detail=4), [(0.3, "#3E3428"), (0.5, "#6E5A40"), (0.7, "#94805E")])
        base = g.mix(bare, base, tcol)
        rough = g.mixf(bare, rough, 0.92)
        gravel = g.voronoi(co, scale=18, out="Distance")
        normal = g.bump(g.mixf(bare, height, gravel), strength=0.35, distance=0.03)
    _principled(g, base, rough, normal, Specular_IOR_Level=0.45, Subsurface_Weight=0.25,
                Subsurface_Scale=0.03)
    g.bsdf().inputs["Subsurface Radius"].default_value = (0.7, 0.85, 1.0)
    return mat


def heightmap_fields(image, x_range, y_range):
    """Fields for snow_section() read from a height image (see landscape.height_image):
    R = ground z, G = snow surface z, B/A = bottom/top z of an air cavity (den) at (x, y).
    Used for a horizontal cut face that moves with the cut: alpha hides it outside the
    solid (above the surface or inside the cavity)."""
    def fields(g):
        pos = g.xyz(g.node("ShaderNodeNewGeometry").outputs["Position"])
        u = g.map_range(pos[0], x_range[0], x_range[1], clamp=False)
        v = g.map_range(pos[1], y_range[0], y_range[1], clamp=False)
        tex = g.node("ShaderNodeTexImage", image=image, interpolation="Linear", extension="EXTEND")
        g.set(tex.inputs["Vector"], g.node("ShaderNodeCombineXYZ", {"X": u, "Y": v, "Z": 0.0}))
        rgb = g.node("ShaderNodeSeparateColor")
        g.set(rgb.inputs[0], tex.outputs["Color"])
        ground, top, lo = rgb.outputs[0], rgb.outputs[1], rgb.outputs[2]
        hi = tex.outputs["Alpha"]
        z = pos[2]
        inside = g.math("LESS_THAN", z, top)
        in_cavity = g.math("MULTIPLY", g.math("GREATER_THAN", z, lo), g.math("LESS_THAN", z, hi))
        alpha = g.math("MULTIPLY", inside, g.math("SUBTRACT", 1.0, in_cavity))
        return {"hag": g.math("SUBTRACT", z, ground), "sdepth": g.math("SUBTRACT", top, ground), "alpha": alpha}
    return fields


def snow_section(name="SnowSection", entrance=None, entrance_radius=0.45, fields=None, bedrock_depth=3.8):
    """Cut face through snowpack and frozen ground. By default needs per-vertex attributes:
    hag = height above the ground surface (m, negative below ground), sdepth = snow depth (m).
    fields(graph) -> {"hag", "sdepth", optional "alpha"} can supply them instead.

    Snowpack: depth hoar at the base, wind-slab layers with thin bright wind crusts and one
    ice lens, fresh snow on top; layers follow both ground and surface. Ground: dark organic
    mat, frozen active layer, grey-brown permafrost with sparse ice lenses and stones, then
    fractured bedrock below bedrock_depth.
    entrance: (x, y, z) of a snow plug (freshly blown-in snow) shown softer and whiter.
    """
    mat, g = new(name)
    co = g.coords()
    f = fields(g) if fields else {"hag": g.attr("hag"), "sdepth": g.attr("sdepth")}
    hag = f["hag"]
    sdepth = g.math("MAXIMUM", f["sdepth"], 0.05)
    wob = g.math("MULTIPLY", g.math("SUBTRACT", g.noise(g.scale_vec(co, (0.5, 1, 1.4)), scale=0.9, detail=2), 0.5), 0.07)
    h = g.math("ADD", hag, wob)
    t = g.math("DIVIDE", h, sdepth)
    layers = g.ramp(t, [
        (0.00, "#A9BDD2"), (0.10, "#B8CADD"), (0.112, "#F4F8FB"), (0.125, "#C3D3E4"),
        (0.28, "#CBD9E8"), (0.295, "#F7FAFD"), (0.31, "#9FC3DE"), (0.325, "#D6E2EE"),
        (0.48, "#C6D5E5"), (0.495, "#F6F9FC"), (0.51, "#D9E4F0"), (0.68, "#CFDCEA"),
        (0.695, "#F6F9FC"), (0.71, "#DEE8F2"), (0.87, "#E2EAF4"), (0.91, "#F0F4F9"), (1.0, "#F4F7FA"),
    ])
    crust = g.ramp(t, [(0.0, (0, 0, 0, 1)), (0.108, (0, 0, 0, 1)), (0.112, (1, 1, 1, 1)), (0.118, (0, 0, 0, 1)),
                       (0.291, (0, 0, 0, 1)), (0.295, (1, 1, 1, 1)), (0.31, (0.5, 0.5, 0.5, 1)),
                       (0.325, (0, 0, 0, 1)), (0.491, (0, 0, 0, 1)), (0.495, (1, 1, 1, 1)), (0.501, (0, 0, 0, 1)),
                       (0.691, (0, 0, 0, 1)), (0.695, (1, 1, 1, 1)), (0.701, (0, 0, 0, 1)), (1.0, (0, 0, 0, 1))])
    # Depth hoar: coarse, darker, grainy band right on the ground.
    hoar = g.map_range(h, 0.2, 0.12)
    fine = g.noise(co, scale=90, detail=1)
    hoar_col = g.mix(g.map_range(fine, 0.35, 0.65), "#8CA3BA", "#B2C4D6")
    snow_col = g.mix(hoar, layers, hoar_col)
    snow_col = g.mix(g.math("MULTIPLY", g.math("SUBTRACT", fine, 0.5), 0.25), snow_col, "#7F93A8", "MIX")
    if entrance is not None:
        d = g.vmath("DISTANCE", co, entrance)
        plug = g.map_range(g.math("ADD", d, g.math("MULTIPLY", wob, 1.5)), entrance_radius, entrance_radius - 0.06)
        snow_col = g.mix(plug, snow_col, "#F3F6F9")
        crust = g.mix(plug, crust, (0, 0, 0, 1))

    # Frozen ground: organic mat, active layer, permafrost with stones and ice lenses, bedrock.
    depth = g.math("MULTIPLY", h, -1.0)
    D = bedrock_depth
    soil = g.ramp(g.map_range(depth, 0.0, D), [
        (0.0, "#3A2C20"), (0.08 / D, "#3F3023"), (0.10 / D, "#6B5440"), (0.40 / D, "#735B44"),
        (0.55 / D, "#6E655B"), (1.0, "#625A52")])
    mottle = g.noise(co, scale=3.0, detail=3)
    soil = g.mix(g.map_range(mottle, 0.35, 0.7, 0.0, 0.3), soil, "#3A332D", "MULTIPLY")
    lens_n = g.noise(g.scale_vec(co, (0.5, 1.0, 12.0)), scale=1.2, detail=1)
    lens = g.math("MULTIPLY", g.map_range(lens_n, 0.71, 0.73, 0.0, 0.25),
                  g.math("MULTIPLY", g.map_range(depth, 0.55, 0.8), g.map_range(depth, D - 0.4, D - 0.8)))
    soil = g.mix(lens, soil, "#A3B4C0")
    wco = g.vmath("ADD", co, g.math("MULTIPLY", mottle, 0.5))
    big = g.voronoi(wco, scale=1.3, out=None)
    small = g.voronoi(wco, scale=5.0, out=None)
    big_rnd = g.node("ShaderNodeRGBToBW", {"Color": big.outputs["Color"]}).outputs[0]
    small_rnd = g.node("ShaderNodeRGBToBW", {"Color": small.outputs["Color"]}).outputs[0]
    deep = g.math("MULTIPLY", g.map_range(depth, 0.2, 0.45), g.map_range(depth, D - 0.1, D - 0.4))
    pick_b = g.math("GREATER_THAN", big_rnd, 0.45)
    pick_s = g.math("GREATER_THAN", small_rnd, 0.55)
    stone_big = g.math("MULTIPLY", g.map_range(big.outputs["Distance"], 0.275, 0.265), pick_b)
    stone_small = g.math("MULTIPLY", g.map_range(small.outputs["Distance"], 0.215, 0.2), pick_s)
    stones = g.math("MULTIPLY", g.math("MAXIMUM", stone_big, stone_small), deep)
    rim = g.math("MULTIPLY", g.math("MULTIPLY", g.map_range(big.outputs["Distance"], 0.29, 0.272), pick_b), deep)
    soil = g.mix(g.math("MULTIPLY", rim, 0.3), soil, "#1E1B19")
    stone_shade = g.math("ADD", g.math("MULTIPLY", g.map_range(big.outputs["Distance"], 0.0, 0.27), 0.6),
                         g.math("MULTIPLY", big_rnd, 0.4))
    stone_col = g.ramp(stone_shade, [(0.1, "#A39C91"), (0.55, "#7C766E"), (0.95, "#55504A")])
    soil = g.mix(stones, soil, stone_col)
    # Bedrock: grey rock with faint bedding and dark joints.
    bedding = g.noise(g.scale_vec(co, (0.25, 1.0, 3.0)), scale=1.4, detail=2)
    bed = g.map_range(g.math("ADD", depth, g.math("MULTIPLY", g.math("SUBTRACT", mottle, 0.5), 0.6)), D - 0.05, D + 0.05)
    bed_col = g.ramp(bedding, [(0.3, "#5A5856"), (0.5, "#6A6764"), (0.7, "#77736F")])
    soil = g.mix(bed, soil, bed_col)

    ground = g.math("LESS_THAN", h, 0.0)
    base = g.mix(ground, snow_col, soil)
    # Gently darker with depth, so the eye stays on the snowpack and the den.
    base = g.mix(g.map_range(depth, 0.5, 6.0, 0.0, 0.25), base, "#000000")
    crust_h = g.node("ShaderNodeRGBToBW", {"Color": crust}).outputs[0]
    rough = g.mixf(ground, g.mixf(crust_h, 0.8, 0.45), g.mixf(stones, 0.95, 0.65))
    height = g.math("ADD", g.math("MULTIPLY", crust_h, 0.4), g.math("MULTIPLY", fine, 0.25))
    height = g.mixf(ground, height, g.math("ADD", g.math("MULTIPLY", stones, 0.8), g.math("MULTIPLY", mottle, 0.3)))
    normal = g.bump(height, strength=0.35, distance=0.02)
    _principled(g, base, rough, normal, Specular_IOR_Level=0.3)
    if "alpha" in f:
        transparent = g.node("ShaderNodeBsdfTransparent")

        def build(src):
            mix = g.node("ShaderNodeMixShader")
            g.set(mix.inputs[0], f["alpha"])
            g.links.new(transparent.outputs[0], mix.inputs[1])
            g.links.new(src, mix.inputs[2])
            return mix.outputs[0]

        _wrap_output(g, build)
        mat.surface_render_method = "DITHERED"
        mat.use_transparent_shadow = True
    return mat


def den_wall(name="DenWall", entrance=None, entrance_radius=0.45):
    """Inside surface of a dug snow cavity: scooped dig marks, slight icy glaze."""
    mat, g = new(name)
    co = g.coords()
    scoops = g.voronoi(co, scale=4.5, feature="SMOOTH_F1", out="Distance")
    fine = g.noise(co, scale=45, detail=2)
    height = g.math("ADD", g.math("MULTIPLY", scoops, 0.8), g.math("MULTIPLY", fine, 0.2))
    base = g.mix(g.map_range(scoops, 0.2, 0.6), "#D5DFE9", "#BCCADA")
    rough = g.mixf(g.map_range(g.noise(co, scale=3.0), 0.4, 0.6), 0.32, 0.55)
    if entrance is not None:
        d = g.vmath("DISTANCE", co, entrance)
        plug = g.map_range(d, entrance_radius, entrance_radius - 0.1)
        base = g.mix(plug, base, "#F4F7FA")
        rough = g.mixf(plug, rough, 0.75)
    _principled(g, base, rough, g.bump(height, strength=0.35, distance=0.04), Specular_IOR_Level=0.5,
                Subsurface_Weight=0.2, Subsurface_Scale=0.03)
    return mat


def rock(name="Rock", dark="#2B2A29", mid="#46423F", light="#625C55", snow_cap=True):
    """Weathered dark rock: mottled color, cracks and pitting, optional snow on upward faces."""
    mat, g = new(name)
    co = g.coords()
    n1 = g.noise(co, scale=2.5, detail=8, roughness=0.6)
    cracks = g.voronoi(g.vmath("ADD", co, g.math("MULTIPLY", n1, 0.3)), scale=3.5, feature="DISTANCE_TO_EDGE")
    base = g.ramp(n1, [(0.35, dark), (0.5, mid), (0.65, light)])
    crack_mask = g.map_range(cracks, 0.0, 0.04, 1.0, 0.0)
    base = g.mix(g.math("MULTIPLY", crack_mask, 0.7), base, "#141312")
    height = g.math("SUBTRACT", g.math("MULTIPLY", n1, 1.0), g.math("MULTIPLY", crack_mask, 0.5))
    normal = g.bump(height, strength=0.6, distance=0.05)
    rough = g.mixf(crack_mask, 0.82, 0.95)
    if snow_cap:
        nz = g.xyz(g.node("ShaderNodeNewGeometry").outputs["Normal"])[2]
        cap = g.map_range(g.math("ADD", nz, g.math("MULTIPLY", g.math("SUBTRACT", g.noise(co, scale=4, detail=3), 0.5), 0.6)),
                          0.62, 0.72)
        base = g.mix(cap, base, "#E6ECF2")
        rough = g.mixf(cap, rough, 0.6)
        normal = g.bump(g.mixf(cap, height, g.noise(co, scale=40)), strength=0.5, distance=0.05)
    _principled(g, base, rough, normal, Specular_IOR_Level=0.35)
    return mat


def grass(name="DrySedge"):
    mat, g = new(name)
    co = g.coords("Generated")
    base = g.ramp(g.noise(g.coords(), scale=8.0), [(0.3, "#5C4630"), (0.55, "#9C8256"), (0.75, "#BCA373")])
    tip = g.xyz(g.coords())[2]
    base = g.mix(g.map_range(tip, 0.0, 0.08, 0.6, 0.0), base, "#3B2E22")
    _principled(g, base, 0.8, Specular_IOR_Level=0.25, Subsurface_Weight=0.1)
    mat.use_backface_culling = False
    del co
    return mat


def fur(name="Fur", col="#EEE4CE", shade="#D8C7A4"):
    """Short dense fur: yellowish-cream variation, clumpy bump, sheen, slight subsurface."""
    mat, g = new(name)
    co = g.coords()
    tone = g.noise(co, scale=2.0, detail=3)
    base = g.mix(g.map_range(tone, 0.4, 0.7), col, shade)
    clumps = g.voronoi(g.scale_vec(co, (1, 1, 2.0)), scale=14, feature="SMOOTH_F1", out="Distance")
    strands = g.noise(g.scale_vec(co, (1, 1, 5)), scale=60, detail=2)
    height = g.math("ADD", g.math("MULTIPLY", clumps, 0.7), g.math("MULTIPLY", strands, 0.3))
    _principled(g, base, 0.78, g.bump(height, strength=0.18, distance=0.01), Sheen_Weight=0.6,
                Sheen_Roughness=0.5, Subsurface_Weight=0.2, Subsurface_Scale=0.02, Specular_IOR_Level=0.3)
    g.bsdf().inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.35)
    return mat


def glossy_dark(name="Dark"):
    mat, g = new(name)
    _principled(g, "#121214", 0.28, Specular_IOR_Level=0.6)
    return mat


def sea_ice(name="SeaIce"):
    """Flat sea ice seen from afar: snow patches, grey-blue refrozen leads and cracks."""
    mat, g = new(name)
    co = g.coords("Object")
    patches = g.noise(co, scale=0.025, detail=4)
    leads = g.voronoi(g.vmath("ADD", co, g.math("MULTIPLY", patches, 20)), scale=0.012, feature="DISTANCE_TO_EDGE")
    base = g.mix(g.map_range(patches, 0.45, 0.6), "#C9D6E1", "#E8EEF4")
    lead_mask = g.map_range(leads, 0.0, 0.02, 1.0, 0.0)
    base = g.mix(lead_mask, base, "#7C93A8")
    rough = g.mixf(lead_mask, 0.55, 0.15)
    _principled(g, base, rough, g.bump(g.noise(co, scale=0.4, detail=3), 0.2, 0.2), Specular_IOR_Level=0.5)
    return mat


def ice_blocks(name="IceBlocks"):
    mat, g = new(name)
    co = g.coords()
    nz = g.xyz(g.node("ShaderNodeNewGeometry").outputs["Normal"])[2]
    side = g.map_range(nz, 0.75, 0.3)
    base = g.mix(side, "#E9F0F5", "#93BBD3")
    base = g.mix(g.map_range(g.noise(co, scale=1.5), 0.4, 0.7, 0.0, 0.3), base, "#6F9FBF")
    _principled(g, base, 0.3, g.bump(g.noise(co, scale=3, detail=4), 0.3, 0.1), Specular_IOR_Level=0.6)
    return mat


def mountain(name="Mountain"):
    mat, g = new(name)
    co = g.coords()
    nz = g.xyz(g.node("ShaderNodeNewGeometry").outputs["Normal"])[2]
    n = g.noise(co, scale=0.03, detail=6)
    rocky = g.map_range(g.math("ADD", nz, g.math("MULTIPLY", g.math("SUBTRACT", n, 0.5), 0.5)), 0.72, 0.6)
    base = g.mix(rocky, "#DCE4EE", "#3C3F47")
    _principled(g, base, 0.7, g.bump(n, 0.4, 2.0), Specular_IOR_Level=0.3)
    return mat


# ---------------------------------------------------------------- add-ons

def _wrap_output(g, build):
    """Replace the material output's surface shader with build(old_shader_socket)."""
    out, src = g.output_link()
    g.links.new(build(src), out.inputs["Surface"])


def add_haze(mat, col, start=12.0, distance=140.0, max_amount=0.92):
    """Fade the surface toward `col` with camera distance (aerial perspective)."""
    g = Graph(mat)
    d = g.node("ShaderNodeCameraData").outputs["View Distance"]
    x = g.math("DIVIDE", g.math("MAXIMUM", g.math("SUBTRACT", d, start), 0.0), distance)
    fac = g.math("MULTIPLY", g.math("SUBTRACT", 1.0, g.math("EXPONENT", g.math("MULTIPLY", x, -1.0))), max_amount)
    emit = g.node("ShaderNodeEmission", {"Color": col, "Strength": 1.0})

    def build(src):
        mix = g.node("ShaderNodeMixShader")
        g.set(mix.inputs[0], fac)
        g.links.new(src, mix.inputs[1])
        g.links.new(emit.outputs[0], mix.inputs[2])
        return mix.outputs[0]

    _wrap_output(g, build)
    return emit.inputs["Color"]  # animate to follow the sky (e.g. for seasons)


def _alpha_wrap(mat, g, alpha, transparent_shadow=None):
    """Multiply the material's visibility by alpha (0 = hidden), as dithered transparency."""
    transparent = g.node("ShaderNodeBsdfTransparent")

    def build(src):
        mix = g.node("ShaderNodeMixShader")
        g.set(mix.inputs[0], alpha)
        g.links.new(transparent.outputs[0], mix.inputs[1])
        g.links.new(src, mix.inputs[2])
        return mix.outputs[0]

    _wrap_output(g, build)
    mat.surface_render_method = "DITHERED"
    if transparent_shadow is not None:
        mat.use_transparent_shadow = transparent_shadow
    return mat


def add_hole(mat, ctl, shape="sphere", transparent_shadow=True):
    """Cut an animatable hole into a surface, controlled by empty `ctl` (scale it to grow).

    shape="sphere": hidden inside ctl's unit sphere.
    shape="shaft": hidden inside ctl's unit vertical cylinder from local z = 0 to 1
    (scale X/Y = radius, Z = height; grow Z from ~0 to dig upward).
    """
    g = Graph(mat)
    co = g.coords("Object", ctl)
    if shape == "sphere":
        inside = g.math("LESS_THAN", g.vmath("LENGTH", co), 1.0)
    else:
        x, y, z = g.xyz(co)
        r = g.vmath("LENGTH", g.node("ShaderNodeCombineXYZ", {"X": x, "Y": y, "Z": 0.0}))
        inside = g.math("MULTIPLY", g.math("LESS_THAN", r, 1.0),
                        g.math("MULTIPLY", g.math("GREATER_THAN", z, 0.0), g.math("LESS_THAN", z, 1.0)))
    return _alpha_wrap(mat, g, g.math("SUBTRACT", 1.0, inside), transparent_shadow=transparent_shadow)


def add_solid_only(mat, image, x_range, y_range):
    """Show the surface only inside solid snow/ground (below the snow surface and outside
    the den cavity), read from a height image. For hole walls (entrance, air shaft)."""
    g = Graph(mat)
    return _alpha_wrap(mat, g, heightmap_fields(image, x_range, y_range)(g)["alpha"])


def add_section_clip(mat, ctl, mode="keep_back", glint_color="#BFE3FF"):
    """Clip a material against a section controller empty `ctl`.

    The cut plane is ctl's local XZ plane (camera side = local -Y) and the cut is open
    above ctl's local Z = 0. Animate ctl's Z location to sweep the cut.
    mode="keep_back": hide the part in front of the plane above the cut's lower edge.
    mode="face": show only where the cut has passed (for the static cut-face mesh), with a
    thin glowing line at the moving edge. Returns the glint strength socket (animate it)
    for mode="face", else None.
    """
    g = Graph(mat)
    local = g.xyz(g.coords("Object", ctl))
    above = g.math("GREATER_THAN", local[2], 0.0)
    glint = None
    if mode == "keep_back":
        front = g.math("LESS_THAN", local[1], 0.0)
        alpha = g.math("SUBTRACT", 1.0, g.math("MULTIPLY", front, above))
    else:
        alpha = above
        band = g.map_range(local[2], 0.0, 0.05, 1.0, 0.0)
        strength = g.node("ShaderNodeValue", label="GlintStrength")
        strength.outputs[0].default_value = 0.0
        glint = strength.outputs[0]
        emit = g.node("ShaderNodeEmission", {"Color": glint_color})
        g.set(emit.inputs["Strength"], g.math("MULTIPLY", band, glint))
    transparent = g.node("ShaderNodeBsdfTransparent")

    def build(src):
        s = src
        if mode == "face":
            add = g.node("ShaderNodeAddShader")
            g.links.new(src, add.inputs[0])
            g.links.new(emit.outputs[0], add.inputs[1])
            s = add.outputs[0]
        mix = g.node("ShaderNodeMixShader")
        g.set(mix.inputs[0], alpha)
        g.links.new(transparent.outputs[0], mix.inputs[1])
        g.links.new(s, mix.inputs[2])
        return mix.outputs[0]

    _wrap_output(g, build)
    mat.surface_render_method = "DITHERED"
    mat.use_transparent_shadow = True
    return glint
