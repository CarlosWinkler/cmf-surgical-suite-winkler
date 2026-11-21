bl_info = {
    "name": "CMF Photomapping Winkler",
    "author": "Dr. Winkler / IA Google",
    "version": (3, 9),
    "blender": (4, 2, 9),
    "location": "View3D > Barra Lateral (N) > Aba Tool",
    "category": "Interface",
}

import bpy

class CMF_PT_PhotomappingPanel(bpy.types.Panel):
    bl_label = "Mapeamento Fotográfico (CMF)"
    bl_idname = "CMF_PT_photomapping_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="Mapeamento por Projeção Direta de Malha:", icon='IMAGE_DATA')
        box = layout.box()
        box.prop_search(scene, "cmf_photo_mesh", scene, "objects", text="Face 3D (STL)")
        box.prop_search(scene, "cmf_photo_plane_obj", scene, "objects", text="Plano da Foto (Mesh)")
        
        layout.separator()
        layout.operator("cmf.execute_scene_project_saw", text="Carimbar Foto na Face 3D", icon='SHADING_TEXTURE')
        
        layout.separator()
        box_hud = layout.box()
        box_hud.label(text="Sliders de Pré-visualização / Ajuste:", icon='GREASEPENCIL')
        box_hud.prop(scene, "cmf_lat_scale", text="Zoom Ajuste")
        box_hud.prop(scene, "cmf_lat_x", text="Deslocar X (Lados)")
        box_hud.prop(scene, "cmf_lat_z", text="Deslocar Z (Altura)")

class CMF_OT_ExecuteSceneProjectSaw(bpy.types.Operator):
    bl_idname = "cmf.execute_scene_project_saw"
    bl_label = "Carimbar Foto na Face 3D"
    
    def execute(self, context):
        scene = context.scene
        obj_face = scene.objects.get(scene.cmf_photo_mesh)
        obj_plane = scene.objects.get(scene.cmf_photo_plane_obj)
        
        if not obj_face or not obj_plane:
            self.report({'ERROR'}, "Selecione a face STL e o plano da foto nos campos!")
            return {'CANCELLED'}
            
        context.view_layer.objects.active = obj_plane
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        context.view_layer.objects.active = obj_face
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        img_material = obj_plane.active_material
        if not img_material or not img_material.use_nodes:
            self.report({'ERROR'}, "O plano da foto precisa ter uma imagem no material!")
            return {'CANCELLED'}
            
        tex_img = None
        for node in img_material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                tex_img = node.image
                break
                
        if not tex_img:
            self.report({'ERROR'}, "Nenhuma imagem de textura encontrada no plano selecionado!")
            return {'CANCELLED'}
            
        uv_name = "UV_Frontal" if "FRONT" in obj_plane.name.upper() else "UV_Lateral"
        
        uv_layers = obj_face.data.uv_layers
        uv_layer = uv_layers.get(uv_name) or uv_layers.new(name=uv_name)
        uv_layers.active = uv_layer
        
        mod = obj_face.modifiers.new(name="CMF_Scene_Project", type='DATA_TRANSFER')
        mod.object = obj_plane
        mod.use_loop_data = True
        mod.data_types_loops = {'UV'}
        mod.loop_mapping = 'NEAREST_POLYNOR'
        
        if obj_plane.data.uv_layers.active:
            mod.layers_uv_select_src = obj_plane.data.uv_layers.active.name
        mod.layers_uv_select_dst = uv_name
        
        bpy.ops.object.modifier_apply(modifier="CMF_Scene_Project")
        
        mat_name = f"Mat_Face_Projetada_{obj_face.name}"
        mat_face = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
        mat_face.use_nodes = True
        nodes = mat_face.node_tree.nodes
        links = mat_face.node_tree.links
        
        nodes.clear()
        node_output = nodes.new(type='ShaderNodeOutputMaterial')
        node_emission = nodes.new(type='ShaderNodeEmission') # AUTO-ILUMINAÇÃO CIRÚRGICA ATIVA
        
        node_mix = nodes.new(type='ShaderNodeMix')
        node_mix.data_type = 'RGBA'
        node_mix.blend_type = 'MIX'
        node_mix.inputs['Factor'].default_value = 0.016
        
        node_uv = nodes.new(type='ShaderNodeAttribute')
        node_uv.attribute_name = uv_name
        node_mapping = nodes.new(type='ShaderNodeMapping')
        node_tex = nodes.new(type='ShaderNodeTexImage')
        node_tex.image = tex_img
        node_tex.extension = 'CLIP'
        
        # AMARRAS DE EMISSÃO BRILHANTE (Anula a dependência de lâmpadas na cena)
        links.new(node_uv.outputs['Vector'], node_mapping.inputs['Vector'])
        links.new(node_mapping.outputs['Vector'], node_tex.inputs['Vector'])
        links.new(node_tex.outputs['Color'], node_mix.inputs['A'])
        links.new(node_mix.outputs['Result'], node_emission.inputs['Color'])
        links.new(node_emission.outputs['Emission'], node_output.inputs['Surface'])
            
        obj_face.active_material = mat_face
        
        def refresh_marcos_foto(scene_eval, depsgraph=None):
            try:
                sc = 1.0 / scene.cmf_lat_scale if scene.cmf_lat_scale != 0 else 1.0
                node_mapping.inputs['Scale'].x = sc
                node_mapping.inputs['Scale'].y = sc
                node_mapping.inputs['Location'].x = (-scene.cmf_lat_x * sc) + 0.5
                node_mapping.inputs['Location'].y = (scene.cmf_lat_z * sc) + 0.5
            except: pass

        if refresh_marcos_foto not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(refresh_marcos_foto)
            
        self.report({'INFO'}, f"Foto projetada! Use os sliders para ajustar a posição.")
        return {'FINISHED'}

def register():
    try: bpy.utils.unregister_class(CMF_PT_PhotomappingPanel)
    except: pass
    try: bpy.utils.unregister_class(CMF_OT_ExecuteSceneProjectSaw)
    except: pass

    if not hasattr(bpy.types.Scene, "cmf_photo_mesh"):
        bpy.types.Scene.cmf_photo_mesh = bpy.props.StringProperty(name="Malha da Face")
    if not hasattr(bpy.types.Scene, "cmf_photo_plane_obj"):
        bpy.types.Scene.cmf_photo_plane_obj = bpy.props.StringProperty(name="Plano da Foto")
        
    bpy.types.Scene.cmf_lat_scale = bpy.props.FloatProperty(name="Zoom Ajuste", default=1.0, min=0.001, max=100.0)
    bpy.types.Scene.cmf_lat_x = bpy.props.FloatProperty(name="Deslocar X", default=0.0, min=-500.0, max=500.0)
    bpy.types.Scene.cmf_lat_z = bpy.props.FloatProperty(name="Deslocar Z", default=0.0, min=-500.0, max=500.0)
    
    bpy.utils.register_class(CMF_PT_PhotomappingPanel)
    bpy.utils.register_class(CMF_OT_ExecuteSceneProjectSaw)

def unregister():
    bpy.utils.unregister_class(CMF_PT_PhotomappingPanel)
    bpy.utils.unregister_class(CMF_OT_ExecuteSceneProjectSaw)

if __name__ == "__main__":
    register()