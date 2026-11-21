bl_info = {"name": "CMF Assimetria - Winkler", "author": "Dr. Winkler", "version": (4, 2), "blender": (4, 2, 0), "location": "View3D > Aba CMF CANT", "category": "Interface"}
import bpy, math, csv, os
from datetime import datetime

D = ["17", "13", "11", "21", "23", "27"]
ASYM = ["LMS_POS", "GoDir_PRE", "GoDir_POS", "GoEsq_PRE", "GoEsq_POS"]
PROPS = [("cmf_linha_cant", "String", "CANT", None), ("cmf_linha_plv", "String", "PLV", None), ("cmf_cant_font_size", "Float", "Tam", 4.2), ("cmf_cant_offset_x", "Float", "X", -4.26), ("cmf_cant_offset_y", "Float", "Y", -43.38), ("cmf_cant_offset_z", "Float", "Z", -4.95)]

def find_obj(names):
    return next((o for o in bpy.context.scene.objects if o.name.strip() in names), None)

def pos(o):
    return o.matrix_world.to_translation()

class CMF_PT_CantPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "CMF Assimetria - Winkler", "CMF_PT_cant_panel", 'VIEW_3D', 'UI', 'CMF CANT'
    def draw(self, context):
        layout, s = self.layout, context.scene
        for n, k, i in [("CANT", "cmf_linha_cant", 'AXIS_TOP'), ("Linha Média", "cmf_linha_plv", 'AXIS_SIDE')]:
            bx = layout.box(); bx.label(text=n, icon=i); bx.prop_search(s, k, s, "objects", text=n)
        bx = layout.box(); bx.label(text="HUD Texto", icon='FONT_DATA')
        for k, t in [("cmf_cant_font_size", "Tam"), ("cmf_cant_offset_x", "X"), ("cmf_cant_offset_y", "Y"), ("cmf_cant_offset_z", "Z")]: bx.prop(s, k, text=t)
        lo, po = s.objects.get(s.cmf_linha_cant), s.objects.get(s.cmf_linha_plv)
        if lo:
            zr = pos(lo).z
            for d in D:
                o = find_obj([f"{d}_POS", d, f"V {d}"])
                layout.row().label(text=f"Dente {d}: {abs(pos(o).z - zr):.1f} mm" if o else f"Dente {d}: N/E", icon='CHECKMARK' if o else 'BLANK1')
        if po:
            xr = pos(po).x
            layout.row().label(text="--- Medidas de Assimetria (PLV) ---")
            for n in ASYM:
                o, lbl = find_obj([n]), n.replace("_POS", "") if n == "LMI_POS" else n
                layout.row().label(text=f"{lbl}: {abs(pos(o).x - xr):.1f} mm" if o else f"{lbl}: N/E", icon='ALIGN_CENTER' if o else 'BLANK1')
        layout.separator(); layout.box().operator("cmf.create_physical_cant", text="Fixar Linhas e Ângulo", icon='PINNED')
        bx_rep = layout.box(); bx_rep.label(text="Relatório de Assimetria", icon='SPREADSHEET'); bx_rep.operator("cmf.exp_csv", text="Exportar Planilha Calc", icon='EXPORT')
        for o in [o for o in s.objects if any(p in o.name for p in ("MEDIDA_CANT_", "MEDIDA_LM_", "MEDIDA_ASYM_"))]:
            row = layout.row(align=True); row.operator("cmf.toggle_cant_visibility", text="", icon='HIDE_ON' if o.hide_viewport else 'HIDE_OFF').obj_name = o.name
            row.label(text=o.name.replace("MEDIDA_CANT_", "Cota ").replace("MEDIDA_LM_", "LM ").replace("MEDIDA_ASYM_", "Cota ")); row.operator("cmf.delete_cant_objects", text="", icon='TRASH').obj_name = o.name

class CMF_OT_CreatePhysicalCant(bpy.types.Operator):
    bl_idname, bl_label = "cmf.create_physical_cant", "Fixar Linhas e Ângulo"
    def execute(self, context):
        s = context.scene; lo, po = s.objects.get(s.cmf_linha_cant), s.objects.get(s.cmf_linha_plv)
        if not lo and not po: self.report({'ERROR'}, "Selecione Linha!"); return {'CANCELLED'}
        mats = []
        for mn, col in [("Mat_L_CANT", (0.1,0.1,0.1,1.0)), ("Mat_T_CANT", (1.0,0.0,0.0,1.0)), ("Mat_F_CANT", (0.04,0.04,0.04,1.0))]:
            m = bpy.data.materials.get(mn) or bpy.data.materials.new(name=mn); m.diffuse_color = col; mats.append(m)
        ml, mt, mf = mats
        def setup_obj(n, p, parent, target, is_z, ref, r_obj):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.0004, depth=1.0); cl = context.active_object; cl.name, cl.parent = f"L_{n}", parent
            cl.constraints.new('STRETCH_TO').target = target; cl.location = (p.x, p.y, ref) if is_z else (ref, p.y, p.z)
            if ml.name not in cl.data.materials: cl.data.materials.append(ml)
            bpy.ops.object.text_add(); to = context.active_object; to.name, to.parent = f"T_{n}", parent
            to.data.body, to.data.size, to.data.extrude, to.data.align_x, to.data.align_y = f"{abs((p.z if is_z else p.x) - ref):.1f}", s.cmf_cant_font_size, 0.1, 'CENTER', 'CENTER'
            if mt.name not in to.data.materials: to.data.materials.append(mt)
            m = bpy.data.meshes.new(f"M_{n}"); fo = bpy.data.objects.new(f"F_{n}", m); context.collection.objects.link(fo); fo.parent = parent
            m.from_pydata([(-0.5,-0.5,0), (0.5,-0.5,0), (0.5,0.5,0), (-0.5,0.5,0)], [], [(0,1,2,3)]); m.update()
            if mf.name not in fo.data.materials: fo.data.materials.append(mf)
            to.rotation_euler = fo.rotation_euler = (math.radians(90), 0.0, 0.0)
            def up(s_ev, d_ev=None):
                try:
                    r, cp = (pos(r_obj).z if is_z else pos(r_obj).x), pos(target); v = cp.z if is_z else cp.x
                    to.data.body, to.data.size = f"{abs(v - r):.1f}", s.cmf_cant_font_size
                    fo.scale.x, fo.scale.y = s.cmf_cant_font_size * 2.4, s.cmf_cant_font_size * 1.1
                    tx, ty, tz = cp.x + s.cmf_cant_offset_x, cp.y + s.cmf_cant_offset_y, cp.z + s.cmf_cant_offset_z
                    to.location, fo.location = (tx, ty, tz), (tx, ty + 0.2, tz)
                except: pass
            if hasattr(bpy.app.handlers, 'depsgraph_update_post'): bpy.app.handlers.depsgraph_update_post.append(up)
        if lo:
            zr = pos(lo).z
            for d in D:
                od = find_obj([f"{d}_POS", d, f"V {d}"])
                if od: ct = bpy.data.objects.new(f"MEDIDA_CANT_{d}", None); context.collection.objects.link(ct); setup_obj(d, pos(od), ct, od, True, zr, lo)
        if po:
            xr = pos(po).x; lms = find_obj(["LMS_POS"])
            if lms: clm = bpy.data.objects.new("MEDIDA_LM_LMS", None); context.collection.objects.link(clm); setup_obj("LM", pos(lms), clm, lms, False, xr, po)
            for sfx in ASYM[1:]:
                go = find_obj([sfx])
                if go: c_asym = bpy.data.objects.new(f"MEDIDA_ASYM_{sfx}", None); context.collection.objects.link(c_asym); setup_obj(sfx, pos(go), c_asym, go, False, xr, po)
        context.view_layer.update(); self.report({'INFO'}, "Finalizado!"); return {'FINISHED'}

class CMF_OT_ExpCSV(bpy.types.Operator):
    bl_idname, bl_label = "cmf.exp_csv", "Exportar Planilha Calc"
    def execute(self, context):
        s, target_dir = context.scene, "C:\\CMF_Library"
        os.makedirs(target_dir, exist_ok=True)
        lo, po = s.objects.get(s.cmf_linha_cant), s.objects.get(s.cmf_linha_plv)
        path = os.path.join(target_dir, f"CMF_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, delimiter=';'); w.writerow(["Parametro", "Valor (mm)", "Referencia"])
            if lo:
                zr = pos(lo).z
                for d in D:
                    o = find_obj([f"{d}_POS", d, f"V {d}"])
                    w.writerow([f"Dente {d} (CANT)", f"{abs(pos(o).z - zr):.2f}".replace('.', ',') if o else "N/E", lo.name])
            if po:
                xr = pos(po).x
                for n in ASYM:
                    o, lbl = find_obj([n]), n.replace("_POS", "") if n == "LMI_POS" else n
                    w.writerow([f"{lbl} (Assimetria)", f"{abs(pos(o).x - xr):.2f}".replace('.', ',') if o else "N/E", po.name])
        os.startfile(target_dir); self.report({'INFO'}, f"Salvo: {path}"); return {'FINISHED'}

class CMF_OT_ToggleCantVisibility(bpy.types.Operator):
    bl_idname, bl_label = "cmf.toggle_cant_visibility", "Visibilidade"
    obj_name: bpy.props.StringProperty()
    def execute(self, context):
        p = context.scene.objects.get(self.obj_name)
        if p:
            st = not p.hide_viewport; p.hide_viewport = st
            for c in p.children: c.hide_viewport = st
        return {'FINISHED'}

class CMF_OT_DeleteCantObjects(bpy.types.Operator):
    bl_idname, bl_label = "cmf.delete_cant_objects", "Deletar"
    obj_name: bpy.props.StringProperty()
    def execute(self, context):
        p = context.scene.objects.get(self.obj_name)
        if p:
            for c in list(p.children): bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.objects.remove(p, do_unlink=True)
        return {'FINISHED'}

CLASSES = (CMF_PT_CantPanel, CMF_OT_CreatePhysicalCant, CMF_OT_ExpCSV, CMF_OT_ToggleCantVisibility, CMF_OT_DeleteCantObjects)

def register():
    for k, t, n, d in PROPS:
        setattr(bpy.types.Scene, k, bpy.props.StringProperty(name=n) if t == "String" else bpy.props.FloatProperty(name=n, default=d, min=-200.0 if n != "Tam" else 1.0, max=200.0 if n != "Tam" else 30.0))
    for cls in CLASSES:
        try: bpy.utils.unregister_class(cls)
        except: pass
        bpy.utils.register_class(cls)

def unregister():
    for cls in CLASSES:
        try: bpy.utils.unregister_class(cls)
        except: pass
    for k, _, _, _ in PROPS:
        if hasattr(bpy.types.Scene, k): delattr(bpy.types.Scene, k)

if __name__ == "__main__":
    register()