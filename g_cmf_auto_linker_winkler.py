bl_info = {"name": "CMF Auto Linker Winkler", "author": "Dr. Winkler / IA Google", "version": (1, 2), "blender": (4, 2, 0), "location": "View3D > Barra Lateral (N) > Aba Tool", "category": "Interface"}
import bpy

HIERARQUIA_CMF = {
    "MX_POS": ["11_POS", "13_POS", "17_POS", "21_POS", "23_POS", "27_POS", "A_POS", "ENA_POS", "ENP_POS", "LMS_POS", "MD_POS"],
    "MD_POS": ["MD_MENTO"],
    "MD_MENTO": ["31_POS", "33_POS", "37_POS", "41_POS", "43_POS", "47_POS", "B_POS", "Gn_POS", "LMI_POS", "Me_POS", "Pg_POS", "MENTO"],
    "RMD_POS": ["GoDir_POS"],
    "RME_POS": ["GoEsq_POS"]
}

def find_obj(scene, nome):
    nl = nome.strip().lower()
    return next((o for o in scene.objects if o.name.strip().lower() == nl), None)

def parentar_mantendo_posicao(filho, pai):
    if filho.parent == pai: return
    mw = filho.matrix_world.copy()
    filho.parent = pai
    filho.matrix_parent_inverse = pai.matrix_world.inverted()
    filho.matrix_world = mw

class CMF_PT_AutoLinkerPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Hierarquia Cirúrgica CMF", "CMF_PT_auto_linker_panel", 'VIEW_3D', 'UI', 'Tool'
    def draw(self, context):
        l, s = self.layout, context.scene
        l.operator("cmf.linkar_objetos", text="Linkar Objetos", icon='LINKED')
        if s.cmf_linker_status == "OK":
            l.box().label(text="Linkado!", icon='CHECKMARK')
        elif s.cmf_linker_status == "MISSING" and s.cmf_linker_missing:
            box = l.box()
            box.label(text="Faltam objetos para linkar:", icon='ERROR')
            col = box.column(align=True)
            for item in s.cmf_linker_missing.split("|"):
                if item: col.label(text=f"• {item}", icon='DOT')

class CMF_OT_LinkarObjetos(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.linkar_objetos", "Linkar Objetos", {'REGISTER', 'UNDO'}
    def execute(self, context):
        scene = context.scene
        faltando, pares = [], []
        for nome_pai, lista_filhos in HIERARQUIA_CMF.items():
            obj_pai = find_obj(scene, nome_pai)
            if not obj_pai and nome_pai not in faltando: faltando.append(nome_pai)
            for nome_filho in lista_filhos:
                obj_filho = find_obj(scene, nome_filho)
                if not obj_filho and nome_filho not in faltando: faltando.append(nome_filho)
                elif obj_pai and obj_filho: pares.append((obj_filho, obj_pai))
        if faltando:
            scene.cmf_linker_status = "MISSING"
            scene.cmf_linker_missing = "|".join(faltando)
            self.report({'WARNING'}, f"Faltam {len(faltando)} objeto(s): {', '.join(faltando)}")
            return {'CANCELLED'}
        for obj_filho, obj_pai in pares:
            parentar_mantendo_posicao(obj_filho, obj_pai)
        context.view_layer.update()
        scene.cmf_linker_status = "OK"
        scene.cmf_linker_missing = ""
        self.report({'INFO'}, "Linkado!")
        return {'FINISHED'}

def register():
    bpy.types.Scene.cmf_linker_status = bpy.props.StringProperty(default="")
    bpy.types.Scene.cmf_linker_missing = bpy.props.StringProperty(default="")
    bpy.utils.register_class(CMF_PT_AutoLinkerPanel)
    bpy.utils.register_class(CMF_OT_LinkarObjetos)

def unregister():
    bpy.utils.unregister_class(CMF_PT_AutoLinkerPanel)
    bpy.utils.unregister_class(CMF_OT_LinkarObjetos)
    del bpy.types.Scene.cmf_linker_status
    del bpy.types.Scene.cmf_linker_missing

if __name__ == "__main__": register()