bl_info = {"name": "CMF Alinhamento 3D (Pontos + ICP)", "author": "Dr. Winkler / IA Google", "version": (1, 2), "blender": (4, 2, 0), "location": "View3D > Barra Lateral (N) > Aba Tool", "category": "Interface"}
import bpy, gpu, mathutils, numpy as np
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils

_pts_a, _pts_m, _handle = [], [], None

def draw_pts():
    if not _pts_a and not _pts_m: return
    try:
        sh = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.point_size_set(12.0); gpu.state.blend_set('ALPHA')
        for pts, col in [(_pts_a, (0.1, 0.4, 1.0, 1.0)), (_pts_m, (1.0, 0.15, 0.15, 1.0))]:
            if pts:
                b = batch_for_shader(sh, 'POINTS', {"pos": [tuple(p) for p in pts]})
                sh.bind(); sh.uniform_float("color", col); b.draw(sh)
        gpu.state.point_size_set(1.0); gpu.state.blend_set('NONE')
    except: pass

def calc_svd(pm_list, pa_list):
    P = np.array([[v.x, v.y, v.z] for v in pm_list], dtype=np.float64)
    Q = np.array([[v.x, v.y, v.z] for v in pa_list], dtype=np.float64)
    cm, ca = P.mean(axis=0), Q.mean(axis=0)
    H = (P - cm).T @ (Q - ca)
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0.0:
        Vt[2, :] *= -1.0
        R = Vt.T @ U.T
    t = ca - R @ cm
    M = mathutils.Matrix(((R[0,0], R[0,1], R[0,2], t[0]), (R[1,0], R[1,1], R[1,2], t[1]), (R[2,0], R[2,1], R[2,2], t[2]), (0.0, 0.0, 0.0, 1.0)))
    return M

def calc_rms(a, b):
    return (sum((x - y).length_squared for x, y in zip(a, b)) / len(a)) ** 0.5 if a else 0.0

class CMF_OT_MarcarModal(bpy.types.Operator):
    bl_idname, bl_label = "cmf.marcar_pontos_modal", "Marcar Pontos"
    modo: bpy.props.StringProperty(default="ALVO")
    def modal(self, ctx, ev):
        ctx.area.tag_redraw()
        obj = ctx.scene.objects.get(ctx.scene.cmf_reg_alvo if self.modo == "ALVO" else ctx.scene.cmf_reg_movel)
        if not obj or obj.type != 'MESH': return {'CANCELLED'}
        if ev.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}: return {'PASS_THROUGH'}
        if ev.type == 'LEFTMOUSE' and ev.value == 'PRESS':
            c = (ev.mouse_region_x, ev.mouse_region_y)
            vv = view3d_utils.region_2d_to_vector_3d(ctx.region, ctx.region_data, c)
            ro = view3d_utils.region_2d_to_origin_3d(ctx.region, ctx.region_data, c)
            mi = obj.matrix_world.inverted()
            hit, loc, _, _ = obj.ray_cast(mi @ ro, (mi.to_3x3() @ vv).normalized())
            if hit:
                lst = _pts_a if self.modo == "ALVO" else _pts_m
                lst.append(obj.matrix_world @ loc)
                self.report({'INFO'}, f"{self.modo}: Ponto {len(lst)} marcado.")
            else: self.report({'WARNING'}, f"Clique sobre {obj.name}!")
            return {'RUNNING_MODAL'}
        if ev.type in {'RIGHTMOUSE', 'ESC', 'RET', 'NUMPAD_ENTER'}:
            ctx.workspace.status_text_set(None); return {'FINISHED'}
        return {'RUNNING_MODAL'}
    def invoke(self, ctx, ev):
        global _handle
        obj = ctx.scene.objects.get(ctx.scene.cmf_reg_alvo if self.modo == "ALVO" else ctx.scene.cmf_reg_movel)
        if not obj or obj.type != 'MESH': self.report({'ERROR'}, "Selecione uma malha!"); return {'CANCELLED'}
        if _handle is None: _handle = bpy.types.SpaceView3D.draw_handler_add(draw_pts, (), 'WINDOW', 'POST_VIEW')
        ctx.workspace.status_text_set(f"MARCANDO {self.modo} ({obj.name}) | Esq: Ponto | Dir/ESC: Sair")
        ctx.window_manager.modal_handler_add(self); return {'RUNNING_MODAL'}

class CMF_OT_LimparReg(bpy.types.Operator):
    bl_idname, bl_label = "cmf.limpar_pontos_reg", "Limpar Pontos"
    tipo: bpy.props.StringProperty(default="TODOS")
    def execute(self, ctx):
        if self.tipo in ("ALVO", "TODOS"): _pts_a.clear()
        if self.tipo in ("MOVEL", "TODOS"): _pts_m.clear()
        ctx.scene.cmf_reg_rms_msg = ""
        for a in ctx.screen.areas:
            if a.type == 'VIEW_3D': a.tag_redraw()
        return {'FINISHED'}

class CMF_OT_CalcPontos(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.calcular_alinhamento_pontos", "Calcular Pontos", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        s = ctx.scene
        oa, om = s.objects.get(s.cmf_reg_alvo), s.objects.get(s.cmf_reg_movel)
        if not oa or not om: self.report({'ERROR'}, "Selecione Alvo e Móvel!"); return {'CANCELLED'}
        if len(_pts_a) < 3 or len(_pts_a) != len(_pts_m): self.report({'ERROR'}, "Marque >= 3 pontos iguais em ambos!"); return {'CANCELLED'}
        M = calc_svd(_pts_m, _pts_a)
        om.matrix_world = M @ om.matrix_world
        for i in range(len(_pts_m)): _pts_m[i] = M @ _pts_m[i]
        rms = calc_rms(_pts_m, _pts_a)
        s.cmf_reg_rms_msg = f"Pontos OK | RMS: {rms:.3f} mm"
        ctx.view_layer.update(); self.report({'INFO'}, s.cmf_reg_rms_msg); return {'FINISHED'}

class CMF_OT_RefinarICP(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.refinar_icp", "Refinar ICP", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        s = ctx.scene
        oa, om = s.objects.get(s.cmf_reg_alvo), s.objects.get(s.cmf_reg_movel)
        if not oa or not om or oa.type != 'MESH' or om.type != 'MESH': self.report({'ERROR'}, "Selecione malhas válidas!"); return {'CANCELLED'}
        bvh = mathutils.bvhtree.BVHTree.FromObject(oa, ctx.evaluated_depsgraph_get())
        verts = om.data.vertices
        if not verts: return {'CANCELLED'}
        passo = max(1, len(verts) // 2500)
        amostras = [verts[i].co.copy() for i in range(0, len(verts), passo)]
        dmax, rms = s.cmf_icp_max_dist, 0.0
        for _ in range(60):
            mw, src, dst = om.matrix_world, [], []
            for v in amostras:
                pw = mw @ v
                hit, _, _, dist = bvh.find_nearest(pw)
                if hit is not None and dist <= dmax: src.append(pw); dst.append(hit)
            if len(src) < 10: self.report({'ERROR'}, "Poucos pontos próximos. Aumente a distância!"); return {'CANCELLED'}
            Ms = calc_svd(src, dst)
            om.matrix_world = Ms @ om.matrix_world
            for i in range(len(_pts_m)): _pts_m[i] = Ms @ _pts_m[i]
            rms = calc_rms([Ms @ p for p in src], dst)
            if Ms.translation.length < 0.0005: break
        s.cmf_reg_rms_msg = f"ICP OK | Desvio RMS: {rms:.3f} mm"
        ctx.view_layer.update(); self.report({'INFO'}, s.cmf_reg_rms_msg); return {'FINISHED'}

class CMF_PT_AlinhamentoICP(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Alinhamento STL (Pontos + ICP)", "CMF_PT_alinhamento_icp", 'VIEW_3D', 'UI', 'Tool'
    def draw(self, ctx):
        l, s = self.layout, ctx.scene
        b1 = l.box(); b1.label(text="1 & 2. Malhas:", icon='OUTLINER_OB_MESH')
        b1.prop_search(s, "cmf_reg_alvo", s, "objects", text="Alvo")
        b1.prop_search(s, "cmf_reg_movel", s, "objects", text="Móvel")
        b2 = l.box(); b2.label(text="3 & 4. Pontos (>= 3):", icon='PIVOT_CURSOR')
        for txt, m, cnt in [("Pontos Alvo", "ALVO", len(_pts_a)), ("Pontos Móvel", "MOVEL", len(_pts_m))]:
            r = b2.row(align=True); r.operator("cmf.marcar_pontos_modal", text=f"{txt} ({cnt})", icon='EYEDROPPER').modo = m
            r.operator("cmf.limpar_pontos_reg", text="", icon='X').tipo = m
        b2.operator("cmf.limpar_pontos_reg", text="Limpar Todos", icon='TRASH').tipo = "TODOS"
        l.operator("cmf.calcular_alinhamento_pontos", text="5. Calcular (Pontos)", icon='CON_TRANSLIKE')
        b3 = l.box(); b3.label(text="6. Refinar ICP:", icon='MOD_SHRINKWRAP')
        b3.prop(s, "cmf_icp_max_dist", text="Distância (mm)")
        b3.operator("cmf.refinar_icp", text="Refinar ICP", icon='CHECKMARK')
        if s.cmf_reg_rms_msg: l.box().label(text=s.cmf_reg_rms_msg, icon='INFO')

CLASSES = (CMF_OT_MarcarModal, CMF_OT_LimparReg, CMF_OT_CalcPontos, CMF_OT_RefinarICP, CMF_PT_AlinhamentoICP)
def register():
    bpy.types.Scene.cmf_reg_alvo = bpy.props.StringProperty()
    bpy.types.Scene.cmf_reg_movel = bpy.props.StringProperty()
    bpy.types.Scene.cmf_icp_max_dist = bpy.props.FloatProperty(default=0.8, min=0.3, max=2.0, step=5, precision=2)
    bpy.types.Scene.cmf_reg_rms_msg = bpy.props.StringProperty(default="")
    for c in CLASSES: bpy.utils.register_class(c)

def unregister():
    global _handle
    if _handle: bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW'); _handle = None
    for c in reversed(CLASSES): bpy.utils.unregister_class(c)
    for k in ("cmf_reg_alvo", "cmf_reg_movel", "cmf_icp_max_dist", "cmf_reg_rms_msg"): delattr(bpy.types.Scene, k)

if __name__ == "__main__":
    register()