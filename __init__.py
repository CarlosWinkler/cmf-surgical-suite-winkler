import importlib

NOMES_MODULOS = (
    "a_cmf_estrutura_de_pastas",
    "b_cmf_colorir",
    "c_cmf_alinhamento_icp_winkler",
    "d_cmf_map_deviation_winkler",
    "e_cmf_detector_colisao_winkler",
    "f_cmf_preparar_posop",
    "g_cmf_auto_linker_winkler",
    "j_cmf_cant_axial_winkler",
    "l_cmf_cant_winkler",
    "m_cm_regua_cirurgica",
    "n_cmf_angular_winkler",
    "o_medida_dentaria_winkler",
    "p_cmf_livre_ortogonal_winkler",
    "q_cmf_osteotomia_winkler",
    "s_cmf_fotomapa_winkler",
    "t_cmf_centroides_winkler",
    "u_cmf_ajuste_automatico_winkler",
    "v_cmf_tecido_mole_winkler",
    "x_cmf_splintdesign_winkler",
    "z_cmf_reverso_winkler",
)

_modulos_carregados = []

def register():
    _modulos_carregados.clear()
    for nome in NOMES_MODULOS:
        try:
            mod = importlib.import_module(f".{nome}", package=__package__)
            if hasattr(mod, "register"):
                mod.register()
                _modulos_carregados.append(mod)
        except Exception as e:
            print(f"[CMF Suite] Erro ao carregar {nome}: {e}")

def unregister():
    for mod in reversed(_modulos_carregados):
        try:
            if hasattr(mod, "unregister"):
                mod.unregister()
        except Exception as e:
            print(f"[CMF Suite] Erro ao descarregar {mod.__name__}: {e}")
    _modulos_carregados.clear()