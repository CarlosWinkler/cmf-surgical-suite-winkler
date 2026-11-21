bl_info = {
    "name": "Medida Dentaria",
    "author": "Dr. Winkler / Assistido por IA Google",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Barra Lateral (N) > Aba Medida Dentaria",
    "description": "Sistema leve e focado para registro e decomposição tridimensional (X, Y, Z) de movimentos maxilomandibulares.",
    "warning": "",
    "doc_url": "",
    "category": "Interface",
}

import bpy
import os
import csv

DICIONARIO_LANDMARKS = {
    "ENA": "Espinha nasal anterior",
    "ENP": "Espinha nasal posterior",
    "A": "Ponto A",
    "17": "2 Molar direito",
    "13": "Canino dir.",
    "11": "Incisivo central dir.",
    "LMS": "Linha media do incisivo sup",
    "21": "Incisivo central esq.",
    "23": "Canino esq.",
    "27": "2 Molar esquerdo",
    "37": "2 Molar esq.",
    "33": "Canino esq.",
    "31": "Incisivo central esq.",
    "LMI": "Linha media do incisivo inf",
    "41": "Incisivo central dir.",
    "43": "Canino dir.",
    "47": "2 Molar dir.",
    "B": "Ponto B",
    "Pg": "Pogonio",
    "Me": "Mento"
}

class CEF_PT_PrinterizePanel(bpy.types.Panel):
    bl_label = "REGISTRO DE MOVIMENTOS PRÉ E PÓS"
    bl_idname = "CEF_PT_printerize_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Medida Dentaria'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="Medida Dentaria", icon='SPREADSHEET')
        
        box = layout.box()
        box.operator("cmf.export_printerize_csv", text="Exportar Planilha para LibreOffice", icon='EXPORT')
        
        layout.separator()
        layout.label(text="Monitor de Deslocamento (mm):", icon='INFO')
        
        for ref, desc in DICIONARIO_LANDMARKS.items():
            obj_pre = scene.objects.get(f"{ref}_PRE")
            obj_pos = scene.objects.get(f"{ref}_POS")
            
            row = layout.row()
            if obj_pre and obj_pos:
                loc_pre = obj_pre.matrix_world.to_translation()
                loc_pos = obj_pos.matrix_world.to_translation()
                
                dx = loc_pos.x - loc_pre.x
                dy = -(loc_pos.y - loc_pre.y)
                dz = loc_pos.z - loc_pre.z
                
                row.label(text=f"{ref}: X:{dx:+.1f} | Y:{dy:+.1f} | Z:{dz:+.1f}", icon='CHECKMARK')
            else:
                row.label(text=f"{ref}: Aguardando esferas _{ref}_PRE e _{ref}_POS", icon='BLANK1')
            
            if ref == "27":
                layout.separator()

class CMF_OT_ExportPrinterizeCSV(bpy.types.Operator):
    bl_idname = "cmf.export_printerize_csv"
    bl_label = "Exportar Medida Dentaria"
    
    def execute(self, context):
        scene = context.scene
        pasta_saida = r"C:\CMF_Library"
        if not os.path.exists(pasta_saida):
            os.makedirs(pasta_saida)
            
        caminho_file = os.path.join(pasta_saida, "Tabela_Movimentacao_Printerize3D.csv")
        
        try:
            with open(caminho_file, mode='w', newline='', encoding='utf-8') as f:
                escritor = csv.writer(f, delimiter=';')
                
                cabecalho = ["REF", "Descrição", "Dir.", "Esq.", "Recua", "Avança", "Desce", "Sobe"]
                escritor.writerow(cabecalho)
                
                for ref, desc in DICIONARIO_LANDMARKS.items():
                    obj_pre = scene.objects.get(f"{ref}_PRE")
                    obj_pos = scene.objects.get(f"{ref}_POS")
                    
                    if obj_pre and obj_pos:
                        loc_pre = obj_pre.matrix_world.to_translation()
                        loc_pos = obj_pos.matrix_world.to_translation()
                        
                        dx = loc_pos.x - loc_pre.x
                        dy = -(loc_pos.y - loc_pre.y)
                        dz = loc_pos.z - loc_pre.z
                        
                        dir = f"{abs(dx):.2f}".replace('.', ',') if dx < 0 else "-"
                        esq_ = f"{abs(dx):.2f}".replace('.', ',') if dx > 0 else "-"
                        recua = f"{abs(dy):.2f}".replace('.', ',') if dy < 0 else "-"
                        avanca = f"{abs(dy):.2f}".replace('.', ',') if dy > 0 else "-"
                        desce = f"{abs(dz):.2f}".replace('.', ',') if dz < 0 else "-"
                        sobe = f"{abs(dz):.2f}".replace('.', ',') if dz > 0 else "-"
                        
                        if abs(dx) < 0.01: dir = esq_ = "0,00"
                        if abs(dy) < 0.01: recua = avanca = "0,00"
                        if abs(dz) < 0.01: desce = sobe = "0,00"
                        
                        escritor.writerow([ref, desc, dir, esq_, recua, avanca, desce, sobe])
                    else:
                        escritor.writerow([ref, desc, "Não mapeado", "-", "-", "-", "-", "-"])
                    
                    if ref == "27":
                        escritor.writerow(cabecalho)
                        
            self.report({'INFO'}, f"Tabela exportada com sucesso para {caminho_file}")
            os.startfile(pasta_saida)
            
        except Exception as e:
            self.report({'ERROR'}, f"Falha ao gerar o arquivo: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

def register():
    bpy.utils.register_class(CEF_PT_PrinterizePanel)
    bpy.utils.register_class(CMF_OT_ExportPrinterizeCSV)

def unregister():
    bpy.utils.unregister_class(CEF_PT_PrinterizePanel)
    bpy.utils.unregister_class(CMF_OT_ExportPrinterizeCSV)

if __name__ == "__main__":
    register()