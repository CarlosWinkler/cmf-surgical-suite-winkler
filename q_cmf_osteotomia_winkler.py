bl_info = {
    "name": "CMF Osteotomia por Cubo Winkler",
    "author": "Dr. Winkler / IA Google",
    "version": (4, 7),
    "blender": (4, 2, 0),
    "location": "View3D > Barra Lateral (N) > Aba Tool",
    "category": "Interface",
}

import bpy

class CMF_PT_CuboCortePanel(bpy.types.Panel):
    bl_label = "Serra por Cubo Winkler (0.8mm)"
    bl_idname = "CMF_PT_cubo_corte_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        layout.operator("cmf.add_surgical_cube", text="1. Adicionar Lâmina", icon='MESH_CUBE')
        layout.separator()
        layout.operator("cmf.execute_cube_boolean_saw", text="2. Cortar e Separar (Shift)", icon='MOD_BOOLEAN')

class CMF_OT_AddSurgicalCube(bpy.types.Operator):
    bl_idname = "cmf.add_surgical_cube"
    bl_label = "Adicionar Lâmina (0.8mm)"
    
    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cubo = context.active_object
        cubo.name = "LAMINA_SERRA_0.8mm"
        cubo.dimensions = (140.0, 140.0, 0.8)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        mat = bpy.data.materials.get("Mat_Lamina_Cirurgica") or bpy.data.materials.new(name="Mat_Lamina_Cirurgica")
        mat.diffuse_color = (1.0, 0.1, 0.1, 0.5)
        if cubo.data.materials: cubo.data.materials = mat
        else: cubo.data.materials.append(mat)
        return {'FINISHED'}

class CMF_OT_ExecuteCubeBooleanSaw(bpy.types.Operator):
    bl_idname = "cmf.execute_cube_boolean_saw"
    bl_label = "Executar Corte e Separar"
    
    def execute(self, context):
        sel = context.selected_objects
        if len(sel) != 2:
            self.report({'ERROR'}, "Selecione 2 objetos com SHIFT: o Osso e a Lâmina Vermelha!")
            return {'CANCELLED'}
            
        obj_cubo = None
        obj_osso = None
        
        for obj in sel:
            if "LAMINA_SERRA" in obj.name.upper():
                obj_cubo = obj
            else:
                obj_osso = obj
                
        if not obj_osso or not obj_cubo or obj_osso.type != 'MESH' or obj_cubo.type != 'MESH':
            self.report({'ERROR'}, "A seleção deve conter o Modelo do Osso e a Lâmina Vermelha!")
            return {'CANCELLED'}
            
        context.view_layer.objects.active = obj_osso
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        mod = obj_osso.modifiers.new(name="CMF_Corte_Serra", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = obj_cubo
        mod.solver = 'EXACT'
        
        bpy.ops.object.modifier_apply(modifier="CMF_Corte_Serra")
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # MODIFICAÇÃO CIRÚRGICA: A linha de deleção foi removida! O cubo vermelho permanece vivo na cena.
        
        self.report({'INFO'}, "Osteotomia executada! Lâmina mantida para o próximo corte.")
        return {'FINISHED'}

def register():
    try: bpy.utils.unregister_class(CMF_PT_CuboCortePanel)
    except: pass
    bpy.utils.register_class(CMF_PT_CuboCortePanel)
    bpy.utils.register_class(CMF_OT_AddSurgicalCube)
    bpy.utils.register_class(CMF_OT_ExecuteCubeBooleanSaw)

if __name__ == "__main__":
    register()