bl_info = {"name": "CMF Inspeção Visual (Mapa de Desvio)", "author": "Dr. Winkler / IA Google", "version": (1, 4), "blender": (4, 2, 0), "location": "View3D > Barra Lateral (N) > Aba Tool", "category": "Interface"}
import bpy, gpu, blf, mathutils, numpy as np
from gpu_extras.batch import batch_for_shader

_hud_handle, _hud_active, _hud_max = None, False, 0.8

def mapear_cor_jet(v):
    v = np.clip(v, -1.0, 1.0)
    r = np.clip(1.5 - np.abs(2.0 * v - 1.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(2.0 * v), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(2.0 * v + 1.0), 0.0, 1.0)
    return r, g, b

def desenhar_barra_escala():
    if not _hud_active: return
    try:
        reg = bpy.context.region
        w, h = reg.width, reg.height
        bw, bh = min(560, int(w * 0.65)), 18
        x0, y0 = (w - bw) // 2, 34

        sh = gpu.shader.from_builtin('SMOOTH_COLOR')
        gpu.state.blend_set('ALPHA')

        sh_bg = gpu.shader.from_builtin('UNIFORM_COLOR')
        bg_coords = [(x0 - 26, y0 - 24), (x0 + bw + 26, y0 - 24), (x0 + bw + 26, y0 + bh + 12), (x0 - 26, y0 + bh + 12)]
        b_bg = batch_for_shader(sh_bg, 'TRI_FAN', {"pos": bg_coords})
        sh_bg.bind(); sh_bg.uniform_float("color", (0.08, 0.08, 0.08, 0.78)); b_bg.draw(sh_bg)

        stops = [(-1.0, (0,0,1,1)), (-0.5, (0,1,1,1)), (0.0, (0,1,0,1)), (0.5, (1,1,0,1)), (1.0, (1,0,0,1))]
        coords, colors, indices = [], [], []
        for i, (t, col) in enumerate(stops):
            xx = x0 + ((t + 1.0) * 0.5) * bw
            coords.extend([(xx, y0), (xx, y0 + bh)])
            colors.extend([col, col])
            if i < len(stops) - 1:
                idx = i * 2
                indices.extend([(idx, idx+2, idx+3), (idx, idx+3, idx+1)])

        b_grad = batch_for_shader(sh, 'TRIS', {"pos": coords, "color": colors}, indices=indices)
        sh.bind(); b_grad.draw(sh)

        blf.size(0, 12)
        blf.color(0, 1.0, 1.0, 1.0, 1.0)
        for i in range(9):
            frac = i / 8.0
            val = _hud_max * (2.0 * frac - 1.0)
            txt = f"{val:+.2f}"
            tw, _ = blf.dimensions(0, txt)
            xx = x0 + bw * frac - (tw * 0.5)
            blf.position(0, xx, y0 - 16, 0)
            blf.draw(0, txt)
        gpu.state.blend_set('NONE')
    except: pass

class CMF_OT_CalcularMapaDesvio(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.calcular_mapa_desvio", "Calcular Mapa de Desvio", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        global _hud_handle, _hud_active, _hud_max
        s = ctx.scene
        oa, on = s.objects.get(s.cmf_insp_actual), s.objects.get(s.cmf_insp_nominal)
        if not oa or not on or oa.type != 'MESH' or on.type != 'MESH':
            self.report({'ERROR'}, "Selecione as malhas Actual e Nominal!"); return {'CANCELLED'}

        bvh = mathutils.bvhtree.BVHTree.FromObject(on, ctx.evaluated_depsgraph_get())
        mesh = oa.data
        n_v = len(mesh.vertices)
        if n_v == 0: return {'CANCELLED'}

        mw, rot_m = oa.matrix_world, oa.matrix_world.to_3x3()
        co_arr = np.empty(n_v * 3, dtype=np.float64)
        no_arr = np.empty(n_v * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", co_arr)
        mesh.vertices.foreach_get("normal", no_arr)
        co_arr, no_arr = co_arr.reshape((n_v, 3)), no_arr.reshape((n_v, 3))

        dmax = s.cmf_insp_max_dist
        dists = np.zeros(n_v, dtype=np.float64)
        fora_alcance = np.zeros(n_v, dtype=bool)

        for i in range(n_v):
            pw = mw @ mathutils.Vector(co_arr[i])
            nw = (rot_m @ mathutils.Vector(no_arr[i])).normalized()
            hit, _, _, d = bvh.find_nearest(pw)
            if hit is not None and d <= dmax:
                dists[i] = d if (pw - hit).dot(nw) >= 0.0 else -d
            else:
                fora_alcance[i] = True

        r, g, b = mapear_cor_jet(dists / dmax)
        r[fora_alcance], g[fora_alcance], b[fora_alcance] = 0.65, 0.65, 0.65
        v_rgba = np.column_stack((r, g, b, np.ones(n_v, dtype=np.float64)))

        attr = mesh.color_attributes.get("CMF_Desvio") or mesh.color_attributes.new(name="CMF_Desvio", type='BYTE_COLOR', domain='POINT')
        mesh.color_attributes.active_color = attr
        attr.data.foreach_set("color", v_rgba.ravel())
        mesh.update()

        for area in ctx.screen.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D' and sp.shading.type == 'SOLID':
                        sp.shading.color_type = 'VERTEX'
                area.tag_redraw()

        mat = bpy.data.materials.get("Mat_CMF_Desvio") or bpy.data.materials.new("Mat_CMF_Desvio")
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out, bsdf, vcol = nodes.new('ShaderNodeOutputMaterial'), nodes.new('ShaderNodeBsdfPrincipled'), nodes.new('ShaderNodeVertexColor')
        vcol.layer_name = "CMF_Desvio"
        links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        oa.data.materials.clear()
        oa.data.materials.append(mat)

        validos = dists[~fora_alcance]
        s.cmf_insp_stats = f"Média: {validos.mean():+.3f} | RMS: {np.sqrt(np.mean(validos**2)):.3f} mm" if len(validos) > 0 else "Nenhuma superfície dentro da distância."

        _hud_max, _hud_active = dmax, True
        if _hud_handle is None:
            _hud_handle = bpy.types.SpaceView3D.draw_handler_add(desenhar_barra_escala, (), 'WINDOW', 'POST_PIXEL')

        self.report({'INFO'}, f"Mapa de Desvio gerado! {s.cmf_insp_stats}")
        return {'FINISHED'}

class CMF_OT_LimparMapaDesvio(bpy.types.Operator):
    bl_idname, bl_label = "cmf.limpar_mapa_desvio", "Limpar Mapa e Cores"
    def execute(self, ctx):
        global _hud_active
        _hud_active = False
        s = ctx.scene
        s.cmf_insp_stats = ""
        oa = s.objects.get(s.cmf_insp_actual)
        if oa and oa.type == 'MESH':
            attr = oa.data.color_attributes.get("CMF_Desvio")
            if attr: oa.data.color_attributes.remove(attr)
            oa.data.materials.clear()
            oa.data.update()
        for a in ctx.screen.areas:
            if a.type == 'VIEW_3D':
                for sp in a.spaces:
                    if sp.type == 'VIEW_3D' and sp.shading.type == 'SOLID':
                        sp.shading.color_type = 'OBJECT'
                a.tag_redraw()
        self.report({'INFO'}, "Mapa de desvio e cores removidos!")
        return {'FINISHED'}

class CMF_PT_InspeçãoDesvio(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Inspeção Visual (Mapa de Cores)", "CMF_PT_inspecao_desvio", 'VIEW_3D', 'UI', 'Tool'
    def draw(self, ctx):
        l, s = self.layout, ctx.scene
        b = l.box()
        b.prop_search(s, "cmf_insp_actual", s, "objects", text="Actual (Colorir)")
        b.prop_search(s, "cmf_insp_nominal", s, "objects", text="Nominal (Ref)")
        b.prop(s, "cmf_insp_max_dist", text="Desvio Máx (mm)")
        r = l.row(align=True)
        r.operator("cmf.calcular_mapa_desvio", text="Calcular Mapa", icon='SHADING_RENDERED')
        r.operator("cmf.limpar_mapa_desvio", text="", icon='TRASH')
        if s.cmf_insp_stats: l.box().label(text=s.cmf_insp_stats, icon='INFO')

CLASSES = (CMF_OT_CalcularMapaDesvio, CMF_OT_LimparMapaDesvio, CMF_PT_InspeçãoDesvio)
def register():
    bpy.types.Scene.cmf_insp_actual = bpy.props.StringProperty()
    bpy.types.Scene.cmf_insp_nominal = bpy.props.StringProperty()
    bpy.types.Scene.cmf_insp_max_dist = bpy.props.FloatProperty(default=0.80, min=0.10, max=5.00, step=5, precision=3)
    bpy.types.Scene.cmf_insp_stats = bpy.props.StringProperty(default="")
    for c in CLASSES: bpy.utils.register_class(c)

def unregister():
    global _hud_handle, _hud_active
    _hud_active = False
    if _hud_handle: bpy.types.SpaceView3D.draw_handler_remove(_hud_handle, 'WINDOW'); _hud_handle = None
    for c in reversed(CLASSES): bpy.utils.unregister_class(c)
    for k in ("cmf_insp_actual", "cmf_insp_nominal", "cmf_insp_max_dist", "cmf_insp_stats"): delattr(bpy.types.Scene, k)

if __name__ == "__main__":
    register()