# cmf-surgical-suite-winkler
# 🦷 CMF Surgical Suite - Dr. Winkler (Blender 4.2+)

**Suíte completa de planejamento virtual 3D (VSP) para Cirurgia Ortognática e Bucomaxilofacial no Blender.**  
*Complete 3D Virtual Surgical Planning (VSP) suite for Orthognathic and Craniomaxillofacial Surgery in Blender.*

---

## 📋 Visão Geral / Overview

Desenvolvida para oferecer precisão clínica, agilidade e código aberto aos cirurgiões bucomaxilofaciais e pesquisadores, a **CMF Surgical Suite** reúne **20 módulos integrados** que cobrem todo o fluxo digital: desde a organização da tomografia e alinhamento de modelos escaneados até a cefalometria 3D com correção inversa automática, simulação de tecido mole, confecção de splints oclusais e movimento reverso para guias de perfuração.

*Developed to bring clinical precision, speed, and open-source tools to oral and maxillofacial surgeons and researchers, the **CMF Surgical Suite** integrates **20 specialized modules** covering the entire digital workflow: from CT/intraoral scan alignment to 3D cephalometry with automatic inverse correction, soft tissue simulation, occlusal splint generation, and reverse movement for surgical drilling guides.*

---

## 🛠️ Módulos Incluídos / Included Modules

| Módulo / File | Função Clínica / Clinical Function |
| :--- | :--- |
| **`a_cmf_estrutura_de_pastas`** | Organização automática das coleções cirúrgicas (`PRE_SIMULACAO`, `POS`, `GUIAS`, etc.). |
| **`b_cmf_colorir`** | Padronização visual e atribuição rápida de materiais anatômicos para ossos, dentes e guias. |
| **`c_cmf_alinhamento_icp_winkler`** | Registro e alinhamento de superfície ICP (*Iterative Closest Point*) entre tomografia e escaneamento intraoral. |
| **`d_cmf_map_deviation_winkler`** | Mapa de cores de desvio volumétrico (*Heatmap*) para controle de qualidade de sobreposição. |
| **`e_cmf_detector_colisao_winkler`** | Detecção em tempo real de interferências e contatos prematuros entre segmentos ósseos. |
| **`f_cmf_preparar_posop`** | Duplicação e preparação automática dos segmentos móveis pós-operatórios (`MX_POS`, `MD_POS`, `MENTO`, `RMD/E`). |
| **`g_cmf_auto_linker_winkler`** | Criação automática da hierarquia cinemática maxilomandibular (`Parent/Child`). |
| **`j_cmf_cant_axial_winkler`** | Análise de CANT vertical (`PLH`) e assimetria axial da maxila perpendicular ao `PLA` com exportação CSV. |
| **`l_cmf_cant_winkler`** | Cotas 3D dinâmicas de CANT e linha média (`PLV`) com HUD em tempo real na viewport. |
| **`m_cm_regua_cirurgica`** | Régua 3D e medição de deslocamentos lineares entre pontos anatômicos. |
| **`n_cmf_angular_winkler`** | Cefalometria 3D Angular e Linear completa (`SNA`, `SNB`, `ANB`, `FMA`, `FNP`, `Plo.PLA`, `A-NPerp`, `Pg-NPerp`) com diagnóstico automático. |
| **`o_medida_dentaria_winkler`** | Avaliação de linha média dentária, trespasse horizontal (*overjet*) e vertical (*overbite*). |
| **`p_cmf_livre_ortogonal_winkler`** | Cotas ortogonais livres com projeção perpendicular dinâmica na vista ativa. |
| **`q_cmf_osteotomia_winkler`** | Ferramentas de corte e osteotomia virtual (Le Fort I, BSSO, Mentoplastia e Maxila Segmentada). |
| **`s_cmf_fotomapa_winkler`** | Sobreposição e calibração de fotografia clínica 2D/3D sobre o modelo facial. |
| **`t_cmf_centroides_winkler`** | Cálculo de centróides e análise de deslocamento tridimensional (Gateno / Xia). |
| **`u_cmf_ajuste_automatico_winkler`** | **Correção Inversa Automática:** movimenta o complexo maxilomandibular (`MX_POS`) até atingir os alvos cefalométricos ideais. |
| **`v_cmf_tecido_mole_winkler`** | Simulação de tecido mole sobre malhas maciças de tomografia (resposta 1:1 no mento + escultura fina *Liquidificar 3D*). |
| **`x_cmf_splintdesign_winkler`** | **Gerador de Splint Oclusal** (Intermediário e Final) com pintura dupla de arcadas e perfuração de amarrias em 90° por clique. |
| **`z_cmf_reverso_winkler`** | **Movimento Reverso (`POS -> PRE`):** retorna os segmentos e guias parenteados à posição original para modelagem de guias de perfuração. |

---

## 💻 Instalação / Installation (Blender 4.2+)

1. Baixe o arquivo **`cmf_surgical_suite_winkler_v1.0.0.zip`** na aba [**Releases**](../../releases) à direita.
2. Abra o **Blender 4.2** ou superior e acesse **Edit > Preferences > Get Extensions**.
3. Clique na seta no canto superior direito (`v`) e selecione **Install from Disk...**.
4. Selecione o arquivo `.zip` baixado e ative a extensão **CMF Surgical Suite - Dr. Winkler**.
5. Pressione **`N`** na Viewport 3D para acessar todas as abas da suíte.

---

## 👨‍⚕️ Autoria e Créditos / Author & Credits

* **Idealização, Fluxo Clínico e Arquitetura:** Dr. Carlos J. Winkler (Cirurgião Bucomaxilofacial)
* **Desenvolvimento Assistido de Código e Algoritmos 3D:** Inteligência Artificial Google (Gemini)

---

## 📄 Licença / License

Distribuído sob a licença **GNU General Public License v3.0 (GPL-3.0-or-later)**
