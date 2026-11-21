bl_info = {"name": "Cefalometria Angular 3D Winkler", "author": "Carlos J. Winkler / IA Google", "version": (4, 6), "blender": (4, 2, 0), "location": "View3D > Barra N > Aba CMF Angular", "category": "Interface"}
import bpy, os, csv, math, mathutils

TAB_CEF = [
    ("0-SNA", "graus", "PRE", ("S", "N", "A_PRE")), ("0-SNB", "graus", "PRE", ("S", "N", "B_PRE")), ("0-ANB", "graus", "PRE", ("A_PRE", "N", "B_PRE")),
    ("0-FNP", "fk_ln", "PRE", ("N", "Pg_PRE")), ("0-FMA", "fk_md", "PRE", ("PRE",)), ("0-A-NPerp", "mm", "PRE", ("A_PRE", "NPerp")),
    ("0-SN-Go-Me", "sn_md", "PRE", ("PRE",)), ("0-Pg-NPerp", "mm", "PRE", ("Pg_PRE", "NPerp")), ("0-N-ENA", "mm", "PRE", ("N", "ENA_PRE")),
    ("0-Me-ENA", "mm", "PRE", ("Me_PRE", "ENA_PRE")), ("0-N-Me", "mm", "PRE", ("N", "Me_PRE")), ("1-Co-A", "mm", "PRE", ("Co", "A_PRE")),
    ("1-Co-Gn", "mm", "PRE", ("Co", "Gn_PRE")), ("0-Frankfurt . Plo", "fk_plo", "PRE", ("PRE",)), ("0-Plo . PLA", "plo_pla", "PRE", ("PRE",)),
    ("1-SNA", "graus", "POS", ("S", "N", "A_POS")), ("1-SNB", "graus", "POS", ("S", "N", "B_POS")), ("1-ANB", "graus", "POS", ("A_POS", "N", "B_POS")),
    ("1-FNP", "fk_ln", "POS", ("N", "Pg_POS")), ("1-FMA", "fk_md", "POS", ("POS",)), ("1-SN-Go-Me", "sn_md", "POS", ("POS",)),
    ("1-A-NPerp", "mm", "POS", ("A_POS", "NPerp")), ("1-Pg-NPerp", "mm", "POS", ("Pg_POS", "NPerp")), ("1-N-ENA", "mm", "POS", ("N", "ENA_POS")),
    ("1-Me-ENA", "mm", "POS", ("Me_POS", "ENA_POS")), ("1-N-Me", "mm", "POS", ("N", "Me_POS")), ("1-Co-A", "mm", "POS", ("Co", "A_POS")),
    ("1-Co-Gn", "mm", "POS", ("Co", "Gn_POS")), ("1-Frankfurt . Plo", "fk_plo", "POS", ("POS",)), ("1-Plo . PLA", "plo_pla", "POS", ("POS",)),
]

TAB_MC = {
    80: ((97, 100), (57, 58)), 81: ((99, 102), (57, 58)), 82: ((101, 104), (58, 59)), 83: ((103, 106), (58, 59)), 84: ((104, 107), (59, 60)),
    85: ((105, 108), (60, 62)), 86: ((107, 110), (60, 62)), 87: ((109, 112), (61, 63)), 88: ((111, 114), (61, 63)), 89: ((112, 115), (62, 64)),
    90: ((113, 116), (63, 64)), 91: ((115, 118), (63, 64)), 92: ((117, 120), (64, 65)), 93: ((119, 122), (65, 66)), 94: ((121, 124), (66, 67)),
    95: ((122, 125), (67, 69)), 96: ((124, 127), (67, 69)), 97: ((126, 129), (68, 70)), 98: ((128, 131), (68, 70)), 99: ((129, 132), (69, 71)),
    100: ((130, 133), (70, 74)), 101: ((132, 135), (71, 75)), 102: ((134, 137), (72, 76)), 103: ((136, 139), (73, 77)), 104: ((137, 140), (74, 78)), 105: ((138, 141), (75, 79)),
}

def get_o(sc, n): return next((o for o in sc.objects if o.name.lower() == n.lower()), None)
def pos(o): return o.matrix_world.to_translation()

def ext_ln(o):
    mw = o.matrix_world
    if o.type == 'MESH' and o.data and len(o.data.vertices) >= 2:
        pts = [mw @ v.co for v in o.data.vertices]; pr = next(iter(pts)); p1 = max(pts, key=lambda p: (p - pr).length)
        return p1, max(pts, key=lambda p: (p - p1).length)
    if o.type == 'CURVE' and o.data and o.data.splines:
        sp = next(iter(o.data.splines))
        if len(sp.points) >= 2: pi, *_, pf = sp.points; return mw @ pi.co.xyz, mw @ pf.co.xyz
        if len(sp.bezier_points) >= 2: pi, *_, pf = sp.bezier_points; return mw @ pi.co, mw @ pf.co
    return None, None

def biss(sc, p1a, p2a, p1b, p2b):
    o1a, o2a, o1b, o2b = (get_o(sc, n) for n in (p1a, p2a, p1b, p2b))
    falt = [n for n, o in zip((p1a, p2a, p1b, p2b), (o1a, o2a, o1b, o2b)) if not o]
    if falt: return None, list(dict.fromkeys(falt))
    vm = (pos(o2a) - pos(o1a)).normalized() + (pos(o2b) - pos(o1b)).normalized()
    return (vm.normalized() if vm.length > 0 else None), []

def dist_np(sc, pt, obj_r):
    p1, p2 = ext_ln(obj_r)
    if p1 and p2 and (p2 - p1).length > 1e-5:
        proj, _ = mathutils.geometry.intersect_point_line(pt, p1, p2); vet = pt - proj; d = vet.length
        v_fr, _ = biss(sc, "Po_Dir", "Or_Dir", "Po_Esq", "Or_Esq")
        return -d if (v_fr and vet.dot(v_fr) < 0) else d
    return (pt - pos(obj_r)).length

def ang_ag(v1, v2): a = math.degrees(v1.angle(v2)); return 180.0 - a if a > 90.0 else a

def calc_num(sc, desc, tipo, fase, pts):
    try:
        if tipo == "plo_pla":
            (suf,) = pts
            o17, o27, olms, opla = get_o(sc, f"17_{suf}"), get_o(sc, f"27_{suf}"), get_o(sc, f"LMS_{suf}"), get_o(sc, "PLA")
            falt = [n for n, o in zip((f"17_{suf}", f"27_{suf}", f"LMS_{suf}", "PLA"), (o17, o27, olms, opla)) if not o]
            if falt: return None, f"Falta: {', '.join(falt)}"
            p1_pla, p2_pla = ext_ln(opla)
            if not (p1_pla and p2_pla): return None, "Erro PLA"
            v_med = pos(olms) - ((pos(o17) + pos(o27)) * 0.5)
            v_pla = p2_pla - p1_pla
            vm_s = mathutils.Vector((0.0, v_med.y, v_med.z))
            vp_s = mathutils.Vector((0.0, v_pla.y, v_pla.z))
            return (ang_ag(vm_s.normalized(), vp_s.normalized()), "") if (vm_s.length > 1e-5 and vp_s.length > 1e-5) else (0.0, "")
        if tipo in ("fk_plo", "fk_ln", "fk_md"):
            v_fr, falt = biss(sc, "Po_Dir", "Or_Dir", "Po_Esq", "Or_Esq")
            if tipo == "fk_plo": (suf,) = pts; v2, f2 = biss(sc, f"17_{suf}", f"LMS_{suf}", f"27_{suf}", f"LMS_{suf}")
            elif tipo == "fk_md": (suf,) = pts; v2, f2 = biss(sc, f"GoDir_{suf}", f"Gn_{suf}", f"GoEsq_{suf}", f"Gn_{suf}")
            else: n1, n2 = pts; o1, o2 = get_o(sc, n1), get_o(sc, n2); f2 = [n for n, o in zip(pts, (o1, o2)) if not o]; v2 = (pos(o2) - pos(o1)).normalized() if not f2 else None
            falt = list(dict.fromkeys(falt + f2))
            if falt: return None, f"Falta: {', '.join(falt)}"
            return (ang_ag(v_fr, v2), "") if (v_fr and v2 and v2.length > 0) else (None, "Erro")
        if tipo == "sn_md":
            (suf,) = pts; os_, on_ = get_o(sc, "S"), get_o(sc, "N"); v_md, f_md = biss(sc, f"GoDir_{suf}", f"Me_{suf}", f"GoEsq_{suf}", f"Me_{suf}")
            falt = list(dict.fromkeys([n for n, o in (("S", os_), ("N", on_)) if not o] + f_md))
            if falt: return None, f"Falta: {', '.join(falt)}"
            v_sn = (pos(on_) - pos(os_)).normalized()
            return (ang_ag(v_sn, v_md), "") if (v_sn.length > 0 and v_md) else (None, "Erro")
        if tipo == "mm":
            n1, n2 = pts; o1, o2 = get_o(sc, n1), get_o(sc, n2); falt = [n for n, o in zip(pts, (o1, o2)) if not o]
            if falt: return None, f"Falta: {', '.join(falt)}"
            return (dist_np(sc, pos(o1), o2), "") if n2.lower() == "nperp" else ((pos(o1) - pos(o2)).length, "")
        n1, n2, n3 = pts; o1, o2, o3 = get_o(sc, n1), get_o(sc, n2), get_o(sc, n3); falt = [n for n, o in zip(pts, (o1, o2, o3)) if not o]
        if falt: return None, f"Falta: {', '.join(falt)}"
        return math.degrees((pos(o1) - pos(o2)).normalized().angle((pos(o3) - pos(o2)).normalized())), ""
    except: return None, "Erro"
    try:
        if tipo in ("fk_plo", "fk_ln", "fk_md", "fk_pla"):
            v_fr, falt = biss(sc, "Po_Dir", "Or_Dir", "Po_Esq", "Or_Esq")
            if tipo == "fk_plo": (suf,) = pts; v2, f2 = biss(sc, f"17_{suf}", f"LMS_{suf}", f"27_{suf}", f"LMS_{suf}")
            elif tipo == "fk_md": (suf,) = pts; v2, f2 = biss(sc, f"GoDir_{suf}", f"Gn_{suf}", f"GoEsq_{suf}", f"Gn_{suf}")
            elif tipo == "fk_pla":
                opla = get_o(sc, "PLA"); f2 = ["PLA"] if not opla else []
                if opla and opla.type == 'MESH' and len(opla.data.polygons) > 0:
                    n_pla = (opla.matrix_world.to_3x3() @ opla.data.polygons[0].normal).normalized()
                    v_proj = v_fr - v_fr.dot(n_pla) * n_pla
                    if falt: return None, f"Falta: {', '.join(falt)}"
                    return (ang_ag(v_fr, v_proj.normalized()), "") if (v_fr and v_proj.length > 1e-5) else (0.0, "")
                v2 = (opla.matrix_world.to_3x3() @ mathutils.Vector((0.0, 1.0, 0.0))).normalized() if opla else None
            else: n1, n2 = pts; o1, o2 = get_o(sc, n1), get_o(sc, n2); f2 = [n for n, o in zip(pts, (o1, o2)) if not o]; v2 = (pos(o2) - pos(o1)).normalized() if not f2 else None
            falt = list(dict.fromkeys(falt + f2))
            if falt: return None, f"Falta: {', '.join(falt)}"
            return (ang_ag(v_fr, v2), "") if (v_fr and v2 and v2.length > 0) else (None, "Erro")
        if tipo == "sn_md":
            (suf,) = pts; os_, on_ = get_o(sc, "S"), get_o(sc, "N"); v_md, f_md = biss(sc, f"GoDir_{suf}", f"Me_{suf}", f"GoEsq_{suf}", f"Me_{suf}")
            falt = list(dict.fromkeys([n for n, o in (("S", os_), ("N", on_)) if not o] + f_md))
            if falt: return None, f"Falta: {', '.join(falt)}"
            v_sn = (pos(on_) - pos(os_)).normalized()
            return (ang_ag(v_sn, v_md), "") if (v_sn.length > 0 and v_md) else (None, "Erro")
        if tipo == "mm":
            n1, n2 = pts; o1, o2 = get_o(sc, n1), get_o(sc, n2); falt = [n for n, o in zip(pts, (o1, o2)) if not o]
            if falt: return None, f"Falta: {', '.join(falt)}"
            return (dist_np(sc, pos(o1), o2), "") if n2.lower() == "nperp" else ((pos(o1) - pos(o2)).length, "")
        n1, n2, n3 = pts; o1, o2, o3 = get_o(sc, n1), get_o(sc, n2), get_o(sc, n3); falt = [n for n, o in zip(pts, (o1, o2, o3)) if not o]
        if falt: return None, f"Falta: {', '.join(falt)}"
        return math.degrees((pos(o1) - pos(o2)).normalized().angle((pos(o3) - pos(o2)).normalized())), ""
    except: return None, "Erro"

def av_diag(sc, desc, fase, val):
    if val is None: return "-"
    sx = sc.cmf_paciente_sexo; pr = "h " if sx == 'H' else "m "
    nm = {"SNA": (82.0, 2.0, 0), "SNB": (80.0, 2.0, 0), "ANB": (2.0, 2.0, 0), "FNP": (87.0, 3.0, 0), "FMA": (25.0, 5.0, 0), "SN-Go-Me": (32.0, 4.0, 0), "A-NPerp": (1.0, 1.0, 0), "Pg-NPerp": (0.0, 2.0, 1) if sx == 'H' else (-2.0, 2.0, 1), "Frankfurt . Plo": (8.0, 4.0, 0)}
    _, ch = desc.split("-", 1) if "-" in desc else ("", desc)
    if ch in nm:
        md, dv, vs = nm[ch]; p = pr if vs else ""
        if (md - dv) <= val <= (md + dv): return f"{p}OK"
        df = md - val; return f"{p}Aumentar {abs(df):.2f}" if df > 0 else f"{p}Diminuir {abs(df):.2f}"
    if ch in ("Co-Gn", "Me-ENA"):
        coa, _ = calc_num(sc, f"{fase}-Co-A", "mm", fase, ("Co", f"A_{fase}"))
        if coa is not None:
            fc, fa = TAB_MC[max(80, min(105, round(coa)))]; vmin, vmax = fc if ch == "Co-Gn" else fa
            if vmin <= val <= vmax: return "OK"
            df = ((vmin + vmax) / 2.0) - val; return f"Aumentar {abs(df):.2f}" if df > 0 else f"Diminuir {abs(df):.2f}"
    return "-"

class CEF_PT_AngularPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "CEFALOMETRIA ANGULAR", "CEF_PT_angular_winkler_panel", 'VIEW_3D', 'UI', 'CMF Angular'
    def draw(self, ctx):
        l, sc = self.layout, ctx.scene; l.row(align=True).prop(sc, "cmf_paciente_sexo", expand=True); l.operator("cmf.export_angular_csv", text="Exportar Tabelas Unificadas", icon='EXPORT'); fat = ""
        for desc, tipo, fase, pts in TAB_CEF:
            if fase != fat: fat = fase; l.separator(); l.box().label(text=f"ANÁLISE CEFALOMÉTRICA {fase}", icon='PREFERENCES'); r = l.row(); r.label(text="Referência"); r.label(text="Obtido"); r.label(text="Conduta")
            vn, em = calc_num(sc, desc, tipo, fase, pts); r = l.row(); r.label(text=desc); r.label(text=f"{vn:.2f}" if vn is not None else em, icon='CHECKMARK' if vn is not None else 'INFO'); r.label(text=av_diag(sc, desc, fase, vn))

class CMF_OT_ExportAngularCSV(bpy.types.Operator):
    bl_idname, bl_label = "cmf.export_angular_csv", "Exportar Planilha Cefalometria Angular"
    def execute(self, ctx):
        sc = ctx.scene; pasta = r"C:\CMF_Library"; os.makedirs(pasta, exist_ok=True); arq = os.path.join(pasta, "Analise_Cefalometrica_Angular_Winkler.csv")
        try:
            with open(arq, mode='w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f, delimiter=';'); w.writerow(["Sexo:", "Homem (h)" if sc.cmf_paciente_sexo == 'H' else "Mulher (m)"]); fat = ""
                for desc, tipo, fase, pts in TAB_CEF:
                    if fase != fat: fat = fase; w.writerows([[], [f"ANÁLISE CEFALOMÉTRICA {fase}"], ["Referência", "Unidades", "Obtido", "Conduta"]])
                    vn, em = calc_num(sc, desc, tipo, fase, pts); w.writerow([desc, "mm" if tipo == "mm" else "graus", f"{vn:.2f}".replace('.', ',') if vn is not None else em, av_diag(sc, desc, fase, vn).replace('.', ',')])
            self.report({'INFO'}, f"Exportado: {arq}"); os.startfile(pasta)
        except Exception as e: self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        return {'FINISHED'}

def register():
    bpy.types.Scene.cmf_paciente_sexo = bpy.props.EnumProperty(
        items=[('H', "Homem (h)", ""), ('M', "Mulher (m)", "")],
        default='H'
    )
    for c in (CEF_PT_AngularPanel, CMF_OT_ExportAngularCSV):
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
        bpy.utils.register_class(c)

def unregister():
    for c in (CEF_PT_AngularPanel, CMF_OT_ExportAngularCSV):
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
    if hasattr(bpy.types.Scene, "cmf_paciente_sexo"):
        delattr(bpy.types.Scene, "cmf_paciente_sexo")

if __name__ == "__main__":
    register()