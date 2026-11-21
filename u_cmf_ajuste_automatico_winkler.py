bl_info = {"name": "CMF Ajuste Automático", "author": "Dr. Winkler / IA Google", "version": (2, 5), "blender": (4, 2, 0), "location": "View3D > Barra N > Aba CMF Angular", "category": "Interface"}
import bpy, math, mathutils

def get_o(sc, n): return next((o for o in sc.objects if o.name.lower() == n.lower()), None)
def pos(o): return o.matrix_world.to_translation()

def biss(sc, p1a, p2a, p1b, p2b):
    o1a, o2a, o1b, o2b = (get_o(sc, n) for n in (p1a, p2a, p1b, p2b))
    if not all((o1a, o2a, o1b, o2b)): return None
    vm = (pos(o2a) - pos(o1a)).normalized() + (pos(o2b) - pos(o1b)).normalized()
    return vm.normalized() if vm.length > 0 else None

def ext_ln(o):
    mw = o.matrix_world
    if o.type == 'MESH' and o.data and len(o.data.vertices) >= 2:
        pts = [mw @ v.co for v in o.data.vertices]
        pr = next(iter(pts))
        p1 = max(pts, key=lambda p: (p - pr).length)
        return p1, max(pts, key=lambda p: (p - p1).length)
    if o.type == 'CURVE' and o.data and o.data.splines:
        sp = next(iter(o.data.splines))
        if len(sp.points) >= 2:
            pi, *_, pf = sp.points
            return mw @ pi.co.xyz, mw @ pf.co.xyz
        if len(sp.bezier_points) >= 2:
            pi, *_, pf = sp.bezier_points
            return mw @ pi.co, mw @ pf.co
    return None, None

def ler_medida(sc, alvo):
    os_, on_ = get_o(sc, "S"), get_o(sc, "N")
    oa, ob, opg = get_o(sc, "A_POS"), get_o(sc, "B_POS"), get_o(sc, "Pg_POS")
    onp, opla = get_o(sc, "NPerp"), get_o(sc, "PLA")
    v_fr = biss(sc, "Po_Dir", "Or_Dir", "Po_Esq", "Or_Esq")
    agudo = lambda v1, v2: 180.0 - math.degrees(v1.angle(v2)) if math.degrees(v1.angle(v2)) > 90.0 else math.degrees(v1.angle(v2))
    ang3 = lambda o1, o2, o3: math.degrees((pos(o1) - pos(o2)).normalized().angle((pos(o3) - pos(o2)).normalized()))

    if alvo == "SNA" and all((os_, on_, oa)): return ang3(os_, on_, oa)
    if alvo == "SNB" and all((os_, on_, ob)): return ang3(os_, on_, ob)
    if alvo == "FNP" and all((v_fr, on_, opg)): return agudo(v_fr, (pos(opg) - pos(on_)).normalized())
    if alvo == "FMA":
        v_md = biss(sc, "GoDir_POS", "Gn_POS", "GoEsq_POS", "Gn_POS")
        if v_fr and v_md: return agudo(v_fr, v_md)
    if alvo in ("A_NPerp", "Pg_NPerp") and onp and v_fr:
        pt_o = oa if alvo == "A_NPerp" else opg
        p1, p2 = ext_ln(onp)
        if pt_o and p1 and p2:
            proj, _ = mathutils.geometry.intersect_point_line(pos(pt_o), p1, p2)
            vet = pos(pt_o) - proj
            return -vet.length if vet.dot(v_fr) < 0 else vet.length
    if alvo == "Plo_PLA" and opla:
        o17, o27, olms = get_o(sc, "17_POS"), get_o(sc, "27_POS"), get_o(sc, "LMS_POS")
        p1_pla, p2_pla = ext_ln(opla)
        if all((o17, o27, olms, p1_pla, p2_pla)):
            m_post = (pos(o17) + pos(o27)) * 0.5
            v_med = pos(olms) - m_post
            v_pla = p2_pla - p1_pla
            v_med_sag = mathutils.Vector((0.0, v_med.y, v_med.z))
            v_pla_sag = mathutils.Vector((0.0, v_pla.y, v_pla.z))
            if v_med_sag.length > 1e-5 and v_pla_sag.length > 1e-5:
                return agudo(v_med_sag.normalized(), v_pla_sag.normalized())
    return None

class CMF_OT_CorrigirUnica(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.corrigir_medida_unica", "Corrigir Medida", {'REGISTER', 'UNDO'}
    medida: bpy.props.StringProperty()

    def execute(self, ctx):
        sc = ctx.scene
        mx = get_o(sc, "MX_POS")
        lms = get_o(sc, "LMS_POS")
        v_fr = biss(sc, "Po_Dir", "Or_Dir", "Po_Esq", "Or_Esq")
        sexo = getattr(sc, "cmf_paciente_sexo", "H")
        alvos = {"SNA": 82.0, "SNB": 80.0, "FNP": 87.0, "FMA": 25.0, "A_NPerp": 1.0, "Pg_NPerp": 0.0 if sexo == 'H' else -2.0, "Plo_PLA": 6.5}
        alvo_val = alvos.get(self.medida)

        val_ini = ler_medida(sc, self.medida)
        if val_ini is None or not mx or not v_fr:
            self.report({'ERROR'}, f"Falta MX_POS ou pontos para {self.medida}!"); return {'CANCELLED'}

        eixo_x = mathutils.Vector((1.0, 0.0, 0.0))
        dir_y = v_fr.normalized()
        pivo_rot = pos(lms) if lms else pos(mx)

        for _ in range(30):
            ctx.view_layer.update()
            atual = ler_medida(sc, self.medida)
            erro = alvo_val - atual
            if abs(erro) < 0.02: break

            if self.medida in ("Plo_PLA", "FMA"):
                mat_d = mathutils.Matrix.Translation(pivo_rot) @ mathutils.Matrix.Rotation(math.radians(erro * 0.5), 4, eixo_x) @ mathutils.Matrix.Translation(-pivo_rot)
                mx.matrix_world = mat_d @ mx.matrix_world; ctx.view_layer.update()
                if abs(alvo_val - ler_medida(sc, self.medida)) > abs(erro):
                    mat_inv = mathutils.Matrix.Translation(pivo_rot) @ mathutils.Matrix.Rotation(math.radians(-erro), 4, eixo_x) @ mathutils.Matrix.Translation(-pivo_rot)
                    mx.matrix_world = mat_inv @ mx.matrix_world
            else:
                fator = 0.6 if self.medida in ("A_NPerp", "Pg_NPerp") else 1.2
                passo = erro * fator
                mx.matrix_world.translation += dir_y * passo; ctx.view_layer.update()
                if abs(alvo_val - ler_medida(sc, self.medida)) > abs(erro):
                    mx.matrix_world.translation -= dir_y * passo * 2.0

        ctx.view_layer.update()
        self.report({'INFO'}, f"{self.medida} ajustado para {ler_medida(sc, self.medida):.2f}!"); return {'FINISHED'}

class CMF_PT_AutoCorrigirPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "CMF Ajuste Automático", "CMF_PT_auto_corrigir_panel", 'VIEW_3D', 'UI', 'CMF Angular'
    def draw(self, ctx):
        l = self.layout
        b_mx = l.box(); b_mx.label(text="Referências Maxilares:", icon='MESH_DATA')
        for m, txt in [("Plo_PLA", "Plo . PLA (6.5°)"), ("SNA", "SNA (82°)"), ("A_NPerp", "A-NPerp (+1.0mm)")]:
            b_mx.operator("cmf.corrigir_medida_unica", text=f"Corrigir {txt}", icon='PLAY').medida = m
        b_md = l.box(); b_md.label(text="Referências Mandibulares (Move Bloco):", icon='LINKED')
        for m, txt in [("FMA", "FMA (25°)"), ("SNB", "SNB (80°)"), ("FNP", "FNP (87°)"), ("Pg_NPerp", "Pg-NPerp (0 / -2mm)")]:
            b_md.operator("cmf.corrigir_medida_unica", text=f"Corrigir {txt}", icon='PLAY').medida = m

def register():
    for c in (CMF_OT_CorrigirUnica, CMF_PT_AutoCorrigirPanel):
        try: bpy.utils.unregister_class(c)
        except: pass
        bpy.utils.register_class(c)

def unregister():
    for c in (CMF_OT_CorrigirUnica, CMF_PT_AutoCorrigirPanel):
        try: bpy.utils.unregister_class(c)
        except: pass

if __name__ == "__main__": register()