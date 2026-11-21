bl_info = {"name": "CMF Detecção de Colisão Oclusal", "author": "Dr. Winkler / IA Google", "version": (1, 4), "blender": (4, 2, 0), "location": "View3D > Barra Lateral (N) > Aba Tool", "category": "Interface"}
import bpy, mathutils, numpy as np

def pintar_contatos(om, bvh, dlim=0.25):
    m = om.data; nv = len(m.vertices)
    if nv == 0: return
    mw = om.matrix_world
    co = np.empty(nv * 3, dtype=np.float64); m.vertices.foreach_get("co", co); co = co.reshape((nv, 3))
    rgba = np.tile(np.array([0.82, 0.72, 0.78, 1.0], dtype=np.float64), (nv, 1))
    for i in range(nv):
        hit, _, _, d = bvh.find_nearest(mw @ mathutils.Vector(co[i]))
        if hit is not None and d <= dlim:
            t = 1.0 - (d / dlim)
            rgba[i] = [np.clip(2.0*t, 0, 1), np.clip(2.0*(1.0 - abs(t - 0.5)), 0, 1), np.clip(1.0 - 2.5*t, 0, 1), 1.0]
    at = m.color_attributes.get("CMF_Contato") or m.color_attributes.new(name="CMF_Contato", type='BYTE_COLOR', domain='POINT')
    m.color_attributes.active_color = at; at.data.foreach_set("color", rgba.ravel()); m.update()
    for a in bpy.context.screen.areas:
        if a.type == 'VIEW_3D':
            for sp in a.spaces:
                if sp.type == 'VIEW_3D' and sp.shading.type == 'SOLID': sp.shading.color_type = 'VERTEX'
            a.tag_redraw()

def get_ancoras(vloc, mw, bvh, tol=0.08):
    prox, md, ps, pd = [], 1e9, None, None
    for v in vloc:
        pw = mw @ v; hit, _, _, d = bvh.find_nearest(pw)
        if hit is not None:
            if d < md: md, ps, pd = d, pw, hit
            if d <= tol: prox.append((d, pw))
    prox.sort(key=lambda x: x[0])
    anc = []
    for _, pt in prox:
        if all((pt - a).length > 8.0 for a in anc):
            anc.append(pt)
            if len(anc) == 3: break
    return md, ps, pd, anc

def resolver_colisao_view(om, vloc, bvh, delta, v_down, pos_travada, rot_acc, em_ajuste):
    mwo = om.matrix_world.copy()
    if not em_ajuste:
        mwt = mwo.copy(); mwt.translation += delta
        md, ps, pd, anc = get_ancoras(vloc, mwt, bvh)
        if md > 0.04 and not anc:
            om.matrix_world = mwt; return 0, False, None, 0.0
        _, _, _, ap = get_ancoras(vloc, mwo, bvh)
        if len(ap) >= 3:
            return 3, True, om.matrix_world.translation.copy(), 0.0
        elif len(ap) == 2:
            eixo = (ap[1] - ap[0]).normalized(); cen = (ap[0] + ap[1]) * 0.5
            sinal = 1.0 if delta.dot(eixo.cross(v_down).normalized()) >= 0 else -1.0
            ang = min(0.015, delta.length * 0.008) * sinal
            om.matrix_world = mathutils.Matrix.Translation(cen) @ mathutils.Matrix.Rotation(ang, 4, eixo) @ mathutils.Matrix.Translation(-cen) @ mwo
            nc = len(get_ancoras(vloc, om.matrix_world, bvh)[3])
            return nc, (nc >= 3), (om.matrix_world.translation.copy() if nc >= 3 else None), 0.0
        elif len(ap) == 1:
            er = delta.cross(-v_down)
            if er.length > 1e-5:
                ang = min(0.018, delta.length * 0.008)
                om.matrix_world = mathutils.Matrix.Translation(ap[0]) @ mathutils.Matrix.Rotation(ang, 4, er.normalized()) @ mathutils.Matrix.Translation(-ap[0]) @ mwo
            nc = len(get_ancoras(vloc, om.matrix_world, bvh)[3])
            return nc, (nc >= 3), (om.matrix_world.translation.copy() if nc >= 3 else None), 0.0
        else:
            if ps and pd: mwt.translation += (pd - ps); om.matrix_world = mwt
            return 1, False, None, 0.0
    else:
        desloc_plano = delta - v_down * delta.dot(v_down)
        offset = (mwo.translation + desloc_plano) - pos_travada
        offset_plano = offset - v_down * offset.dot(v_down)
        if offset_plano.length > 1.0: offset_plano = offset_plano.normalized() * 1.0
        mwt = mwo.copy()
        mwt.translation = pos_travada + offset_plano + v_down * offset.dot(v_down)
        md, ps, pd, anc = get_ancoras(vloc, mwt, bvh, tol=0.10)
        if ps and pd:
            corr = pd - ps
            if corr.dot(v_down) < 0: mwt.translation += v_down * corr.dot(v_down)
            elif md > 0.03: mwt.translation += v_down * min(md, 0.05)
        om.matrix_world = mwt
        return len(anc), True, pos_travada, rot_acc

class CMF_OT_LigueDetector(bpy.types.Operator):
    bl_idname, bl_label, bl_options = "cmf.ligue_detector", "Ligue Detector", {'REGISTER', 'UNDO'}
    def modal(self, ctx, ev):
        s = ctx.scene; om, of = s.objects.get(s.cmf_col_movel), s.objects.get(s.cmf_col_fixo)
        if not om or not of: return {'CANCELLED'}
        if ev.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and not self._ajuste: return {'PASS_THROUGH'}
        v_mat = ctx.region_data.view_matrix.inverted().to_3x3()
        v_right, v_up = v_mat.col[0].normalized(), v_mat.col[1].normalized()
        v_down = -v_up
        if self._ajuste and ev.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'LEFT_ARROW', 'RIGHT_ARROW'} and ev.value == 'PRESS':
            passo_deg = 0.25 if ev.type in {'WHEELUPMOUSE', 'RIGHT_ARROW'} else -0.25
            novo_rot = max(-1.0, min(1.0, self._rot_deg + passo_deg))
            d_rad = np.radians(novo_rot - self._rot_deg); self._rot_deg = novo_rot
            cen = om.matrix_world.translation
            om.matrix_world = mathutils.Matrix.Translation(cen) @ mathutils.Matrix.Rotation(d_rad, 4, v_down) @ mathutils.Matrix.Translation(-cen) @ om.matrix_world
            pintar_contatos(om, self._bvh); s.cmf_col_status = f"Ajuste | Giro: {self._rot_deg:+.2f}°"; return {'RUNNING_MODAL'}
        if ev.type == 'MOUSEMOVE':
            dy = (ev.mouse_y - self._ly) * (0.015 if self._ajuste else 0.04)
            dx = (ev.mouse_x - self._lx) * (0.015 if self._ajuste else 0.025)
            self._lx, self._ly = ev.mouse_x, ev.mouse_y
            nc, aj, pt, _ = resolver_colisao_view(om, self._v, self._bvh, (v_right * dx) + (v_up * dy), v_down, self._pos_trav, self._rot_deg, self._ajuste)
            if aj and not self._ajuste:
                self._ajuste, self._pos_trav = True, pt; pintar_contatos(om, self._bvh)
                ctx.workspace.status_text_set("3 PONTOS! Deslize <=1mm | Scroll/Setas: Girar ±1° | Clique Esq: Confirmar")
            elif self._ajuste: pintar_contatos(om, self._bvh)
            s.cmf_col_status = f"Ajuste (<=1mm | {self._rot_deg:+.2f}°)" if self._ajuste else f"Descendo (View) | Contatos: {nc}/3"
        if ev.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and ev.value == 'PRESS':
            pintar_contatos(om, self._bvh); ctx.workspace.status_text_set(None); s.cmf_col_status = "Intercuspidação Confirmada!"; return {'FINISHED'}
        if ev.type in {'RIGHTMOUSE', 'ESC'} and ev.value == 'PRESS':
            ctx.workspace.status_text_set(None); return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    def invoke(self, ctx, ev):
        s = ctx.scene; om, of = s.objects.get(s.cmf_col_movel), s.objects.get(s.cmf_col_fixo)
        if not om or not of or om.type != 'MESH' or of.type != 'MESH': self.report({'ERROR'}, "Selecione as malhas!"); return {'CANCELLED'}
        ctx.scene.transform_orientation_slots[0].type = 'VIEW'
        self._bvh = mathutils.bvhtree.BVHTree.FromObject(of, ctx.evaluated_depsgraph_get())
        v = om.data.vertices; passo = max(1, len(v) // 3500)
        self._v = [v[i].co.copy() for i in range(0, len(v), passo)]
        self._lx, self._ly, self._ajuste, self._pos_trav, self._rot_deg = ev.mouse_x, ev.mouse_y, False, None, 0.0
        s.cmf_col_status = "Detector LIGADO (View): Arraste..."
        ctx.workspace.status_text_set("DETECTOR (VIEW): Mova o mouse para descer | Botão Meio: Girar | Clique Esq: Confirmar")
        ctx.window_manager.modal_handler_add(self); return {'RUNNING_MODAL'}

class CMF_OT_LimparContato(bpy.types.Operator):
    bl_idname, bl_label = "cmf.limpar_contato", "Limpar Manchas"
    def execute(self, ctx):
        s = ctx.scene; om = s.objects.get(s.cmf_col_movel)
        if om and om.type == 'MESH':
            at = om.data.color_attributes.get("CMF_Contato")
            if at: om.data.color_attributes.remove(at); om.data.update()
        for a in ctx.screen.areas:
            if a.type == 'VIEW_3D':
                for sp in a.spaces:
                    if sp.type == 'VIEW_3D' and sp.shading.type == 'SOLID': sp.shading.color_type = 'OBJECT'
                a.tag_redraw()
        s.cmf_col_status = ""; return {'FINISHED'}

class CMF_PT_DeteccaoColisao(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Detecção de Colisão", "CMF_PT_deteccao_colisao", 'VIEW_3D', 'UI', 'Tool'
    def draw(self, ctx):
        l, s = self.layout, ctx.scene; b = l.box()
        b.prop_search(s, "cmf_col_movel", s, "objects", text="Móvel (Maxila)")
        b.prop_search(s, "cmf_col_fixo", s, "objects", text="Fixo (Mandíbula)")
        r = l.row(align=True); r.operator("cmf.ligue_detector", text="Ligue Detector", icon='MOD_PHYSICS'); r.operator("cmf.limpar_contato", text="", icon='TRASH')
        if s.cmf_col_status: l.box().label(text=s.cmf_col_status, icon='INFO')

CLASSES = (CMF_OT_LigueDetector, CMF_OT_LimparContato, CMF_PT_DeteccaoColisao)
def register():
    bpy.types.Scene.cmf_col_movel = bpy.props.StringProperty()
    bpy.types.Scene.cmf_col_fixo = bpy.props.StringProperty()
    bpy.types.Scene.cmf_col_status = bpy.props.StringProperty(default="")
    for c in CLASSES: bpy.utils.register_class(c)
def unregister():
    for c in reversed(CLASSES): bpy.utils.unregister_class(c)
    for k in ("cmf_col_movel", "cmf_col_fixo", "cmf_col_status"): delattr(bpy.types.Scene, k)
if __name__ == "__main__": register()