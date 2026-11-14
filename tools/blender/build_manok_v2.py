"""
build_manok_v2.py  -  Sabong manok (fighting rooster), production rig v2.

Run headless from the repo root (Blender 5.1+):
  blender --background --python tools/blender/build_manok_v2.py -- --stage A
  blender --background --python tools/blender/build_manok_v2.py -- --stage A --ref prototype/manok.glb

Stage A: one connected low-poly toon mesh, the original 39-bone skeleton, distance-based
         smooth skinning (max 4 influences), Talisayin materials, Tari on tari_socket_L.
         Saves output/manok_v2.blend and preview renders (T-pose + idle).
Later stages (B: animation clips, C: glTF export + breeds) build on the same functions.
"""
import bpy, bmesh, math, os, sys, json, base64
from mathutils import Vector, Matrix, Quaternion
from mathutils.kdtree import KDTree

# ----------------------------------------------------------------------------- paths / args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = arg("--out", os.path.join(HERE, "output"))
STAGE = arg("--stage", "A").upper()
REF_GLB = arg("--ref")
os.makedirs(OUT, exist_ok=True)

TARGET_TRIS = 5600          # hard limit 6000, eyes + tari included
VOXEL = 0.0028              # remesh voxel size (m)
MB_RES = 0.0028             # metaball resolution (m)
MB_K = 0.566                # metaball surface half-extent per unit size (radius 1, stiffness 2)

# ----------------------------------------------------------------------------- skeleton (unchanged from v1)
# name, parent, head, tail, roll, deform
BONES = [
    ("root", None, (0.0, 0.0, 0.0), (0.0, 0.0, 0.3015), True),
    ("pelvis", "root", (0.0, 0.03, 0.3), (0.0, -0.0009, 0.3186), True),
    ("spine_01", "pelvis", (0.0, -0.02, 0.33), (0.0, -0.07, 0.36), True),
    ("chest", "spine_01", (0.0, -0.07, 0.36), (0.0, -0.1072, 0.4158), True),
    ("neck_01", "chest", (0.0, -0.11, 0.42), (0.0, -0.13, 0.47), True),
    ("neck_02", "neck_01", (0.0, -0.13, 0.47), (0.0, -0.14, 0.52), True),
    ("neck_03", "neck_02", (0.0, -0.14, 0.52), (0.0, -0.1444, 0.5645), True),
    ("hackle_C", "neck_03", (0.0, -0.12, 0.56), (0.0, -0.0952, 0.5228), True),
    ("hackle_L", "neck_03", (0.03, -0.12, 0.55), (0.0436, -0.0974, 0.5139), True),
    ("hackle_R", "neck_03", (-0.03, -0.12, 0.55), (-0.0436, -0.0974, 0.5139), True),
    ("neck_04", "neck_03", (0.0, -0.145, 0.57), (0.0, -0.15, 0.61), True),
    ("head", "neck_04", (0.0, -0.15, 0.61), (0.0, -0.1967, 0.6256), True),
    ("comb", "head", (0.0, -0.17, 0.655), (0.0, -0.17, 0.7042), True),
    ("wattle_L", "head", (0.012, -0.205, 0.605), (0.012, -0.205, 0.5558), True),
    ("wattle_R", "head", (-0.012, -0.205, 0.605), (-0.012, -0.205, 0.5558), True),
    ("shoulder_L", "chest", (0.06, -0.07, 0.39), (0.09, -0.05, 0.4), True),
    ("wing_upper_L", "shoulder_L", (0.09, -0.05, 0.4), (0.1, 0.02, 0.38), True),
    ("wing_fore_L", "wing_upper_L", (0.1, 0.02, 0.38), (0.1, 0.09, 0.36), True),
    ("wing_hand_L", "wing_fore_L", (0.1, 0.09, 0.36), (0.0905, 0.1563, 0.3316), True),
    ("shoulder_R", "chest", (-0.06, -0.07, 0.39), (-0.09, -0.05, 0.4), True),
    ("wing_upper_R", "shoulder_R", (-0.09, -0.05, 0.4), (-0.1, 0.02, 0.38), True),
    ("wing_fore_R", "wing_upper_R", (-0.1, 0.02, 0.38), (-0.1, 0.09, 0.36), True),
    ("wing_hand_R", "wing_fore_R", (-0.1, 0.09, 0.36), (-0.0905, 0.1563, 0.3316), True),
    ("tail_base", "pelvis", (0.0, 0.05, 0.33), (0.0, 0.1, 0.38), True),
    ("tail_01", "tail_base", (0.0, 0.1, 0.38), (0.0, 0.14, 0.45), True),
    ("tail_02", "tail_01", (0.0, 0.14, 0.45), (0.0, 0.17, 0.53), True),
    ("tail_03", "tail_02", (0.0, 0.17, 0.53), (0.0, 0.2522, 0.5535), True),
    ("thigh_L", "pelvis", (0.05, 0.02, 0.29), (0.06, -0.04, 0.22), True),
    ("shank_L", "thigh_L", (0.06, -0.04, 0.22), (0.06, 0.01, 0.13), True),
    ("tarsus_L", "shank_L", (0.06, 0.01, 0.13), (0.06, 0.0001, 0.0607), True),
    ("tari_socket_L", "tarsus_L", (0.06, 0.012, 0.06), (0.06, 0.082, 0.06), False),
    ("toe_back_L", "tarsus_L", (0.06, -0.0, 0.025), (0.06, 0.0644, -0.0024), True),
    ("toe_L", "tarsus_L", (0.06, -0.005, 0.025), (0.06, -0.0732, 0.0093), True),
    ("thigh_R", "pelvis", (-0.05, 0.02, 0.29), (-0.06, -0.04, 0.22), True),
    ("shank_R", "thigh_R", (-0.06, -0.04, 0.22), (-0.06, 0.01, 0.13), True),
    ("tarsus_R", "shank_R", (-0.06, 0.01, 0.13), (-0.06, 0.0001, 0.0607), True),
    ("tari_socket_R", "tarsus_R", (-0.06, 0.012, 0.06), (-0.06, 0.082, 0.06), False),
    ("toe_back_R", "tarsus_R", (-0.06, -0.0, 0.025), (-0.06, 0.0644, -0.0024), True),
    ("toe_R", "tarsus_R", (-0.06, -0.005, 0.025), (-0.06, -0.0732, 0.0093), True),
]
BONE_SEG = {n: (Vector(h), Vector(t)) for n, _, h, t, _ in BONES}

# ----------------------------------------------------------------------------- materials (names are used by game.js tint())
MAT_ORDER = ["Body_DeepRed", "Hackle_Gold", "Beak_Horn", "Eye_Orange", "Eye_Black",
             "Comb_Red", "WingTip_Green", "Tail_GreenBlack", "Leg_Yellow"]
BREEDS = {
    "Talisayin": {"Body_DeepRed": (0.32, 0.05, 0.03), "Hackle_Gold": (0.85, 0.42, 0.06),
                  "Beak_Horn": (0.8, 0.6, 0.25), "Eye_Orange": (0.95, 0.45, 0.05),
                  "Eye_Black": (0.01, 0.01, 0.01), "Comb_Red": (0.75, 0.04, 0.03),
                  "WingTip_Green": (0.03, 0.12, 0.07), "Tail_GreenBlack": (0.02, 0.06, 0.04),
                  "Leg_Yellow": (0.85, 0.62, 0.15)},
}
TARI_MATS = {"Tari_Wrap": (0.6, 0.05, 0.05), "Tari_Steel": (0.8, 0.82, 0.85)}

def make_material(name, rgb, rough=0.75, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*rgb, 1)
    m.roughness = rough
    m.metallic = metal
    return m

# ----------------------------------------------------------------------------- part labels: material + allowed bones (bias)
def S(side): return 1.0 if side == "L" else -1.0
LABELS = {
    "body":    ("Body_DeepRed", {"pelvis": 1, "spine_01": 1, "chest": 0.8, "tail_base": 0.5,
                                 "thigh_L": 0.25, "thigh_R": 0.25}),
    "breast":  ("Body_DeepRed", {"chest": 1, "spine_01": 0.8, "neck_01": 0.5, "shoulder_L": 0.3, "shoulder_R": 0.3}),
    "neck":    ("Hackle_Gold", {"chest": 0.5, "neck_01": 1, "neck_02": 1, "neck_03": 1, "neck_04": 1, "head": 0.6}),
    "head":    ("Hackle_Gold", {"head": 1, "neck_04": 0.3}),
    "face":    ("Comb_Red", {"head": 1}),
    "beak":    ("Beak_Horn", {"head": 1}),
    "comb":    ("Comb_Red", {"comb": 1, "head": 0.15}),
    "tail":    ("Tail_GreenBlack", {"tail_base": 1, "tail_01": 1, "tail_02": 1, "tail_03": 1}),
    "saddle":  ("Hackle_Gold", {"tail_base": 1, "pelvis": 0.7, "tail_01": 0.5}),
}
for sd in ("L", "R"):
    LABELS.update({
        f"hackle_{sd}": ("Hackle_Gold", {f"hackle_{sd}": 1.6, "hackle_C": 0.5, "neck_02": 0.4, "neck_03": 0.6}),
        f"wattle_{sd}": ("Comb_Red", {f"wattle_{sd}": 1, "head": 0.1}),
        f"wingcov_{sd}": ("Body_DeepRed", {f"shoulder_{sd}": 1, f"wing_upper_{sd}": 1, f"wing_fore_{sd}": 1}),
        f"wingtip_{sd}": ("WingTip_Green", {f"wing_fore_{sd}": 0.7, f"wing_hand_{sd}": 1}),
        f"thigh_{sd}": ("Body_DeepRed", {f"thigh_{sd}": 1, "pelvis": 0.35, f"shank_{sd}": 0.4}),
        f"drum_{sd}": ("Body_DeepRed", {f"shank_{sd}": 1, f"thigh_{sd}": 0.5}),
        f"leg_{sd}": ("Leg_Yellow", {f"shank_{sd}": 0.6, f"tarsus_{sd}": 1}),
        f"spur_{sd}": ("Leg_Yellow", {f"tarsus_{sd}": 1}),
        f"toe_{sd}": ("Leg_Yellow", {f"toe_{sd}": 1, f"tarsus_{sd}": 0.25}),
        f"toeb_{sd}": ("Leg_Yellow", {f"toe_back_{sd}": 1, f"tarsus_{sd}": 0.25}),
    })
LABELS["hackle_C"] = ("Hackle_Gold", {"hackle_C": 1.6, "hackle_L": 0.4, "hackle_R": 0.4, "neck_02": 0.4, "neck_03": 0.6})

# ----------------------------------------------------------------------------- metaball shape kit
FAMILIES = {}        # family name -> metaball object
SAMPLES = []         # (point, label) on the intended ellipsoid surfaces

def fib_sphere(n):
    pts = []
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        pts.append(Vector((math.cos(g * i) * r, math.sin(g * i) * r, z)))
    return pts
FIB = fib_sphere(48)

def family(name):
    if name not in FAMILIES:
        mb = bpy.data.metaballs.new("MB_" + name)
        mb.resolution = mb.render_resolution = MB_RES
        mb.threshold = 0.6
        o = bpy.data.objects.new("MB_" + name, mb)
        bpy.context.scene.collection.objects.link(o)
        FAMILIES[name] = o
    return FAMILIES[name].data

def ell(fam, center, half, label, rot=None):
    """Ellipsoid with true half-extents `half` (m) at `center`, optional Quaternion `rot`."""
    mb = family(fam)
    e = mb.elements.new()
    e.type = 'ELLIPSOID'
    e.co = center
    e.radius = 1.0
    e.size_x, e.size_y, e.size_z = (h / MB_K for h in half)
    q = rot or Quaternion()
    e.rotation = q
    c = Vector(center)
    for p in FIB:
        SAMPLES.append((c + q @ Vector((p.x * half[0], p.y * half[1], p.z * half[2])), label))

def basis_along(direction, thin_axis=Vector((1, 0, 0))):
    """Quaternion whose local Z points along `direction` and local X stays close to `thin_axis`."""
    z = Vector(direction).normalized()
    x = (thin_axis - z * thin_axis.dot(z))
    if x.length < 1e-6:
        x = Vector((0, 1, 0)) - z * z.y
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed().to_quaternion()

def tube(fam, pts, radii, label, flat=None, step=0.6):
    """Chain of ellipsoids through `pts` with radius per point; `flat` = (thin_axis, thin_ratio)."""
    for (a, ra), (b, rb) in zip(zip(pts, radii), zip(pts[1:], radii[1:])):
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        n = max(1, int(L / (min(ra, rb) * step)))
        for i in range(n + 1):
            t = i / n
            p = a.lerp(b, t)
            r = ra + (rb - ra) * t
            if flat:
                q = basis_along(b - a, flat[0])
                ell(fam, p, (r * flat[1], r, r * 1.15), label, q)
            else:
                ell(fam, p, (r, r, r), label)

def bezier(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = map(Vector, (p0, p1, p2, p3))
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append(p0 * u**3 + p1 * 3 * u * u * t + p2 * 3 * u * t * t + p3 * t**3)
    return out

def rotx(deg): return Quaternion((1, 0, 0), math.radians(deg))

# ----------------------------------------------------------------------------- the rooster
def build_shapes():
    # torso: upright, puffed chest, back sloping up into the tail
    ell("Body", (0, 0.0, 0.33), (0.072, 0.118, 0.078), "body", rotx(-22))
    ell("Body", (0, -0.075, 0.375), (0.07, 0.068, 0.082), "breast")
    ell("Body", (0, -0.035, 0.335), (0.065, 0.07, 0.07), "breast")
    ell("Body", (0, 0.07, 0.355), (0.055, 0.065, 0.05), "saddle", rotx(-15))
    ell("Body", (0, 0.025, 0.285), (0.05, 0.07, 0.04), "body")
    # neck (long, slim, slight S) + head
    neck = [(0, -0.1, 0.415), (0, -0.125, 0.46), (0, -0.138, 0.51), (0, -0.145, 0.56), (0, -0.152, 0.6)]
    tube("Body", neck, [0.04, 0.032, 0.027, 0.024, 0.024], "neck")
    ell("Body", (0, -0.168, 0.624), (0.026, 0.038, 0.028), "head", rotx(8))
    for sd in ("L", "R"):
        s = S(sd)
        ell("Body", (s * 0.016, -0.176, 0.617), (0.012, 0.022, 0.015), "face")
    # beak
    tube("Beak", [(0, -0.198, 0.621), (0, -0.218, 0.614), (0, -0.234, 0.606)], [0.011, 0.007, 0.0028], "beak")
    # single comb, low and serrated (game-fowl trimmed look)
    tube("Comb", [(0, -0.198, 0.648), (0, -0.14, 0.651)], [0.009, 0.007], "comb", flat=(Vector((1, 0, 0)), 0.55))
    for i, (y, h) in enumerate([(-0.192, 0.017), (-0.177, 0.024), (-0.162, 0.025), (-0.148, 0.019)]):
        ell("Comb", (0, y, 0.66 + h * 0.6), (0.0045, 0.0065, h * 0.75), "comb", rotx(10 + i * 8))
    # hackle mane: pointed feathers fanning down over the shoulders
    for ring, (zc, n, L) in enumerate([(0.565, 9, 0.052), (0.515, 11, 0.058), (0.465, 11, 0.05)]):
        yc = -0.142 + ring * 0.012
        for i in range(n):
            th = math.radians(-120 + 240 * i / (n - 1))
            radial = Vector((math.sin(th), math.cos(th), 0))
            d = (radial * 0.55 + Vector((0, 0.15, -1))).normalized()
            base = Vector((0, yc, zc)) + radial * 0.022
            lab = "hackle_C" if abs(th) < math.radians(35) else ("hackle_L" if th > 0 else "hackle_R")
            q = basis_along(d, radial)
            ell("Hackle", base + d * L * 0.5, (0.0045, 0.012, L * 0.5), lab, q)
            ell("Hackle", base + d * L * 0.85, (0.003, 0.006, L * 0.2), lab, q)
    # wattles
    for sd in ("L", "R"):
        s = S(sd)
        ell("Wattle" + sd, (s * 0.009, -0.197, 0.592), (0.0075, 0.009, 0.019), f"wattle_{sd}")
    # wings: blades lying against the body, joined only at the shoulder
    for sd in ("L", "R"):
        s = S(sd)
        fam = "Wing" + sd
        ell(fam, (s * 0.072, -0.06, 0.392), (0.022, 0.024, 0.026), f"wingcov_{sd}")
        cov = [(s * 0.088, -0.05, 0.395), (s * 0.097, 0.0, 0.385), (s * 0.1, 0.05, 0.368)]
        tube(fam, cov, [0.034, 0.038, 0.03], f"wingcov_{sd}", flat=(Vector((1, 0, 0)), 0.22))
        tip = [(s * 0.1, 0.06, 0.36), (s * 0.097, 0.11, 0.345), (s * 0.09, 0.165, 0.325), (s * 0.084, 0.2, 0.31)]
        tube(fam, tip, [0.028, 0.024, 0.016, 0.006], f"wingtip_{sd}", flat=(Vector((1, 0, 0)), 0.25))
    # legs: feathered thighs, scaly yellow shanks, spurs, four toes
    for sd in ("L", "R"):
        s = S(sd)
        ell("Body", (s * 0.052, 0.0, 0.262), (0.032, 0.048, 0.045), f"thigh_{sd}", rotx(25))
        tube("Body", [(s * 0.058, -0.03, 0.225), (s * 0.06, -0.012, 0.18)], [0.024, 0.015], f"drum_{sd}")
        fam = "Leg" + sd
        tube(fam, [(s * 0.06, -0.015, 0.19), (s * 0.06, 0.01, 0.13), (s * 0.06, 0.004, 0.07), (s * 0.06, 0.0, 0.02)],
             [0.0105, 0.0095, 0.0085, 0.009], f"leg_{sd}")
        tube(fam, [(s * 0.06, 0.008, 0.088), (s * 0.058, 0.026, 0.079), (s * 0.056, 0.04, 0.083)],
             [0.0048, 0.0032, 0.0012], f"spur_{sd}")
        ell(fam, (s * 0.06, -0.002, 0.014), (0.012, 0.012, 0.009), f"leg_{sd}")
        for ang in (-28, 0, 28):
            a = math.radians(ang) * s
            tip = Vector((s * 0.06 + math.sin(a) * 0.068, -0.004 - math.cos(a) * 0.068, 0.0062))
            tube(fam, [(s * 0.06, -0.006, 0.0095), tip], [0.0068, 0.0045], f"toe_{sd}")
        tube(fam, [(s * 0.06, 0.004, 0.0095), (s * 0.06, 0.04, 0.006)], [0.006, 0.0042], f"toeb_{sd}")
    # tail: dramatic sickles arching up and over, each its own blade
    sickles = [  # x0, spread, apex height, end y, end z, width
        (0.0, 0.0, 0.69, 0.43, 0.40, 0.016),
        (0.008, 0.012, 0.665, 0.41, 0.37, 0.015),
        (-0.008, -0.012, 0.665, 0.41, 0.37, 0.015),
        (0.016, 0.028, 0.62, 0.37, 0.33, 0.013),
        (-0.016, -0.028, 0.62, 0.37, 0.33, 0.013),
        (0.022, 0.04, 0.56, 0.32, 0.3, 0.012),
        (-0.022, -0.04, 0.56, 0.32, 0.3, 0.012),
    ]
    for i, (x0, sp, apex, ey, ez, w) in enumerate(sickles):
        pts = bezier((x0, 0.075, 0.36), (x0 + sp * 0.3, 0.13, apex), (x0 + sp * 0.8, ey - 0.02, apex + 0.03),
                     (x0 + sp, ey, ez), 10)
        rad = [w * (1 - 0.6 * (k / 10) ** 1.3) for k in range(11)]
        tube(f"Tail{i}", pts, rad, "tail", flat=(Vector((1, 0, 0)), 0.42))
    # tail coverts / saddle hackles draping over the back
    for sd in (1, -1):
        for j, (dy, dz) in enumerate([(0.0, 0.0), (0.02, -0.03)]):
            pts = bezier((sd * 0.03, 0.05 + dy, 0.385 + dz), (sd * 0.045, 0.12 + dy, 0.4 + dz),
                         (sd * 0.055, 0.17 + dy, 0.36 + dz), (sd * 0.058, 0.2 + dy, 0.31 + dz), 6)
            tube(f"Cov{sd}{j}", pts, [0.016, 0.015, 0.013, 0.011, 0.009, 0.006, 0.003], "saddle",
                 flat=(Vector((sd, 0, 0.4)).normalized(), 0.3))

# ----------------------------------------------------------------------------- mesh pipeline
def mesh_from_eval(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    return bpy.data.meshes.new_from_object(obj.evaluated_get(dg))

def tri_count(me):
    me.calc_loop_triangles()
    return len(me.loop_triangles)

def build_body_mesh():
    bm = bmesh.new()
    for o in FAMILIES.values():
        me = mesh_from_eval(o)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for o in list(FAMILIES.values()):
        bpy.data.objects.remove(o)
    raw = bpy.data.meshes.new("raw")
    bm.to_mesh(raw); bm.free()
    obj = bpy.data.objects.new("tmp_union", raw)
    bpy.context.scene.collection.objects.link(obj)
    rm = obj.modifiers.new("Remesh", 'REMESH')
    rm.mode = 'VOXEL'; rm.voxel_size = VOXEL; rm.adaptivity = 0.0
    me = mesh_from_eval(obj)
    obj.modifiers.clear(); obj.data = me
    hi = tri_count(me)
    target = TARGET_TRIS - 2 * 2 * 96 - 120      # eyes + tari budget
    ratio = target / hi
    for _ in range(3):
        dec = obj.modifiers.new("Dec", 'DECIMATE')
        dec.decimate_type = 'COLLAPSE'; dec.ratio = ratio; dec.use_collapse_triangulate = True
        lo = mesh_from_eval(obj)
        obj.modifiers.clear()
        n = tri_count(lo)
        if n <= target or ratio < 1e-3:
            break
        bpy.data.meshes.remove(lo)
        ratio *= target / n * 0.98
    # drop tiny loose slivers the collapse can leave behind
    bm = bmesh.new(); bm.from_mesh(lo)
    seen, kill = set(), []
    for f in bm.faces:
        if f in seen: continue
        isl, stack = [], [f]
        while stack:
            g = stack.pop()
            if g in seen: continue
            seen.add(g); isl.append(g)
            for e in g.edges:
                stack.extend(x for x in e.link_faces if x not in seen)
        if len(isl) < 50:
            kill.extend(isl)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(lo); bm.free()
    obj.data = lo
    print(f"MESH remesh {hi} tris -> decimated {tri_count(lo)} tris")
    return obj

def add_eyes(bm, mats):
    for sd in ("L", "R"):
        s = S(sd)
        for mat, c, r in (("Eye_Orange", (s * 0.0225, -0.181, 0.63), 0.0068), ("Eye_Black", (s * 0.0275, -0.183, 0.63), 0.0034)):
            geom = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=r)
            for v in geom["verts"]:
                v.co += Vector(c)
            idx = mats.index(mat)
            for f in {f for v in geom["verts"] for f in v.link_faces}:
                f.material_index = idx
                f[bm.faces.layers.int.get("eye") or bm.faces.layers.int.new("eye")] = 1

def label_tree():
    kd = KDTree(len(SAMPLES))
    for i, (p, _) in enumerate(SAMPLES):
        kd.insert(p, i)
    kd.balance()
    return kd

def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length

def build_mesh_object():
    build_shapes()
    obj = build_body_mesh()
    obj.name = "Manok_Talisayin"
    obj.data.name = "Manok_Talisayin"
    mats = MAT_ORDER
    for name in mats:
        obj.data.materials.append(make_material(name, BREEDS["Talisayin"][name]))
    kd = label_tree()
    bm = bmesh.new(); bm.from_mesh(obj.data)
    eye_layer = bm.faces.layers.int.new("eye")
    for f in bm.faces:
        _, i, _ = kd.find(f.calc_center_median())
        f.material_index = mats.index(LABELS[SAMPLES[i][1]][0])
        f.smooth = False
    add_eyes(bm, mats)
    bm.to_mesh(obj.data); bm.free()
    return obj, kd

# ----------------------------------------------------------------------------- armature + skin
def build_armature():
    arm = bpy.data.armatures.new("ManokRig")
    ao = bpy.data.objects.new("ManokRig", arm)
    bpy.context.scene.collection.objects.link(ao)
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='EDIT')
    for name, parent, h, t, deform in BONES:
        b = arm.edit_bones.new(name)
        b.head, b.tail, b.roll = h, t, 0.0
        b.use_deform = deform
        if parent:
            b.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.display_type = 'OCTAHEDRAL'
    ao.show_in_front = True
    return ao

def skin(obj, ao, kd):
    me = obj.data
    eye = me.attributes.get("eye")
    eye_verts = set()
    if eye:
        for poly in me.polygons:
            if eye.data[poly.index].value:
                eye_verts.update(poly.vertices)
    groups = {n: obj.vertex_groups.new(name=n) for n, *_, d in BONES if d}
    W = []
    for v in me.vertices:
        if v.index in eye_verts:
            W.append({"head": 1.0}); continue
        p = v.co
        _, i, _ = kd.find(p)
        allowed = LABELS[SAMPLES[i][1]][1]
        ws = {}
        for bn, bias in allowed.items():
            a, b = BONE_SEG[bn]
            d = max(seg_dist(p, a, b), 0.004)
            ws[bn] = bias / d ** 4
        tot = sum(ws.values())
        W.append({k: w / tot for k, w in ws.items()})
    # relax weights across the surface (Laplacian), eyes stay rigid on the head
    nbr = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        nbr[a].append(b); nbr[b].append(a)
    for _ in range(3):
        new = []
        for i, w in enumerate(W):
            if i in eye_verts or not nbr[i]:
                new.append(w); continue
            acc = {}
            for j in nbr[i]:
                for k, x in W[j].items():
                    acc[k] = acc.get(k, 0) + x / len(nbr[i])
            mix = {k: 0.5 * w.get(k, 0) + 0.5 * acc.get(k, 0) for k in set(w) | set(acc)}
            new.append(mix)
        W = new
    # top 4 influences, drop tiny ones, normalise
    for i, w in enumerate(W):
        top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
        top = [(k, x) for k, x in top if x > 0.02] or top[:1]
        tot = sum(x for _, x in top)
        for k, x in top:
            groups[k].add([i], x / tot, 'REPLACE')
    obj.parent = ao
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = ao

def build_tari(ao):
    bm = bmesh.new()
    # wrap around the tarsus
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.0125, radius2=0.0125, depth=0.012)
    for v in g["verts"]:
        v.co += Vector((0.06, 0.004, 0.062))
    for f in {f for v in g["verts"] for f in v.link_faces}:
        f.material_index = 0
    # curved blade pointing back (+Y), edge up
    prof = [(0.0, 0.0045), (0.02, 0.0052), (0.045, 0.0045), (0.07, 0.0025), (0.088, 0.0)]
    rows = []
    for y, h in prof:
        zc = 0.062 + (y / 0.088) ** 2 * 0.012
        rows.append([bm.verts.new((0.06 + dx, 0.016 + y, zc + dz)) for dx, dz in
                     ((0.0012, -h), (0.0012, h), (-0.0012, h), (-0.0012, -h))])
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(4):
            f = bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
            f.material_index = 1
    f = bm.faces.new(list(reversed(rows[0]))); f.material_index = 1
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    me = bpy.data.meshes.new("Tari_Standard")
    bm.to_mesh(me); bm.free()
    for n, c in TARI_MATS.items():
        me.materials.append(make_material(n, c, rough=0.3 if "Steel" in n else 0.8, metal=0.9 if "Steel" in n else 0.0))
    for p in me.polygons:
        p.use_smooth = False
    to = bpy.data.objects.new("Tari_Standard", me)
    bpy.context.scene.collection.objects.link(to)
    to.parent = ao
    to.parent_type = 'BONE'
    to.parent_bone = "tari_socket_L"
    bpy.context.view_layer.update()
    bone = ao.data.bones["tari_socket_L"]
    socket = ao.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
    to.matrix_parent_inverse = socket.inverted()
    return to

# ----------------------------------------------------------------------------- checks
def report(obj, ao, tari):
    me = obj.data
    me.calc_loop_triangles()
    tris = len(me.loop_triangles) + tri_count(tari.data)
    maxinf = max(len([g for g in v.groups if g.weight > 0]) for v in me.vertices)
    zs = [v.co.z for v in me.vertices]
    bm = bmesh.new(); bm.from_mesh(me)
    eye = bm.faces.layers.int.get("eye")
    seen, islands = set(), 0
    for f in bm.faces:
        if f.index in seen or (eye and f[eye]):
            continue
        islands += 1
        stack = [f]
        isl = []
        while stack:
            g = stack.pop()
            if g.index in seen: continue
            seen.add(g.index)
            isl.append(g.calc_center_median())
            for e in g.edges:
                stack.extend(x for x in e.link_faces if x.index not in seen)
        if isl:
            c = sum(isl, Vector()) / len(isl)
            print("ISLAND", len(isl), [round(x, 3) for x in c])
    sizes = []
    for f in bm.faces:
        pass
    bm.free()
    r = {"triangles_total": tris, "triangles_body": len(me.loop_triangles), "vertices": len(me.vertices),
         "max_influences": maxinf, "height_m": round(max(zs), 3), "min_z": round(min(zs), 4),
         "body_islands": islands, "bones": len(ao.data.bones),
         "deform_bones": sum(b.use_deform for b in ao.data.bones)}
    print("REPORT", json.dumps(r))
    return r

# ----------------------------------------------------------------------------- posing helpers
def rot_about_head(ao, name, axis, deg):
    pb = ao.pose.bones[name]
    h = pb.head.copy()
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    pb.matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()

def reset_pose(ao):
    for pb in ao.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()

def t_pose(ao):
    reset_pose(ao)
    for sd, s in (("L", 1), ("R", -1)):
        rot_about_head(ao, f"shoulder_{sd}", 'Z', -88 * s)
        rot_about_head(ao, f"shoulder_{sd}", 'X', -0)
        for b in (f"wing_upper_{sd}", f"wing_fore_{sd}", f"wing_hand_{sd}"):
            pb = ao.pose.bones[b]
            axis = (pb.tail - pb.head).normalized()
            rot_about_head(ao, b, Vector((s * 1, 0, 0)), 0)
        # open the wing flat: spin the whole chain about its span axis
        sh = ao.pose.bones[f"shoulder_{sd}"]
        span = (ao.pose.bones[f"wing_hand_{sd}"].tail - sh.head).normalized()
        h = sh.head.copy()
        R = Matrix.Rotation(math.radians(-80 * s), 4, span)
        sh.matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ sh.matrix
        bpy.context.view_layer.update()

def ref_idle_pose(ao, glb):
    """Copy frame 1 of the v1 Idle clip onto this rig (same bones, same rest)."""
    before = set(bpy.data.objects)
    scn = bpy.context.scene
    scn.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in bpy.data.objects if o not in before]
    ref = next(o for o in new if o.type == 'ARMATURE')
    act = bpy.data.actions.get("Idle")
    ref.animation_data.action = act
    scn.frame_set(1)
    bpy.context.view_layer.update()
    for pb in ao.pose.bones:
        rp = ref.pose.bones.get(pb.name)
        if rp:
            pb.matrix_basis = rp.matrix_basis.copy()
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()

# ----------------------------------------------------------------------------- previews
def setup_render():
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_WORKBENCH'
    sh = scn.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_shadows = True
    sh.shadow_intensity = 0.35
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_object_outline = True
    sh.object_outline_color = (0.05, 0.03, 0.02)
    scn.display.light_direction = (0.4, -0.5, 0.75)
    scn.render.resolution_x = scn.render.resolution_y = 760
    scn.world = bpy.data.worlds.new("Bg")
    scn.world.color = (0.75, 0.68, 0.58)
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0))
    g = bpy.context.object; g.name = "Ground"
    g.data.materials.append(make_material("Ground_Sand", (0.55, 0.45, 0.33)))

def camera(name, loc, target=(0, 0.06, 0.35), ortho=0.95):
    cam = bpy.data.objects.get(name)
    if not cam:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ortho
    return cam

def shot(cam, path):
    scn = bpy.context.scene
    scn.camera = cam
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path

def contact_html(path, title, panels, stats, note=""):
    cells = []
    for img, cap in panels:
        b64 = base64.b64encode(open(img, "rb").read()).decode()
        cells.append(f'<figure><img src="data:image/png;base64,{b64}"><figcaption>{cap}</figcaption></figure>')
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in stats.items())
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>
body{{margin:0;padding:20px;background:#17110d;color:#f1e6d8;font:14px/1.45 system-ui,Segoe UI,sans-serif}}
h1{{font-size:20px;margin:0 0 4px}} p{{color:#c9b8a4;margin:0 0 14px;max-width:70ch}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
figure{{margin:0;background:#241a14;border:1px solid #3a2a20;border-radius:10px;overflow:hidden;opacity:0;transform:translateY(8px);animation:in .5s forwards}}
figure:nth-child(2){{animation-delay:.1s}} figure:nth-child(3){{animation-delay:.2s}} figure:nth-child(4){{animation-delay:.3s}}
@keyframes in{{to{{opacity:1;transform:none}}}}
img{{width:100%;display:block}} figcaption{{padding:8px 10px;color:#e8c9a0;font-weight:600}}
table{{border-collapse:collapse;margin-top:16px}} td{{padding:4px 14px 4px 0;border-bottom:1px solid #33261d}} td:first-child{{color:#a8957f}}
</style></head><body><h1>{title}</h1><p>{note}</p><div class="grid">{''.join(cells)}</div><table>{rows}</table></body></html>"""
    open(path, "w", encoding="utf-8").write(html)

# ----------------------------------------------------------------------------- stage A
def stage_a():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = 30
    obj, kd = build_mesh_object()
    ao = build_armature()
    skin(obj, ao, kd)
    tari = build_tari(ao)
    stats = report(obj, ao, tari)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "manok_v2.blend"))

    setup_render()
    front = camera("Cam_Front", (0, -3, 0.36), (0, 0, 0.36))
    side = camera("Cam_Side", (3, 0.06, 0.36), (0, 0.06, 0.36))
    q34 = camera("Cam_34", (2.2, -2.4, 1.2), (0, 0.04, 0.33))
    panels = []
    t_pose(ao)
    panels.append((shot(front, os.path.join(OUT, "A_tpose_front.png")), "T-pose, front"))
    panels.append((shot(q34, os.path.join(OUT, "A_tpose_34.png")), "T-pose, 3/4"))
    reset_pose(ao)
    if REF_GLB:
        ref_idle_pose(ao, REF_GLB)
        idle_cap = "Idle pose (frame 1 of the v1 Idle clip, played on the new rig)"
    else:
        idle_cap = "Rest pose"
    panels.append((shot(side, os.path.join(OUT, "A_idle_side.png")), idle_cap.split(" (")[0] + ", side"))
    panels.append((shot(q34, os.path.join(OUT, "A_idle_34.png")), idle_cap.split(" (")[0] + ", 3/4"))
    reset_pose(ao)
    # weight check: curl the neck, lift wings, swing the tail, crouch a leg
    for b, d in (("neck_01", 18), ("neck_02", 18), ("neck_03", 16), ("neck_04", 14), ("head", -30)):
        rot_about_head(ao, b, 'X', -d)
    for sd, s in (("L", 1), ("R", -1)):
        rot_about_head(ao, f"shoulder_{sd}", 'Y', 55 * s)
        rot_about_head(ao, f"wing_fore_{sd}", 'Y', 20 * s)
    for b in ("tail_base", "tail_01", "tail_02", "tail_03"):
        rot_about_head(ao, b, 'Z', 9)
    rot_about_head(ao, "hackle_C", 'X', 25); rot_about_head(ao, "hackle_L", 'X', 25); rot_about_head(ao, "hackle_R", 'X', 25)
    panels.append((shot(q34, os.path.join(OUT, "A_deform_34.png")), "Deformation check: neck curl, wings up, tail swing, hackles flared"))
    reset_pose(ao)
    nice = {"Triangles (body + eyes + tari)": stats["triangles_total"],
            "Height (comb tip)": f'{stats["height_m"]} m', "Lowest point": f'{stats["min_z"]} m',
            "Connected body pieces": stats["body_islands"],
            "Max bone influences per vertex": stats["max_influences"],
            "Bones (deforming)": f'{stats["bones"]} ({stats["deform_bones"]})'}
    contact_html(os.path.join(OUT, "stage_A_preview.html"), "Manok v2 · Stage A: model, rig, weights",
                 panels, nice, "Idle uses frame 1 of the current v1 clip on the new rig, as a compatibility check. "
                 "New animation comes in stage B.")
    json.dump(stats, open(os.path.join(OUT, "stage_A_stats.json"), "w"), indent=1)
    print("DONE stage A")

# ============================================================================= STAGE B: animation
# Poses are written in armature axes, relative to the parent, as (pitch about X, roll about Y, yaw about Z)
# in degrees.  +pitch tips an upward bone forward (-Y) / a downward bone backward (+Y).
# Wings: spread swings the folded wing out sideways, flap raises it (both mirrored per side).
FPS = 30
DT = 1.0 / FPS
NECK = ("neck_01", "neck_02", "neck_03", "neck_04")
NECK_SHARE = (0.2, 0.25, 0.28, 0.27)

def merge(*ds):
    out = {}
    for d in ds:
        for k, v in d.items():
            if k in out and isinstance(v, dict):
                out[k] = {**out[k], **v}
            else:
                out[k] = v
    return out

def R(bone, p=0, r=0, y=0, t=None):
    d = {"r": (p, r, y)}
    if t is not None:
        d["t"] = t
    return {bone: d}

STRIKE_SHARE = (0.5, 0.36, 0.12, 0.02)   # lead from the base so the neck extends instead of curling

def neckp(p=0, y=0, head=None, head_y=0, head_r=0, shares=NECK_SHARE):
    d = {}
    for b, s in zip(NECK, shares):
        d.update(R(b, p * s, 0, y * s))
    d.update(R("head", -p * 0.45 if head is None else head, head_r, head_y))
    return d

def wings(spread=0, flap=0, fore=0, hand=0):
    d = {}
    for sd, s in (("L", 1), ("R", -1)):
        d.update(R(f"shoulder_{sd}", 0, -flap * s, -spread * s))
        if fore: d.update(R(f"wing_fore_{sd}", 0, -fore * s * 0.5, -fore * s))
        if hand: d.update(R(f"wing_hand_{sd}", 0, -hand * s * 0.5, -hand * s))
    return d

def hackles(p):
    return merge(R("hackle_C", p), R("hackle_L", p, 0, -p * 0.3), R("hackle_R", p, 0, p * 0.3))

def tail(p=0, y=0):
    return merge(R("tail_base", p * 0.4, 0, y * 0.4), R("tail_01", p * 0.3, 0, y * 0.3), R("tail_02", p * 0.3, 0, y * 0.3))

def pelvis(p=0, r=0, y=0, t=(0, 0, 0)):
    return R("pelvis", p, r, y, t)

def leg(sd, thigh=0, shank=0, tarsus=0, toe=0, toeb=None, splay=0):
    s = 1 if sd == "L" else -1
    d = merge(R(f"thigh_{sd}", thigh, 0, splay * s), R(f"shank_{sd}", shank), R(f"tarsus_{sd}", tarsus),
              R(f"toe_{sd}", toe), R(f"toe_back_{sd}", -toe if toeb is None else toeb))
    return d

def legs(**kw):
    return merge(leg("L", **kw), leg("R", **kw))

def foot(sd, t=(0, 0, 0), p=0, w=1.0):
    """IK control: hock target offset (m, armature axes), tarsus pitch, IK weight."""
    return {f"CTRL_hock_{sd}": {"r": (0, 0, 0), "t": t}, f"CTRL_foot_{sd}": {"r": (p, 0, 0)}, f"ikw_{sd}": w}

def feet(w=1.0):
    return merge(foot("L", w=w), foot("R", w=w))

BASE = merge(feet(1.0))

# -- clips: name -> (length, loop, [(frame, pose, handle)], {frame: label})
def clip_defs():
    C = {}
    V, A, AC = 'VECTOR', 'AUTO', 'AUTO_CLAMPED'
    # Idle: breathing, alert head snaps, hackle ruffle
    idle0 = merge(BASE, neckp(4), tail(2))
    C["Idle"] = (61, True, [
        (1, idle0, A),
        (12, merge(BASE, neckp(0), R("chest", -3), pelvis(t=(0, 0, 0.004)), wings(4, 2), tail(4)), A),
        (21, merge(BASE, neckp(2, 2), R("chest", -2), wings(3, 1), tail(3)), AC),
        (24, merge(BASE, neckp(2, 14, head_y=26, head_r=12), R("chest", -1), tail(3, -4)), AC),
        (36, merge(BASE, neckp(5, 12, head_y=22, head_r=8), pelvis(t=(0, 0, 0.002)), tail(2, -3)), AC),
        (40, merge(BASE, neckp(3, -8, head_y=-16, head_r=-6), hackles(10), tail(3, 3)), AC),
        (50, merge(BASE, neckp(6, -4, head_y=-6), pelvis(t=(0, 0, -0.002)), tail(2, 2)), A),
        (61, idle0, A),
    ], {1: "start", 12: "breathe in", 24: "head snap", 40: "look back", 61: "loop"})

    # Walk: in-place treadmill on IK feet, head-bob, hip sway
    def wl(sd, ph):
        # ph: 0 contact front, 1 mid-stance, 2 push-off, 3 swing (foot up)
        return [foot(sd, (0, -0.04, 0.0), -8), foot(sd, (0, 0.0, 0.0), 0), foot(sd, (0, 0.04, 0.008), 22),
                foot(sd, (0, 0.0, 0.05), 30)][ph]
    def wtoe(sd, ph):
        return leg(sd, toe=[-6, 0, -18, 45][ph], toeb=[0, 0, 10, -30][ph])
    def wpose(phL, phR, bob, sway):
        return merge(wl("L", phL), wl("R", phR), wtoe("L", phL), wtoe("R", phR), neckp(bob),
                     pelvis(0, 3 * sway, 4 * sway, (0, 0, -0.006 if phL in (0, 2) else 0.005)),
                     tail(2, -5 * sway), wings(3, 2))
    w1 = wpose(0, 2, 9, 1)
    C["Walk"] = (25, True, [
        (1, w1, A), (7, wpose(1, 3, -5, 0), A), (13, wpose(2, 0, 9, -1), A), (19, wpose(3, 1, -5, 0), A), (25, w1, A),
    ], {1: "L contact", 7: "R passing", 13: "R contact", 19: "L passing", 25: "loop"})

    # Tuka_Peck: wind back, snap strike at 9, recover
    C["Tuka_Peck"] = (19, False, [
        (1, BASE, AC),
        (5, merge(BASE, neckp(-24, head=8), R("chest", -8), pelvis(-6, t=(0, 0.014, 0.004)), wings(8, 4), hackles(22), tail(6)), AC),
        (9, merge(BASE, neckp(54, head=-14, shares=STRIKE_SHARE), R("chest", 22), pelvis(16, t=(0, -0.03, -0.016)), wings(12, 6), hackles(30), tail(-4)), V),
        (11, merge(BASE, neckp(30, head=-10, shares=STRIKE_SHARE), R("chest", 9), pelvis(7, t=(0, -0.013, -0.007)), wings(10, 3), hackles(24), tail(-2)), AC),
        (19, BASE, AC),
    ], {5: "anticipation", 9: "STRIKE", 11: "snap back", 19: "recover"})

    # Sipa_Kick: crouch, leap, both spurs forward at 11, land
    air = lambda w=0.0: feet(w)
    C["Sipa_Kick"] = (25, False, [
        (1, BASE, AC),
        (6, merge(feet(1), pelvis(8, t=(0, 0.01, -0.032)), neckp(-10), wings(25, 18), tail(5), hackles(15)), AC),
        (8, merge(feet(1), pelvis(0, t=(0, 0.0, 0.02)), neckp(-14), wings(40, -12), tail(4)), AC),
        (9, merge(air(), pelvis(-10, t=(0, -0.005, 0.07)), legs(thigh=18, shank=-8, tarsus=10, toe=30), neckp(-18), wings(55, -25), tail(8)), A),
        (11, merge(air(), pelvis(-32, t=(0, -0.012, 0.12)), legs(thigh=-62, shank=-28, tarsus=-22, toe=35),
                   neckp(-26, head=18), wings(78, 48, 10, 10), tail(16), hackles(30)), V),
        (13, merge(air(), pelvis(-18, t=(0, -0.008, 0.11)), legs(thigh=-8, shank=-4, tarsus=0, toe=20), neckp(-16), wings(70, 10, 6, 6), tail(10)), A),
        (14, merge(air(), pelvis(-14, t=(0, -0.01, 0.1)), legs(thigh=-16, shank=-6, tarsus=-2, toe=16), neckp(-12), wings(60, -14), tail(4)), AC),
        (17, merge(air(), pelvis(-2, t=(0, -0.005, 0.04)), legs(thigh=4, shank=6, tarsus=4, toe=10), neckp(0), wings(45, 20), tail(-2)), A),
        (20, merge(feet(1), pelvis(7, t=(0, 0, -0.026)), neckp(10), wings(28, 6), tail(-8), hackles(10)), AC),
        (25, BASE, AC),
    ], {6: "crouch", 9: "takeoff", 11: "KICK", 13: "snap back", 20: "land"})

    # Lipad_Jump: crouch 8, takeoff 14, apex strike 20, descent 26, land 33
    # Airborne height is NOT in the clip: the game lifts the whole manok. Pelvis Z only carries the crouch/squash.
    C["Lipad_Jump"] = (41, False, [
        (1, BASE, AC),
        (8, merge(feet(1), pelvis(12, t=(0, 0.012, -0.046)), neckp(-6, head=4), wings(42, 32), tail(6), hackles(20)), AC),
        (11, merge(feet(1), pelvis(4, t=(0, 0.0, -0.02)), neckp(-10), wings(70, -18), tail(4)), AC),
        (14, merge(air(), pelvis(-6, t=(0, -0.01, 0.0)), legs(thigh=26, shank=-6, tarsus=16, toe=42), neckp(-14), wings(82, -38, 8, 8), tail(10)), AC),
        (17, merge(air(), pelvis(-20, t=(0, -0.02, 0.0)), legs(thigh=-24, shank=-10, tarsus=-4, toe=25), neckp(-18), wings(80, 46, 10, 12), tail(14)), AC),
        (20, merge(air(), pelvis(-30, t=(0, -0.03, 0.0)), legs(thigh=-48, shank=-26, tarsus=-14, toe=38),
                   neckp(-24, head=16), wings(90, -8, 12, 14), tail(20), hackles(35)), V),
        (23, merge(air(), pelvis(-16, t=(0, -0.024, 0.0)), legs(thigh=-22, shank=-8, tarsus=-2, toe=18), neckp(-12), wings(85, 40, 8, 10), tail(8)), AC),
        (26, merge(air(), pelvis(-14, t=(0, -0.025, 0.0)), legs(thigh=-10, shank=0, tarsus=2, toe=10), neckp(-4), wings(80, -22, 6, 6), tail(-2)), AC),
        (30, merge(feet(0.15), pelvis(-2, t=(0, -0.01, 0.0)), legs(thigh=6, shank=4, tarsus=4, toe=-10), neckp(4), wings(70, 32), tail(-6)), V),
        (33, merge(feet(1), pelvis(13, t=(0, 0.01, -0.042)), neckp(14, head=-4), wings(48, 22), tail(-12), hackles(18)), AC),
        (37, merge(feet(1), pelvis(3, t=(0, 0, 0.004)), neckp(4), wings(14, 4), tail(-3)), A),
        (41, BASE, AC),
    ], {8: "crouch", 14: "takeoff", 20: "APEX STRIKE", 26: "descent", 33: "land"})

    # Hit_React: snapped back at 3, recoil, recover
    C["Hit_React"] = (16, False, [
        (1, BASE, AC),
        (3, merge(BASE, pelvis(-14, 0, 0, (0, 0.03, 0.006)), R("chest", -6), neckp(-32, head=-14), wings(30, 22), hackles(36), tail(10)), V),
        (6, merge(BASE, pelvis(-9, 6, 8, (0, 0.034, 0.0)), neckp(-16, 6), wings(20, 6), hackles(26), tail(4, 6)), AC),
        (10, merge(BASE, pelvis(5, -2, -2, (0, 0.01, -0.008)), neckp(8, -3), wings(6, -2), hackles(8), tail(-4, -2)), AC),
        (16, BASE, AC),
    ], {3: "impact", 6: "recoil", 10: "recover"})

    # Hingal_Exhausted: head low, wings drooping, panting loop
    def pant(z, nk, hd, wsp, ch):
        return merge(BASE, pelvis(10, t=(0, 0, z)), R("chest", ch), neckp(nk, head=hd), wings(wsp, -16), tail(-12), hackles(-6))
    h1 = pant(-0.02, 28, -20, 18, 4)
    C["Hingal_Exhausted"] = (17, True, [
        (1, h1, A), (5, pant(-0.013, 22, -16, 22, 0), A), (9, pant(-0.026, 32, -24, 16, 5), A),
        (13, pant(-0.016, 24, -18, 21, 1), A), (17, h1, A),
    ], {1: "exhale", 5: "inhale", 9: "exhale", 17: "loop"})

    # Talikod_TurnAway: flinch, then turn its back by stepping around (root rotates, never translates)
    def tk(yaw, lift_l=0.0, lift_r=0.0, **kw):
        return merge(R("root", 0, 0, yaw), foot("L", (0, 0, lift_l)), foot("R", (0, 0, lift_r)), *kw.values())
    C["Talikod_TurnAway"] = (30, False, [
        (1, BASE, AC),
        (5, tk(-4, n=neckp(-18, -10, head_y=-14), h=hackles(-10), t=tail(-5), p=pelvis(-4, t=(0, 0.012, 0))), AC),
        (8, tk(30, 0.045, 0, n=neckp(-8, 15), p=pelvis(0, 0, 18), t=tail(-8), w=wings(4, -4)), A),
        (11, tk(70, 0.0, 0.0, n=neckp(-2, 20), p=pelvis(0, 0, 12), t=tail(-12)), A),
        (14, tk(105, 0, 0.045, n=neckp(2, 14), p=pelvis(0, 0, 10), t=tail(-16)), A),
        (17, tk(135, 0, 0, n=neckp(6, 8), p=pelvis(2, 0, 6), t=tail(-20)), A),
        (20, tk(155, 0.035, 0, n=neckp(8, 4), p=pelvis(3), t=tail(-22), w=wings(6, -10)), A),
        (24, tk(168, 0, 0.03, n=neckp(10, 0, head=4), p=pelvis(4), t=tail(-24), h=hackles(-14)), A),
        (30, tk(172, n=neckp(12, 0, head=6), p=pelvis(5, t=(0, 0, -0.006)), t=tail(-26), h=hackles(-16), w=wings(6, -12)), AC),
    ], {5: "flinch", 11: "turning", 20: "back turned", 30: "end"})

    # KO: stagger, legs give, falls on its left side, twitch
    C["KO"] = (40, False, [
        (1, BASE, AC),
        (4, merge(BASE, pelvis(-12, 0, 0, (0, 0.02, 0)), neckp(-26, head=-14), wings(30, 24), tail(8), hackles(20)), AC),
        (9, merge(BASE, pelvis(-2, 10, 6, (0.01, 0.024, -0.02)), neckp(10, 14), wings(24, -10), tail(-4, 6)), AC),
        (12, merge(feet(0.6), pelvis(0, 24, 4, (0.03, 0.03, -0.05)), neckp(18, 10), wings(26, -14), tail(-6)), A),
        (16, merge(feet(0), pelvis(0, 52, 0, (0.09, 0.04, -0.12)), legs(thigh=-20, shank=-10, tarsus=6, toe=10),
                   neckp(22, 6), wings(30, 30), tail(-8)), A),
        (20, merge(feet(0), pelvis(0, 84, 0, (0.2, 0.05, -0.19)), legs(thigh=-52, shank=-22, tarsus=8, toe=30, splay=8),
                   neckp(6, 0, head=0), wings(20, -18), tail(-10)), V),
        (24, merge(feet(0), pelvis(0, 78, 0, (0.205, 0.05, -0.17)), legs(thigh=-46, shank=-18, tarsus=6, toe=24, splay=6),
                   neckp(12, 0, head=4), wings(26, 10), tail(-4)), AC),
        (29, merge(feet(0), pelvis(0, 85, 0, (0.21, 0.05, -0.2)), legs(thigh=-50, shank=-20, tarsus=8, toe=36, splay=8),
                   neckp(8), wings(22, -16), tail(-10)), AC),
        (33, merge(feet(0), pelvis(0, 85, 0, (0.21, 0.05, -0.2)), legs(thigh=-58, shank=-26, tarsus=12, toe=55, splay=8),
                   neckp(8), wings(22, -14), tail(-10)), AC),
        (40, merge(feet(0), pelvis(0, 85, 0, (0.21, 0.05, -0.2)), legs(thigh=-50, shank=-20, tarsus=8, toe=40, splay=8),
                   neckp(8), wings(22, -16), tail(-10)), AC),
    ], {4: "stagger", 12: "legs give", 20: "hits ground", 33: "twitch", 40: "out"})

    # NEW Ilag_Dodge: quick hop to its right, eyes kept on the opponent
    C["Ilag_Dodge"] = (18, False, [
        (1, BASE, AC),
        (4, merge(feet(1), pelvis(4, 8, 0, (0.012, 0, -0.03)), neckp(-6, head_y=-6), wings(24, 16), tail(4, 4)), AC),
        (7, merge(feet(0.2), pelvis(-2, -12, 4, (-0.02, 0, 0.06)), legs(thigh=-10, shank=18, tarsus=-20, toe=30), wings(50, -20), tail(4, 6)), A),
        (8, merge(feet(0), pelvis(-4, -20, 6, (-0.04, 0, 0.11)), legs(thigh=-32, shank=48, tarsus=-52, toe=45),
                  neckp(-10, -8, head_y=18, head_r=10), wings(62, 36, 6, 6), tail(6, 10), hackles(20)), A),
        (12, merge(feet(1), pelvis(8, -8, 2, (-0.02, 0, -0.03)), neckp(8, -4, head_y=10), wings(36, -6), tail(-6, -6)), AC),
        (18, BASE, AC),
    ], {4: "load", 8: "airborne", 12: "land"})

    # NEW Banat_Combo: three pecks, strikes at 6, 14, 22 (third is the big one)
    C["Banat_Combo"] = (32, False, [
        (1, BASE, AC),
        (3, merge(BASE, neckp(-16, head=6), R("chest", -5), pelvis(-3, t=(0, 0.01, 0)), wings(8, 4), hackles(25)), AC),
        (6, merge(BASE, neckp(64, 2, head=-20, shares=STRIKE_SHARE), R("chest", 11), pelvis(8, t=(0, -0.016, -0.008)), wings(10, 2), hackles(30), tail(-3)), V),
        (9, merge(BASE, neckp(-8, 12, head=4, head_y=8), R("chest", -2), pelvis(0, t=(0, 0.004, 0)), wings(8, 6), hackles(26)), AC),
        (11, merge(BASE, neckp(-18, 14, head=8, head_y=10), R("chest", -6), pelvis(-3, 0, 4, (0, 0.012, 0)), wings(10, 8), hackles(28)), AC),
        (14, merge(BASE, neckp(65, -10, head=-20, head_y=-6, shares=STRIKE_SHARE), R("chest", 12), pelvis(8, 0, -6, (0, -0.017, -0.009)), wings(12, 0), hackles(32), tail(-3, 4)), V),
        (17, merge(BASE, neckp(-10, -12, head=4, head_y=-8), R("chest", -2), pelvis(0, 0, -3), wings(10, 8), hackles(26)), AC),
        (19, merge(BASE, neckp(-26, 0, head=10), R("chest", -9), pelvis(-6, 0, 2, (0, 0.018, 0.004)), wings(26, 22), hackles(34), tail(8)), AC),
        (22, merge(BASE, neckp(70, 6, head=-22, shares=STRIKE_SHARE), R("chest", 16), pelvis(14, 0, 3, (0, -0.026, -0.013)), wings(34, -12, 6, 6), hackles(36), tail(-6)), V),
        (25, merge(BASE, neckp(30, 4, head=-10, shares=STRIKE_SHARE), R("chest", 6), pelvis(5, 0, 2, (0, -0.008, -0.004)), wings(20, 2), hackles(28), tail(-2)), AC),
        (32, BASE, AC),
    ], {6: "STRIKE 1", 14: "STRIKE 2", 22: "STRIKE 3", 25: "snap back"})
    return C

# -- secondary motion: damped springs on world rotation + inertia from head acceleration
# bone: (stiffness, damping, amount, max_deg, accel_gain rad per m/s^2, max_tilt_deg)
SIM = {
    "neck_02": (520, 40, 0.3, 8, 0, 0), "neck_03": (500, 38, 0.32, 9, 0, 0), "neck_04": (470, 36, 0.32, 9, 0, 0),
    "hackle_C": (210, 13, 1.0, 35, 0.02, 25), "hackle_L": (210, 13, 1.0, 35, 0.02, 25), "hackle_R": (210, 13, 1.0, 35, 0.02, 25),
    "comb": (340, 14, 1.0, 22, 0.012, 14),
    "wattle_L": (150, 7, 1.0, 45, 0.035, 38), "wattle_R": (160, 7.5, 1.0, 45, 0.035, 38),
    "tail_base": (420, 30, 0.45, 10, 0.004, 5), "tail_01": (230, 14, 1.0, 26, 0.012, 12),
    "tail_02": (190, 12, 1.0, 30, 0.015, 15), "tail_03": (155, 10, 1.0, 36, 0.018, 18),
    "wing_upper_L": (520, 36, 0.3, 14, 0, 0), "wing_upper_R": (520, 36, 0.3, 14, 0, 0),
    "wing_fore_L": (300, 20, 0.7, 30, 0.005, 8), "wing_fore_R": (300, 20, 0.7, 30, 0.005, 8),
    "wing_hand_L": (220, 15, 0.9, 40, 0.008, 12), "wing_hand_R": (220, 15, 0.9, 40, 0.008, 12),
}
CTRL = ("CTRL_hock_L", "CTRL_foot_L", "CTRL_hock_R", "CTRL_foot_R")

def add_controls(ao):
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ao.data.edit_bones
    for sd in ("L", "R"):
        h = eb[f"shank_{sd}"].tail.copy()
        b = eb.new(f"CTRL_hock_{sd}"); b.head = h; b.tail = h + Vector((0, 0, 0.03)); b.parent = eb["root"]; b.use_deform = False
        t = eb[f"tarsus_{sd}"]
        f = eb.new(f"CTRL_foot_{sd}"); f.head, f.tail, f.roll = t.head, t.tail, t.roll; f.parent = eb["root"]; f.use_deform = False
    bpy.ops.object.mode_set(mode='POSE')
    for sd in ("L", "R"):
        ik = ao.pose.bones[f"shank_{sd}"].constraints.new('IK')
        ik.name = "IK"; ik.target = ao; ik.subtarget = f"CTRL_hock_{sd}"; ik.chain_count = 2; ik.use_tail = True
        cr = ao.pose.bones[f"tarsus_{sd}"].constraints.new('COPY_ROTATION')
        cr.name = "FootRot"; cr.target = ao; cr.subtarget = f"CTRL_foot_{sd}"
        for b in (f"thigh_{sd}", f"shank_{sd}"):
            ao.pose.bones[b].lock_ik_y = True
    bpy.ops.object.mode_set(mode='OBJECT')

def remove_controls(ao):
    bpy.context.view_layer.objects.active = ao
    bpy.ops.object.mode_set(mode='POSE')
    for pb in ao.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        pb.lock_ik_y = False
    bpy.ops.object.mode_set(mode='EDIT')
    for n in CTRL:
        ao.data.edit_bones.remove(ao.data.edit_bones[n])
    bpy.ops.object.mode_set(mode='OBJECT')

def qw(p, r, y):
    return (Quaternion((0, 1, 0), math.radians(r)) @ Quaternion((1, 0, 0), math.radians(p))
            @ Quaternion((0, 0, 1), math.radians(y)))

def apply_pose(ao, pose, rest_q):
    for pb in ao.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        spec = pose.get(pb.name, {})
        Rr = rest_q[pb.name]
        q = Rr.inverted() @ qw(*spec.get("r", (0, 0, 0))) @ Rr
        prev = pb.rotation_quaternion.copy()
        if prev.dot(q) < 0:
            q.negate()
        pb.rotation_quaternion = q
        pb.location = Rr.inverted() @ Vector(spec.get("t", (0, 0, 0)))
    for sd in ("L", "R"):
        w = pose.get(f"ikw_{sd}", 1.0)
        ao.pose.bones[f"shank_{sd}"].constraints["IK"].influence = w
        ao.pose.bones[f"tarsus_{sd}"].constraints["FootRot"].influence = w

def channelbag(action, slot):
    from bpy_extras import anim_utils
    return anim_utils.action_get_channelbag_for_slot(action, slot)

def author(ao, name, length, loop, keys, rest_q):
    act = bpy.data.actions.new("_auth_" + name)
    ao.animation_data_create()
    ao.animation_data.action = act
    for pb in ao.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
    for f, pose, handle in keys:
        apply_pose(ao, pose, rest_q)
        for pb in ao.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
            pb.keyframe_insert("location", frame=f, group=pb.name)
        for sd in ("L", "R"):
            ao.pose.bones[f"shank_{sd}"].constraints["IK"].keyframe_insert("influence", frame=f)
            ao.pose.bones[f"tarsus_{sd}"].constraints["FootRot"].keyframe_insert("influence", frame=f)
    cb = channelbag(act, ao.animation_data.action_slot)
    hmap = {f: h for f, _, h in keys}
    for fc in cb.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            h = hmap.get(int(round(kp.co[0])), 'AUTO_CLAMPED')
            kp.handle_left_type = kp.handle_right_type = h
        if loop:
            fc.modifiers.new('CYCLES')
        fc.update()
    return act

def sample(ao, frames):
    """Constraint-evaluated local basis (4x4) for every real bone at each frame."""
    scn = bpy.context.scene
    real = [n for n, *_ in BONES]
    bones = ao.data.bones
    rel = {}
    for n in real:
        b = bones[n]
        rel[n] = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy()
    out = []
    for f in frames:
        scn.frame_set(int(f))
        M = {}
        for n in real:
            pb = ao.pose.bones[n]
            par = bones[n].parent
            base = (ao.pose.bones[par.name].matrix @ rel[n]) if par else rel[n]
            M[n] = base.inverted() @ pb.matrix
        out.append(M)
    return out, rel

PIN_BONES = ("neck_02", "neck_03", "neck_04")
STRIKE_PINS = {"Tuka_Peck": [9], "Banat_Combo": [6, 14, 22], "Sipa_Kick": [11]}

def simulate(seq, rel, ao, fade_out=0, pins=(), frame_of=None):
    order = [n for n, *_ in BONES]
    parent = {n: p for n, p, *_ in BONES}
    st = {}
    out = []
    for k, B in enumerate(seq):
        B = {n: m.copy() for n, m in B.items()}
        W = {}
        for n in order:
            pw = W[parent[n]] if parent[n] else Matrix()
            frame0 = pw @ rel[n]
            if n in SIM:
                kk, cc, amt, mx, gain, mtilt = SIM[n]
                target = (frame0 @ B[n]).to_quaternion()
                raw = target.copy()
                h = frame0.translation.copy()
                s = st.get(n)
                if s is None:
                    s = st[n] = {"q": target.copy(), "w": Vector(), "h1": h.copy(), "h2": h.copy()}
                a = (h - 2 * s["h1"] + s["h2"]) / (DT * DT)
                s["h2"], s["h1"] = s["h1"], h.copy()
                if gain:
                    d = target @ Vector((0, 1, 0))
                    ap = a - d * a.dot(d)
                    if ap.length > 1e-4:
                        ang = min(gain * ap.length, math.radians(mtilt))
                        ax = d.cross(-ap)
                        if ax.length > 1e-8:
                            target = Quaternion(ax.normalized(), ang) @ target
                err = target @ s["q"].inverted()
                if err.w < 0:
                    err.negate()
                ax, an = err.to_axis_angle()
                e = Vector(ax) * an
                s["w"] = (s["w"] + e * kk * DT) / (1 + cc * DT)
                if s["w"].length > 1e-9:
                    s["q"] = Quaternion(s["w"].normalized(), s["w"].length * DT) @ s["q"]
                s["q"].normalize()
                fade = 1.0
                if fade_out:
                    left = len(seq) - 1 - k
                    if left < fade_out:
                        x = left / fade_out
                        fade = x * x * (3 - 2 * x)   # smoothstep to the authored pose on the last frame
                if pins and n in PIN_BONES:
                    fade = 0.0   # strike clips: the neck follows its authored keys exactly so hits land on time
                fq = raw.slerp(s["q"], amt * fade)
                diff = fq.rotation_difference(raw).angle
                lim = math.radians(mx)
                if diff > lim:
                    fq = raw.slerp(fq, lim / diff)
                loc = B[n].to_translation()
                local_q = frame0.to_quaternion().inverted() @ fq
                B[n] = Matrix.Translation(loc) @ local_q.to_matrix().to_4x4()
            W[n] = frame0 @ B[n]
        out.append(B)
    return out

def bake(ao, name, length, frames_B):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type='OBJECT', name="ManokRig")
    layer = act.layers.new("Layer")
    strip = layer.strips.new(type='KEYFRAME')
    cb = strip.channelbag(slot, ensure=True)
    n = len(frames_B)
    for bn, *_ in BONES:
        qs, ls = [], []
        prev = None
        for B in frames_B:
            q = B[bn].to_quaternion().normalized()
            if prev is not None and prev.dot(q) < 0:
                q.negate()
            prev = q
            qs.append(q); ls.append(B[bn].to_translation())
        path = f'pose.bones["{bn}"]'
        for i in range(4):
            fc = cb.fcurves.new(path + ".rotation_quaternion", index=i, group_name=bn)
            fc.keyframe_points.add(n)
            co = []
            for k, q in enumerate(qs):
                co += [k + 1, q[i]]
            fc.keyframe_points.foreach_set("co", co)
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            fc.update()
        if bn == "pelvis":   # root gets no location channel at all (in-place)
            for i in range(3):
                fc = cb.fcurves.new(path + ".location", index=i, group_name=bn)
                fc.keyframe_points.add(n)
                co = []
                for k, l in enumerate(ls):
                    co += [k + 1, 0.0 if bn == "root" else l[i]]
                fc.keyframe_points.foreach_set("co", co)
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
                fc.update()
    act.use_frame_range = True
    act.frame_start, act.frame_end = 1, length
    return act, slot

def make_clip(ao, name, spec, rest_q):
    length, loop, keys, _ = spec
    auth = author(ao, name, length, loop, keys, rest_q)
    if loop:
        cyc = list(range(1, length))
        seq, rel = sample(ao, cyc)
        sim = simulate(seq * 3, rel, ao, pins=STRIKE_PINS.get(name, []),
                       frame_of=lambda k: k % len(cyc) + 1)[-len(cyc):]
        frames = sim + [sim[0]]
    else:
        seq, rel = sample(ao, range(1, length + 1))
        sim = simulate([seq[0]] * 10 + seq, rel, ao, fade_out=max(4, length // 4),
                       pins=STRIKE_PINS.get(name, []), frame_of=lambda k: k - 9)[10:]
        frames = sim
    ao.animation_data.action = None
    bpy.data.actions.remove(auth)
    act, slot = bake(ao, name, length, frames)
    return act, slot

def clip_checks(ao, acts):
    res = {}
    for name, (act, slot) in acts.items():
        cb = channelbag(act, slot)
        root_t = max((abs(kp.co[1]) for fc in cb.fcurves if fc.data_path == 'pose.bones["root"].location'
                      for kp in fc.keyframe_points), default=0.0)
        q = {}
        for fc in cb.fcurves:
            if fc.data_path.endswith("rotation_quaternion"):
                bn = fc.data_path.split('"')[1]
                q.setdefault(bn, [[0] * 4, [0] * 4])
                q[bn][0][fc.array_index] = fc.keyframe_points[0].co[1]
                q[bn][1][fc.array_index] = fc.keyframe_points[-1].co[1]
        seam, worst = 0.0, ""
        for bn, (a, b) in q.items():
            ang = math.degrees(Quaternion(a).normalized().rotation_difference(Quaternion(b).normalized()).angle)
            if ang > seam:
                seam, worst = ang, bn
        res[name] = {"frames": [act.frame_start, act.frame_end], "root_translation_max": round(root_t, 6),
                     "first_last_max_deg": round(seam, 2), "worst_bone": worst}
    return res

def stage_b():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "manok_v2.blend"))
    scn = bpy.context.scene
    scn.render.fps = FPS
    ao = bpy.data.objects["ManokRig"]
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    add_controls(ao)
    rest_q = {b.name: b.matrix_local.to_quaternion() for b in ao.data.bones}
    defs = clip_defs()
    acts = {}
    for name, spec in defs.items():
        acts[name] = make_clip(ao, name, spec, rest_q)
        print("CLIP", name, spec[0])
    remove_controls(ao)
    checks = clip_checks(ao, acts)
    for k, v in checks.items():
        print("CHECK", k, v)
    ao.animation_data.action = None
    for pb in ao.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "manok_v2.blend"))
    json.dump(checks, open(os.path.join(OUT, "stage_B_checks.json"), "w"), indent=1)
    render_stage_b(ao, defs, acts, checks)
    print("DONE stage B")

def render_stage_b(ao, defs, acts, checks):
    scn = bpy.context.scene
    setup_render()
    scn.render.resolution_x = scn.render.resolution_y = 300
    scn.render.image_settings.file_format = 'JPEG'
    scn.render.image_settings.quality = 82
    cam = camera("Cam_B", (2.3, -2.6, 1.55), (0, 0.03, 0.47), ortho=1.42)
    scn.camera = cam
    fdir = os.path.join(OUT, "stage_B_frames")
    os.makedirs(fdir, exist_ok=True)
    data = []
    for name, (act, slot) in acts.items():
        length, loop, keys, labels = defs[name]
        ao.animation_data.action = act
        ao.animation_data.action_slot = slot
        frames = []
        for f in range(1, length + 1):
            scn.frame_set(f)
            p = os.path.join(fdir, f"{name}_{f:02d}.jpg")
            scn.render.filepath = p
            bpy.ops.render.render(write_still=True)
            frames.append(base64.b64encode(open(p, "rb").read()).decode())
        data.append({"name": name, "len": length, "loop": loop, "labels": {str(k): v for k, v in labels.items()},
                     "frames": frames, "new": name in ("Ilag_Dodge", "Banat_Combo"), "check": checks[name]})
        print("RENDERED", name)
    ao.animation_data.action = None
    write_player(os.path.join(OUT, "stage_B_preview.html"), data)

def write_player(path, data):
    payload = json.dumps(data)
    html = """<!doctype html><html><head><meta charset="utf-8"><title>Manok v2 · Stage B</title><style>
:root{--bg:#17110d;--card:#221913;--line:#3a2a20;--ink:#f1e6d8;--dim:#a8957f;--gold:#e8b45a;--red:#d8452e}
*{box-sizing:border-box}body{margin:0;padding:18px;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,Segoe UI,sans-serif}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--dim);margin:0 0 14px;max-width:80ch}
.bar{display:flex;gap:8px;align-items:center;margin:0 0 14px;flex-wrap:wrap}
button{background:#2c2018;color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:6px 11px;font:inherit;cursor:pointer}
button.on{background:var(--gold);color:#1a120c;border-color:var(--gold)}
.clip{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:14px;opacity:0;transform:translateY(6px);animation:in .45s forwards}
@keyframes in{to{opacity:1;transform:none}}
.head{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:8px}
.name{font-weight:700;font-size:16px}.tag{font-size:11px;padding:2px 7px;border-radius:99px;background:var(--red);color:#fff;margin-left:6px}
.meta{color:var(--dim);font-size:12px}
.row{display:grid;grid-template-columns:minmax(200px,300px) 1fr;gap:12px;align-items:start}
@media(max-width:620px){.row{grid-template-columns:1fr}}
.player img{width:100%;border-radius:8px;display:block;background:#bfb3a3}
.scrub{display:flex;align-items:center;gap:8px;margin-top:6px}.scrub input{flex:1;accent-color:var(--gold)}
.fnum{font-variant-numeric:tabular-nums;color:var(--gold);min-width:52px;text-align:right}
.keys{display:grid;grid-template-columns:repeat(auto-fill,minmax(92px,1fr));gap:6px}
.k{background:#2a1f18;border-radius:7px;overflow:hidden;cursor:pointer;border:1px solid transparent}
.k:hover{border-color:var(--gold)}.k img{width:100%;display:block}
.k div{font-size:11px;padding:3px 5px;color:var(--dim)}.k b{color:var(--ink)}
</style></head><body>
<h1>Manok v2 · Stage B: animation</h1>
<p class="sub">Every clip plays at 30 fps from the baked actions. Click a key frame to jump to it. Strikes and loops sit on the frames the game expects; the root never translates.</p>
<div class="bar"><span class="meta">Speed</span><button data-s="1" class="on">1×</button><button data-s="0.5">½×</button><button data-s="0.25">¼×</button><button id="pp">Pause all</button></div>
<div id="list"></div>
<script>
const D = __DATA__;
let speed = 1, paused = false; const players = [];
const list = document.getElementById('list');
D.forEach((c, i) => {
  const el = document.createElement('div'); el.className = 'clip'; el.style.animationDelay = (i * 0.05) + 's';
  const keys = Object.keys(c.labels).map(Number).sort((a, b) => a - b);
  el.innerHTML = `<div class="head"><div><span class="name">${c.name}</span>${c.new ? '<span class="tag">NEW</span>' : ''}</div>
   <div class="meta">1–${c.len} @30fps · ${c.loop ? 'loop, seam ' + c.check.first_last_max_deg + '°' : 'one-shot'} · root move ${c.check.root_translation_max} m</div></div>
   <div class="row"><div class="player"><img><div class="scrub"><input type="range" min="1" max="${c.len}" value="1"><span class="fnum"></span></div></div>
   <div class="keys">${keys.map(k => `<div class="k" data-f="${k}"><img src="data:image/jpeg;base64,${c.frames[k - 1]}"><div><b>${k}</b> ${c.labels[k]}</div></div>`).join('')}</div></div>`;
  list.appendChild(el);
  const img = el.querySelector('.player img'), rng = el.querySelector('input'), fn = el.querySelector('.fnum');
  const p = { c, f: 1, acc: 0, hold: 0, img, rng, fn, show(f) { this.f = f; img.src = 'data:image/jpeg;base64,' + c.frames[f - 1]; rng.value = f; fn.textContent = 'f ' + f + (c.labels[f] ? ' · ' + c.labels[f] : ''); } };
  p.show(1); players.push(p);
  rng.oninput = () => { p.show(+rng.value); p.hold = 1.2; };
  el.querySelectorAll('.k').forEach(k => k.onclick = () => { p.show(+k.dataset.f); p.hold = 1.5; });
});
document.querySelectorAll('[data-s]').forEach(b => b.onclick = () => { speed = +b.dataset.s; document.querySelectorAll('[data-s]').forEach(x => x.classList.toggle('on', x === b)); });
document.getElementById('pp').onclick = (e) => { paused = !paused; e.target.textContent = paused ? 'Play all' : 'Pause all'; };
let last = performance.now();
function tick(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (!paused) for (const p of players) {
    if (p.hold > 0) { p.hold -= dt; continue; }
    p.acc += dt * 30 * speed;
    while (p.acc >= 1) { p.acc -= 1; let f = p.f + 1; if (f > p.c.len) { f = 1; if (!p.c.loop) p.hold = 0.5; } p.show(f); }
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
</script></body></html>"""
    open(path, "w", encoding="utf-8").write(html.replace("__DATA__", payload))

# ============================================================================= STAGE C: export
GLB_NAME = "manok.glb"
# Breed palettes, linear RGB, keyed by the exact material names in the .blend.
# talisayin = the shipped v1 materials; puti = the tint game.js already applies for Wala.
# kelso/hatch/roundhead/sweater/asil: approximations of each breed's typical plumage and leg colour
# (render_portraits.py with the original palette was not in the repo); edit breeds.json to taste.
_T = BREEDS["Talisayin"]
def _breed(**over):
    d = dict(_T); d.update(over); return d
BREED_PALETTES = {
    "talisayin": _breed(),
    "puti": _breed(Body_DeepRed=(0.86, 0.85, 0.82), Hackle_Gold=(0.96, 0.95, 0.9), WingTip_Green=(0.25, 0.27, 0.3),
                   Tail_GreenBlack=(0.03, 0.035, 0.04)),
    "kelso": _breed(Body_DeepRed=(0.42, 0.08, 0.03), Hackle_Gold=(0.9, 0.5, 0.1), WingTip_Green=(0.04, 0.1, 0.06),
                    Leg_Yellow=(0.88, 0.66, 0.18)),
    "hatch": _breed(Body_DeepRed=(0.2, 0.03, 0.02), Hackle_Gold=(0.55, 0.16, 0.04), WingTip_Green=(0.02, 0.07, 0.04),
                    Leg_Yellow=(0.25, 0.33, 0.12)),
    "roundhead": _breed(Body_DeepRed=(0.55, 0.16, 0.05), Hackle_Gold=(0.95, 0.62, 0.22), WingTip_Green=(0.05, 0.05, 0.04),
                        Tail_GreenBlack=(0.02, 0.025, 0.02), Leg_Yellow=(0.9, 0.78, 0.45)),
    "sweater": _breed(Body_DeepRed=(0.48, 0.12, 0.03), Hackle_Gold=(0.98, 0.6, 0.12), Leg_Yellow=(0.92, 0.72, 0.2)),
    "asil": _breed(Body_DeepRed=(0.12, 0.025, 0.015), Hackle_Gold=(0.35, 0.08, 0.03), WingTip_Green=(0.02, 0.03, 0.025),
                   Tail_GreenBlack=(0.01, 0.015, 0.012), Leg_Yellow=(0.8, 0.6, 0.2), Eye_Orange=(0.9, 0.85, 0.6)),
}
REQUIRED_KEYS = {"Tuka_Peck": [9], "Sipa_Kick": [11], "Lipad_Jump": [8, 14, 20, 26, 33], "Banat_Combo": [6, 14, 22],
                 "Ilag_Dodge": [], "Hit_React": [], "KO": [], "Talikod_TurnAway": [], "Idle": [], "Walk": [], "Hingal_Exhausted": []}
LENGTHS = {"Idle": 61, "Walk": 25, "Tuka_Peck": 19, "Sipa_Kick": 25, "Lipad_Jump": 41, "Hit_React": 16,
           "Hingal_Exhausted": 17, "Talikod_TurnAway": 30, "KO": 40, "Ilag_Dodge": 18, "Banat_Combo": 32}
LOOPS = ("Idle", "Walk", "Hingal_Exhausted")

def set_breed(palette):
    for name, rgb in palette.items():
        m = bpy.data.materials.get(name)
        if not m: continue
        bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        m.diffuse_color = (*rgb, 1)

def use_action(ao, act):
    ao.animation_data.action = act
    ao.animation_data.action_slot = act.slots[0]

def track(ao, act, fn):
    use_action(ao, act)
    out = []
    for f in range(int(act.frame_start), int(act.frame_end) + 1):
        bpy.context.scene.frame_set(f)
        out.append(fn(ao.pose.bones))
    return out

def pre_export_checks(obj, ao):
    defs = clip_defs()
    chk = {}
    # root location keys
    bad = []
    for a in bpy.data.actions:
        cb = channelbag(a, a.slots[0])
        if any(fc.data_path == 'pose.bones["root"].location' for fc in cb.fcurves):
            bad.append(a.name)
    chk["root_has_no_location_keys"] = {"pass": not bad, "actions_with_root_location": bad}
    # loops
    loops = {}
    for n in LOOPS:
        a = bpy.data.actions[n]
        cb = channelbag(a, a.slots[0])
        worst = max(abs(fc.keyframe_points[0].co[1] - fc.keyframe_points[-1].co[1]) for fc in cb.fcurves)
        loops[n] = {"first_frame": int(a.frame_start), "last_frame": int(a.frame_end), "max_channel_diff": round(worst, 7),
                    "pass": worst < 1e-5}
    chk["loops_first_equals_last"] = loops
    # clip lengths + key poses
    keys = {}
    for n, L in LENGTHS.items():
        a = bpy.data.actions.get(n)
        authored = sorted(f for f, *_ in defs[n][2])
        req = REQUIRED_KEYS[n]
        entry = {"range": [int(a.frame_start), int(a.frame_end)] if a else None, "expected_range": [1, L],
                 "authored_key_frames": authored, "required_key_frames": req,
                 "required_present": all(f in authored for f in req)}
        keys[n] = entry
    # measured extremes, from the baked clips
    hy = lambda pb: pb["head"].tail.y
    t = track(ao, bpy.data.actions["Tuka_Peck"], hy)
    keys["Tuka_Peck"]["measured"] = {"head_most_forward_frame": 1 + t.index(min(t))}
    b = track(ao, bpy.data.actions["Banat_Combo"], hy)
    mins = [1 + i for i in range(1, len(b) - 1) if b[i] < b[i - 1] and b[i] <= b[i + 1] and b[i] < b[0] - 0.05]
    keys["Banat_Combo"]["measured"] = {"head_forward_peaks": mins}
    s = track(ao, bpy.data.actions["Sipa_Kick"], lambda pb: (pb["tari_socket_L"].head.y + pb["tari_socket_R"].head.y) / 2)
    keys["Sipa_Kick"]["measured"] = {"spurs_most_forward_frame": 1 + s.index(min(s))}
    z = track(ao, bpy.data.actions["Lipad_Jump"], lambda pb: pb["pelvis"].head.z - 0.3)
    sp = track(ao, bpy.data.actions["Lipad_Jump"], lambda pb: (pb["tari_socket_L"].head.y + pb["tari_socket_R"].head.y) / 2)
    air = sp[13:30]
    keys["Lipad_Jump"]["measured"] = {"crouch_low_frame": 1 + z.index(min(z[:12])),
                                      "apex_strike_frame": 14 + air.index(min(air)),
                                      "land_low_frame": 28 + z[27:].index(min(z[27:])),
                                      "airborne_pelvis_lift_max_m": round(max(z[13:30]), 4),
                                      "crouch_depth_m": round(min(z[:12]), 4), "land_depth_m": round(min(z[27:]), 4)}
    for n, e in keys.items():
        m = e.get("measured", {})
        req = e["required_key_frames"]
        ok = e["required_present"] and e["range"] == e["expected_range"]
        if n == "Tuka_Peck": ok &= m["head_most_forward_frame"] == 9
        if n == "Banat_Combo": ok &= m["head_forward_peaks"] == [6, 14, 22]
        if n == "Sipa_Kick": ok &= m["spurs_most_forward_frame"] == 11
        if n == "Lipad_Jump": ok &= ((m["crouch_low_frame"], m["apex_strike_frame"], m["land_low_frame"]) == (8, 20, 33)
                                     and m["airborne_pelvis_lift_max_m"] <= 0.002)
        e["pass"] = bool(ok)
    chk["key_poses"] = keys
    ao.animation_data.action = None
    for pb in ao.pose.bones:
        pb.matrix_basis = Matrix()
    # mesh limits
    me = obj.data
    me.calc_loop_triangles()
    tari = bpy.data.objects["Tari_Standard"]
    tris = len(me.loop_triangles) + tri_count(tari.data)
    inf = max(len([g for g in v.groups if g.weight > 0]) for v in me.vertices)
    chk["mesh"] = {"triangles_total": tris, "max_influences": inf, "pass": tris < 6000 and inf <= 4}
    return chk

def read_glb(path):
    import struct
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    ln, typ = struct.unpack_from("<II", data, 12)
    gl = json.loads(data[20:20 + ln])
    return gl, len(data)

def glb_checks(path):
    gl, size = read_glb(path)
    nodes = gl.get("nodes", [])
    names = [n.get("name") for n in nodes]
    def idx(n): return names.index(n) if n in names else None
    socket_L, socket_R, tari = idx("tari_socket_L"), idx("tari_socket_R"), idx("Tari_Standard")
    tari_parent = next((names[i] for i, n in enumerate(nodes) if tari is not None and tari in n.get("children", [])), None)
    skin = gl["skins"][0] if gl.get("skins") else {}
    joints = [names[j] for j in skin.get("joints", [])]
    anims = []
    for a in gl.get("animations", []):
        tmin = min(gl["accessors"][s["input"]]["min"][0] for s in a["samplers"])
        tmax = max(gl["accessors"][s["input"]]["max"][0] for s in a["samplers"])
        anims.append({"name": a["name"], "first_frame": round(tmin * FPS), "last_frame": round(tmax * FPS),
                      "frame_count": round((tmax - tmin) * FPS) + 1})
    tri_total = 0
    for m in gl.get("meshes", []):
        for p in m["primitives"]:
            if "indices" in p:
                tri_total += gl["accessors"][p["indices"]]["count"] // 3
    import struct
    raw = open(path, "rb").read()
    jl = struct.unpack_from("<I", raw, 12)[0]
    bin0 = 20 + jl + 8
    def floats(ai):
        acc = gl["accessors"][ai]; bv = gl["bufferViews"][acc["bufferView"]]
        off = bin0 + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = acc["count"] * {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[acc["type"]]
        return struct.unpack_from(f"<{n}f", raw, off)
    root_t, root_moves = [], []
    root = idx("root")
    for a in gl.get("animations", []):
        for c in a["channels"]:
            if c["target"].get("node") == root and c["target"]["path"] == "translation":
                root_t.append(a["name"])
                vals = floats(a["samplers"][c["sampler"]]["output"])
                if max(abs(v) for v in vals) > 1e-6:
                    root_moves.append(a["name"])
    return {
        "file": path, "size_bytes": size, "size_MB": round(size / 1048576, 3), "under_1MB": size <= 1048576,
        "extensions_used": gl.get("extensionsUsed", []),
        "animations": anims, "animation_names": [a["name"] for a in anims],
        "skin_joint_count": len(joints), "tari_socket_L_in_skin": "tari_socket_L" in joints,
        "tari_socket_R_in_skin": "tari_socket_R" in joints,
        "nodes_present": {"tari_socket_L": socket_L is not None, "tari_socket_R": socket_R is not None,
                          "Tari_Standard": tari is not None},
        "Tari_Standard_parent_node": tari_parent,
        "root_translation_channels": root_t, "root_translation_nonzero": root_moves,
        "materials": [m["name"] for m in gl.get("materials", [])],
        "triangles_in_glb": tri_total,
    }

def export_glb(path, draco):
    obj = bpy.data.objects["Manok_Talisayin"]; ao = bpy.data.objects["ManokRig"]; tari = bpy.data.objects["Tari_Standard"]
    bpy.ops.object.select_all(action='DESELECT')
    for o in (obj, ao, tari):
        o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = ao
    kw = dict(filepath=path, export_format='GLB', use_selection=True,
              export_apply=False, export_yup=True,
              export_texcoords=False, export_normals=True, export_tangents=False,
              export_materials='EXPORT', export_cameras=False, export_lights=False, export_extras=False,
              export_skins=True, export_def_bones=False, export_all_influences=False, export_influence_nb=4,
              export_animations=True, export_animation_mode='ACTIONS', export_frame_range=False,
              export_force_sampling=True, export_frame_step=1, export_optimize_animation_size=True,
              export_anim_single_armature=True, export_reset_pose_bones=True, export_rest_position_armature=True,
              export_morph=False, export_bake_animation=False)
    if draco:
        kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                  export_draco_position_quantization=14, export_draco_normal_quantization=10,
                  export_draco_texcoord_quantization=12, export_draco_generic_quantization=12)
    bpy.ops.export_scene.gltf(**kw)

def render_portraits(ao):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_WORKBENCH'
    sh = scn.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_cavity = True; sh.cavity_type = 'BOTH'
    sh.show_object_outline = True; sh.object_outline_color = (0.05, 0.03, 0.02); sh.show_shadows = False
    scn.display.light_direction = (0.4, -0.5, 0.75)
    scn.render.film_transparent = True
    scn.render.image_settings.file_format = 'PNG'
    scn.render.image_settings.color_mode = 'RGBA'
    scn.render.resolution_x = scn.render.resolution_y = 900
    cam = bpy.data.objects.new("Cam_Portrait", bpy.data.cameras.new("Cam_Portrait"))
    scn.collection.objects.link(cam)
    cam.location = (1.15, -1.55, 0.62)
    cam.rotation_euler = (Vector((0, 0.03, 0.37)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 70
    scn.camera = cam
    use_action(ao, bpy.data.actions["Idle"])
    scn.frame_set(1)
    pdir = os.path.join(OUT, "portraits")
    os.makedirs(pdir, exist_ok=True)
    paths = {}
    for breed, pal in BREED_PALETTES.items():
        set_breed(pal)
        p = os.path.join(pdir, f"portrait_{breed}.png")
        scn.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths[breed] = p
    set_breed(BREED_PALETTES["talisayin"])
    ao.animation_data.action = None
    for pb in ao.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.data.objects.remove(cam)
    return paths

def stage_c():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "manok_v2.blend"))
    scn = bpy.context.scene
    scn.render.fps = FPS
    obj = bpy.data.objects["Manok_Talisayin"]; ao = bpy.data.objects["ManokRig"]
    for o in list(bpy.data.objects):
        if o.name not in ("Manok_Talisayin", "ManokRig", "Tari_Standard"):
            bpy.data.objects.remove(o)
    # export-facing cleanup: no control bones, identity object transforms, no helper attributes
    assert not any(b.name.startswith("CTRL_") for b in ao.data.bones), "control bones left in rig"
    assert len(ao.data.bones) == len(BONES)
    for o in (obj, ao):
        assert o.matrix_world == Matrix(), f"{o.name} has a non-identity transform"
    if obj.data.attributes.get("eye"):
        obj.data.attributes.remove(obj.data.attributes["eye"])
    set_breed(BREED_PALETTES["talisayin"])
    checks = {"pre_export": pre_export_checks(obj, ao)}
    path = os.path.join(OUT, GLB_NAME)
    export_glb(path, draco=False)
    raw = glb_checks(path)
    compression = {"uncompressed_size_bytes": raw["size_bytes"], "draco_available": True, "used": "none"}
    if not raw["under_1MB"]:
        export_glb(path, draco=True)
        compression["used"] = "KHR_draco_mesh_compression"
    compression["meshopt_available"] = False
    compression["note"] = ("Blender's glTF exporter has Draco but no meshopt (EXT_meshopt_compression). "
                           "Draco is only applied when the plain file is over 1 MB.")
    g = glb_checks(path)
    g["compression"] = compression
    g["pass"] = (g["under_1MB"] and all(g["nodes_present"].values()) and g["Tari_Standard_parent_node"] == "tari_socket_L"
                 and not g["root_translation_nonzero"] and len(g["animations"]) == 11
                 and all(a["frame_count"] == LENGTHS[a["name"]] for a in g["animations"]))
    checks["glb"] = g
    checks["all_pass"] = bool(g["pass"] and checks["pre_export"]["root_has_no_location_keys"]["pass"]
                              and all(v["pass"] for v in checks["pre_export"]["loops_first_equals_last"].values())
                              and all(v["pass"] for v in checks["pre_export"]["key_poses"].values())
                              and checks["pre_export"]["mesh"]["pass"])
    json.dump(checks, open(os.path.join(OUT, "stage_C_checks.json"), "w"), indent=1)
    breeds = {b: {m: [round(c, 4) for c in pal[m]] for m in MAT_ORDER} for b, pal in BREED_PALETTES.items()}
    json.dump(breeds, open(os.path.join(OUT, "breeds.json"), "w"), indent=1)
    portraits = render_portraits(ao)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "manok_v2.blend"))
    write_stage_c_page(checks, breeds, portraits)
    print("CHECKS", json.dumps({"all_pass": checks["all_pass"], "size": g["size_bytes"], "anims": g["animation_names"],
                                "nodes": g["nodes_present"], "tari_parent": g["Tari_Standard_parent_node"],
                                "compression": compression["used"]}))
    print("DONE stage C")

def write_stage_c_page(checks, breeds, portraits):
    pe, g = checks["pre_export"], checks["glb"]
    def mark(ok): return '<span class="ok">✔</span>' if ok else '<span class="bad">✘</span>'
    cards = []
    for b, p in portraits.items():
        b64 = base64.b64encode(open(p, "rb").read()).decode()
        sw = "".join(f'<i title="{m}" style="background:rgb({",".join(str(round(255 * (c ** (1 / 2.2)))) for c in breeds[b][m])})"></i>'
                     for m in ("Body_DeepRed", "Hackle_Gold", "WingTip_Green", "Tail_GreenBlack", "Leg_Yellow", "Comb_Red"))
        cards.append(f'<figure><img src="data:image/png;base64,{b64}"><figcaption><b>{b.capitalize()}</b><span class="sw">{sw}</span></figcaption></figure>')
    rows = [
        ("Root bone has no location keys (all actions)", pe["root_has_no_location_keys"]["pass"], "no root location channel in any action"),
        *[(f"Loop {n}: frame {v['first_frame']} = frame {v['last_frame']}", v["pass"], f"max channel diff {v['max_channel_diff']}")
          for n, v in pe["loops_first_equals_last"].items()],
        *[(f"{n} 1–{v['expected_range'][1]}" + (f", keys {v['required_key_frames']}" if v["required_key_frames"] else ""), v["pass"],
           ", ".join(f"{k} {x}" for k, x in v.get("measured", {}).items()) or f"authored keys {v['authored_key_frames']}")
          for n, v in pe["key_poses"].items()],
        (f"≤ 4 weights per vertex", pe["mesh"]["max_influences"] <= 4, f"max {pe['mesh']['max_influences']}"),
        (f"Under 6k triangles", pe["mesh"]["triangles_total"] < 6000, f"{pe['mesh']['triangles_total']}"),
        (f"glb ≤ 1 MB", g["under_1MB"], f"{g['size_bytes']:,} bytes ({g['compression']['used']})"),
        ("tari_socket_L / _R nodes in glb", g["nodes_present"]["tari_socket_L"] and g["nodes_present"]["tari_socket_R"], "both present as skin joints" if g["tari_socket_L_in_skin"] and g["tari_socket_R_in_skin"] else "present"),
        ("Tari_Standard mesh parented to tari_socket_L", g["Tari_Standard_parent_node"] == "tari_socket_L", f"parent node: {g['Tari_Standard_parent_node']}"),
        ("Root never translates in the glb", not g["root_translation_nonzero"], "exporter writes a constant (0,0,0) rest channel per clip; every value is 0" if g["root_translation_channels"] else "no root translation channels"),
    ]
    trs = "".join(f"<tr><td>{mark(ok)}</td><td>{a}</td><td>{d}</td></tr>" for a, ok, d in rows)
    anims = "".join(f"<li><b>{a['name']}</b> · frames {a['first_frame']}–{a['last_frame']}</li>" for a in g["animations"])
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Manok v2 · Stage C</title><style>
body{{margin:0;padding:18px;background:#17110d;color:#f1e6d8;font:14px/1.45 system-ui,Segoe UI,sans-serif}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:15px;margin:22px 0 8px;color:#e8b45a}} p{{color:#a8957f;margin:0 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}}
figure{{margin:0;background:repeating-conic-gradient(#2a201a 0 25%,#221913 0 50%) 0 0/18px 18px;border:1px solid #3a2a20;border-radius:10px;overflow:hidden;opacity:0;animation:in .5s forwards}}
{''.join(f'figure:nth-child({i+1}){{animation-delay:{i*0.07:.2f}s}}' for i in range(7))}
@keyframes in{{from{{opacity:0;transform:scale(.96)}}to{{opacity:1;transform:none}}}}
img{{width:100%;display:block}} figcaption{{background:#221913;padding:6px 8px;display:flex;justify-content:space-between;align-items:center}}
.sw i{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-left:3px;border:1px solid #0006}}
table{{border-collapse:collapse;width:100%;max-width:900px}} td{{padding:5px 10px 5px 0;border-bottom:1px solid #33261d;vertical-align:top}}
td:last-child{{color:#a8957f}} .ok{{color:#7bd389;font-weight:700}} .bad{{color:#ff6b57;font-weight:700}}
ul{{columns:2;max-width:600px;padding-left:18px;margin:0}} .big{{font-size:28px;font-weight:800;color:#e8b45a}}
</style></head><body>
<h1>Manok v2 · Stage C: export</h1>
<p><span class="big">{g['size_bytes'] / 1024:.0f} KB</span> &nbsp;manok.glb · {len(g['animations'])} clips · {g['skin_joint_count']} joints · {g['triangles_in_glb']} triangles · {'all checks pass' if checks['all_pass'] else 'SOME CHECKS FAILED'}</p>
<h2>Breed portraits (Idle, transparent PNG)</h2><div class="grid">{''.join(cards)}</div>
<h2>Checks</h2><table>{trs}</table>
<h2>Animations in manok.glb</h2><ul>{anims}</ul>
</body></html>"""
    open(os.path.join(OUT, "stage_C_preview.html"), "w", encoding="utf-8").write(html)

# ============================================================================= STAGE V: glb round-trip
def evaluated_points(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts

VERIFY_FRAMES = {"Idle": [1, 24, 61], "Walk": [1, 13], "Tuka_Peck": [5, 9], "Sipa_Kick": [11], "Lipad_Jump": [8, 20, 33],
                 "Hit_React": [3], "Hingal_Exhausted": [9], "Talikod_TurnAway": [30], "KO": [40], "Ilag_Dodge": [8],
                 "Banat_Combo": [6, 14, 22]}

def stage_v():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "manok_v2.blend"))
    scn = bpy.context.scene; scn.render.fps = FPS
    ao = bpy.data.objects["ManokRig"]; obj = bpy.data.objects["Manok_Talisayin"]; tari = bpy.data.objects["Tari_Standard"]
    ref = {}
    for clip, frames in VERIFY_FRAMES.items():
        use_action(ao, bpy.data.actions[clip])
        for f in frames:
            scn.frame_set(f)
            ref[(clip, f)] = (evaluated_points(obj), (tari.matrix_world @ Vector((0.06, 0.1, 0.07))).copy(),
                              {b: (ao.matrix_world @ ao.pose.bones[b].tail).copy() for b in ("head", "tarsus_L", "tail_03", "wing_hand_L")})
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, GLB_NAME))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("Manok"))
    tar = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("Tari"))
    if arm.animation_data:
        for t in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(t)
    res = {}
    worst = 0.0
    for clip, frames in VERIFY_FRAMES.items():
        act = bpy.data.actions.get(clip) or next(a for a in bpy.data.actions if a.name.startswith(clip))
        arm.animation_data_create()
        arm.animation_data.action = act
        if act.slots: arm.animation_data.action_slot = act.slots[0]
        for f in frames:
            scn.frame_set(f)
            pts = evaluated_points(mesh)
            kd = KDTree(len(pts))
            for i, p in enumerate(pts): kd.insert(p, i)
            kd.balance()
            rp, rt, rb = ref[(clip, f)]
            dmax = max(kd.find(p)[2] for p in rp[::3])
            bmax = max((arm.matrix_world @ arm.pose.bones[b].tail - v).length for b, v in rb.items())
            tmax = (tar.matrix_world @ Vector((0.06, 0.1, 0.07)) - rt).length
            worst = max(worst, dmax, bmax, tmax)
            res[f"{clip}@{f}"] = {"mesh_max_mm": round(dmax * 1000, 2), "bones_max_mm": round(bmax * 1000, 2),
                                  "tari_mm": round(tmax * 1000, 2)}
    out = {"frames_compared": len(res), "worst_mm": round(worst * 1000, 2), "pass": worst < 0.004, "per_frame": res}
    cp = os.path.join(OUT, "stage_C_checks.json")
    c = json.load(open(cp))
    c["glb_roundtrip"] = out
    c["all_pass"] = bool(c["all_pass"] and out["pass"])
    json.dump(c, open(cp, "w"), indent=1)
    print("ROUNDTRIP", json.dumps({k: out[k] for k in ("frames_compared", "worst_mm", "pass")}))
    print("DONE stage V")

if STAGE == "A":
    stage_a()
elif STAGE == "B":
    stage_b()
elif STAGE == "C":
    stage_c()
elif STAGE == "V":
    stage_v()
