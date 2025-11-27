import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="SuperNutri-Score", page_icon="🥖", layout="wide")

st.markdown('<h1 style="text-align:center;color:#1f77b4;">🥖 SuperNutri-Score - Interface Consommateur</h1>', 
            unsafe_allow_html=True)

# Chargement données
@st.cache_data
def load_data():
    try:
        pain = pd.read_csv("Products.csv", encoding='utf-8-sig')
        yaourt = pd.read_csv("data_yaourt.csv", encoding='utf-8-sig')
        return pain, yaourt, True
    except:
        pain = pd.DataFrame({'product_name': [f'Pain {i}' for i in range(121)],
                            'nutriscore_grade': np.random.choice(['A','B','C','D','E'], 121),
                            'ecoscore_grade': np.random.choice(['A','B','C','D','E'], 121)})
        yaourt = pd.DataFrame({'product_name': [f'Yaourt {i}' for i in range(208)],
                              'nutriscore_grade': np.random.choice(['A','B','C','D','E'], 208),
                              'ecoscore_grade': np.random.choice(['A','B','C','D','E'], 208)})
        return pain, yaourt, False

# Fonctions ELECTRE TRI
def concordance_partielle(H, b, crit, sens_dict):
    if sens_dict[crit] == 'max':
        return 1 if H[crit] >= b[crit] else 0
    else:
        return 1 if H[crit] <= b[crit] else 0

def concordance_globale(H, b, poids_dict, sens_dict):
    num = sum(poids_dict[c] * concordance_partielle(H, b, c, sens_dict) for c in poids_dict)
    denom = sum(poids_dict.values())
    return num / denom

@st.cache_data
def calculate_all_scores(df_pain, df_yaourt):
    """Calcule ELECTRE TRI et SuperNutri-Score pour tous les produits"""
    
    # Paramètres fixes
    poids = {
        'energy_kj': 2, 'saturated_fat': 2, 'sugar': 2, 'sodium_g': 1,
        'protein': 1, 'fiber': 1, 'fruits_veg_nuts_pct': 1, 'additives_count': 1
    }
    
    sens = {
        'energy_kj': 'min', 'saturated_fat': 'min', 'sugar': 'min', 'sodium_g': 'min',
        'protein': 'max', 'fiber': 'max', 'fruits_veg_nuts_pct': 'max', 'additives_count': 'min'
    }
    
    criteres = list(poids.keys())
    quantiles = [0.05, 0.2, 0.4, 0.6, 0.8, 0.95]
    
    # Calcul profils
    profils = {}
    for i, q in enumerate(quantiles, start=1):
        profils[f"pi{i}"] = {}
        for crit in criteres:
            if crit in df_pain.columns and crit in df_yaourt.columns:
                data = pd.concat([df_pain[crit], df_yaourt[crit]]).dropna()
                if sens[crit] == 'max':
                    profils[f"pi{i}"][crit] = float(data.quantile(q))
                else:
                    profils[f"pi{i}"][crit] = float(data.quantile(1-q))
            else:
                defaults = {
                    'energy_kj': [2000, 1500, 1200, 1100, 1050, 1000],
                    'saturated_fat': [10, 5, 2, 1, 0.5, 0.3],
                    'sugar': [18, 8, 4, 3, 2.5, 2],
                    'sodium_g': [1.0, 0.7, 0.5, 0.4, 0.4, 0.35],
                    'protein': [7, 8, 9, 10, 11, 12],
                    'fiber': [0, 2.5, 4, 5.5, 8.5, 9.5],
                    'fruits_veg_nuts_pct': [0, 0, 0, 0, 5, 12],
                    'additives_count': [12, 7, 4, 1, 0, 0]
                }
                profils[f"pi{i}"][crit] = defaults[crit][i-1]
    
    def classify_product(row, lambda_val):
        """Classifie un produit avec ELECTRE TRI"""
        produit = {crit: row.get(crit, 0) for crit in criteres}
        
        # Pessimiste
        classe_pess = "E'"
        for i in reversed(range(1, 6)):
            c = concordance_globale(produit, profils[f"pi{i}"], poids, sens)
            if c >= lambda_val:
                classe_pess = ["E'", "D'", "C'", "B'", "A'"][i-1]
                break
        
        # Optimiste
        classe_opt = "A'"
        for i in range(2, 7):
            b = profils[f"pi{i-1}"]
            c_biH = concordance_globale(b, produit, poids, sens)
            c_Hbi = concordance_globale(produit, b, poids, sens)
            if c_biH >= lambda_val and c_Hbi < lambda_val:
                classe_opt = ["E'", "D'", "C'", "B'", "A'"][i-2]
                break
        
        return classe_pess, classe_opt
    
    def calculate_supernutri(row, electre_pess_06):
        """Calcule SuperNutri-Score"""
        map_in = {"A'":1, "B'":2, "C'":3, "D'":4, "E'":5}
        map_out = {1:"A", 2:"B", 3:"C", 4:"D", 5:"E"}
        
        score = map_in[electre_pess_06]
        eco = str(row.get('ecoscore_grade', 'C')).upper()
        is_bio = str(row.get('is_organic', 'No')).lower() in ['yes', 'oui', '1', 'true']
        
        if eco == "A" and score > 1:
            score -= 1
        if eco in ["D", "E"] and score < 5:
            score += 1
        if is_bio and eco != "E" and score > 1:
            score -= 1
        if eco == "E":
            score = max(score, 3)
        
        score = max(1, min(5, score))
        return map_out[score]
    
    # Calculer pour les pains
    df_pain_calc = df_pain.copy()
    df_pain_calc[['electre_pess_06', 'electre_opt_06']] = df_pain_calc.apply(
        lambda row: classify_product(row, 0.6), axis=1, result_type='expand')
    df_pain_calc[['electre_pess_07', 'electre_opt_07']] = df_pain_calc.apply(
        lambda row: classify_product(row, 0.7), axis=1, result_type='expand')
    df_pain_calc['supernutri_score'] = df_pain_calc.apply(
        lambda row: calculate_supernutri(row, row['electre_pess_06']), axis=1)
    
    # Calculer pour les yaourts
    df_yaourt_calc = df_yaourt.copy()
    df_yaourt_calc[['electre_pess_06', 'electre_opt_06']] = df_yaourt_calc.apply(
        lambda row: classify_product(row, 0.6), axis=1, result_type='expand')
    df_yaourt_calc[['electre_pess_07', 'electre_opt_07']] = df_yaourt_calc.apply(
        lambda row: classify_product(row, 0.7), axis=1, result_type='expand')
    df_yaourt_calc['supernutri_score'] = df_yaourt_calc.apply(
        lambda row: calculate_supernutri(row, row['electre_pess_06']), axis=1)
    
    return df_pain_calc, df_yaourt_calc

df_pain, df_yaourt, is_real = load_data()

# Calculer tous les scores
if is_real:
    df_pain, df_yaourt = calculate_all_scores(df_pain, df_yaourt)
    st.success("✅ Données chargées et scores calculés!")
else:
    st.warning("⚠️ Données d'exemple. Ajoutez Products.csv et data_yaourt.csv pour les vraies données.")

# Sidebar Navigation
st.sidebar.title("📊 Navigation")
page = st.sidebar.radio("", [
    "🧮 Calculateur Complet",
    "📊 Analyse de Données", 
    "⚖️ Comparaison Groupes"
])

COLORS = {'A':'#038141','B':'#85BB2F','C':'#FECB02','D':'#EE8100','E':'#E63E11'}

# ============================================================
# PAGE 1: CALCULATEUR COMPLET (Requis par professeur)
# ============================================================
if page == "🧮 Calculateur Complet":
    st.header("🧮 Interface Consommateur - Évaluation Complète")
    
    st.info("""
    **Entrez les informations nutritionnelles de votre produit et obtenez:**
    - ✅ Nutri-Score (score + grade)
    - ✅ ELECTRE TRI Pessimiste & Optimiste
    - ✅ SuperNutri-Score (modèle amélioré)
    """)
    
    # ========== SECTION 1: INFORMATIONS NUTRITIONNELLES ==========
    st.markdown("---")
    st.subheader("📝 1. Informations Nutritionnelles (pour 100g)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        energy_kj = st.number_input("Énergie (kJ)", 0, 4000, 1000, 
                                    help="Valeur énergétique en kilojoules")
    
    with col2:
        saturated_fat = st.number_input("Graisses saturées (g)", 0.0, 100.0, 1.0, 0.1)
    
    with col3:
        sugar = st.number_input("Sucres (g)", 0.0, 100.0, 5.0, 0.1)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sodium_mg = st.number_input("Sodium (mg)", 0, 5000, 100)
    
    with col2:
        protein = st.number_input("Protéines (g)", 0.0, 100.0, 5.0, 0.1)
    
    with col3:
        fiber = st.number_input("Fibres (g)", 0.0, 50.0, 2.0, 0.1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fruits_veg_nuts_pct = st.slider("Fruits/Légumes/Noix (%)", 0, 100, 0)
    
    with col2:
        additives_count = st.number_input("Nombre d'additifs", 0, 20, 0)
    
    # ========== SECTION 2: ECO-SCORE ET BIO ==========
    st.markdown("---")
    st.subheader("🌱 2. Informations Environnementales")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ecoscore_grade = st.selectbox("Eco-Score (Green-Score)", 
                                     ['A', 'B', 'C', 'D', 'E'],
                                     help="Impact environnemental du produit")
    
    with col2:
        is_organic = st.checkbox("Produit biologique (Bio)", 
                                 help="Produit issu de l'agriculture biologique")
    
    # ========== SECTION 3: PARAMÈTRES ELECTRE TRI (Fixes) ==========
    st.markdown("---")
    st.subheader("⚙️ 3. Paramètres ELECTRE TRI (Prédéfinis)")
    
    st.info("""
    **Paramètres fixes du modèle:**
    - Poids: Énergie=2, Sucres=2, Graisses sat.=2, Sodium=1, Protéines=1, Fibres=1, Fruits/Lég.=1, Additifs=1
    - Seuils λ: 0.6 et 0.7 (les deux seront calculés)
    """)
    
    # ========== BOUTON CALCUL ==========
    st.markdown("---")
    
    if st.button("🚀 CALCULER LES 3 ALGORITHMES", type="primary", use_container_width=True):
        
        # Conversion sodium → sel
        sodium_g = sodium_mg / 1000
        sel_g = sodium_mg / 400
        
        # ==========================================
        # ALGORITHME 1: NUTRI-SCORE 2025
        # ==========================================
        st.markdown("---")
        st.header("📊 RÉSULTATS")
        
        st.subheader("1️⃣ Nutri-Score 2025 (ANSES)")
        
        # Calcul points négatifs
        def score_energie(kj):
            seuils = [335,670,1005,1340,1675,2010,2345,2680,3015,3350]
            return int(np.searchsorted(seuils, kj, side="right"))
        
        def score_satures(g):
            seuils = [1,2,3,4,5,6,7,8,9,10]
            return int(np.searchsorted(seuils, g, side="right"))
        
        def score_sucres(g):
            seuils = [3.4,6.8,10,14,17,20,24,27,31,34,37,41,44,48,51]
            return int(np.searchsorted(seuils, g, side="right"))
        
        def score_sel(g):
            seuils = [0.2,0.4,0.6,0.8,1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.4,2.6,2.8,3.0,3.2,3.4,3.6,3.8,4.0]
            return int(np.searchsorted(seuils, g, side="right"))
        
        pts_energie = score_energie(energy_kj)
        pts_sat_fat = score_satures(saturated_fat)
        pts_sugar = score_sucres(sugar)
        pts_sel = score_sel(sel_g)
        
        negative_pts = pts_energie + pts_sat_fat + pts_sugar + pts_sel
        
        # Calcul points positifs
        if fruits_veg_nuts_pct > 80:
            pts_fruits = 5
        elif fruits_veg_nuts_pct > 60:
            pts_fruits = 2
        elif fruits_veg_nuts_pct > 40:
            pts_fruits = 1
        else:
            pts_fruits = 0
        
        pts_fiber = int(np.searchsorted([0.9,1.9,2.8,3.7,4.7], fiber, side="right"))
        pts_protein = int(np.searchsorted([1.6,3.2,4.8,6.4,8.0], protein, side="right"))
        
        positive_pts = pts_fruits + pts_fiber + pts_protein
        
        # Règle 2025
        if negative_pts >= 11 and fruits_veg_nuts_pct < 80:
            positive_pts_final = positive_pts - pts_protein
        else:
            positive_pts_final = positive_pts
        
        nutriscore_score = negative_pts - positive_pts_final
        
        # Grade Nutri-Score
        if nutriscore_score <= -1:
            nutriscore_grade = "A"
        elif nutriscore_score <= 2:
            nutriscore_grade = "B"
        elif nutriscore_score <= 10:
            nutriscore_grade = "C"
        elif nutriscore_score <= 18:
            nutriscore_grade = "D"
        else:
            nutriscore_grade = "E"
        
        # Affichage Nutri-Score
        col1, col2, col3 = st.columns([1,2,1])
        
        with col2:
            st.markdown(f"""
            <div style='text-align:center; padding:2rem; background-color:{COLORS[nutriscore_grade]}22; border-radius:10px;'>
                <h1 style='color:{COLORS[nutriscore_grade]}; font-size:6rem; margin:0;'>{nutriscore_grade}</h1>
                <h3 style='color:#666;'>Score: {nutriscore_score}</h3>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("❌ Points négatifs", negative_pts)
            st.caption(f"• Énergie: {pts_energie} pts")
            st.caption(f"• Graisses sat.: {pts_sat_fat} pts")
            st.caption(f"• Sucres: {pts_sugar} pts")
            st.caption(f"• Sel: {pts_sel} pts")
        
        with col2:
            st.metric("✅ Points positifs", positive_pts_final)
            st.caption(f"• Fruits/Légumes: {pts_fruits} pts")
            st.caption(f"• Fibres: {pts_fiber} pts")
            st.caption(f"• Protéines: {pts_protein if positive_pts_final == positive_pts else 0} pts")
            if negative_pts >= 11 and fruits_veg_nuts_pct < 80:
                st.warning("⚠️ Protéines non comptées (règle 2025)")
        
        with col3:
            st.metric("📊 Score final", nutriscore_score)
            st.caption("Négatifs - Positifs")
        
        # ==========================================
        # ALGORITHME 2: ELECTRE TRI
        # ==========================================
        st.markdown("---")
        st.subheader("2️⃣ ELECTRE TRI (Pessimiste & Optimiste)")
        
        # Création du vecteur produit
        produit = {
            'energy_kj': energy_kj,
            'saturated_fat': saturated_fat,
            'sugar': sugar,
            'sodium_g': sodium_g,
            'protein': protein,
            'fiber': fiber,
            'fruits_veg_nuts_pct': fruits_veg_nuts_pct,
            'additives_count': additives_count
        }
        
        # Poids fixes selon tableau
        poids = {
            'energy_kj': 2,
            'saturated_fat': 2,
            'sugar': 2,
            'sodium_g': 1,
            'protein': 1,
            'fiber': 1,
            'fruits_veg_nuts_pct': 1,
            'additives_count': 1
        }
        
        # Sens d'optimisation
        sens = {
            'energy_kj': 'min',
            'saturated_fat': 'min',
            'sugar': 'min',
            'sodium_g': 'min',
            'protein': 'max',
            'fiber': 'max',
            'fruits_veg_nuts_pct': 'max',
            'additives_count': 'min'
        }
        
        # Calcul des profils (quantiles)
        criteres = list(poids.keys())
        quantiles = [0.05, 0.2, 0.4, 0.6, 0.8, 0.95]
        
        profils = {}
        for i, q in enumerate(quantiles, start=1):
            profils[f"pi{i}"] = {}
            for crit in criteres:
                if crit in df_pain.columns:
                    data = pd.concat([df_pain[crit], df_yaourt[crit]]).dropna()
                    if sens[crit] == 'max':
                        profils[f"pi{i}"][crit] = float(data.quantile(q))
                    else:
                        profils[f"pi{i}"][crit] = float(data.quantile(1-q))
                else:
                    # Valeurs par défaut
                    defaults = {
                        'energy_kj': [2000, 1500, 1200, 1100, 1050, 1000],
                        'saturated_fat': [10, 5, 2, 1, 0.5, 0.3],
                        'sugar': [18, 8, 4, 3, 2.5, 2],
                        'sodium_g': [1.0, 0.7, 0.5, 0.4, 0.4, 0.35],
                        'protein': [7, 8, 9, 10, 11, 12],
                        'fiber': [0, 2.5, 4, 5.5, 8.5, 9.5],
                        'fruits_veg_nuts_pct': [0, 0, 0, 0, 5, 12],
                        'additives_count': [12, 7, 4, 1, 0, 0]
                    }
                    if sens[crit] == 'max':
                        profils[f"pi{i}"][crit] = defaults[crit][i-1]
                    else:
                        profils[f"pi{i}"][crit] = defaults[crit][i-1]
        
        # Fonctions ELECTRE
        def concordance_partielle(H, b, crit, sens):
            if sens[crit] == 'max':
                return 1 if H[crit] >= b[crit] else 0
            else:
                return 1 if H[crit] <= b[crit] else 0
        
        def concordance_globale(H, b, poids, sens):
            num = sum(poids[c] * concordance_partielle(H, b, c, sens) for c in poids)
            denom = sum(poids.values())
            return num / denom
        
        # PESSIMISTE λ=0.6
        classe_pess_06 = "E'"
        for i in reversed(range(1, 6)):
            c = concordance_globale(produit, profils[f"pi{i}"], poids, sens)
            if c >= 0.6:
                classe_pess_06 = ["E'", "D'", "C'", "B'", "A'"][i-1]
                break
        
        # OPTIMISTE λ=0.6
        classe_opt_06 = "A'"
        for i in range(2, 7):
            b = profils[f"pi{i-1}"]
            c_biH = concordance_globale(b, produit, poids, sens)
            c_Hbi = concordance_globale(produit, b, poids, sens)
            if c_biH >= 0.6 and c_Hbi < 0.6:
                classe_opt_06 = ["E'", "D'", "C'", "B'", "A'"][i-2]
                break
        
        # PESSIMISTE λ=0.7
        classe_pess_07 = "E'"
        for i in reversed(range(1, 6)):
            c = concordance_globale(produit, profils[f"pi{i}"], poids, sens)
            if c >= 0.7:
                classe_pess_07 = ["E'", "D'", "C'", "B'", "A'"][i-1]
                break
        
        # OPTIMISTE λ=0.7
        classe_opt_07 = "A'"
        for i in range(2, 7):
            b = profils[f"pi{i-1}"]
            c_biH = concordance_globale(b, produit, poids, sens)
            c_Hbi = concordance_globale(produit, b, poids, sens)
            if c_biH >= 0.7 and c_Hbi < 0.7:
                classe_opt_07 = ["E'", "D'", "C'", "B'", "A'"][i-2]
                break
        
        # Affichage ELECTRE TRI - 4 résultats
        st.markdown("**λ = 0.6**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#3498db22; border-radius:10px;'>
                <h4>Pessimiste (λ=0.6)</h4>
                <h1 style='color:#3498db; font-size:3.5rem; margin:0;'>{classe_pess_06}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#2ecc7122; border-radius:10px;'>
                <h4>Optimiste (λ=0.6)</h4>
                <h1 style='color:#2ecc71; font-size:3.5rem; margin:0;'>{classe_opt_06}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("**λ = 0.7**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#e67e2222; border-radius:10px;'>
                <h4>Pessimiste (λ=0.7)</h4>
                <h1 style='color:#e67e22; font-size:3.5rem; margin:0;'>{classe_pess_07}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#9b59b622; border-radius:10px;'>
                <h4>Optimiste (λ=0.7)</h4>
                <h1 style='color:#9b59b6; font-size:3.5rem; margin:0;'>{classe_opt_07}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.info("**Paramètres:** Poids fixes (voir ci-dessus) | Profils calculés sur 329 produits")
        
        # ==========================================
        # ALGORITHME 3: SUPERNUTRI-SCORE
        # ==========================================
        st.markdown("---")
        st.subheader("3️⃣ SuperNutri-Score (Modèle Amélioré)")
        
        st.info("""
        **SuperNutri-Score = ELECTRE TRI + Eco-Score + Bio**
        
        Combinaison des 3 dimensions: Nutrition (ELECTRE) + Environnement (Eco) + Agriculture (Bio)
        """)
        
        # Calcul SuperNutri-Score (basé sur pessimiste λ=0.6)
        map_in = {"A'":1, "B'":2, "C'":3, "D'":4, "E'":5}
        map_out = {1:"A", 2:"B", 3:"C", 4:"D", 5:"E"}
        
        score_super = map_in[classe_pess_06]
        
        # Règles
        regles_appliquees = []
        
        # Eco-Score A
        if ecoscore_grade == "A" and score_super > 1:
            score_super -= 1
            regles_appliquees.append("✅ Bonus Eco-Score A: +1 grade")
        
        # Eco-Score D/E
        if ecoscore_grade in ["D", "E"] and score_super < 5:
            score_super += 1
            regles_appliquees.append("⚠️ Malus Eco-Score D/E: -1 grade")
        
        # Bio
        if is_organic and ecoscore_grade != "E" and score_super > 1:
            score_super -= 1
            regles_appliquees.append("✅ Bonus Bio: +1 grade")
        
        # Limitation Eco E
        if ecoscore_grade == "E":
            score_super = max(score_super, 3)
            regles_appliquees.append("⚠️ Limitation Eco-Score E: grade max = C")
        
        score_super = max(1, min(5, score_super))
        supernutri_grade = map_out[score_super]
        
        # Affichage SuperNutri-Score
        st.markdown(f"""
        <div style='text-align:center; padding:2rem; background-color:{COLORS[supernutri_grade]}22; border-radius:10px; border: 3px solid {COLORS[supernutri_grade]};'>
            <h2 style='color:#333; margin:0;'>SuperNutri-Score Final</h2>
            <h1 style='color:{COLORS[supernutri_grade]}; font-size:7rem; margin:0.5rem 0;'>{supernutri_grade}</h1>
            <p style='font-size:1.2rem; color:#666;'>
                Base: ELECTRE Pessimiste λ=0.6 ({classe_pess_06}) | Eco: {ecoscore_grade} | Bio: {'Oui' if is_organic else 'Non'}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if regles_appliquees:
            st.markdown("**Règles appliquées:**")
            for regle in regles_appliquees:
                st.markdown(f"- {regle}")
        
        # ==========================================
        # TABLEAU RÉCAPITULATIF
        # ==========================================
        st.markdown("---")
        st.subheader("📋 Tableau Récapitulatif")
        
        recap_df = pd.DataFrame({
            'Algorithme': [
                'Nutri-Score 2025',
                'ELECTRE TRI Pessimiste (λ=0.6)',
                'ELECTRE TRI Optimiste (λ=0.6)',
                'ELECTRE TRI Pessimiste (λ=0.7)',
                'ELECTRE TRI Optimiste (λ=0.7)',
                'SuperNutri-Score'
            ],
            'Grade': [
                nutriscore_grade,
                classe_pess_06,
                classe_opt_06,
                classe_pess_07,
                classe_opt_07,
                supernutri_grade
            ],
            'Info': [
                f'Score: {nutriscore_score}',
                'Classification conservatrice',
                'Classification favorable',
                'Classification conservatrice (strict)',
                'Classification favorable (strict)',
                'ELECTRE + Eco + Bio'
            ]
        })
        
        st.dataframe(recap_df[['Algorithme', 'Grade', 'Info']], use_container_width=True, hide_index=True)
        
        # Visualisation comparative
        st.markdown("---")
        st.subheader("📊 Comparaison Visuelle")
        
        grades_map = {'A':5, 'B':4, 'C':3, 'D':2, 'E':1, "A'":5, "B'":4, "C'":3, "D'":2, "E'":1}
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Nutri-Score', 'ELECTRE\nPess. 0.6', 'ELECTRE\nOpt. 0.6', 
               'ELECTRE\nPess. 0.7', 'ELECTRE\nOpt. 0.7', 'SuperNutri'],
            y=[grades_map[nutriscore_grade], grades_map[classe_pess_06], 
               grades_map[classe_opt_06], grades_map[classe_pess_07],
               grades_map[classe_opt_07], grades_map[supernutri_grade]],
            marker_color=[COLORS[nutriscore_grade], '#3498db', '#2ecc71', 
                         '#e67e22', '#9b59b6', COLORS[supernutri_grade]],
            text=[nutriscore_grade, classe_pess_06, classe_opt_06, 
                  classe_pess_07, classe_opt_07, supernutri_grade],
            textposition='outside',
            textfont=dict(size=18, color='black')
        ))
        
        fig.update_layout(
            yaxis_title="Qualité (1=E, 5=A)",
            height=400,
            showlegend=False,
            yaxis=dict(range=[0, 6], tickmode='array', tickvals=[1,2,3,4,5], ticktext=['E','D','C','B','A'])
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE 2: ANALYSE DE DONNÉES
# ============================================================
elif page == "📊 Analyse de Données":
    st.header("📊 Analyse des Données")
    
    tab1, tab2 = st.tabs(["🥖 Pains", "🥛 Yaourts"])
    
    with tab1:
        st.subheader(f"Analyse des Pains ({len(df_pain)} produits)")
        
        if is_real:
            # Nutri-Score
            st.markdown("#### Nutri-Score")
            if 'nutriscore_grade' in df_pain.columns:
                pc = df_pain['nutriscore_grade'].value_counts().sort_index()
                fig = go.Figure(go.Bar(
                    x=pc.index, y=pc.values,
                    marker_color=[COLORS.get(x, '#999') for x in pc.index],
                    text=pc.values, textposition='outside'
                ))
                fig.update_layout(title="Distribution Nutri-Score", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # ELECTRE TRI
            st.markdown("#### ELECTRE TRI")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**λ = 0.6**")
                # Pessimiste 0.6
                if 'electre_pess_06' in df_pain.columns:
                    p06 = df_pain['electre_pess_06'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=p06.index, y=p06.values, marker_color='#3498db',
                                          text=p06.values, textposition='outside', name='Pess. 0.6'))
                    fig.update_layout(title="Pessimiste λ=0.6", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Optimiste 0.6
                if 'electre_opt_06' in df_pain.columns:
                    o06 = df_pain['electre_opt_06'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=o06.index, y=o06.values, marker_color='#2ecc71',
                                          text=o06.values, textposition='outside', name='Opt. 0.6'))
                    fig.update_layout(title="Optimiste λ=0.6", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**λ = 0.7**")
                # Pessimiste 0.7
                if 'electre_pess_07' in df_pain.columns:
                    p07 = df_pain['electre_pess_07'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=p07.index, y=p07.values, marker_color='#e67e22',
                                          text=p07.values, textposition='outside', name='Pess. 0.7'))
                    fig.update_layout(title="Pessimiste λ=0.7", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Optimiste 0.7
                if 'electre_opt_07' in df_pain.columns:
                    o07 = df_pain['electre_opt_07'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=o07.index, y=o07.values, marker_color='#9b59b6',
                                          text=o07.values, textposition='outside', name='Opt. 0.7'))
                    fig.update_layout(title="Optimiste λ=0.7", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            
            # SuperNutri-Score
            st.markdown("#### SuperNutri-Score")
            if 'supernutri_score' in df_pain.columns:
                sn = df_pain['supernutri_score'].value_counts().sort_index()
                fig = go.Figure(go.Bar(
                    x=sn.index, y=sn.values,
                    marker_color=[COLORS.get(x, '#999') for x in sn.index],
                    text=sn.values, textposition='outside'
                ))
                fig.update_layout(title="Distribution SuperNutri-Score", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Tableau de données
            st.markdown("#### Aperçu des données")
            display_cols = ['product_name', 'nutriscore_grade', 'electre_pess_06', 'electre_opt_06',
                           'electre_pess_07', 'electre_opt_07', 'supernutri_score']
            display_cols = [c for c in display_cols if c in df_pain.columns]
            st.dataframe(df_pain[display_cols].head(10), use_container_width=True)
        else:
            st.info("Chargez les vraies données pour voir les analyses complètes.")
    
    with tab2:
        st.subheader(f"Analyse des Yaourts ({len(df_yaourt)} produits)")
        
        if is_real:
            # Nutri-Score
            st.markdown("#### Nutri-Score")
            if 'nutriscore_grade' in df_yaourt.columns:
                yc = df_yaourt['nutriscore_grade'].value_counts().sort_index()
                fig = go.Figure(go.Bar(
                    x=yc.index, y=yc.values,
                    marker_color=[COLORS.get(x, '#999') for x in yc.index],
                    text=yc.values, textposition='outside'
                ))
                fig.update_layout(title="Distribution Nutri-Score", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # ELECTRE TRI
            st.markdown("#### ELECTRE TRI")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**λ = 0.6**")
                # Pessimiste 0.6
                if 'electre_pess_06' in df_yaourt.columns:
                    p06 = df_yaourt['electre_pess_06'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=p06.index, y=p06.values, marker_color='#3498db',
                                          text=p06.values, textposition='outside'))
                    fig.update_layout(title="Pessimiste λ=0.6", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Optimiste 0.6
                if 'electre_opt_06' in df_yaourt.columns:
                    o06 = df_yaourt['electre_opt_06'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=o06.index, y=o06.values, marker_color='#2ecc71',
                                          text=o06.values, textposition='outside'))
                    fig.update_layout(title="Optimiste λ=0.6", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**λ = 0.7**")
                # Pessimiste 0.7
                if 'electre_pess_07' in df_yaourt.columns:
                    p07 = df_yaourt['electre_pess_07'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=p07.index, y=p07.values, marker_color='#e67e22',
                                          text=p07.values, textposition='outside'))
                    fig.update_layout(title="Pessimiste λ=0.7", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Optimiste 0.7
                if 'electre_opt_07' in df_yaourt.columns:
                    o07 = df_yaourt['electre_opt_07'].value_counts().sort_index()
                    fig = go.Figure(go.Bar(x=o07.index, y=o07.values, marker_color='#9b59b6',
                                          text=o07.values, textposition='outside'))
                    fig.update_layout(title="Optimiste λ=0.7", height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            
            # SuperNutri-Score
            st.markdown("#### SuperNutri-Score")
            if 'supernutri_score' in df_yaourt.columns:
                sn = df_yaourt['supernutri_score'].value_counts().sort_index()
                fig = go.Figure(go.Bar(
                    x=sn.index, y=sn.values,
                    marker_color=[COLORS.get(x, '#999') for x in sn.index],
                    text=sn.values, textposition='outside'
                ))
                fig.update_layout(title="Distribution SuperNutri-Score", height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Tableau de données
            st.markdown("#### Aperçu des données")
            display_cols = ['product_name', 'nutriscore_grade', 'electre_pess_06', 'electre_opt_06',
                           'electre_pess_07', 'electre_opt_07', 'supernutri_score']
            display_cols = [c for c in display_cols if c in df_yaourt.columns]
            st.dataframe(df_yaourt[display_cols].head(10), use_container_width=True)
        else:
            st.info("Chargez les vraies données pour voir les analyses complètes.")

# ============================================================
# PAGE 3: COMPARAISON GROUPES
# ============================================================
elif page == "⚖️ Comparaison Groupes":
    st.header("⚖️ Comparaison Pains vs Yaourts")
    
    if is_real:
        # Nutri-Score
        st.subheader("1️⃣ Nutri-Score")
        if 'nutriscore_grade' in df_pain.columns and 'nutriscore_grade' in df_yaourt.columns:
            grades = ['A','B','C','D','E']
            pc = df_pain['nutriscore_grade'].value_counts().reindex(grades, fill_value=0)
            yc = df_yaourt['nutriscore_grade'].value_counts().reindex(grades, fill_value=0)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(name='🥖 Pains', x=grades, y=pc.values,
                                marker_color='#3498db', text=pc.values, textposition='outside'))
            fig.add_trace(go.Bar(name='🥛 Yaourts', x=grades, y=yc.values,
                                marker_color='#e74c3c', text=yc.values, textposition='outside'))
            fig.update_layout(barmode='group', height=400, xaxis_title="Grade", yaxis_title="Nombre")
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示每个grade的百分比
            st.markdown("#### Répartition en pourcentage")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🥖 Pains**")
                for grade in grades:
                    pct = (pc[grade] / len(df_pain) * 100)
                    st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
            
            with col2:
                st.markdown("**🥛 Yaourts**")
                for grade in grades:
                    pct = (yc[grade] / len(df_yaourt) * 100)
                    st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
        
        # ELECTRE TRI
        st.markdown("---")
        st.subheader("2️⃣ ELECTRE TRI")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Pessimiste λ=0.6", "Optimiste λ=0.6", 
                                          "Pessimiste λ=0.7", "Optimiste λ=0.7"])
        
        with tab1:
            if 'electre_pess_06' in df_pain.columns and 'electre_pess_06' in df_yaourt.columns:
                grades = ["A'","B'","C'","D'","E'"]
                pc = df_pain['electre_pess_06'].value_counts().reindex(grades, fill_value=0)
                yc = df_yaourt['electre_pess_06'].value_counts().reindex(grades, fill_value=0)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(name='🥖 Pains', x=grades, y=pc.values,
                                    marker_color='#3498db', text=pc.values, textposition='outside'))
                fig.add_trace(go.Bar(name='🥛 Yaourts', x=grades, y=yc.values,
                                    marker_color='#e74c3c', text=yc.values, textposition='outside'))
                fig.update_layout(barmode='group', height=400, title="ELECTRE Pessimiste λ=0.6")
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("#### Répartition en pourcentage")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🥖 Pains**")
                    for grade in grades:
                        pct = (pc[grade] / len(df_pain) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
                with col2:
                    st.markdown("**🥛 Yaourts**")
                    for grade in grades:
                        pct = (yc[grade] / len(df_yaourt) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
        
        with tab2:
            if 'electre_opt_06' in df_pain.columns and 'electre_opt_06' in df_yaourt.columns:
                grades = ["A'","B'","C'","D'","E'"]
                pc = df_pain['electre_opt_06'].value_counts().reindex(grades, fill_value=0)
                yc = df_yaourt['electre_opt_06'].value_counts().reindex(grades, fill_value=0)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(name='🥖 Pains', x=grades, y=pc.values,
                                    marker_color='#2ecc71', text=pc.values, textposition='outside'))
                fig.add_trace(go.Bar(name='🥛 Yaourts', x=grades, y=yc.values,
                                    marker_color='#e74c3c', text=yc.values, textposition='outside'))
                fig.update_layout(barmode='group', height=400, title="ELECTRE Optimiste λ=0.6")
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("#### Répartition en pourcentage")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🥖 Pains**")
                    for grade in grades:
                        pct = (pc[grade] / len(df_pain) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
                with col2:
                    st.markdown("**🥛 Yaourts**")
                    for grade in grades:
                        pct = (yc[grade] / len(df_yaourt) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
        
        with tab3:
            if 'electre_pess_07' in df_pain.columns and 'electre_pess_07' in df_yaourt.columns:
                grades = ["A'","B'","C'","D'","E'"]
                pc = df_pain['electre_pess_07'].value_counts().reindex(grades, fill_value=0)
                yc = df_yaourt['electre_pess_07'].value_counts().reindex(grades, fill_value=0)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(name='🥖 Pains', x=grades, y=pc.values,
                                    marker_color='#e67e22', text=pc.values, textposition='outside'))
                fig.add_trace(go.Bar(name='🥛 Yaourts', x=grades, y=yc.values,
                                    marker_color='#e74c3c', text=yc.values, textposition='outside'))
                fig.update_layout(barmode='group', height=400, title="ELECTRE Pessimiste λ=0.7")
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("#### Répartition en pourcentage")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🥖 Pains**")
                    for grade in grades:
                        pct = (pc[grade] / len(df_pain) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
                with col2:
                    st.markdown("**🥛 Yaourts**")
                    for grade in grades:
                        pct = (yc[grade] / len(df_yaourt) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
        
        with tab4:
            if 'electre_opt_07' in df_pain.columns and 'electre_opt_07' in df_yaourt.columns:
                grades = ["A'","B'","C'","D'","E'"]
                pc = df_pain['electre_opt_07'].value_counts().reindex(grades, fill_value=0)
                yc = df_yaourt['electre_opt_07'].value_counts().reindex(grades, fill_value=0)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(name='🥖 Pains', x=grades, y=pc.values,
                                    marker_color='#9b59b6', text=pc.values, textposition='outside'))
                fig.add_trace(go.Bar(name='🥛 Yaourts', x=grades, y=yc.values,
                                    marker_color='#e74c3c', text=yc.values, textposition='outside'))
                fig.update_layout(barmode='group', height=400, title="ELECTRE Optimiste λ=0.7")
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("#### Répartition en pourcentage")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🥖 Pains**")
                    for grade in grades:
                        pct = (pc[grade] / len(df_pain) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
                with col2:
                    st.markdown("**🥛 Yaourts**")
                    for grade in grades:
                        pct = (yc[grade] / len(df_yaourt) * 100)
                        st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
        
        # SuperNutri-Score
        st.markdown("---")
        st.subheader("3️⃣ SuperNutri-Score")
        if 'supernutri_score' in df_pain.columns and 'supernutri_score' in df_yaourt.columns:
            grades = ['A','B','C','D','E']
            pc = df_pain['supernutri_score'].value_counts().reindex(grades, fill_value=0)
            yc = df_yaourt['supernutri_score'].value_counts().reindex(grades, fill_value=0)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(name='🥖 Pains', x=grades, y=pc.values,
                                marker_color='#3498db', text=pc.values, textposition='outside'))
            fig.add_trace(go.Bar(name='🥛 Yaourts', x=grades, y=yc.values,
                                marker_color='#e74c3c', text=yc.values, textposition='outside'))
            fig.update_layout(barmode='group', height=400, xaxis_title="Grade", yaxis_title="Nombre")
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Répartition en pourcentage")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🥖 Pains**")
                for grade in grades:
                    pct = (pc[grade] / len(df_pain) * 100)
                    st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
            with col2:
                st.markdown("**🥛 Yaourts**")
                for grade in grades:
                    pct = (yc[grade] / len(df_yaourt) * 100)
                    st.metric(f"Grade {grade}", f"{pct:.1f}%", label_visibility="visible")
    else:
        st.info("Chargez les vraies données pour voir les comparaisons complètes.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:gray;padding:1rem;'>
    <p><strong>SuperNutri-Score</strong> - Projet ELECTRE TRI</p>
    <p style='font-size:0.9rem;'>3 algorithmes: Nutri-Score + ELECTRE TRI + SuperNutri-Score</p>
</div>
""", unsafe_allow_html=True)