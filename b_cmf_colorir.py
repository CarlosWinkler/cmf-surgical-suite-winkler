bl_info = {
    "name": "CMF Colorir",
    "author": "Assistente AI",
    "version": (1, 9),
    "blender": (4, 2, 0),
    "location": "View3D > Object Menu OU View3D > Sidebar (N) > CMF Colorir",
    "description": "Mapeamento automático de cores CMF para visualização em MatCap",
    "category": "Interface",
}

import bpy
import random

CORES_CMF = {
    "BRANCO": (1.0, 1.0, 1.0, 1.0),
    "AZUL_CLARO_BRANCO": (0.85, 0.93, 0.98, 1.0),
    "AZUL_FRANCIA": (0.0, 0.31, 0.73, 1.0),
    "AMARELO_LIMAO": (0.75, 0.89, 0.14, 1.0),
    "ROXO_VIOLET": (0.54, 0.17, 0.89, 1.0),
    "VERDE_PRIMAVERA": (0.0, 1.0, 0.5, 1.0),
    "VERMELHO_CARMIN": (0.59, 0.0, 0.09, 1.0),
    "AZUL_BEBE": (0.68, 0.85, 0.90, 1.0),
}

class OBJECT_OT_cmf_colorir_duplo(bpy.types.Operator):
    bl_idname = "object.cmf_colorir_duplo"
    bl_label = "Colorir Peças Anatômicas"
    bl_description = "Aplica as cores automáticas nos objetos baseado nos nomes cadastrados"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        random.seed()
        count_mapped = 0
        count_random = 0
        
        for obj in context.blend_data.objects:
            if obj.type == 'MESH':
                name = obj.name.upper().strip()
                cor_definida = None
                
                # 1. Regras ultraespecíficas primeiro (Ex: dentes e ramos)
                if "DENT_MX" in name or "DENT_MD" in name:
                    cor_definida = CORES_CMF["VERMELHO_CARMIN"]
                elif any(x in name for x in ["RMD_PRE", "RME_PRE", "RMD_POS", "RME_POS"]):
                    cor_definida = CORES_CMF["VERDE_PRIMAVERA"]
                
                # 2. Regras de segmentos específicos com prefixos/sufixos
                elif any(x in name for x in ["MD_PRE", "MD_POS", "MD_CUT", "MD_MENTO"]):
                    cor_definida = CORES_CMF["AMARELO_LIMAO"]
                elif any(x in name for x in ["MX_PRE", "MX_POS"]):
                    cor_definida = CORES_CMF["AZUL_FRANCIA"]
                elif "FACE_PRE" in name or "FACE_POS" in name:
                    cor_definida = CORES_CMF["AZUL_BEBE"]
                
                # 3. Termos genéricos ou estruturas anatômicas isoladas (Mentoplastia, Calvária)
                elif "MENTO" in name:  
                    cor_definida = CORES_CMF["ROXO_VIOLET"]
                elif "MD" in name:
                    cor_definida = CORES_CMF["AMARELO_LIMAO"]
                elif "MX" in name:
                    cor_definida = CORES_CMF["AZUL_FRANCIA"]
                elif "CALV" in name or "CR" in name:
                    cor_definida = CORES_CMF["BRANCO"]
                
                # Aplicação da cor
                if cor_definida:
                    obj.color = cor_definida
                    count_mapped += 1
                else:
                    obj.color = (random.random(), random.random(), random.random(), 1.0)
                    count_random += 1
                    
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
                
        self.report({'INFO'}, f"Mapeados: {count_mapped} | Aleatórios: {count_random}")
        return {'FINISHED'}

# Painel na Barra Lateral N
class VIEW3D_PT_cmf_colorir_sidebar(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CMF Colorir'
    bl_label = "Simulação Cirúrgica"
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Fluxo Digital Simplificado:")
        layout.operator("object.cmf_colorir_duplo", icon='COLOR')

# Botão no menu Object do topo
def menu_func_duplo(self, context):
    self.layout.separator()
    self.layout.operator(OBJECT_OT_cmf_colorir_duplo.bl_idname, icon='COLOR', text="CMF Colorir")

def register():
    bpy.utils.register_class(OBJECT_OT_cmf_colorir_duplo)
    bpy.utils.register_class(VIEW3D_PT_cmf_colorir_sidebar)
    bpy.types.VIEW3D_MT_object.append(menu_func_duplo)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_cmf_colorir_duplo)
    bpy.utils.unregister_class(VIEW3D_PT_cmf_colorir_sidebar)
    bpy.types.VIEW3D_MT_object.remove(menu_func_duplo)

if __name__ == "__main__":
    register()