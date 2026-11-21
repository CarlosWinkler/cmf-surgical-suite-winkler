l_info = {"name": "CMF Movimento Reverso (Guias 3D)", "author": "Dr. Winkler / IA Google", "version": (2, 5), "blender": (4, 2, 0), "location": "View3D > Barra N > Aba Mov. Reverso", "category": "Interface"}
import bpy, mathutils, numpy as np

PARES = [
    ("MX_POS", ["SEG_MX_PRE", "MX_PRE", "CR"]), ("MXD_POS", ["SEG_MXD_PRE", "MXD_PRE", "CR"]),
    ("MXM_POS", ["SEG_MXM_PRE", "MXM_PRE", "CR"]), ("MXE_POS", ["SEG_MXE_PRE", "MXE_PRE", "CR"]),
    ("MD_POS", ["SEG_MD_PRE", "MD_PRE", "MD"]), ("MD_MENTO", ["SEG_MD_MENTO_PRE", "MD_MENTO_PRE", "MENTO_PRE", "MD"]),
    ("MENTO", ["MENTO_PRE", "MD_MENTO_PRE", "MD"]), ("RMD_POS", ["SEG_RMD_PRE", "RMD_PRE", "MD"]),
    ("RME_POS", ["SEG_RME_PRE", "RME_PRE", "MD"]),
]
_cache_pos = {}

def get_o(nome, priorizar_pre=False):
    nl = nome.strip().lower()
    if priorizar_pre:
        col_pre = next((c for c in bpy.data.collections if "pre" in c.name.lower()), None)
        if col_pre:
            for o in col_pre.all_objects:
                if o.name.strip().lower() == nl: return o
    for o in bpy.data.objects:
        if o.name.strip().lower() == nl: return o
    return None

def prof_hier(par):
    o, _ = par
    d, p = 0, o.parent
    while p: d += 1; p = p.parent
    return d

def mat_svd(om, oa):
    if om.type != 'MESH' or oa.type != 'MESH': return None
    vm, va = om.data.vertices, oa.data.vertices
    if len(vm) < 4 or len(vm) != len(va): return None
    ps = max(1, len(vm) // 2500); idxs = range(0, len(vm), ps)
    mwm, mwa = om.matrix_world, oa.matrix_world
    P = np.array([mwm @ vm[i].co for i in idxs], dtype=np.float64)
    Q = np.array([mwa @ va[i].co for i in idxs], dtype=np.float64)
    cp, cq = P.mean(axis=0), Q.mean(axis=0)
    H = (P - cp).T @ (Q - cq); U, _, Vt = np.linalg.svd(H); R = Vt.T @ U.T
    if np.linalg.det(R) < 0: Vt[2, :] *= -1; R = Vt.T @ U.T
    t = cq - (R @ cp)
    r0, r1, r2 = R.tolist()
    tx, ty, tz = t.tolist()
    return mathutils.Matrix([r0 + [tx], r1 + [ty], r2 + [tz], [0.0, 0.0, 0.0, 1.0]])

class CMF_OT_RevPre(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.reverter_planejamento_pre", "Reverter para Posição PRE", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        sc = ctx.scene
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        enc = []
        for np_, lpre in PARES:
            op = get_o(np_, False)
            if op:
                opr = next((get_o(n, True) for n in lpre if get_o(n, True) and get_o(n, True) != op), None)
                enc.append((op, opr))
        if not enc: self.report({'ERROR'}, "Nenhum segmento POS encontrado!"); return {'CANCELLED'}
        enc.sort(key=prof_hier)
        rev = 0
        for op, opr in enc:
            if op.name not in _cache_pos: _cache_pos[op.name] = op.matrix_world.copy()
            ctx.view_layer.update()
            if opr:
                md = mat_svd(op, opr)
                if md:
                    op.matrix_world = md @ op.matrix_world
                    ctx.view_layer.update()
                    rev += 1
        sc.cmf_rev_status = f"Revertido! ({rev} segmentos sobrepostos ao PRE)"; return {'FINISHED'}

class CMF_OT_RestPos(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.restaurar_planejamento_pos", "Voltar para POS (Planejado)", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        sc = ctx.scene
        if not _cache_pos: self.report({'WARNING'}, "Nenhuma posição POS na memória."); return {'CANCELLED'}
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        ords = sorted([(get_o(n, False), m) for n, m in _cache_pos.items() if get_o(n, False)], key=prof_hier)
        for o, m in ords:
            o.matrix_world = m.copy()
            ctx.view_layer.update()
        _cache_pos.clear(); sc.cmf_rev_status = f"Restaurado! ({len(ords)} segmentos no POS)"; return {'FINISHED'}

class CMF_PT_RevPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Movimento Reverso (Guias 3D)", "CMF_PT_movimento_reverso_panel", 'VIEW_3D', 'UI', 'Mov. Reverso'
    def draw(self, ctx):
        l, sc = self.layout, ctx.scene; b = l.box(); b.label(text="Transferência de Guias (POS -> PRE):", icon='TRACKING_BACKWARDS')
        b.label(text="Alvos: MX, MXD/M/E, MD, MENTO, RMD/E")
        l.operator("cmf.reverter_planejamento_pre", text="1. Reverter Tudo para PRE", icon='LOOP_BACK')
        l.operator("cmf.restaurar_planejamento_pos", text="2. Voltar para POS (Planejado)", icon='LOOP_FORWARDS')
        if sc.cmf_rev_status: l.box().label(text=sc.cmf_rev_status, icon='CHECKMARK')

CLS = (CMF_OT_RevPre, CMF_OT_RestPos, CMF_PT_RevPanel)
def register():
    bpy.types.Scene.cmf_rev_status = bpy.props.StringProperty(default="")
    for c in CLS:
        try: bpy.utils.unregister_class(c)
        except: pass
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(CLS):
        try: bpy.utils.unregister_class(c)
        except: pass
    if hasattr(bpy.types.Scene, "cmf_rev_status"): delattr(bpy.types.Scene, "cmf_rev_status")

if __name__ == "__main__":
    register()