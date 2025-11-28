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
    "📖 Transparence des Algorithmes",
    "🧮 Calculateur Complet",
    "🧮 Calculator (English)",
    "📊 Analyse de Données", 
    "⚖️ Comparaison Groupes"
])

COLORS = {'A':'#038141','B':'#85BB2F','C':'#FECB02','D':'#EE8100','E':'#E63E11'}

# ============================================================
# PAGE 0: TRANSPARENCE DES ALGORITHMES
# ============================================================
if page == "📖 Transparence des Algorithmes":
    st.header("📖 Transparence des Algorithmes de Décision")
    
    st.markdown("""
    Dans le cadre du cours **"Transparence des Algorithmes pour la Décision"**, nous présentons 
    trois modèles d'évaluation nutritionnelle avec une transparence totale sur leurs mécanismes de calcul.
    """)
    
    # ========== NUTRI-SCORE 2025 ==========
    st.markdown("---")
    st.subheader("1️⃣ Nutri-Score 2025 (ANSES)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 Principe
        Le Nutri-Score est un système de notation officiel développé par l'ANSES (Agence nationale de sécurité sanitaire).
        Il attribue un score de -15 à +40 basé sur la composition nutritionnelle pour 100g de produit.
        
        ### 📊 Calcul du Score
        **Score Final = Points Négatifs - Points Positifs**
        
        #### ❌ Points Négatifs (0-60 points)
        - **Énergie (kJ):** 0-10 points
          - *Pourquoi?* L'excès calorique contribue à l'obésité
          - Seuils: 335 kJ = 1pt, 670 kJ = 2pts, ..., 3350+ kJ = 10pts
        
        - **Graisses saturées (g):** 0-10 points
          - *Pourquoi?* Augmentent le risque cardiovasculaire
          - Seuils: 1g = 1pt, 2g = 2pts, ..., 10+ g = 10pts
        
        - **Sucres (g):** 0-15 points
          - *Pourquoi?* Favorisent diabète et obésité
          - Seuils: 3.4g = 1pt, 6.8g = 2pts, ..., 51+ g = 15pts
        
        - **Sel (g):** 0-20 points
          - *Pourquoi?* Hypertension artérielle
          - Seuils: 0.2g = 1pt, 0.4g = 2pts, ..., 4.0+ g = 20pts
        
        #### ✅ Points Positifs (0-15 points)
        - **Fruits/Légumes/Noix (%):** 0-5 points
          - *Pourquoi?* Riches en vitamines, minéraux, fibres
          - >40% = 1pt, >60% = 2pts, >80% = 5pts
        
        - **Fibres (g):** 0-5 points
          - *Pourquoi?* Santé digestive, satiété
          - Seuils: 0.9g = 1pt, 1.9g = 2pts, ..., 4.7+ g = 5pts
        
        - **Protéines (g):** 0-5 points
          - *Pourquoi?* Essentielles pour l'organisme
          - Seuils: 1.6g = 1pt, 3.2g = 2pts, ..., 8.0+ g = 5pts
        
        ### ⚖️ Règle Spéciale 2025
        **Si Points Négatifs ≥ 11 ET Fruits/Légumes < 80%**
        → Les points protéines ne sont PAS comptés
        
        *Pourquoi?* Éviter que des produits trop gras/sucrés/salés obtiennent un bon score 
        uniquement grâce aux protéines.
        
        ### 🎨 Attribution du Grade
        - **A (Vert foncé):** Score ≤ -1 (Meilleure qualité)
        - **B (Vert clair):** Score 0 à 2
        - **C (Jaune):** Score 3 à 10
        - **D (Orange):** Score 11 à 18
        - **E (Rouge):** Score ≥ 19 (Moins bonne qualité)
        """)
    
    with col2:
        st.markdown("""
        ### 📌 Transparence
        
        ✅ **Tous les seuils sont publics**
        
        ✅ **Formule simple et reproductible**
        
        ✅ **Basé sur des preuves scientifiques**
        
        ✅ **Validé par l'ANSES**
        
        ### 🔍 Exemple
        **Pain complet:**
        - Énergie: 1050 kJ → 2 pts
        - Graisses sat.: 0.8g → 0 pts
        - Sucres: 2.1g → 0 pts
        - Sel: 1.05g → 2 pts
        - **Négatifs = 4 pts**
        
        - Fruits/Lég.: 5% → 0 pts
        - Fibres: 8.5g → 5 pts
        - Protéines: 10.2g → 2 pts
        - **Positifs = 7 pts**
        
        **Score = 4 - 7 = -3**
        **→ Grade A** ✅
        """)
    
    # ========== ELECTRE TRI ==========
    st.markdown("---")
    st.subheader("2️⃣ ELECTRE TRI (Méthode Multicritère)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 Principe
        ELECTRE TRI est une méthode de classification multicritère développée pour des décisions complexes.
        Elle compare chaque produit à des **profils de référence** pour déterminer sa catégorie.
        
        ### 📊 Les 8 Critères Évalués
        
        | Critère | Poids | Sens | Pourquoi? |
        |---------|-------|------|-----------|
        | **Énergie** | 2 | ⬇️ Minimiser | Contrôle calorique |
        | **Graisses saturées** | 2 | ⬇️ Minimiser | Santé cardiovasculaire |
        | **Sucres** | 2 | ⬇️ Minimiser | Prévention diabète |
        | **Sodium** | 1 | ⬇️ Minimiser | Hypertension |
        | **Protéines** | 1 | ⬆️ Maximiser | Nutrition essentielle |
        | **Fibres** | 1 | ⬆️ Maximiser | Santé digestive |
        | **Fruits/Légumes** | 1 | ⬆️ Maximiser | Apports bénéfiques |
        | **Additifs** | 1 | ⬇️ Minimiser | Naturalité |
        
        ### 🎚️ Profils de Référence
        6 profils (π1 à π6) calculés automatiquement sur les **329 produits** (Pains + Yaourts):
        - **π1:** Quantile 5% ou 95% (selon le sens)
        - **π2:** Quantile 20% ou 80%
        - **π3:** Quantile 40% ou 60%
        - **π4:** Quantile 60% ou 40%
        - **π5:** Quantile 80% ou 20%
        - **π6:** Quantile 95% ou 5%
        
        Ces profils définissent les frontières entre les classes A', B', C', D', E'.
        
        ### 🔄 Deux Procédures
        
        **Pessimiste (Conservative):**
        - Compare du meilleur (π5) vers le moins bon (π1)
        - Classe le produit dès qu'il dépasse un profil
        - **Plus strict** → Grades souvent plus bas
        
        **Optimiste (Favorable):**
        - Compare du moins bon (π1) vers le meilleur (π6)
        - Classe le produit au niveau où il ne dépasse plus
        - **Plus généreux** → Grades souvent plus hauts
        
        ### 🎛️ Seuil Lambda (λ)
        **λ = niveau de concordance requis**
        - **λ = 0.6:** 60% des critères (pondérés) doivent être favorables
        - **λ = 0.7:** 70% des critères doivent être favorables (plus strict)
        
        ### 🎨 Attribution des Classes
        - **A' (Excellent):** Dépasse π5
        - **B' (Très bon):** Entre π4 et π5
        - **C' (Bon):** Entre π3 et π4
        - **D' (Moyen):** Entre π2 et π3
        - **E' (À améliorer):** En dessous de π2
        """)
    
    with col2:
        st.markdown("""
        ### 📌 Transparence
        
        ✅ **8 critères explicites**
        
        ✅ **Poids justifiés et fixes**
        
        ✅ **Profils calculés sur vraies données**
        
        ✅ **Procédures reproductibles**
        
        ✅ **4 résultats affichés** (2 procédures × 2 lambdas)
        
        ### 🔍 Avantages
        
        **Multi-dimensionnel:**
        Prend en compte 8 aspects simultanément
        
        **Robuste:**
        4 classifications différentes pour voir la variabilité
        
        **Transparent:**
        Toutes les règles sont visibles
        
        **Adaptable:**
        Profils recalculés sur vraies données
        
        ---
        
        ### ⚙️ Calcul de Concordance
        
        Pour chaque critère:
        - Si le produit est meilleur que le profil → 1
        - Sinon → 0
        
        Concordance globale:

        C = Σ(poids × concordance) 
            ─────────────────────
                Σ(poids)
        
        Si C ≥ λ → le produit dépasse le profil
        """)
    
    # ========== SUPERNUTRI-SCORE ==========
    st.markdown("---")
    st.subheader("3️⃣ SuperNutri-Score (Modèle Innovant)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 Principe
        Le **SuperNutri-Score** combine 3 dimensions pour une évaluation holistique:
        1. **Nutrition** (via ELECTRE TRI)
        2. **Environnement** (via Green-Score / Eco-Score)
        3. **Agriculture** (Bio ou non)
        
        ### 🧮 Algorithme Transparent
        
        **Étape 1: Base Nutritionnelle**
        - Départ = ELECTRE TRI Pessimiste λ=0.6
        - A' → A, B' → B, C' → C, D' → D, E' → E
        
        **Étape 2: Bonus Green-Score A**
        """)
        
        st.code("""if green_score == 'A' and grade > A:
    grade += 1  # Amélioration d'un niveau""", language="python")
        
        st.markdown("*Pourquoi?* Récompense l'excellence environnementale")
        st.markdown("**Étape 3: Malus Green-Score D/E**")
        
        st.code("""if green_score in ['D', 'E'] and grade < E:
    grade -= 1  # Dégradation d'un niveau""", language="python")
        
        st.markdown("*Pourquoi?* Pénalise l'impact environnemental élevé")
        st.markdown("**Étape 4: Bonus Bio**")
        
        st.code("""if is_bio and green_score != 'E' and grade > A:
    grade += 1  # Amélioration d'un niveau""", language="python")
        
        st.markdown("*Pourquoi?* Valorise l'agriculture biologique (si pas de Green-Score E)")
        st.markdown("**Étape 5: Limitation Green-Score E**")
        
        st.code("""if green_score == 'E':
    grade = max(grade, C)  # Plafond à C""", language="python")
        
        st.markdown("""
        *Pourquoi?* Un produit très polluant ne peut pas avoir A ou B
        
        ### 🎨 Grade Final
        Le grade final (A à E) reflète l'équilibre entre:
        - Qualité nutritionnelle
        - Impact environnemental
        - Mode de production
        
        ### 📊 Exemple de Calcul
        
        **Produit: Pain bio avec Green-Score B**
        1. ELECTRE Pess. 0.6 → B' → **Grade B**
        2. Green-Score = B → Pas de bonus A
        3. Green-Score = B → Pas de malus D/E
        4. Bio = Oui + Green ≠ E → **Bonus! B → A**
        5. Green-Score ≠ E → Pas de limitation
        
        **SuperNutri-Score Final: A** ✅
        
        **Produit: Yaourt avec Green-Score E**
        1. ELECTRE Pess. 0.6 → A' → **Grade A**
        2. Green-Score = E → Pas de bonus A
        3. Green-Score = E → **Malus! A → B**
        4. Bio = Non → Pas de bonus
        5. Green-Score = E → **Limitation! Max = C**
        
        **SuperNutri-Score Final: C** ⚠️
        """)
    
    with col2:
        st.markdown("""
        ### 📌 Transparence
        
        ✅ **5 règles simples et fixes**
        
        ✅ **Aucun paramètre caché**
        
        ✅ **Logique explicite et reproductible**
        
        ✅ **Chaque règle est justifiée**
        
        ### 🌟 Innovation
        
        **Holistique:**
        Première fois que nutrition, environnement et bio sont combinés
        
        **Équilibré:**
        Chaque dimension a un impact limité (±1 grade)
        
        **Protecteur:**
        Limitation pour Green-Score E
        
        **Pédagogique:**
        Le consommateur voit quelles règles s'appliquent
        
        ### 🎯 Objectif
        
        Guider vers des choix:
        - ✅ Nutritionnellement sains
        - ✅ Écologiquement responsables
        - ✅ Issus d'agriculture durable
        
        ### 📋 Règles Appliquées
        
        L'application affiche toujours:
        - Le grade de base ELECTRE
        - Les bonus/malus appliqués
        - Le grade final
        
        """)
    
    # ========== SYNTHÈSE ==========
    st.markdown("---")
    st.subheader("📊 Comparaison des 3 Modèles")
    
    comparison_df = pd.DataFrame({
        'Caractéristique': [
            'Type',
            'Critères évalués',
            'Résultats fournis',
            'Complexité',
            'Dimensions',
            'Base scientifique',
            'Poids des critères',
            'Calcul',
            'Grades possibles'
        ],
        'Nutri-Score 2025': [
            'Officiel ANSES',
            '7 (nutrition uniquement)',
            '1 grade',
            'Simple',
            'Nutrition seule',
            'Très forte',
            'Fixes et publics',
            'Addition/Soustraction',
            'A, B, C, D, E'
        ],
        'ELECTRE TRI': [
            'Multicritère',
            '8 (nutrition + additifs)',
            '4 grades (2λ × 2 procédures)',
            'Avancée',
            'Nutrition + Additifs',
            'Forte (méthode MCDA)',
            'Fixes: 2-2-2-1-1-1-1-1',
            'Concordance + Profils',
            "A', B', C', D', E'"
        ],
        'SuperNutri-Score': [
            'Innovant',
            '8 nutrition + Eco + Bio',
            '1 grade',
            'Modérée',
            'Nutrition + Environnement',
            'Combinaison de modèles',
            'Hérités d\'ELECTRE',
            'ELECTRE + Règles',
            'A, B, C, D, E'
        ]
    })
    
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    st.markdown("""
    ---
    ### 🎓 Conclusion: La Transparence au Service de la Décision
    
    Les trois modèles présentés illustrent différents niveaux de complexité dans l'aide à la décision:
    
    1. **Nutri-Score:** Simplicité et adoption massive (réglementaire)
    2. **ELECTRE TRI:** Robustesse méthodologique et analyse multicritère
    3. **SuperNutri-Score:** Innovation et vision holistique (nutrition + environnement)
    
    **L'objectif commun:** Permettre au consommateur de faire des choix éclairés en comprenant 
    **exactement comment** les algorithmes arrivent à leurs conclusions.

    """)

# ============================================================
# PAGE 1: CALCULATEUR COMPLET (Requis par professeur)
# ============================================================
elif page == "🧮 Calculateur Complet":
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

    # ========== SECTION 4: SUPERNUTRI-SCORE (Règles) ==========
    st.markdown("---")
    st.subheader("🌟 4. SuperNutri-Score (Règles Prédéfinies)")
    
    st.info("""
    **SuperNutri-Score = ELECTRE TRI + Green-Score + Bio**
    
    **Règles de calcul:**
    1. **Base:** ELECTRE TRI Pessimiste λ=0.6 (A'→A, B'→B, C'→C, D'→D, E'→E)
    2. **Bonus Green-Score A:** +1 grade (mais pas au-dessus de A)
    3. **Malus Green-Score D/E:** -1 grade
    4. **Bonus Bio:** +1 grade (non applicable si Green-Score = E)
    5. **Limitation:** Si Green-Score = E → grade maximum = C
    
    *Toutes les règles sont fixes et transparentes pour le consommateur.*
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
# PAGE: CALCULATOR (ENGLISH VERSION)
# ============================================================
elif page == "🧮 Calculator (English)":
    st.header("🧮 Consumer Interface - Complete Evaluation")
    
    st.info("""
    **Enter your product information and get:**
    - ✅ Nutri-Score (score + grade)
    - ✅ ELECTRE TRI Pessimistic & Optimistic
    - ✅ SuperNutri-Score (enhanced model)
    """)
    
    # ========== SECTION 1: NUTRITIONAL INFORMATION ==========
    st.markdown("---")
    st.subheader("📝 1. Nutritional Information (per 100g)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        energy_kj_en = st.number_input("Energy (kJ)", 0, 4000, 1000, 
                                    help="Energy value in kilojoules")
    
    with col2:
        saturated_fat_en = st.number_input("Saturated Fat (g)", 0.0, 100.0, 1.0, 0.1)
    
    with col3:
        sugar_en = st.number_input("Sugars (g)", 0.0, 100.0, 5.0, 0.1)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sodium_mg_en = st.number_input("Sodium (mg)", 0, 5000, 100)
    
    with col2:
        protein_en = st.number_input("Proteins (g)", 0.0, 100.0, 5.0, 0.1)
    
    with col3:
        fiber_en = st.number_input("Fiber (g)", 0.0, 50.0, 2.0, 0.1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fruits_veg_nuts_pct_en = st.slider("Fruits/Vegetables/Nuts (%)", 0, 100, 0)
    
    with col2:
        additives_count_en = st.number_input("Number of additives", 0, 20, 0)
    
    # ========== SECTION 2: ENVIRONMENTAL INFORMATION ==========
    st.markdown("---")
    st.subheader("🌱 2. Environmental Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ecoscore_grade_en = st.selectbox("Eco-Score (Green-Score)", 
                                     ['A', 'B', 'C', 'D', 'E'],
                                     help="Environmental impact of the product")
    
    with col2:
        is_organic_en = st.checkbox("Organic Product (Bio)", 
                                 help="Product from organic farming")
    
    # ========== SECTION 3: ELECTRE TRI PARAMETERS ==========
    st.markdown("---")
    st.subheader("⚙️ 3. ELECTRE TRI Parameters (Predefined)")
    
    st.info("""
    **Fixed model parameters:**
    - Weights: Energy=2, Sugars=2, Saturated Fat=2, Sodium=1, Proteins=1, Fiber=1, Fruits/Veg.=1, Additives=1
    - Thresholds λ: 0.6 and 0.7 (both will be calculated)
    """)
    
    # ========== CALCULATE BUTTON ==========
    st.markdown("---")
    
    if st.button("🚀 CALCULATE THE 3 ALGORITHMS", type="primary", use_container_width=True, key="calc_en"):
        
        # Convert sodium to salt
        sodium_g_en = sodium_mg_en / 1000
        sel_g_en = sodium_mg_en / 400
        
        # ==========================================
        # ALGORITHM 1: NUTRI-SCORE 2025
        # ==========================================
        st.markdown("---")
        st.header("📊 RESULTS")
        
        st.subheader("1️⃣ Nutri-Score 2025 (ANSES)")
        
        # Calculate negative points
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
        
        pts_energie_en = score_energie(energy_kj_en)
        pts_sat_fat_en = score_satures(saturated_fat_en)
        pts_sugar_en = score_sucres(sugar_en)
        pts_sel_en = score_sel(sel_g_en)
        
        negative_pts_en = pts_energie_en + pts_sat_fat_en + pts_sugar_en + pts_sel_en
        
        # Calculate positive points
        if fruits_veg_nuts_pct_en > 80:
            pts_fruits_en = 5
        elif fruits_veg_nuts_pct_en > 60:
            pts_fruits_en = 2
        elif fruits_veg_nuts_pct_en > 40:
            pts_fruits_en = 1
        else:
            pts_fruits_en = 0
        
        pts_fiber_en = int(np.searchsorted([0.9,1.9,2.8,3.7,4.7], fiber_en, side="right"))
        pts_protein_en = int(np.searchsorted([1.6,3.2,4.8,6.4,8.0], protein_en, side="right"))
        
        positive_pts_en = pts_fruits_en + pts_fiber_en + pts_protein_en
        
        # 2025 rule
        if negative_pts_en >= 11 and fruits_veg_nuts_pct_en < 80:
            positive_pts_final_en = positive_pts_en - pts_protein_en
        else:
            positive_pts_final_en = positive_pts_en
        
        nutriscore_score_en = negative_pts_en - positive_pts_final_en
        
        # Nutri-Score grade
        if nutriscore_score_en <= -1:
            nutriscore_grade_en = "A"
        elif nutriscore_score_en <= 2:
            nutriscore_grade_en = "B"
        elif nutriscore_score_en <= 10:
            nutriscore_grade_en = "C"
        elif nutriscore_score_en <= 18:
            nutriscore_grade_en = "D"
        else:
            nutriscore_grade_en = "E"
        
        # Display Nutri-Score
        col1, col2, col3 = st.columns([1,2,1])
        
        with col2:
            st.markdown(f"""
            <div style='text-align:center; padding:2rem; background-color:{COLORS[nutriscore_grade_en]}22; border-radius:10px;'>
                <h1 style='color:{COLORS[nutriscore_grade_en]}; font-size:6rem; margin:0;'>{nutriscore_grade_en}</h1>
                <h3 style='color:#666;'>Score: {nutriscore_score_en}</h3>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("❌ Negative points", negative_pts_en)
            st.caption(f"• Energy: {pts_energie_en} pts")
            st.caption(f"• Saturated fat: {pts_sat_fat_en} pts")
            st.caption(f"• Sugars: {pts_sugar_en} pts")
            st.caption(f"• Salt: {pts_sel_en} pts")
        
        with col2:
            st.metric("✅ Positive points", positive_pts_final_en)
            st.caption(f"• Fruits/Vegetables: {pts_fruits_en} pts")
            st.caption(f"• Fiber: {pts_fiber_en} pts")
            st.caption(f"• Proteins: {pts_protein_en if positive_pts_final_en == positive_pts_en else 0} pts")
            if negative_pts_en >= 11 and fruits_veg_nuts_pct_en < 80:
                st.warning("⚠️ Proteins not counted (2025 rule)")
        
        with col3:
            st.metric("📊 Final score", nutriscore_score_en)
            st.caption("Negative - Positive")
        
        # ==========================================
        # ALGORITHM 2: ELECTRE TRI
        # ==========================================
        st.markdown("---")
        st.subheader("2️⃣ ELECTRE TRI (Pessimistic & Optimistic)")
        
        # Create product vector
        produit_en = {
            'energy_kj': energy_kj_en,
            'saturated_fat': saturated_fat_en,
            'sugar': sugar_en,
            'sodium_g': sodium_g_en,
            'protein': protein_en,
            'fiber': fiber_en,
            'fruits_veg_nuts_pct': fruits_veg_nuts_pct_en,
            'additives_count': additives_count_en
        }
        
        # Fixed weights
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
        
        # Optimization direction
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
        
        # Calculate profiles (quantiles)
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
        
        # ELECTRE functions
        def concordance_partielle_en(H, b, crit, sens):
            if sens[crit] == 'max':
                return 1 if H[crit] >= b[crit] else 0
            else:
                return 1 if H[crit] <= b[crit] else 0
        
        def concordance_globale_en(H, b, poids, sens):
            num = sum(poids[c] * concordance_partielle_en(H, b, c, sens) for c in poids)
            denom = sum(poids.values())
            return num / denom
        
        # PESSIMISTIC λ=0.6
        classe_pess_06_en = "E'"
        for i in reversed(range(1, 6)):
            c = concordance_globale_en(produit_en, profils[f"pi{i}"], poids, sens)
            if c >= 0.6:
                classe_pess_06_en = ["E'", "D'", "C'", "B'", "A'"][i-1]
                break
        
        # OPTIMISTIC λ=0.6
        classe_opt_06_en = "A'"
        for i in range(2, 7):
            b = profils[f"pi{i-1}"]
            c_biH = concordance_globale_en(b, produit_en, poids, sens)
            c_Hbi = concordance_globale_en(produit_en, b, poids, sens)
            if c_biH >= 0.6 and c_Hbi < 0.6:
                classe_opt_06_en = ["E'", "D'", "C'", "B'", "A'"][i-2]
                break
        
        # PESSIMISTIC λ=0.7
        classe_pess_07_en = "E'"
        for i in reversed(range(1, 6)):
            c = concordance_globale_en(produit_en, profils[f"pi{i}"], poids, sens)
            if c >= 0.7:
                classe_pess_07_en = ["E'", "D'", "C'", "B'", "A'"][i-1]
                break
        
        # OPTIMISTIC λ=0.7
        classe_opt_07_en = "A'"
        for i in range(2, 7):
            b = profils[f"pi{i-1}"]
            c_biH = concordance_globale_en(b, produit_en, poids, sens)
            c_Hbi = concordance_globale_en(produit_en, b, poids, sens)
            if c_biH >= 0.7 and c_Hbi < 0.7:
                classe_opt_07_en = ["E'", "D'", "C'", "B'", "A'"][i-2]
                break
        
        # Display ELECTRE TRI - 4 results
        st.markdown("**λ = 0.6**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#3498db22; border-radius:10px;'>
                <h4>Pessimistic (λ=0.6)</h4>
                <h1 style='color:#3498db; font-size:3.5rem; margin:0;'>{classe_pess_06_en}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#2ecc7122; border-radius:10px;'>
                <h4>Optimistic (λ=0.6)</h4>
                <h1 style='color:#2ecc71; font-size:3.5rem; margin:0;'>{classe_opt_06_en}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("**λ = 0.7**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#e67e2222; border-radius:10px;'>
                <h4>Pessimistic (λ=0.7)</h4>
                <h1 style='color:#e67e22; font-size:3.5rem; margin:0;'>{classe_pess_07_en}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style='text-align:center; padding:1.5rem; background-color:#9b59b622; border-radius:10px;'>
                <h4>Optimistic (λ=0.7)</h4>
                <h1 style='color:#9b59b6; font-size:3.5rem; margin:0;'>{classe_opt_07_en}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.info("**Parameters:** Fixed weights (see above) | Profiles calculated on 329 products")
        
        # ==========================================
        # ALGORITHM 3: SUPERNUTRI-SCORE
        # ==========================================
        st.markdown("---")
        st.subheader("3️⃣ SuperNutri-Score (Enhanced Model)")
        
        st.info("""
        **SuperNutri-Score = ELECTRE TRI + Eco-Score + Bio**
        
        Combination of 3 dimensions: Nutrition (ELECTRE) + Environment (Eco) + Agriculture (Bio)
        """)
        
        # Calculate SuperNutri-Score (based on pessimistic λ=0.6)
        map_in = {"A'":1, "B'":2, "C'":3, "D'":4, "E'":5}
        map_out = {1:"A", 2:"B", 3:"C", 4:"D", 5:"E"}
        
        score_super_en = map_in[classe_pess_06_en]
        
        # Rules
        regles_appliquees_en = []
        
        # Eco-Score A
        if ecoscore_grade_en == "A" and score_super_en > 1:
            score_super_en -= 1
            regles_appliquees_en.append("✅ Eco-Score A Bonus: +1 grade")
        
        # Eco-Score D/E
        if ecoscore_grade_en in ["D", "E"] and score_super_en < 5:
            score_super_en += 1
            regles_appliquees_en.append("⚠️ Eco-Score D/E Penalty: -1 grade")
        
        # Bio
        if is_organic_en and ecoscore_grade_en != "E" and score_super_en > 1:
            score_super_en -= 1
            regles_appliquees_en.append("✅ Organic Bonus: +1 grade")
        
        # Eco E limitation
        if ecoscore_grade_en == "E":
            score_super_en = max(score_super_en, 3)
            regles_appliquees_en.append("⚠️ Eco-Score E Limitation: max grade = C")
        
        score_super_en = max(1, min(5, score_super_en))
        supernutri_grade_en = map_out[score_super_en]
        
        # Display SuperNutri-Score
        st.markdown(f"""
        <div style='text-align:center; padding:2rem; background-color:{COLORS[supernutri_grade_en]}22; border-radius:10px; border: 3px solid {COLORS[supernutri_grade_en]};'>
            <h2 style='color:#333; margin:0;'>Final SuperNutri-Score</h2>
            <h1 style='color:{COLORS[supernutri_grade_en]}; font-size:7rem; margin:0.5rem 0;'>{supernutri_grade_en}</h1>
            <p style='font-size:1.2rem; color:#666;'>
                Base: ELECTRE Pessimistic λ=0.6 ({classe_pess_06_en}) | Eco: {ecoscore_grade_en} | Bio: {'Yes' if is_organic_en else 'No'}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if regles_appliquees_en:
            st.markdown("**Applied rules:**")
            for regle in regles_appliquees_en:
                st.markdown(f"- {regle}")
        
        # ==========================================
        # SUMMARY TABLE
        # ==========================================
        st.markdown("---")
        st.subheader("📋 Summary Table")
        
        recap_df_en = pd.DataFrame({
            'Algorithm': [
                'Nutri-Score 2025',
                'ELECTRE TRI Pessimistic (λ=0.6)',
                'ELECTRE TRI Optimistic (λ=0.6)',
                'ELECTRE TRI Pessimistic (λ=0.7)',
                'ELECTRE TRI Optimistic (λ=0.7)',
                'SuperNutri-Score'
            ],
            'Grade': [
                nutriscore_grade_en,
                classe_pess_06_en,
                classe_opt_06_en,
                classe_pess_07_en,
                classe_opt_07_en,
                supernutri_grade_en
            ],
            'Info': [
                f'Score: {nutriscore_score_en}',
                'Conservative classification',
                'Favorable classification',
                'Conservative classification (strict)',
                'Favorable classification (strict)',
                'ELECTRE + Eco + Bio'
            ]
        })
        
        st.dataframe(recap_df_en[['Algorithm', 'Grade', 'Info']], use_container_width=True, hide_index=True)
        
        # Comparative visualization
        st.markdown("---")
        st.subheader("📊 Visual Comparison")
        
        grades_map = {'A':5, 'B':4, 'C':3, 'D':2, 'E':1, "A'":5, "B'":4, "C'":3, "D'":2, "E'":1}
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Nutri-Score', 'ELECTRE\nPess. 0.6', 'ELECTRE\nOpt. 0.6', 
               'ELECTRE\nPess. 0.7', 'ELECTRE\nOpt. 0.7', 'SuperNutri'],
            y=[grades_map[nutriscore_grade_en], grades_map[classe_pess_06_en], 
               grades_map[classe_opt_06_en], grades_map[classe_pess_07_en],
               grades_map[classe_opt_07_en], grades_map[supernutri_grade_en]],
            marker_color=[COLORS[nutriscore_grade_en], '#3498db', '#2ecc71', 
                         '#e67e22', '#9b59b6', COLORS[supernutri_grade_en]],
            text=[nutriscore_grade_en, classe_pess_06_en, classe_opt_06_en, 
                  classe_pess_07_en, classe_opt_07_en, supernutri_grade_en],
            textposition='outside',
            textfont=dict(size=18, color='black')
        ))
        
        fig.update_layout(
            yaxis_title="Quality (1=E, 5=A)",
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