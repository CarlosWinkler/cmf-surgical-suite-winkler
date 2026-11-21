bl_info = {"name": "CMF Régua Winkler", "author": "Dr. Winkler", "version": (11, 0), "blender": (4, 2, 0), "location": "View3D > Barra N > Tool", "category": "Interface"}
import bpy, gpu, blf, mathutils
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader

_reguas = []
_atual = {"p1": None, "p2": None, "dist": 0.0, "ativo": False, "fase": 0, "snap": False}

def desenhar_reguas():
    ctx = bpy.context
    rv3d = ctx.region_data
    reg = ctx.region
    if not rv3d or not getattr(ctx.scene, "winkler_ver_reguas", True):
        return
    gpu.state.blend_set('ALPHA')
    sh = gpu.shader.from_builtin('UNIFORM_COLOR')
    sh.bind()

    lista = list(_reguas)
    if _atual["ativo"] and _atual["p1"] is not None:
        lista.append(_atual)

    for r in lista:
        p2 = r["p2"] if r["p2"] is not None else r["p1"]
        a = view3d_utils.location_3d_to_region_2d(reg, rv3d, r["p1"])
        b = view3d_utils.location_3d_to_region_2d(reg, rv3d, p2)
        if a and b:
            bl = batch_for_shader(sh, 'LINES', {"pos": [(a.x, a.y), (b.x, b.y)]})
            sh.uniform_float("color", (0.15, 0.55, 0.95, 0.95))
            gpu.state.line_width_set(2.5)
            bl.draw(sh)

            cx, cy = (a.x + b.x) / 2, (a.y + b.y) / 2
            bg = [(cx-28, cy-9), (cx+28, cy-9), (cx+28, cy+9), (cx-28, cy+9)]
            bbg = batch_for_shader(sh, 'TRI_FAN', {"pos": bg})
            sh.uniform_float("color", (0.04, 0.04, 0.04, 0.88))
            bbg.draw(sh)

            txt = f"{r['dist']:.2f}"
            blf.size(0, 13)
            tw, th = blf.dimensions(0, txt)
            blf.color(0, 0.95, 0.95, 0.95, 1.0)
            blf.position(0, cx - tw/2, cy - th/2, 0)
            blf.draw(0, txt)

    # Indicador visual laranja quando o ímã (Ctrl) trava em um vértice
    if _atual["ativo"] and _atual["snap"] and _atual["p2"] is not None:
        sp = view3d_utils.location_3d_to_region_2d(reg, rv3d, _atual["p2"])
        if sp:
            q = [(sp.x-5, sp.y-5), (sp.x+5, sp.y-5), (sp.x+5, sp.y+5), (sp.x-5, sp.y+5), (sp.x-5, sp.y-5)]
            bq = batch_for_shader(sh, 'LINE_STRIP', {"pos": q})
            sh.uniform_float("color", (1.0, 0.55, 0.0, 1.0))
            gpu.state.line_width_set(2.0)
            bq.draw(sh)

    gpu.state.blend_set('NONE')

def buscar_vertice_proximo(ctx, reg, rv3d, coord, raio_px=25.0):
    melhor_pt = None
    menor_dist = raio_px
    deps = ctx.evaluated_depsgraph_get()
    for obj in ctx.visible_objects:
        if obj.type != 'MESH':
            continue
        eval_obj = obj.evaluated_get(deps)
        mesh = eval_obj.to_mesh()
        mw = eval_obj.matrix_world
        for v in mesh.vertices:
            w_co = mw @ v.co
            p2d = view3d_utils.location_3d_to_region_2d(reg, rv3d, w_co)
            if p2d:
                d = (mathutils.Vector(coord) - p2d).length
                if d < menor_dist:
                    menor_dist = d
                    melhor_pt = w_co
        eval_obj.to_mesh_clear()
    return melhor_pt

class CMF_OT_ReguaWinkler(bpy.types.Operator):
    bl_idname = "view3d.cmf_regua_winkler"
    bl_label = "Ligar Régua"
    bl_options = {'REGISTER', 'BLOCKING'}

    def atualizar_ponto(self, ctx, ev):
        reg = ctx.region
        rv3d = ctx.region_data
        if not rv3d:
            return
        coord = (ev.mouse_region_x, ev.mouse_region_y)
        pt = None
        _atual["snap"] = False

        if ev.ctrl:
            pt_snap = buscar_vertice_proximo(ctx, reg, rv3d, coord)
            if pt_snap is not None:
                pt = pt_snap
                _atual["snap"] = True
            else:
                orig = view3d_utils.region_2d_to_origin_3d(reg, rv3d, coord)
                dir_v = view3d_utils.region_2d_to_vector_3d(reg, rv3d, coord)
                hit, loc, _, _, _, _ = ctx.scene.ray_cast(ctx.evaluated_depsgraph_get(), orig, dir_v)
                if hit:
                    pt = loc
                    _atual["snap"] = True

        if pt is None:
            ref = _atual["p1"] or ctx.scene.cursor.location
            pt = view3d_utils.region_2d_to_location_3d(reg, rv3d, coord, ref)

        if _atual["fase"] == 1:
            _atual["p1"] = pt
            _atual["p2"] = pt
        elif _atual["fase"] == 2:
            _atual["p2"] = pt
            _atual["dist"] = (_atual["p2"] - _atual["p1"]).length

    def modal(self, ctx, ev):
        ctx.area.tag_redraw()
        if ev.type in {'MOUSEMOVE', 'LEFT_CTRL', 'RIGHT_CTRL'}:
            self.atualizar_ponto(ctx, ev)

        if ev.type == 'LEFTMOUSE' and ev.value == 'PRESS':
            self.atualizar_ponto(ctx, ev)
            if _atual["fase"] == 1:
                _atual["dist"] = 0.0
                _atual["fase"] = 2
                ctx.workspace.status_text_set("Mova o mouse | Segure CTRL para Ímã | Clique Esquerdo para Fixar")
            elif _atual["fase"] == 2:
                _reguas.append({"p1": _atual["p1"].copy(), "p2": _atual["p2"].copy(), "dist": _atual["dist"]})
                _atual["ativo"] = False
                _atual["fase"] = 0
                _atual["snap"] = False
                ctx.workspace.status_text_set(None)
                return {'FINISHED'}
            return {'RUNNING_MODAL'}

        elif ev.type in {'RIGHTMOUSE', 'ESC'}:
            _atual["ativo"] = False
            _atual["fase"] = 0
            _atual["snap"] = False
            ctx.workspace.status_text_set(None)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, ctx, ev):
        if ctx.space_data.type != 'VIEW_3D':
            return {'CANCELLED'}
        _atual["p1"] = None
        _atual["p2"] = None
        _atual["dist"] = 0.0
        _atual["ativo"] = True
        _atual["fase"] = 1
        _atual["snap"] = False
        ctx.window_manager.modal_handler_add(self)
        ctx.workspace.status_text_set("Clique com o botão esquerdo para iniciar (Segure CTRL para Ímã)")
        return {'RUNNING_MODAL'}

class CMF_OT_ApagarRegua(bpy.types.Operator):
    bl_idname = "cmf.apagar_regua"
    bl_label = "Apagar"
    idx: bpy.props.IntProperty()

    def execute(self, ctx):
        if 0 <= self.idx < len(_reguas):
            _reguas.pop(self.idx)
        ctx.area.tag_redraw()
        return {'FINISHED'}

class CMF_PT_PainelReguaWinklerV11(bpy.types.Panel):
    bl_label = "Régua Cirúrgica"
    bl_idname = "CMF_PT_painel_regua_v11"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, ctx):
        l = self.layout
        sc = ctx.scene
        b = l.box()
        b.operator("view3d.cmf_regua_winkler", text="Ligar Régua", icon='DRIVER_DISTANCE')

        r_ver = b.row(align=True)
        txt = "Ocultar Medidas" if sc.winkler_ver_reguas else "Mostrar Medidas"
        ico = 'HIDE_OFF' if sc.winkler_ver_reguas else 'HIDE_ON'
        r_ver.prop(sc, "winkler_ver_reguas", text=txt, icon=ico, toggle=True)

        if _reguas:
            l.separator()
            for i, r in enumerate(_reguas):
                row = l.row(align=True)
                row.label(text=f"Medida {i+1}: {r['dist']:.2f}")
                op = row.operator("cmf.apagar_regua", text="", icon='TRASH')
                op.idx = i

_handler = None
def register():
    global _handler
    for p_antigo in ("CMF_PT_regua_n_panel", "CMF_PT_painel_regua", "CMF_PT_painel_regua_v10"):
        cls = getattr(bpy.types, p_antigo, None)
        if cls:
            try:
                bpy.utils.unregister_class(cls)
            except:
                pass

    bpy.types.Scene.winkler_ver_reguas = bpy.props.BoolProperty(default=True)
    bpy.utils.register_class(CMF_OT_ReguaWinkler)
    bpy.utils.register_class(CMF_OT_ApagarRegua)
    bpy.utils.register_class(CMF_PT_PainelReguaWinklerV11)
    _handler = bpy.types.SpaceView3D.draw_handler_add(desenhar_reguas, (), 'WINDOW', 'POST_PIXEL')

def unregister():
    global _handler
    bpy.utils.unregister_class(CMF_OT_ReguaWinkler)
    bpy.utils.unregister_class(CMF_OT_ApagarRegua)
    bpy.utils.unregister_class(CMF_PT_PainelReguaWinklerV11)
    if _handler:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
    if hasattr(bpy.types.Scene, "winkler_ver_reguas"):
        del bpy.types.Scene.winkler_ver_reguas

if __name__ == "__main__":
    register()