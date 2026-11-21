bl_info = {"name": "CMF Estrutura de Pastas", "author": "Dr. Winkler / IA Google", "version": (1, 1), "blender": (4, 2, 0), "location": "View3D > Barra Lateral (N) > Aba Tool", "category": "Interface"}
import bpy

ESTRUTURA_PASTAS = [
    ("CRANIO COMPOSTO", "NONE", []),
    ("COMUM", "NONE", []),
    ("PRE_SIMULAÇÃO", "COLOR_04", ["SEG_MX_PRE", "SEG_MD_PRE"]),
    ("POS_SIMULAÇÃO", "COLOR_05", ["SEG_MX_POS", "SEG_MD_POS"]),
    ("REG. MOVIMENTO PRE", "COLOR_03", ["R_MX_PRE", "R_MD_PRE"]),
    ("REG. MOVIMENTO POS", "COLOR_02", ["R_MX_POS", "R_MD_POS"]),
    ("CEFALOMETRIA FIXA", "COLOR_01", []),
    ("CEFALOMETRIA MOVEL", "COLOR_03", []),
    ("TECIDO MOLE", "COLOR_06", []),
    ("FOTOS PACIENTE", "COLOR_05", []),
    ("GUIAS", "NONE", []),
    ("PLACAS_PARAF", "NONE", []),
]

def obter_ou_criar_colecao(nome, pai, color_tag="NONE"):
    col = bpy.data.collections.get(nome)
    if not col:
        col = bpy.data.collections.new(nome)
    if col.name not in pai.children:
        pai.children.link(col)
    if color_tag != "NONE":
        col.color_tag = color_tag
    return col

class CMF_OT_CriarPastas(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.criar_pastas", "Criar Pastas", {'REGISTER', 'UNDO'}
    def execute(self, ctx):
        cena_raiz = ctx.scene.collection
        for nome_pai, tag, subs in ESTRUTURA_PASTAS:
            col_pai = obter_ou_criar_colecao(nome_pai, cena_raiz, tag)
            for sub in subs:
                obter_ou_criar_colecao(sub, col_pai, tag)
        ctx.scene.cmf_pastas_msg = "Pastas criadas!"
        self.report({'INFO'}, "Pastas criadas!")
        return {'FINISHED'}

class CMF_PT_CriarPastasPanel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Organização CMF", "CMF_PT_criar_pastas", 'VIEW_3D', 'UI', 'Tool'
    def draw(self, ctx):
        l, s = self.layout, ctx.scene
        l.operator("cmf.criar_pastas", text="Criar Pastas", icon='NEWFOLDER')
        if s.cmf_pastas_msg:
            l.box().label(text=s.cmf_pastas_msg, icon='CHECKMARK')

CLASSES = (CMF_OT_CriarPastas, CMF_PT_CriarPastasPanel)
def register():
    bpy.types.Scene.cmf_pastas_msg = bpy.props.StringProperty(default="")
    for c in CLASSES: bpy.utils.register_class(c)
def unregister():
    for c in reversed(CLASSES): bpy.utils.unregister_class(c)
    del bpy.types.Scene.cmf_pastas_msg
if __name__ == "__main__": register()