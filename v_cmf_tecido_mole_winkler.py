bl_info = {"name": "CMF Simulação de Tecido Mole", "author": "Dr. Winkler / IA Google", "version": (8, 0), "blender": (4, 2, 0), "location": "View3D > Barra N > Aba Tecido Mole", "category": "Interface"}
import bpy, mathutils, numpy as np
from bpy_extras import view3d_utils

SEGS = ["MX_POS", "MD_POS", "MD_MENTO", "MENTO", "RMD_POS", "RME_POS"]
_tm = {"on": False, "fn": "", "vo": None, "w": {}, "mi": {}}

def get_o(sc, n): return next((o for o in sc.objects if o.name.strip().lower() == n.strip().lower()), None)

def upd_pele(sc, deps=None):
    if not _tm["on"]: return
    fc = sc.objects.get(_tm["fn"])
    if not fc or fc.type != 'MESH' or _tm["vo"] is None or len(fc.data.vertices) != len(_tm["vo"]): return
    mw, mwi, vo = fc.matrix_world, fc.matrix_world.inverted(), _tm["vo"]
    vn, mov = vo.copy(), False
    vh = np.hstack((vo, np.ones((len(vo), 1), dtype=np.float64)))
    for nm, w in _tm["w"].items():
        o = get_o(sc, nm)
        if not o: continue
        mi, ma = _tm["mi"][nm], o.matrix_world
        if (ma.translation - mi.translation).length < 1e-5 and ma.to_quaternion().rotation_difference(mi.to_quaternion()).angle < 1e-5: continue
        mov = True
        md = np.array(mwi @ (ma @ mi.inverted()) @ mw, dtype=np.float64)
        vn += ((vh @ md.T)[:, :3] - vo) * w[:, np.newaxis]
    if mov:
        fc.data.vertices.foreach_set("co", vn.ravel())
        fc.data.update()

class CMF_OT_PintarFixas(bpy.types.Operator):
    bl_idname, bl_label = "cmf.pintar_zonas_fixas", "1. Pintar Zonas Fixas (Opcional)"
    def execute(self, ctx):
        fc = ctx.scene.objects.get(ctx.scene.cmf_tm_face)
        if not fc or fc.type != 'MESH': self.report({'ERROR'}, "Selecione a FACE!"); return {'CANCELLED'}
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT'); fc.select_set(True); ctx.view_layer.objects.active = fc
        vg = fc.vertex_groups.get("CMF_ZONA_FIXA") or fc.vertex_groups.new(name="CMF_ZONA_FIXA")
        fc.vertex_groups.active = vg; bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        return {'FINISHED'}

class CMF_OT_PrepTM(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.preparar_tecido_mole", "2. Vincular Tecido Mole", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        sc = ctx.scene; fc = sc.objects.get(sc.cmf_tm_face)
        if not fc or fc.type != 'MESH': self.report({'ERROR'}, "Selecione a FACE!"); return {'CANCELLED'}
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        for m in list(fc.modifiers):
            if m.type in {'LATTICE', 'ARMATURE', 'MESH_DEFORM'}: fc.modifiers.remove(m)
        nv = len(fc.data.vertices); co = np.empty(nv * 3, dtype=np.float64); fc.data.vertices.foreach_get("co", co)
        vl = co.reshape((nv, 3)); mw = np.array(fc.matrix_world, dtype=np.float64)
        vw = (np.hstack((vl, np.ones((nv, 1), dtype=np.float64))) @ mw.T)[:, :3]
        alt = max(1e-4, vw[:, 2].max() - vw[:, 2].min()); sig = alt * (sc.cmf_tm_raio / 100.0)
        pf_man = np.zeros(nv, dtype=np.float64); vgf = fc.vertex_groups.get("CMF_ZONA_FIXA")
        if vgf:
            ig = vgf.index
            for i, v in enumerate(fc.data.vertices):
                for g in v.groups:
                    if g.group == ig: pf_man[i] = g.weight; break
        deps = ctx.evaluated_depsgraph_get(); pb, mi, pts_o = {}, {}, []
        for nm in SEGS:
            o = get_o(sc, nm)
            if not o or o.type != 'MESH': continue
            mi[nm] = o.matrix_world.copy(); eo = o.evaluated_get(deps); mo = eo.to_mesh(); nvo = len(mo.vertices)
            if nvo > 0:
                ps = max(1, nvo // 1500); rng = range(0, nvo, ps); kd = mathutils.kdtree.KDTree(len(rng)); mwo = o.matrix_world
                for idx, vi in enumerate(rng):
                    pw = mwo @ mo.vertices[vi].co; kd.insert(pw, idx); pts_o.append(pw)
                kd.balance()
                ds = np.empty(nv, dtype=np.float64)
                for i in range(nv):
                    _, _, dist_val = kd.find(vw[i])
                    ds[i] = dist_val
                if "MENTO" in nm:
                    rm = sig * 1.8; t = np.clip((ds - rm * 0.55) / max(1e-4, rm * 0.45), 0.0, 1.0); pb[nm] = 1.0 - (t ** 1.5)
                else:
                    fs = 1.2 if "RM" in nm else 1.6; pb[nm] = np.maximum(0.0, 1.0 - (ds / (sig * fs))) ** 2.5
            eo.to_mesh_clear()
        if not pb: self.report({'ERROR'}, "Nenhum segmento POS!"); return {'CANCELLED'}
        ao = np.array(pts_o, dtype=np.float64); yc = vw[:, 1].mean()
        if abs(ao[:, 1].min() - yc) > abs(ao[:, 1].max() - yc):
            mf = np.clip((ao[:, 1].max() + sig * 0.25 - vw[:, 1]) / max(1e-4, sig), 0.0, 1.0)
        else:
            mf = np.clip((vw[:, 1] - (ao[:, 1].min() - sig * 0.25)) / max(1e-4, sig), 0.0, 1.0)
        mb = np.clip((ao[:, 2].max() + sig * 0.4 - vw[:, 2]) / max(1e-4, sig), 0.0, 1.0)
        msk = (mf ** 1.5) * (mb ** 1.5) * (1.0 - pf_man)
        for k in pb: pb[k] *= msk
        if "MENTO" in pb and "MD_POS" in pb: pb["MD_POS"] *= (1.0 - pb["MENTO"])
        ss = sum(pb.values()); fn = np.where(ss > 1.0, 1.0 / np.maximum(1e-5, ss), 1.0)
        _tm.update({"on": True, "fn": fc.name, "vo": vl, "w": {k: (w * fn) for k, w in pb.items()}, "mi": mi})
        sc.cmf_tm_status = f"Vinculado! ({len(pb)} segs | Mento 1:1)"
        return {'FINISHED'}

class CMF_OT_CongelarTM(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.congelar_tecido_mole", "3. Congelar Deformação Óssea", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        sc = ctx.scene
        if not _tm["on"]:
            self.report({'WARNING'}, "Nenhuma vinculação óssea ativa para congelar.")
            return {'CANCELLED'}
        upd_pele(sc)
        _tm["on"] = False
        sc.cmf_tm_status = "Deformação Congelada! Pronto para Liquidificar."
        self.report({'INFO'}, sc.cmf_tm_status)
        return {'FINISHED'}

class CMF_OT_ResetTM(bpy.types.Operator):
    bl_idname, bl_label = "cmf.resetar_tecido_mole", "Restaurar Pele Original"
    def execute(self, ctx):
        sc = ctx.scene
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        fc = sc.objects.get(_tm["fn"] or sc.cmf_tm_face)
        if fc and _tm["vo"] is not None and len(fc.data.vertices) == len(_tm["vo"]):
            fc.data.vertices.foreach_set("co", _tm["vo"].ravel()); fc.data.update()
        _tm["on"] = False; sc.cmf_tm_status = "Pele restaurada."; return {'FINISHED'}

class CMF_OT_Liquidificar3D(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.liquidificar_tecido_3d", "4. Liquidificar 3D (Arrastar Pele)", {'REGISTER', 'UNDO', 'BLOCKING'}
    def invoke(self, ctx, ev):
        sc = ctx.scene; fc = sc.objects.get(sc.cmf_tm_face)
        if not fc or fc.type != 'MESH': self.report({'ERROR'}, "Selecione a FACE!"); return {'CANCELLED'}
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        if _tm["on"]:
            upd_pele(sc); _tm["on"] = False; sc.cmf_tm_status = "Congelado automaticamente para ajuste fino."
        self.fc = fc; self.arrastando = False; self.pt_ref = None; self.v_base = None; self.pesos_pincel = None
        ctx.window_manager.modal_handler_add(self)
        ctx.workspace.status_text_set("LIQUIDIFICAR 3D: Segure Botão Esquerdo na pele e arraste | Direito ou ESC para sair")
        return {'RUNNING_MODAL'}

    def modal(self, ctx, ev):
        reg, rv3d = ctx.region, ctx.region_data
        if not rv3d: return {'PASS_THROUGH'}
        coord = (ev.mouse_region_x, ev.mouse_region_y)

        if ev.type == 'LEFTMOUSE' and ev.value == 'PRESS':
            orig = view3d_utils.region_2d_to_origin_3d(reg, rv3d, coord)
            dir_v = view3d_utils.region_2d_to_vector_3d(reg, rv3d, coord)
            mwi = self.fc.matrix_world.inverted()
            hit, loc_l, _, _ = self.fc.ray_cast(mwi @ orig, (mwi.to_3x3() @ dir_v).normalized())
            if hit:
                self.arrastando = True
                self.pt_ref = self.fc.matrix_world @ loc_l
                nv = len(self.fc.data.vertices); co = np.empty(nv * 3, dtype=np.float64)
                self.fc.data.vertices.foreach_get("co", co); self.v_base = co.reshape((nv, 3))
                mw = np.array(self.fc.matrix_world, dtype=np.float64)
                vw = (np.hstack((self.v_base, np.ones((nv, 1), dtype=np.float64))) @ mw.T)[:, :3]
                alt = max(1e-4, vw[:, 2].max() - vw[:, 2].min())
                raio_w = alt * (ctx.scene.cmf_tm_pincel_raio / 100.0)
                dists = np.linalg.norm(vw - np.array(self.pt_ref, dtype=np.float64), axis=1)
                self.pesos_pincel = np.maximum(0.0, 1.0 - (dists / max(1e-4, raio_w))) ** 2.0
            return {'RUNNING_MODAL'}

        elif ev.type == 'MOUSEMOVE' and self.arrastando and self.pt_ref is not None:
            pt_atual = view3d_utils.region_2d_to_location_3d(reg, rv3d, coord, self.pt_ref)
            delta_w = (pt_atual - self.pt_ref) * (ctx.scene.cmf_tm_pincel_forca / 100.0)
            delta_loc = np.array(self.fc.matrix_world.to_3x3().inverted() @ delta_w, dtype=np.float64)
            v_novo = self.v_base + np.outer(self.pesos_pincel, delta_loc)
            self.fc.data.vertices.foreach_set("co", v_novo.ravel()); self.fc.data.update()
            ctx.area.tag_redraw()
            return {'RUNNING_MODAL'}

        elif ev.type == 'LEFTMOUSE' and ev.value == 'RELEASE':
            self.arrastando = False; self.pt_ref = None
            return {'RUNNING_MODAL'}

        elif ev.type in {'RIGHTMOUSE', 'ESC'}:
            ctx.workspace.status_text_set(None)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

class CMF_PT_TMPanel(bpy.types.Panel):
    bl_label = "Simulação de Tecido Mole"
    bl_idname = "CMF_PT_tecido_mole_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tecido Mole'

    def draw(self, ctx):
        l, sc = self.layout, ctx.scene
        b = l.box()
        b.prop_search(sc, "cmf_tm_face", sc, "objects", text="Malha Face")
        b.prop(sc, "cmf_tm_raio", text="Raio Ósseo (%)")
        l.operator("cmf.pintar_zonas_fixas", text="1. Pintar Zonas Fixas", icon='BRUSH_DATA')
        r = l.row(align=True)
        r.operator("cmf.preparar_tecido_mole", text="2. Vincular Tecido Mole", icon='MOD_SMOOTH')
        r.operator("cmf.resetar_tecido_mole", text="", icon='LOOP_BACK')
        l.operator("cmf.congelar_tecido_mole", text="3. Congelar Deformação Óssea", icon='FREEZE')
        if sc.cmf_tm_status:
            l.box().label(text=sc.cmf_tm_status, icon='CHECKMARK')
        l.separator()
        bl = l.box()
        bl.label(text="Ajuste Fino (Estilo Liquidificar):", icon='SCULPTMODE_HLT')
        rl = bl.row(align=True)
        rl.prop(sc, "cmf_tm_pincel_raio", text="Raio")
        rl.prop(sc, "cmf_tm_pincel_forca", text="Força")
        bl.operator("cmf.liquidificar_tecido_3d", text="4. Liquidificar 3D (Arrastar Pele)", icon='HAND')

CLS = (CMF_OT_PintarFixas, CMF_OT_PrepTM, CMF_OT_CongelarTM, CMF_OT_ResetTM, CMF_OT_Liquidificar3D, CMF_PT_TMPanel)

def register():
    bpy.types.Scene.cmf_tm_face = bpy.props.StringProperty(default="FACE")
    bpy.types.Scene.cmf_tm_raio = bpy.props.FloatProperty(default=14.0, min=5.0, max=35.0, step=100, precision=0)
    bpy.types.Scene.cmf_tm_pincel_raio = bpy.props.FloatProperty(default=10.0, min=2.0, max=30.0, step=100, precision=0)
    bpy.types.Scene.cmf_tm_pincel_forca = bpy.props.FloatProperty(default=80.0, min=10.0, max=100.0, step=100, precision=0)
    bpy.types.Scene.cmf_tm_status = bpy.props.StringProperty(default="")
    for c in CLS:
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
        bpy.utils.register_class(c)
    if upd_pele not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(upd_pele)

def unregister():
    if upd_pele in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(upd_pele)
    for c in reversed(CLS):
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
    for k in ("cmf_tm_face", "cmf_tm_raio", "cmf_tm_pincel_raio", "cmf_tm_pincel_forca", "cmf_tm_status"):
        if hasattr(bpy.types.Scene, k):
            delattr(bpy.types.Scene, k)

if __name__ == "__main__":
    register()