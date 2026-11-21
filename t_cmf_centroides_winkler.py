bl_info = {"name": "CMF Navegação 3D e Centróide", "author": "Dr. Winkler / IA Google", "version": (3, 8), "blender": (4, 2, 0), "location": "View3D > Barra N > Aba Centroide", "category": "Interface"}
import bpy, os, csv, math, mathutils
from bpy_extras.io_utils import ExportHelper

def centro_obj(o):
    if not o: return None
    if o.type == 'MESH' and o.data and len(o.data.vertices) > 0:
        return sum((o.matrix_world @ v.co for v in o.data.vertices), mathutils.Vector()) / len(o.data.vertices)
    return o.matrix_world.to_translation()

def buscar_esf(nome):
    nl, cands = nome.strip().lower(), []
    for o in bpy.data.objects:
        on = o.name.strip().lower()
        if on == nl or on.startswith(nl + "."):
            c = centro_obj(o)
            if c is not None: cands.append((c.length > 0.01, on == nl, o, c))
    if not cands: return None, None
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return cands[0][2], cands[0][3]

def calc_3pts(pd, pe, pa):
    vx, vy = pe - pd, ((pd + pe) / 2.0) - pa
    if vx.length < 1e-4 or vy.length < 1e-4: return None, None
    ey = vy.normalized(); vz = vx.normalized().cross(ey)
    if vz.length < 1e-4: return None, None
    ez = vz.normalized(); ex = ey.cross(ez).normalized()
    return (pd + pe + pa) / 3.0, mathutils.Matrix((ex, ey, ez)).transposed()

def get_tri(sc, arc, fase):
    chaves = ("17", "27", "LMS") if arc == 'MAX' else ("47", "37", "LMI")
    pts = []
    for k in chaves:
        om = sc.objects.get(getattr(sc, f"cmf_esf_{k.lower()}_{fase.lower()}", ""))
        pts.append(centro_obj(om) if om else buscar_esf(f"{k}_{fase}")[1])
    return pts[0], pts[1], pts[2]

def calc_arc(sc, arc):
    pd0, pe0, pa0 = get_tri(sc, arc, "PRE")
    pd1, pe1, pa1 = get_tri(sc, arc, "POS")
    if not (pd0 and pe0 and pa0 and pd1 and pe1 and pa1): return None
    c0, m0 = calc_3pts(pd0, pe0, pa0)
    c1, m1 = calc_3pts(pd1, pe1, pa1)
    if c0 is None or c1 is None: return "ORIGEM"
    ang = (m1 @ m0.transposed()).to_euler('XYZ')
    return c0, c1, (c1 - c0), (math.degrees(ang.x), math.degrees(ang.y), math.degrees(ang.z))

def nav_cor(sc, deps=None):
    if not getattr(sc, "cmf_nav_ativa", False): return
    malha = sc.objects.get(sc.cmf_nav_malha)
    if not malha or malha.type != 'MESH': return
    res = calc_arc(sc, sc.cmf_centroide_arcada)
    if not res or res == "ORIGEM": return
    _, _, dl, (p, r, y) = res
    ok = (dl.length <= sc.cmf_nav_tol_mm) and (max(abs(p), abs(r), abs(y)) <= sc.cmf_nav_tol_deg)
    mat = bpy.data.materials.get("Mat_CMF_Nav") or bpy.data.materials.new("Mat_CMF_Nav")
    mat.use_nodes = False; mat.diffuse_color = (0.05, 0.85, 0.25, 1.0) if ok else (0.90, 0.12, 0.12, 1.0)
    if len(malha.data.materials) == 0: malha.data.materials.append(mat)
    else: malha.data.materials[0] = mat

class CMF_OT_GerarCentroide(bpy.types.Operator):
    bl_idname, bl_label = "cmf.gerar_marcador_centroide", "Mostrar Centróides 3D"
    def execute(self, ctx):
        sc, arc = ctx.scene, ctx.scene.cmf_centroide_arcada
        for fase, cor in [("PRE", (0.1, 0.8, 0.2, 1.0)), ("POS", (0.9, 0.1, 0.1, 1.0))]:
            pd, pe, pa = get_tri(sc, arc, fase)
            if pd and pe and pa:
                c, _ = calc_3pts(pd, pe, pa)
                if c is None: continue
                nm = f"CENTROIDE_{arc}_{fase}"; obj = sc.objects.get(nm)
                if not obj: bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=c); obj = ctx.active_object; obj.name = nm
                else: obj.location = c
                mat = bpy.data.materials.get(f"Mat_{nm}") or bpy.data.materials.new(f"Mat_{nm}"); mat.diffuse_color = cor
                if len(obj.data.materials) == 0: obj.data.materials.append(mat)
                else: obj.data.materials[0] = mat
        return {'FINISHED'}

class CMF_OT_ExportCentroideCSV(bpy.types.Operator, ExportHelper):
    bl_idname, bl_label, filename_ext = "cmf.exportar_centroide_csv", "Exportar Relatório CSV", ".csv"
    filter_glob: bpy.props.StringProperty(default="*.csv", options={'HIDDEN'})
    def invoke(self, ctx, ev):
        bp = bpy.data.filepath; base = os.path.splitext(os.path.basename(bp))[0] if bp else "Relatorio"
        self.filepath = os.path.join(os.path.dirname(bp), f"{base}_Centroide_PRY.csv") if bp else "Relatorio_Centroide_PRY.csv"
        ctx.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, ctx):
        linhas = [["RELATÓRIO DESLOCAMENTO 3D (CENTRÓIDE E PRY)"], ["Arcada", "X (mm)", "Y (mm)", "Z (mm)", "Pitch X (°)", "Roll Y (°)", "Yaw Z (°)"]]
        for arc, nm in [("MAX", "Maxila (17/27/LMS)"), ("MAND", "Mandíbula (47/37/LMI)")]:
            res = calc_arc(ctx.scene, arc)
            if res and res != "ORIGEM":
                _, _, dl, (p, r, y) = res
                linhas.append([nm] + [f"{v:.2f}".replace(".", ",") for v in (dl.x, dl.y, dl.z, p, r, y)])
            else: linhas.append([nm, "N/E", "N/E", "N/E", "N/E", "N/E", "N/E"])
        with open(self.filepath, "w", newline="", encoding="utf-8-sig") as f: csv.writer(f, delimiter=";").writerows(linhas)
        self.report({'INFO'}, f"Salvo: {self.filepath}"); return {'FINISHED'}

class CMF_PT_CentroidePRY(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Auditoria e Navegação 3D", "CMF_PT_centroide_pry", 'VIEW_3D', 'UI', 'Centroide'
    def draw(self, ctx):
        l, sc = self.layout, ctx.scene; l.row(align=True).prop(sc, "cmf_centroide_arcada", expand=True); arc = sc.cmf_centroide_arcada
        res = calc_arc(sc, arc)
        if res is None or res == "ORIGEM":
            b = l.box(); b.label(text="Esferas PRE na origem (0,0,0) ou faltando:", icon='ERROR')
            for k in (("17", "27", "LMS") if arc == 'MAX' else ("47", "37", "LMI")): b.prop_search(sc, f"cmf_esf_{k.lower()}_pre", bpy.data, "objects", text=f"{k}_PRE")
        else:
            c0, c1, dl, (p, r, y) = res
            b1 = l.box(); b1.label(text="Deslocamento Linear (X, Y, Z):", icon='ORIENTATION_GLOBAL')
            b1.label(text=f"X (Médio-Lateral): {dl.x:+.2f} mm"); b1.label(text=f"Y (Ântero-Posterior): {dl.y:+.2f} mm"); b1.label(text=f"Z (Súpero-Inferior): {dl.z:+.2f} mm")
            b2 = l.box(); b2.label(text="Diferença Angular (Pitch, Roll, Yaw):", icon='EMPTY_AXIS')
            b2.label(text=f"Pitch (Eixo X): {p:+.2f}°"); b2.label(text=f"Roll / Cant (Eixo Y): {r:+.2f}°"); b2.label(text=f"Yaw / Axial (Eixo Z): {y:+.2f}°")
            bc = l.box(); bc.label(text="Centróides:", icon='PIVOT_MEDIAN')
            bc.label(text=f"PRE: X {c0.x:.1f} | Y {c0.y:.1f} | Z {c0.z:.1f}"); bc.label(text=f"POS: X {c1.x:.1f} | Y {c1.y:.1f} | Z {c1.z:.1f}")
            bn = l.box(); bn.label(text="Navegação (Cor Alvo):", icon='RESTRICT_COLOR_ON'); bn.prop_search(sc, "cmf_nav_malha", sc, "objects", text="Osso")
            rt = bn.row(align=True); rt.prop(sc, "cmf_nav_tol_mm", text="Tol. mm"); rt.prop(sc, "cmf_nav_tol_deg", text="Tol. °")
            bn.prop(sc, "cmf_nav_ativa", text="Navegação Ativa" if sc.cmf_nav_ativa else "Ligar Alerta de Cor", toggle=True, icon='PLAY')
            l.operator("cmf.gerar_marcador_centroide", text=f"Desenhar Centróides ({arc})", icon='SPHERE')
        l.separator(); l.operator("cmf.exportar_centroide_csv", text="Exportar Relatório CSV", icon='EXPORT')

ESF_PROPS = [f"cmf_esf_{k}_{f}" for k in ("17", "27", "lms", "47", "37", "lmi") for f in ("pre", "pos")]
def register():
    bpy.types.Scene.cmf_centroide_arcada = bpy.props.EnumProperty(items=[('MAX', "Maxila (17/27/LMS)", ""), ('MAND', "Mandíbula (47/37/LMI)", "")], default='MAX')
    bpy.types.Scene.cmf_nav_malha = bpy.props.StringProperty()
    bpy.types.Scene.cmf_nav_tol_mm = bpy.props.FloatProperty(default=0.5, min=0.05, max=10.0)
    bpy.types.Scene.cmf_nav_tol_deg = bpy.props.FloatProperty(default=1.0, min=0.1, max=15.0)
    bpy.types.Scene.cmf_nav_ativa = bpy.props.BoolProperty(default=False, update=nav_cor)
    for p in ESF_PROPS: setattr(bpy.types.Scene, p, bpy.props.StringProperty())
    for c in (CMF_OT_GerarCentroide, CMF_OT_ExportCentroideCSV, CMF_PT_CentroidePRY): bpy.utils.register_class(c)
    if nav_cor not in bpy.app.handlers.depsgraph_update_post: bpy.app.handlers.depsgraph_update_post.append(nav_cor)

def unregister():
    if nav_cor in bpy.app.handlers.depsgraph_update_post: bpy.app.handlers.depsgraph_update_post.remove(nav_cor)
    for c in (CMF_OT_GerarCentroide, CMF_OT_ExportCentroideCSV, CMF_PT_CentroidePRY): bpy.utils.unregister_class(c)
    for k in ["cmf_centroide_arcada", "cmf_nav_malha", "cmf_nav_tol_mm", "cmf_nav_tol_deg", "cmf_nav_ativa"] + ESF_PROPS:
        if hasattr(bpy.types.Scene, k): delattr(bpy.types.Scene, k)

if __name__ == "__main__": register()