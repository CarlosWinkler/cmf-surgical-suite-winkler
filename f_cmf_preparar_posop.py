bl_info = {"name": "CMF Preparar Pós-Operatório (Auto-POS)", "author": "Dr. Winkler / IA Google", "version": (1, 3), "blender": (4, 2, 0), "location": "View3D > Barra Lateral (N) > Aba Tool", "category": "Interface"}
import bpy, mathutils

MAPA_COLECOES = [
    ("SEG_MX_PRE", "SEG_MX_POS", "POS_SIMULAÇÃO", "COLOR_05"),
    ("SEG_MD_PRE", "SEG_MD_POS", "POS_SIMULAÇÃO", "COLOR_05"),
    ("R_MX_PRE", "R_MX_POS", "REG. MOVIMENTO POS", "COLOR_02"),
    ("R_MD_PRE", "R_MD_POS", "REG. MOVIMENTO POS", "COLOR_02"),
]

HIERARQUIA_POS = {
    "MX_POS": ["11_POS", "13_POS", "17_POS", "21_POS", "23_POS", "27_POS", "A_POS", "ENA_POS", "ENP_POS", "LMS_POS", "MD_POS"],
    "MD_POS": ["MD_MENTO"],
    "MD_MENTO": ["31_POS", "33_POS", "37_POS", "41_POS", "43_POS", "47_POS", "B_POS", "Gn_POS", "LMI_POS", "Me_POS", "Pg_POS", "MENTO"],
    "RMD_POS": ["GoDir_POS"],
    "RME_POS": ["GoEsq_POS"],
}

def get_or_create_col(nome, pai, tag="NONE"):
    col = bpy.data.collections.get(nome) or bpy.data.collections.new(nome)
    if col.name not in pai.children: pai.children.link(col)
    if tag != "NONE": col.color_tag = tag
    return col

def find_obj(scene, nome):
    nl = nome.strip().lower()
    return next((o for o in scene.objects if o.name.strip().lower() == nl), None)

def origin_to_geometry_seguro(obj):
    if not obj or obj.type != 'MESH' or not obj.data or len(obj.data.vertices) == 0: return
    centro_local = sum((mathutils.Vector(b) for b in obj.bound_box), mathutils.Vector()) / 8.0
    if centro_local.length < 1e-6: return
    obj.data.transform(mathutils.Matrix.Translation(-centro_local))
    obj.data.update()
    obj.matrix_world.translation = obj.matrix_world @ centro_local

def parentar(filho, pai):
    if not filho or not pai or filho.parent == pai: return
    mw = filho.matrix_world.copy()
    filho.parent = pai
    filho.matrix_parent_inverse = pai.matrix_world.inverted()
    filho.matrix_world = mw

class CMF_OT_PrepararAutoPOS(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.preparar_auto_pos", "Preparar Pós-Operatório (Auto-POS)", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        scene = ctx.scene
        raiz = scene.collection
        criados, objetos_pos = 0, []

        for orig_nome, dest_nome, pai_dest_nome, tag in MAPA_COLECOES:
            col_orig = bpy.data.collections.get(orig_nome)
            if not col_orig: continue
            col_pai_dest = get_or_create_col(pai_dest_nome, raiz, tag)
            col_dest = get_or_create_col(dest_nome, col_pai_dest, tag)

            for obj in list(col_orig.objects):
                if obj.name.endswith("_PRE"):
                    novo_nome = obj.name[:-4] + "_POS"
                elif obj.name in ("MD_MENTO", "MENTO"):
                    if obj.name not in col_dest.objects: col_dest.objects.link(obj)
                    if obj.name in col_orig.objects: col_orig.objects.unlink(obj)
                    objetos_pos.append(obj)
                    continue
                else:
                    novo_nome = obj.name + "_POS"

                existente = find_obj(scene, novo_nome)
                if existente:
                    objetos_pos.append(existente)
                    continue

                novo_obj = obj.copy()
                if obj.data: novo_obj.data = obj.data.copy()
                novo_obj.name = novo_nome
                novo_obj.matrix_world = obj.matrix_world.copy()
                col_dest.objects.link(novo_obj)
                objetos_pos.append(novo_obj)
                criados += 1

        for obj_p in objetos_pos:
            origin_to_geometry_seguro(obj_p)
        ctx.view_layer.update()

        links_feitos = 0
        for nome_pai, filhos in HIERARQUIA_POS.items():
            op = find_obj(scene, nome_pai)
            if not op: continue
            for nf in filhos:
                of = find_obj(scene, nf)
                if of:
                    parentar(of, op)
                    links_feitos += 1

        ctx.view_layer.update()
        scene.cmf_autopos_msg = f"OK! {criados} criados, origens centralizadas e {links_feitos} links."
        self.report({'INFO'}, scene.cmf_autopos_msg)
        return {'FINISHED'}

class CMF_PT_AutoPOSPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Automação Pós-Operatória", "CMF_PT_auto_pos", 'VIEW_3D', 'UI', 'Tool'
    def draw(self, ctx):
        l, s = self.layout, ctx.scene
        l.operator("cmf.preparar_auto_pos", text="Preparar Pós-Operatório (Auto-POS)", icon='DUPLICATE')
        if s.cmf_autopos_msg: l.box().label(text=s.cmf_autopos_msg, icon='CHECKMARK')

CLASSES = (CMF_OT_PrepararAutoPOS, CMF_PT_AutoPOSPanel)
def register():
    bpy.types.Scene.cmf_autopos_msg = bpy.props.StringProperty(default="")
    for c in CLASSES: bpy.utils.register_class(c)
def unregister():
    for c in reversed(CLASSES): bpy.utils.unregister_class(c)
    del bpy.types.Scene.cmf_autopos_msg
if __name__ == "__main__": register()