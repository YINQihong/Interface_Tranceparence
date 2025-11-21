import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 页面配置
st.set_page_config(
    page_title="ELECTRE TRI - Analyse Nutri-Score",
    page_icon="🥖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 标题和介绍
st.title("🥖 Analyse ELECTRE TRI - Classification des Produits Alimentaires")
st.markdown("""
Cette application interactive présente les résultats de la méthode **ELECTRE TRI** 
appliquée à la classification des produits alimentaires en fonction de critères nutritionnels.
""")

# 侧边栏
st.sidebar.header("📊 Navigation")
page = st.sidebar.radio(
    "Choisissez une section:",
    ["Vue d'ensemble", "Résultats ELECTRE TRI", "Comparaison avec Nutri-Score", "Analyse détaillée"]
)

# 数据加载函数
@st.cache_data
def load_data():
    """加载数据 - 你需要准备这些文件"""
    try:
        # 假设你有这个Excel文件
        df_results = pd.read_excel("ELECTRE_TRI_Resultats.xlsx")
        df_products = pd.read_csv("Products.csv")
        return df_results, df_products
    except FileNotFoundError:
        # 如果文件不存在,创建示例数据
        st.warning("⚠️ Fichiers de données non trouvés. Utilisation de données d'exemple.")
        return create_sample_data()

def create_sample_data():
    """创建示例数据用于演示"""
    # 这是示例数据,你需要替换成真实数据
    sample_results = pd.DataFrame({
        'product_id': range(1, 21),
        'product_name': [f'Produit {i}' for i in range(1, 21)],
        'nutriscore_grade': ['A', 'B', 'C', 'D', 'E'] * 4,
        'Classe_Pessimiste_λ=0.6': ['A\'', 'B\'', 'C\'', 'D\'', 'E\''] * 4,
        'Classe_Optimiste_λ=0.6': ['A\'', 'B\'', 'C\'', 'D\'', 'E\''] * 4,
        'Classe_Pessimiste_λ=0.7': ['A\'', 'B\'', 'C\'', 'D\'', 'E\''] * 4,
        'Classe_Optimiste_λ=0.7': ['A\'', 'B\'', 'C\'', 'D\'', 'E\''] * 4,
    })
    
    sample_products = pd.DataFrame({
        'product_id': range(1, 21),
        'product_name': [f'Produit {i}' for i in range(1, 21)],
        'energy_kj': np.random.randint(800, 2000, 20),
        'saturated_fat': np.random.uniform(0.5, 10, 20),
        'sugar': np.random.uniform(2, 20, 20),
        'sodium_g': np.random.uniform(0.1, 2, 20),
        'protein': np.random.uniform(5, 15, 20),
        'fiber': np.random.uniform(0, 10, 20),
    })
    
    return sample_results, sample_products

# 加载数据
df_results, df_products = load_data()

# 合并数据
if 'product_id' in df_results.columns and 'product_id' in df_products.columns:
    df_merged = df_results.merge(df_products, on='product_id', how='left', suffixes=('', '_prod'))

# ==================== PAGE 1: VUE D'ENSEMBLE ====================
if page == "Vue d'ensemble":
    st.header("📈 Vue d'ensemble du projet")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Nombre de produits", 
            len(df_results),
            help="Nombre total de produits analysés"
        )
    
    with col2:
        st.metric(
            "Critères analysés", 
            8,
            help="Energy, Graisses saturées, Sucres, Sodium, Protéines, Fibres, Fruits/Légumes, Additifs"
        )
    
    with col3:
        st.metric(
            "Valeurs λ testées", 
            2,
            help="λ = 0.6 et λ = 0.7"
        )
    
    st.markdown("---")
    
    # Aperçu des données
    st.subheader("📋 Aperçu des résultats")
    st.dataframe(
        df_results.head(10),
        use_container_width=True,
        hide_index=True
    )
    
    # Statistiques de base
    st.subheader("📊 Statistiques des classifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Nutri-Score")
        nutri_counts = df_results['nutriscore_grade'].value_counts().sort_index()
        fig_nutri = px.bar(
            x=nutri_counts.index,
            y=nutri_counts.values,
            labels={'x': 'Grade', 'y': 'Nombre de produits'},
            color=nutri_counts.index,
            color_discrete_map={'A': '#038141', 'B': '#85BB2F', 'C': '#FECB02', 'D': '#EE8100', 'E': '#E63E11'}
        )
        fig_nutri.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig_nutri, use_container_width=True)
    
    with col2:
        st.markdown("#### ELECTRE TRI (λ=0.6, Pessimiste)")
        electre_counts = df_results['Classe_Pessimiste_λ=0.6'].value_counts().sort_index()
        fig_electre = px.bar(
            x=electre_counts.index,
            y=electre_counts.values,
            labels={'x': 'Classe', 'y': 'Nombre de produits'},
            color=electre_counts.index,
            color_discrete_map={'A\'': '#038141', 'B\'': '#85BB2F', 'C\'': '#FECB02', 'D\'': '#EE8100', 'E\'': '#E63E11'}
        )
        fig_electre.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig_electre, use_container_width=True)

# ==================== PAGE 2: RÉSULTATS ELECTRE TRI ====================
elif page == "Résultats ELECTRE TRI":
    st.header("🎯 Résultats ELECTRE TRI")
    
    # Sélection de λ et procédure
    col1, col2 = st.columns(2)
    with col1:
        lambda_val = st.selectbox(
            "Choisir la valeur de λ:",
            ["0.6", "0.7"],
            help="Seuil de concordance majoritaire"
        )
    
    with col2:
        procedure = st.selectbox(
            "Choisir la procédure:",
            ["Pessimiste", "Optimiste"],
            help="Procédure d'affectation ELECTRE TRI"
        )
    
    col_name = f"Classe_{procedure}_λ={lambda_val}"
    
    st.markdown("---")
    
    # Distribution des classes
    st.subheader(f"📊 Distribution - {procedure} (λ={lambda_val})")
    
    class_counts = df_results[col_name].value_counts().sort_index()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = px.bar(
            x=class_counts.index,
            y=class_counts.values,
            labels={'x': 'Classe ELECTRE TRI', 'y': 'Nombre de produits'},
            color=class_counts.index,
            color_discrete_map={'A\'': '#038141', 'B\'': '#85BB2F', 'C\'': '#FECB02', 'D\'': '#EE8100', 'E\'': '#E63E11'},
            text=class_counts.values
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Statistiques")
        for classe in sorted(class_counts.index):
            count = class_counts[classe]
            pct = (count / len(df_results)) * 100
            st.metric(f"Classe {classe}", f"{count} produits", f"{pct:.1f}%")
    
    # Tableau détaillé
    st.subheader("📋 Liste des produits classés")
    
    # Filtre par classe
    selected_class = st.multiselect(
        "Filtrer par classe:",
        options=sorted(df_results[col_name].unique()),
        default=sorted(df_results[col_name].unique())
    )
    
    filtered_df = df_results[df_results[col_name].isin(selected_class)]
    
    st.dataframe(
        filtered_df[['product_name', 'nutriscore_grade', col_name]],
        use_container_width=True,
        hide_index=True
    )
    
    # Téléchargement
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger les résultats (CSV)",
        data=csv,
        file_name=f"resultats_electre_{procedure}_lambda{lambda_val}.csv",
        mime="text/csv",
    )

# ==================== PAGE 3: COMPARAISON ====================
elif page == "Comparaison avec Nutri-Score":
    st.header("🔄 Comparaison ELECTRE TRI vs Nutri-Score")
    
    # Sélection des paramètres
    col1, col2 = st.columns(2)
    with col1:
        lambda_val = st.selectbox("Valeur de λ:", ["0.6", "0.7"])
    with col2:
        procedure = st.selectbox("Procédure:", ["Pessimiste", "Optimiste"])
    
    col_name = f"Classe_{procedure}_λ={lambda_val}"
    
    st.markdown("---")
    
    # Matrice de confusion
    st.subheader("📊 Matrice de comparaison")
    
    # Créer la matrice de confusion
    confusion_matrix = pd.crosstab(
        df_results['nutriscore_grade'],
        df_results[col_name],
        margins=True,
        margins_name="Total"
    )
    
    # Heatmap
    fig = px.imshow(
        confusion_matrix.iloc[:-1, :-1],  # Exclure les totaux
        labels=dict(x="Classe ELECTRE TRI", y="Nutri-Score", color="Nombre"),
        x=confusion_matrix.columns[:-1],
        y=confusion_matrix.index[:-1],
        color_continuous_scale="Blues",
        text_auto=True
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau de la matrice
    st.dataframe(confusion_matrix, use_container_width=True)
    
    st.markdown("---")
    
    # Taux de concordance
    st.subheader("📈 Taux de concordance")
    
    # Calculer le taux de concordance (A=A', B=B', etc.)
    mapping = {'A': 'A\'', 'B': 'B\'', 'C': 'C\'', 'D': 'D\'', 'E': 'E\''}
    df_results['match'] = df_results.apply(
        lambda row: row['nutriscore_grade'] in mapping and row[col_name] == mapping[row['nutriscore_grade']], 
        axis=1
    )
    
    concordance_rate = (df_results['match'].sum() / len(df_results)) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Taux de concordance global", f"{concordance_rate:.1f}%")
    
    with col2:
        matches = df_results['match'].sum()
        st.metric("Produits concordants", f"{matches}/{len(df_results)}")
    
    with col3:
        discordants = len(df_results) - matches
        st.metric("Produits discordants", discordants)
    
    # Analyse par grade Nutri-Score
    st.subheader("📊 Concordance par grade Nutri-Score")
    
    concordance_by_grade = []
    for grade in ['A', 'B', 'C', 'D', 'E']:
        grade_df = df_results[df_results['nutriscore_grade'] == grade]
        if len(grade_df) > 0:
            grade_match = grade_df['match'].sum()
            grade_total = len(grade_df)
            grade_pct = (grade_match / grade_total) * 100
            concordance_by_grade.append({
                'Grade': grade,
                'Concordants': grade_match,
                'Total': grade_total,
                'Pourcentage': grade_pct
            })
    
    concordance_df = pd.DataFrame(concordance_by_grade)
    
    fig = px.bar(
        concordance_df,
        x='Grade',
        y='Pourcentage',
        text='Pourcentage',
        color='Grade',
        color_discrete_map={'A': '#038141', 'B': '#85BB2F', 'C': '#FECB02', 'D': '#EE8100', 'E': '#E63E11'}
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(showlegend=False, yaxis_title="Taux de concordance (%)", height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(concordance_df, use_container_width=True, hide_index=True)

# ==================== PAGE 4: ANALYSE DÉTAILLÉE ====================
elif page == "Analyse détaillée":
    st.header("🔍 Analyse détaillée des produits")
    
    # Recherche de produit
    st.subheader("🔎 Rechercher un produit")
    search_term = st.text_input("Nom du produit:", "")
    
    if search_term:
        filtered = df_results[df_results['product_name'].str.contains(search_term, case=False, na=False)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Comparaison des procédures
    st.subheader("📊 Comparaison Pessimiste vs Optimiste")
    
    lambda_choice = st.radio("Choisir λ:", ["0.6", "0.7"], horizontal=True)
    
    col_pess = f"Classe_Pessimiste_λ={lambda_choice}"
    col_opt = f"Classe_Optimiste_λ={lambda_choice}"
    
    # Différences entre pessimiste et optimiste
    df_results['difference'] = df_results[col_pess] != df_results[col_opt]
    diff_count = df_results['difference'].sum()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Produits avec classification identique", len(df_results) - diff_count)
    
    with col2:
        st.metric("Produits avec classification différente", diff_count)
    
    if diff_count > 0:
        st.subheader("⚠️ Produits avec classifications différentes")
        diff_df = df_results[df_results['difference']][['product_name', 'nutriscore_grade', col_pess, col_opt]]
        st.dataframe(diff_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Impact du λ
    st.subheader("📈 Impact du seuil λ")
    
    procedure_choice = st.radio("Choisir la procédure:", ["Pessimiste", "Optimiste"], horizontal=True)
    
    col_06 = f"Classe_{procedure_choice}_λ=0.6"
    col_07 = f"Classe_{procedure_choice}_λ=0.7"
    
    df_results['lambda_diff'] = df_results[col_06] != df_results[col_07]
    lambda_diff_count = df_results['lambda_diff'].sum()
    
    st.metric("Produits affectés différemment selon λ", lambda_diff_count)
    
    if lambda_diff_count > 0:
        lambda_diff_df = df_results[df_results['lambda_diff']][['product_name', 'nutriscore_grade', col_06, col_07]]
        st.dataframe(lambda_diff_df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Projet ELECTRE TRI - Analyse des produits alimentaires</p>
    <p>Méthode: ELECTRE TRI avec procédures pessimiste et optimiste</p>
</div>
""", unsafe_allow_html=True)
