bl_info = {"name": "Cefalometria Livre Ortogonal Winkler", "author": "Dr. Winkler / IA Google", "version": (2, 5), "blender": (4, 2, 0), "category": "Interface"}
import bpy, math, mathutils

def eixo_profundidade_vista():
    """Detecta qual eixo (X, Y ou Z) está apontando para a câmera na Viewport 3D."""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            rv3d = area.spaces.active.region_3d
            if rv3d:
                v_dir = rv3d.view_rotation @ mathutils.Vector((0.0, 0.0, 1.0))
                ax, ay, az = abs(v_dir.x), abs(v_dir.y), abs(v_dir.z)
                if az >= ax and az >= ay:
                    return 'Z' # Vista Superior/Inferior (projeta no plano XY)
                elif ay >= ax and ay >= az:
                    return 'Y' # Vista Frontal/Posterior (projeta no plano XZ)
                else:
                    return 'X' # Vista Lateral (projeta no plano YZ)
    return 'Z'

def achatar_2d(pt, eixo_ignorar):
    if eixo_ignorar == 'Z':
        return mathutils.Vector((pt.x, pt.y, 0.0))
    elif eixo_ignorar == 'Y':
        return mathutils.Vector((pt.x, 0.0, pt.z))
    else:
        return mathutils.Vector((0.0, pt.y, pt.z))

def calcular_distancia_ortogonal(obj_guia, pt_alvo):
    """Mede a distância puramente perpendicular na vista ortográfica (ignora profundidade da câmera)."""
    mw = obj_guia.matrix_world
    eixo_cam = eixo_profundidade_vista()
    pt_2d = achatar_2d(pt_alvo, eixo_cam)

    # 1. Coleta extremos reais se for Linha (Mesh) ou Curva
    p1, p2 = None, None
    if obj_guia.type == 'MESH' and obj_guia.data and len(obj_guia.data.vertices) >= 2:
        pts = [mw @ v.co for v in obj_guia.data.vertices]
        p_ref = next(iter(pts))
        p1 = max(pts, key=lambda p: (p - p_ref).length)
        p2 = max(pts, key=lambda p: (p - p1).length)
    elif obj_guia.type == 'CURVE' and obj_guia.data and len(obj_guia.data.splines) > 0:
        sp = obj_guia.data.splines.active or next(iter(obj_guia.data.splines))
        pts = [mw @ p.co.xyz for p in sp.points] if len(sp.points) >= 2 else [mw @ p.co for p in sp.bezier_points]
        if len(pts) >= 2:
            p_ref = next(iter(pts))
            p1 = max(pts, key=lambda p: (p - p_ref).length)
            p2 = max(pts, key=lambda p: (p - p1).length)

    if p1 and p2:
        p1_2d = achatar_2d(p1, eixo_cam)
        p2_2d = achatar_2d(p2, eixo_cam)
        if (p2_2d - p1_2d).length > 1e-6:
            p_perp, _ = mathutils.geometry.intersect_point_line(pt_2d, p1_2d, p2_2d)
            return (pt_2d - p_perp).length, p_perp

    # 2. Fallback caso seja um Empty
    p_orig = achatar_2d(mw.to_translation(), eixo_cam)
    d = mathutils.Vector((0, 0, 1))
    d.rotate(mw.to_euler())
    d_2d = achatar_2d(d, eixo_cam)
    if d_2d.length > 1e-6:
        p_perp, _ = mathutils.geometry.intersect_point_line(pt_2d, p_orig, p_orig + d_2d)
        return (pt_2d - p_perp).length, p_perp
    return (pt_2d - p_orig).length, p_orig
def atualizar_todas_cotas_livres(scene, depsgraph=None):
    for obj in scene.objects:
        if obj.name.startswith("COTA_LIVRE_"):
            l_name, p_name = obj.get("cmf_line", ""), obj.get("cmf_point", "")
            o_line, o_point = scene.objects.get(l_name), scene.objects.get(p_name)
            t_obj = scene.objects.get(f"Texto_Cota_{p_name}")
            f_obj = scene.objects.get(f"Fundo_Cota_{p_name}")
            if not (o_line and o_point and t_obj and f_obj): continue
            try:
                p_p = o_point.matrix_world.to_translation()
                dist, _ = calcular_distancia_ortogonal(o_line, p_p)
                obj["cmf_valor"] = f"{dist:.2f} mm"
                t_obj.data.body = f"{dist:.1f}"
                t_obj.data.size = scene.cmf_livre_font_size
                f_obj.scale.x = scene.cmf_livre_font_size * 2.4
                f_obj.scale.y = scene.cmf_livre_font_size * 1.1
                tx = p_p.x + scene.cmf_livre_offset_x
                ty = p_p.y + scene.cmf_livre_offset_y
                tz = p_p.z + scene.cmf_livre_offset_z
                t_obj.location = (tx, ty, tz)
                f_obj.location = (tx, ty + 0.2, tz)
                f_obj.rotation_euler = t_obj.rotation_euler
            except: pass

class CMF_PT_LivrePanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Cotas Ortogonais Livres", "CMF_PT_livre_panel", 'VIEW_3D', 'UI', 'CMF Livre'
    def draw(self, context):
        layout, scene = self.layout, context.scene
        layout.label(text="Medição Perpendicular Dinâmica", icon='RESTRICT_SELECT_OFF')
        sel = list(context.selected_objects)

        box_hud = layout.box()
        box_hud.prop(scene, "cmf_livre_font_size", text="Tamanho do Texto")
        box_hud.prop(scene, "cmf_livre_offset_x", text="Ajustar Lateral (X)")
        box_hud.prop(scene, "cmf_livre_offset_y", text="Trazer para Frente (Y)")
        box_hud.prop(scene, "cmf_livre_offset_z", text="Ajustar Altura (Z)")

        box = layout.box()
        if len(sel) == 2:
            obj_act = context.active_object
            obj_sec = next((o for o in sel if o != obj_act), obj_act)
            box.label(text="Pronto para Fixar!", icon='CHECKMARK')
            box.label(text=f"1º Esfera (Alvo): {obj_sec.name}", icon='DOT')
            box.label(text=f"2º Linha Guia (Plano): {obj_act.name}", icon='CURVE_PATH')
            op = box.operator("cmf.create_orthogonal_measure", text="Fixar Cota Perpendicular", icon='DRIVER_DISTANCE')
            op.line_name, op.point_name = obj_act.name, obj_sec.name
        else:
            box.label(text="Ordem de Seleção (SHIFT):")
            box.label(text="1º Clique: Esfera / 2º Clique: Linha")

        grupos_livres = [obj for obj in scene.objects if obj.name.startswith("COTA_LIVRE_")]
        for obj in grupos_livres:
            box_cota = layout.box()
            row = box_cota.row(align=True)
            row.operator("cmf.toggle_livre_visibility", text="", icon='HIDE_ON' if obj.hide_viewport else 'HIDE_OFF').obj_name = obj.name
            val_txt = obj.get("cmf_valor", "")
            nome_limpo = obj.name.replace("COTA_LIVRE_", "")
            row.label(text=f"{nome_limpo}: {val_txt}")
            row.operator("cmf.delete_livre_objects", text="", icon='TRASH').obj_name = obj.name
            txt_obj = scene.objects.get(f"Texto_Cota_{nome_limpo}")
            if txt_obj:
                col_rot = box_cota.column(align=True)
                col_rot.prop(txt_obj, "rotation_euler", index=0, text="Girar Eixo X")
                col_rot.prop(txt_obj, "rotation_euler", index=1, text="Girar Eixo Y")
                col_rot.prop(txt_obj, "rotation_euler", index=2, text="Girar Eixo Z")

class CMF_OT_CreateOrthogonalMeasure(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.create_orthogonal_measure", "Fixar Cota Perpendicular", {'REGISTER', 'UNDO'}
    line_name: bpy.props.StringProperty()
    point_name: bpy.props.StringProperty()
    def execute(self, context):
        scene = context.scene
        obj_line, obj_point = scene.objects.get(self.line_name), scene.objects.get(self.point_name)
        if not (obj_line and obj_point): return {'CANCELLED'}

        mat_t = bpy.data.materials.get("Mat_L_T_Livre") or bpy.data.materials.new(name="Mat_L_T_Livre")
        mat_t.diffuse_color = (1.0, 0.0, 0.0, 1.0)
        mat_f = bpy.data.materials.get("Mat_L_F_Livre") or bpy.data.materials.new(name="Mat_L_F_Livre")
        mat_f.diffuse_color = (0.04, 0.04, 0.04, 1.0)

        nome_cota = f"COTA_LIVRE_{obj_point.name}"
        antigo = scene.objects.get(nome_cota)
        if antigo:
            for f in list(antigo.children): bpy.data.objects.remove(f, do_unlink=True)
            bpy.data.objects.remove(antigo, do_unlink=True)

        container = bpy.data.objects.new(nome_cota, None)
        container["cmf_line"], container["cmf_point"] = obj_line.name, obj_point.name
        context.collection.objects.link(container)

        curve_data = bpy.data.curves.new(name=f"TextData_{obj_point.name}", type='FONT')
        txt_obj = bpy.data.objects.new(f"Texto_Cota_{obj_point.name}", curve_data)
        context.collection.objects.link(txt_obj)
        txt_obj.parent = container
        txt_obj.data.size, txt_obj.data.extrude = scene.cmf_livre_font_size, 0.1
        txt_obj.data.align_x, txt_obj.data.align_y = 'CENTER', 'CENTER'
        txt_obj.data.materials.append(mat_t)

        mesh_fundo = bpy.data.meshes.new(f"FundoMesh_{obj_point.name}")
        fundo_obj = bpy.data.objects.new(f"Fundo_Cota_{obj_point.name}", mesh_fundo)
        context.collection.objects.link(fundo_obj)
        fundo_obj.parent = container
        mesh_fundo.from_pydata([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)])
        mesh_fundo.update()
        fundo_obj.data.materials.append(mat_f)

        txt_obj.rotation_euler = fundo_obj.rotation_euler = (math.radians(180), 0.0, 0.0)
        atualizar_todas_cotas_livres(scene)
        context.view_layer.update()
        return {'FINISHED'}

class CMF_OT_ToggleLivreVisibility(bpy.types.Operator):
    bl_idname, bl_label = "cmf.toggle_livre_visibility", "Alternar Visibilidade"
    obj_name: bpy.props.StringProperty()
    def execute(self, context):
        p = context.scene.objects.get(self.obj_name)
        if p:
            st = not p.hide_viewport
            p.hide_viewport = st
            for f in p.children: f.hide_viewport = st
        return {'FINISHED'}

class CMF_OT_DeleteLivreObjects(bpy.types.Operator):
    bl_idname, bl_label = "cmf.delete_livre_objects", "Deletar Cota"
    obj_name: bpy.props.StringProperty()
    def execute(self, context):
        p = context.scene.objects.get(self.obj_name)
        if p:
            for f in list(p.children): bpy.data.objects.remove(f, do_unlink=True)
            bpy.data.objects.remove(p, do_unlink=True)
        return {'FINISHED'}

CLASSES = (CMF_PT_LivrePanel, CMF_OT_CreateOrthogonalMeasure, CMF_OT_ToggleLivreVisibility, CMF_OT_DeleteLivreObjects)
def register():
    bpy.types.Scene.cmf_livre_font_size = bpy.props.FloatProperty(name="Tamanho Texto", default=4.2, min=1.0, max=30.0)
    bpy.types.Scene.cmf_livre_offset_x = bpy.props.FloatProperty(name="Lateral X", default=0.0, min=-200.0, max=200.0)
    bpy.types.Scene.cmf_livre_offset_y = bpy.props.FloatProperty(name="Afastamento Y", default=0.0, min=-200.0, max=200.0)
    bpy.types.Scene.cmf_livre_offset_z = bpy.props.FloatProperty(name="Altura Z", default=-12.0, min=-200.0, max=200.0)
    for c in CLASSES:
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
        bpy.utils.register_class(c)
    if atualizar_todas_cotas_livres not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(atualizar_todas_cotas_livres)

def unregister():
    if atualizar_todas_cotas_livres in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(atualizar_todas_cotas_livres)
    for c in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
    for k in ("cmf_livre_font_size", "cmf_livre_offset_x", "cmf_livre_offset_y", "cmf_livre_offset_z"):
        if hasattr(bpy.types.Scene, k):
            delattr(bpy.types.Scene, k)

if __name__ == "__main__":
    register()