bl_info = {"name": "CMF Gerador de Splint Oclusal", "author": "Dr. Winkler / IA Google", "version": (2, 4), "blender": (4, 2, 0), "location": "View3D > Barra N > Aba Splint Oclusal", "category": "Interface"}
import bpy, bmesh, math, mathutils, numpy as np
from bpy_extras import view3d_utils

def get_o(sc, n): return next((o for o in sc.objects if o.name.strip().lower() == n.strip().lower()), None)

class CMF_OT_PintarArcadaSplint(bpy.types.Operator):
    bl_idname, bl_label = "cmf.pintar_arcada_splint", "Pintar Oclusal"
    alvo: bpy.props.StringProperty()
    def execute(self, ctx):
        sc = ctx.scene; obj = get_o(sc, self.alvo)
        if not obj or obj.type != 'MESH': self.report({'ERROR'}, f"Malha {self.alvo} não encontrada!"); return {'CANCELLED'}
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        for n in ("MXI_40", "MDI_40", "MXF_40", "MDF_40"):
            ot = get_o(sc, n)
            if ot and ot != obj: ot.hide_set(True)
        obj.hide_viewport = False; obj.hide_set(False)
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); ctx.view_layer.objects.active = obj
        vg = obj.vertex_groups.get("CMF_ZONA_SPLINT") or obj.vertex_groups.new(name="CMF_ZONA_SPLINT")
        obj.vertex_groups.active = vg; bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        return {'FINISHED'}

def coletar_pts(obj):
    pts = []
    if not obj or obj.type != 'MESH': return pts
    vg = obj.vertex_groups.get("CMF_ZONA_SPLINT"); mw = obj.matrix_world
    if vg:
        ig = vg.index
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group == ig and g.weight > 0.2: pts.append(mw @ v.co); break
    return pts

def perfurar_amarrias(ctx, splint, pts_c, larg, diam, qtd):
    if len(pts_c) < 6 or qtd < 2: return
    idxs = [int(round(x)) for x in np.linspace(2, len(pts_c) - 3, qtd)]
    cils = []
    for i in idxs:
        pa = pts_c[i]; tg = (pts_c[min(len(pts_c)-1, i+1)] - pts_c[max(0, i-1)]).normalized()
        rad = mathutils.Vector((-tg.y, tg.x, 0.0)).normalized()
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=diam * 0.5, depth=larg * 2.5, location=pa)
        c = ctx.active_object; c.rotation_euler = rad.to_track_quat('Z', 'Y').to_euler(); cils.append(c)
    if not cils: return
    bpy.ops.object.select_all(action='DESELECT')
    for c in cils: c.select_set(True)
    ctx.view_layer.objects.active = next(iter(cils))
    if len(cils) > 1: bpy.ops.object.join()
    bloco = ctx.active_object
    bpy.ops.object.select_all(action='DESELECT'); splint.select_set(True); ctx.view_layer.objects.active = splint
    mf = splint.modifiers.new(name="Furos_Amarria", type='BOOLEAN')
    mf.operation = 'DIFFERENCE'; mf.solver = 'EXACT'; mf.object = bloco
    bpy.ops.object.modifier_apply(modifier="Furos_Amarria"); bpy.data.objects.remove(bloco, do_unlink=True)

def construir_splint(ctx, osup, oinf, larg, alt):
    pts_all = coletar_pts(osup) + coletar_pts(oinf)
    if len(pts_all) < 10: return None, []
    arr = np.array([[p.x, p.y, p.z] for p in pts_all], dtype=np.float64)
    cx, cyp = float(arr[:, 0].mean()), float(arr[:, 1].max()) + 5.0
    angs = np.arctan2(arr[:, 1] - cyp, arr[:, 0] - cx)
    bins = np.linspace(float(angs.min()), float(angs.max()), 30)
    pts_c = []
    for i in range(len(bins) - 1):
        msk = (angs >= bins[i]) & (angs <= bins[i + 1])
        if np.any(msk):
            vx, vy, vz = arr[msk].mean(axis=0).tolist()
            pts_c.append(mathutils.Vector((vx, vy, vz)))
    if len(pts_c) < 4: return None, []
    cv = bpy.data.curves.new("CMF_Splint_Curva", type='CURVE'); cv.dimensions = '3D'
    sp = cv.splines.new('POLY'); sp.points.add(len(pts_c) - 1)
    for idx, pt in enumerate(pts_c): sp.points[idx].co = (pt.x, pt.y, pt.z, 1.0)
    ocv = bpy.data.objects.new("CMF_Splint_Temp", cv); ctx.scene.collection.objects.link(ocv)
    bpy.ops.object.select_all(action='DESELECT'); ocv.select_set(True); ctx.view_layer.objects.active = ocv
    bpy.ops.object.convert(target='MESH'); splint = ctx.active_object
    bm = bmesh.new(); bm.from_mesh(splint.data); bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=2, use_grid_fill=True); bm.to_mesh(splint.data); bm.free()
    ms = splint.modifiers.new(name="Skin", type='SKIN')
    camada_skin = next(iter(splint.data.skin_vertices))
    for v in camada_skin.data: v.radius = (larg * 0.5, alt * 0.5)
    bpy.ops.object.modifier_apply(modifier="Skin")
    mr = splint.modifiers.new(name="Remesh", type='REMESH'); mr.mode = 'VOXEL'; mr.voxel_size = 0.25
    bpy.ops.object.modifier_apply(modifier="Remesh")
    return splint, pts_c

class CMF_OT_GerarSplint(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.gerar_splint_oclusal", "Gerar Splint Oclusal", {'REGISTER', 'UNDO'}
    tipo: bpy.props.StringProperty()
    def execute(self, ctx):
        sc = ctx.scene
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        ns, ni = ("MXI_40", "MDI_40") if self.tipo == 'INT' else ("MXF_40", "MDF_40")
        nout = "SPLINT_INTERMEDIARIO" if self.tipo == 'INT' else "SPLINT_FINAL"
        osup, oinf = get_o(sc, ns), get_o(sc, ni)
        if not osup or not oinf: self.report({'ERROR'}, f"Malhas {ns} e {ni} não encontradas!"); return {'CANCELLED'}
        osup.hide_set(False); oinf.hide_set(False)
        ant = get_o(sc, nout)
        if ant: bpy.data.objects.remove(ant, do_unlink=True)
        splint, pts_c = construir_splint(ctx, osup, oinf, sc.cmf_sp_largura, sc.cmf_sp_altura)
        if not splint: self.report({'ERROR'}, f"Pinte a zona oclusal em {ns} e/ou {ni}!"); return {'CANCELLED'}
        splint.name = nout
        for idx, alvo in enumerate((osup, oinf)):
            mb = splint.modifiers.new(name=f"Bool_{idx}", type='BOOLEAN'); mb.operation = 'DIFFERENCE'; mb.solver = 'EXACT'; mb.object = alvo
            bpy.ops.object.modifier_apply(modifier=mb.name)
        if sc.cmf_sp_furos: perfurar_amarrias(ctx, splint, pts_c, sc.cmf_sp_largura, sc.cmf_sp_furo_diam, sc.cmf_sp_furo_qtd)
        msm = splint.modifiers.new(name="Smooth", type='SMOOTH'); msm.factor = 0.4; msm.iterations = 3
        bpy.ops.object.modifier_apply(modifier="Smooth")
        mat = bpy.data.materials.get("Mat_CMF_Splint") or bpy.data.materials.new("Mat_CMF_Splint")
        mat.diffuse_color = (0.15, 0.75, 0.85, 0.9) if self.tipo == 'INT' else (0.2, 0.85, 0.45, 0.9)
        splint.data.materials.append(mat); sc.cmf_sp_status = f"{nout} gerado!"; return {'FINISHED'}

class CMF_OT_ApontarFurosSplint(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.apontar_furos_splint", "Apontar Furos (Clique no Splint)", {'REGISTER', 'UNDO'}
    def invoke(self, ctx, ev):
        if ctx.object and ctx.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        obj = ctx.active_object
        if not obj or obj.type != 'MESH' or "SPLINT" not in obj.name.upper():
            obj = get_o(ctx.scene, "SPLINT_FINAL") or get_o(ctx.scene, "SPLINT_INTERMEDIARIO")
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Selecione o Splint antes de apontar os furos!"); return {'CANCELLED'}
        self.splint = obj
        ctx.window_manager.modal_handler_add(self)
        ctx.workspace.status_text_set("APONTAR FUROS: Clique com Botão Esquerdo na parede do Splint para perfurar em 90° | Direito ou ESC para sair")
        return {'RUNNING_MODAL'}

    def modal(self, ctx, ev):
        if ev.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        if ev.type == 'LEFTMOUSE' and ev.value == 'PRESS':
            reg, rv3d = ctx.region, ctx.region_data
            if not rv3d: return {'PASS_THROUGH'}
            coord = (ev.mouse_region_x, ev.mouse_region_y)
            orig = view3d_utils.region_2d_to_origin_3d(reg, rv3d, coord)
            dir_v = view3d_utils.region_2d_to_vector_3d(reg, rv3d, coord)
            mwi = self.splint.matrix_world.inverted()
            hit, loc_l, norm_l, _ = self.splint.ray_cast(mwi @ orig, (mwi.to_3x3() @ dir_v).normalized())
            if hit:
                loc_w = self.splint.matrix_world @ loc_l
                norm_w = (self.splint.matrix_world.to_3x3() @ norm_l).normalized()
                diam = ctx.scene.cmf_sp_furo_diam
                prof = ctx.scene.cmf_sp_largura * 2.5
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=diam * 0.5, depth=prof, location=loc_w)
                cil = ctx.active_object
                cil.rotation_euler = norm_w.to_track_quat('Z', 'Y').to_euler()
                bpy.ops.object.select_all(action='DESELECT')
                self.splint.select_set(True); ctx.view_layer.objects.active = self.splint
                mf = self.splint.modifiers.new(name="Furo_Manual", type='BOOLEAN')
                mf.operation = 'DIFFERENCE'; mf.solver = 'EXACT'; mf.object = cil
                bpy.ops.object.modifier_apply(modifier="Furo_Manual")
                bpy.data.objects.remove(cil, do_unlink=True)
                ctx.area.tag_redraw()
            return {'RUNNING_MODAL'}
        elif ev.type in {'RIGHTMOUSE', 'ESC'}:
            ctx.workspace.status_text_set(None)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

class CMF_PT_SplintPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Gerador de Splint Oclusal", "CMF_PT_splint_panel", 'VIEW_3D', 'UI', 'Splint Oclusal'
    def draw(self, ctx):
        l, sc = self.layout, ctx.scene; b = l.box(); b.label(text="Dimensões e Amarrias (mm):", icon='MOD_SOLIDIFY')
        b.prop(sc, "cmf_sp_largura", text="Largura Vest-Lingual"); b.prop(sc, "cmf_sp_altura", text="Altura Oclusal")
        b.prop(sc, "cmf_sp_furos", text="Furos Automáticos no Arco")
        rf = b.row(align=True)
        if sc.cmf_sp_furos: rf.prop(sc, "cmf_sp_furo_qtd", text="Qtd")
        if sc.cmf_sp_furos:
            rf.prop(sc, "cmf_sp_furo_qtd", text="Qtd")
        rf.prop(sc, "cmf_sp_furo_diam", text="Diâm. Furo (mm)")
        b.operator("cmf.apontar_furos_splint", text="Apontar Furos (Clique na Face)", icon='PIVOT_CURSOR')

        bi = l.box()
        bi.label(text="Guia Intermediário (MXI_40 / MDI_40):", icon='MESH_TORUS')
        r1 = bi.row(align=True)
        r1.operator("cmf.pintar_arcada_splint", text="1. Pintar MXI_40", icon='BRUSH_DATA').alvo = 'MXI_40'
        r1.operator("cmf.pintar_arcada_splint", text="2. Pintar MDI_40", icon='BRUSH_DATA').alvo = 'MDI_40'
        bi.operator("cmf.gerar_splint_oclusal", text="3. Gerar Splint Intermediário", icon='PLAY').tipo = 'INT'

        bf = l.box()
        bf.label(text="Guia Final (MXF_40 / MDF_40):", icon='MESH_TORUS')
        r2 = bf.row(align=True)
        r2.operator("cmf.pintar_arcada_splint", text="1. Pintar MXF_40", icon='BRUSH_DATA').alvo = 'MXF_40'
        r2.operator("cmf.pintar_arcada_splint", text="2. Pintar MDF_40", icon='BRUSH_DATA').alvo = 'MDF_40'
        bf.operator("cmf.gerar_splint_oclusal", text="3. Gerar Splint Final", icon='PLAY').tipo = 'FIN'

        if sc.cmf_sp_status:
            l.box().label(text=sc.cmf_sp_status, icon='CHECKMARK')

CLS = (CMF_OT_PintarArcadaSplint, CMF_OT_GerarSplint, CMF_OT_ApontarFurosSplint, CMF_PT_SplintPanel)

def register():
    bpy.types.Scene.cmf_sp_largura = bpy.props.FloatProperty(default=15.0, min=5.0, max=25.0, step=50, precision=1)
    bpy.types.Scene.cmf_sp_altura = bpy.props.FloatProperty(default=9.0, min=3.0, max=18.0, step=50, precision=1)
    bpy.types.Scene.cmf_sp_furos = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.cmf_sp_furo_qtd = bpy.props.IntProperty(default=6, min=2, max=12)
    bpy.types.Scene.cmf_sp_furo_diam = bpy.props.FloatProperty(default=1.5, min=0.8, max=3.0, step=10, precision=1)
    bpy.types.Scene.cmf_sp_status = bpy.props.StringProperty(default="")
    for c in CLS:
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(CLS):
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
    for k in ("cmf_sp_largura", "cmf_sp_altura", "cmf_sp_furos", "cmf_sp_furo_qtd", "cmf_sp_furo_diam", "cmf_sp_status"):
        if hasattr(bpy.types.Scene, k):
            delattr(bpy.types.Scene, k)

if __name__ == "__main__":
    register()