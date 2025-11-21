import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 页面配置
st.set_page_config(
    page_title="ELECTRE TRI - Test",
    page_icon="🥖",
    layout="wide"
)

st.title("🥖 ELECTRE TRI - Version Test")
st.success("✅ L'application fonctionne!")

# 创建示例数据
@st.cache_data
def create_sample_data():
    np.random.seed(42)
    n_products = 139
    
    results = pd.DataFrame({
        'product_id': range(1, n_products + 1),
        'product_name': [f'Produit {i}' for i in range(1, n_products + 1)],
        'nutriscore_grade': np.random.choice(['A', 'B', 'C', 'D', 'E'], n_products),
        'Classe_Pessimiste_λ=0.6': np.random.choice(['A\'', 'B\'', 'C\'', 'D\'', 'E\''], n_products),
        'Classe_Optimiste_λ=0.6': np.random.choice(['A\'', 'B\'', 'C\'', 'D\'', 'E\''], n_products),
        'Classe_Pessimiste_λ=0.7': np.random.choice(['A\'', 'B\'', 'C\'', 'D\'', 'E\''], n_products),
        'Classe_Optimiste_λ=0.7': np.random.choice(['A\'', 'B\'', 'C\'', 'D\'', 'E\''], n_products),
    })
    
    return results

df_results = create_sample_data()

st.info("ℹ️ Cette version utilise des données d'exemple pour tester le déploiement.")

# Statistiques
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Nombre de produits", len(df_results))

with col2:
    st.metric("Critères analysés", 8)

with col3:
    st.metric("Valeurs λ testées", 2)

st.markdown("---")

# Aperçu des données
st.subheader("📋 Aperçu des résultats (données d'exemple)")
st.dataframe(df_results.head(10), use_container_width=True, hide_index=True)

# Distribution Nutri-Score
st.subheader("📊 Distribution Nutri-Score")
nutri_counts = df_results['nutriscore_grade'].value_counts().sort_index()

fig = px.bar(
    x=nutri_counts.index,
    y=nutri_counts.values,
    labels={'x': 'Grade', 'y': 'Nombre de produits'},
    color=nutri_counts.index,
    color_discrete_map={
        'A': '#038141', 
        'B': '#85BB2F', 
        'C': '#FECB02', 
        'D': '#EE8100', 
        'E': '#E63E11'
    },
    text=nutri_counts.values
)
fig.update_traces(textposition='outside')
fig.update_layout(showlegend=False, height=400)
st.plotly_chart(fig, use_container_width=True)

# Distribution ELECTRE TRI
st.subheader("📊 Distribution ELECTRE TRI (Pessimiste, λ=0.6)")
electre_counts = df_results['Classe_Pessimiste_λ=0.6'].value_counts().sort_index()

fig2 = px.bar(
    x=electre_counts.index,
    y=electre_counts.values,
    labels={'x': 'Classe', 'y': 'Nombre de produits'},
    color=electre_counts.index,
    color_discrete_map={
        'A\'': '#038141', 
        'B\'': '#85BB2F', 
        'C\'': '#FECB02', 
        'D\'': '#EE8100', 
        'E\'': '#E63E11'
    },
    text=electre_counts.values
)
fig2.update_traces(textposition='outside')
fig2.update_layout(showlegend=False, height=400)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.success("✅ Si vous voyez cette page, le déploiement fonctionne!")
st.info("📝 Prochaine étape: Ajouter vos vrais fichiers de données.")
