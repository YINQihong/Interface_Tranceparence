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

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<h1 class="main-header">🥖 Analyse ELECTRE TRI - Classification des Produits Alimentaires</h1>', unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; margin-bottom: 2rem;'>
    <p style='font-size: 1.2rem;'>
    Application interactive présentant les résultats de la méthode <strong>ELECTRE TRI</strong> 
    pour la classification des produits alimentaires.
    </p>
</div>
""", unsafe_allow_html=True)

# 数据加载
@st.cache_data
def load_data():
    try:
        df_results = pd.read_excel("ELECTRE_TRI_Resultats.xlsx")
        df_products = pd.read_csv("Products.csv", encoding='utf-8')
        return df_results, df_products, True
    except:
        return create_sample_data(), None, False

def create_sample_data():
    np.random.seed(42)
    n = 139
    
    products = ['Pain complet', 'Baguette', 'Pain de mie', 'Brioche', 'Croissant', 
                'Pain aux céréales', 'Pain blanc', 'Pain azyme', 'Ciabatta', 'Pain pita']
    
    names = [f"{np.random.choice(products)} {np.random.choice(['bio', 'classique', 'artisanal', ''])} {i+1}".strip() 
             for i in range(n)]
    
    nutri = []
    pess06 = []
    opt06 = []
    pess07 = []
    opt07 = []
    
    for i in range(n):
        ng = np.random.choice(['A', 'B', 'C', 'D', 'E'], p=[0.2, 0.25, 0.25, 0.2, 0.1])
        nutri.append(ng)
        
        idx = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}[ng]
        classes = ['A\'', 'B\'', 'C\'', 'D\'', 'E\'']
        
        pess06.append(classes[min(idx + np.random.choice([0,1,2], p=[0.5,0.3,0.2]), 4)])
        opt06.append(classes[max(0, min(idx + np.random.choice([-1,0,1], p=[0.2,0.5,0.3]), 4))])
        pess07.append(classes[min(idx + np.random.choice([0,1,2,3], p=[0.3,0.35,0.25,0.1]), 4)])
        opt07.append(classes[max(0, min(idx + np.random.choice([-1,0,1], p=[0.25,0.45,0.3]), 4))])
    
    return pd.DataFrame({
        'product_id': range(1, n+1),
        'product_name': names,
        'nutriscore_grade': nutri,
        'Classe_Pessimiste_λ=0.6': pess06,
        'Classe_Optimiste_λ=0.6': opt06,
        'Classe_Pessimiste_λ=0.7': pess07,
        'Classe_Optimiste_λ=0.7': opt07,
    })

df_results, df_products, is_real = load_data()

if not is_real:
    st.warning("⚠️ Données d'exemple utilisées. Ajoutez vos fichiers pour voir vos vraies données.")
else:
    st.success("✅ Données réelles chargées!")

# Sidebar
st.sidebar.title("📊 Navigation")
page = st.sidebar.radio(
    "",
    ["🏠 Vue d'ensemble", 
     "🎯 Résultats ELECTRE TRI", 
     "🔄 Comparaison Nutri-Score", 
     "🔍 Analyse détaillée",
     "📈 Visualisations avancées"]
)

st.sidebar.markdown("---")
st.sidebar.info("""
**ELECTRE TRI**

Méthode multicritère de classification.

**8 Critères:**
- Énergie, Graisses, Sucres
- Sodium, Protéines, Fibres
- Fruits/Légumes, Additifs
""")

# Couleurs
COLORS = {
    'A': '#038141', 'B': '#85BB2F', 'C': '#FECB02', 'D': '#EE8100', 'E': '#E63E11',
    'A\'': '#038141', 'B\'': '#85BB2F', 'C\'': '#FECB02', 'D\'': '#EE8100', 'E\'': '#E63E11'
}

# PAGE 1: Vue d'ensemble
if page == "🏠 Vue d'ensemble":
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Produits", len(df_results))
    with col2:
        st.metric("📊 Critères", 8)
    with col3:
        st.metric("🎚️ Valeurs λ", 2)
    with col4:
        mapping = {'A':'A\'','B':'B\'','C':'C\'','D':'D\'','E':'E\''}
        match = sum(df_results.apply(lambda r: r['nutriscore_grade'] in mapping and 
                    r['Classe_Pessimiste_λ=0.6'] == mapping[r['nutriscore_grade']], axis=1))
        st.metric("✅ Concordance", f"{(match/len(df_results)*100):.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Nutri-Score")
        nutri = df_results['nutriscore_grade'].value_counts().sort_index()
        fig = go.Figure(go.Bar(x=nutri.index, y=nutri.values,
                               marker_color=[COLORS[x] for x in nutri.index],
                               text=nutri.values, textposition='outside'))
        fig.update_layout(showlegend=False, height=350, xaxis_title="Grade", yaxis_title="Nombre")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 ELECTRE TRI (λ=0.6)")
        electre = df_results['Classe_Pessimiste_λ=0.6'].value_counts().sort_index()
        fig = go.Figure(go.Bar(x=electre.index, y=electre.values,
                               marker_color=[COLORS[x] for x in electre.index],
                               text=electre.values, textposition='outside'))
        fig.update_layout(showlegend=False, height=350, xaxis_title="Classe", yaxis_title="Nombre")
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📋 Aperçu des données")
    
    col1, col2 = st.columns([2,1])
    with col1:
        search = st.text_input("🔍 Rechercher:", "")
    with col2:
        nutri_f = st.multiselect("Filtrer Nutri-Score:", 
                                 sorted(df_results['nutriscore_grade'].unique()), [])
    
    disp = df_results.copy()
    if search:
        disp = disp[disp['product_name'].str.contains(search, case=False, na=False)]
    if nutri_f:
        disp = disp[disp['nutriscore_grade'].isin(nutri_f)]
    
    st.dataframe(disp[['product_name', 'nutriscore_grade', 'Classe_Pessimiste_λ=0.6', 
                       'Classe_Optimiste_λ=0.6']], use_container_width=True, hide_index=True)

# PAGE 2: Résultats ELECTRE
elif page == "🎯 Résultats ELECTRE TRI":
    st.header("🎯 Résultats ELECTRE TRI")
    
    col1, col2 = st.columns(2)
    with col1:
        lam = st.selectbox("🎚️ Seuil λ:", ["0.6", "0.7"])
    with col2:
        proc = st.selectbox("📐 Procédure:", ["Pessimiste", "Optimiste"])
    
    col_name = f"Classe_{proc}_λ={lam}"
    
    st.markdown("---")
    st.subheader(f"📊 Distribution - {proc} (λ={lam})")
    
    counts = df_results[col_name].value_counts().sort_index()
    
    col1, col2 = st.columns([2,1])
    
    with col1:
        fig = go.Figure(go.Bar(x=counts.index, y=counts.values,
                               marker_color=[COLORS[x] for x in counts.index],
                               text=counts.values, textposition='outside'))
        fig.update_layout(showlegend=False, height=400, 
                         xaxis_title="Classe", yaxis_title="Nombre")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Stats")
        for c in sorted(counts.index):
            st.metric(f"Classe {c}", f"{counts[c]}", f"{counts[c]/len(df_results)*100:.1f}%")
    
    st.markdown("---")
    st.subheader("📋 Liste des produits")
    
    classes = st.multiselect("Filtrer:", sorted(df_results[col_name].unique()),
                            sorted(df_results[col_name].unique()))
    
    filtered = df_results[df_results[col_name].isin(classes)]
    st.dataframe(filtered[['product_name', 'nutriscore_grade', col_name]],
                use_container_width=True, hide_index=True, height=400)
    
    csv = filtered.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger CSV", csv, 
                      f"electre_{proc}_lambda{lam}.csv", "text/csv")

# PAGE 3: Comparaison
elif page == "🔄 Comparaison Nutri-Score":
    st.header("🔄 Comparaison vs Nutri-Score")
    
    col1, col2 = st.columns(2)
    with col1:
        lam = st.selectbox("λ:", ["0.6", "0.7"])
    with col2:
        proc = st.selectbox("Procédure:", ["Pessimiste", "Optimiste"])
    
    col_name = f"Classe_{proc}_λ={lam}"
    
    st.markdown("---")
    st.subheader("📊 Matrice de confusion")
    
    conf = pd.crosstab(df_results['nutriscore_grade'], df_results[col_name], 
                       margins=True, margins_name="Total")
    
    fig = go.Figure(go.Heatmap(
        z=conf.iloc[:-1, :-1].values,
        x=conf.columns[:-1], y=conf.index[:-1],
        colorscale='Blues', text=conf.iloc[:-1, :-1].values, texttemplate='%{text}'))
    fig.update_layout(xaxis_title="ELECTRE TRI", yaxis_title="Nutri-Score", height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📋 Matrice complète"):
        st.dataframe(conf)
    
    st.markdown("---")
    st.subheader("✅ Concordance")
    
    mapping = {'A':'A\'','B':'B\'','C':'C\'','D':'D\'','E':'E\''}
    df_results['match'] = df_results.apply(
        lambda r: r['nutriscore_grade'] in mapping and r[col_name] == mapping[r['nutriscore_grade']], 
        axis=1)
    
    conc_rate = (df_results['match'].sum() / len(df_results)) * 100
    matches = df_results['match'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Taux global", f"{conc_rate:.1f}%")
    with col2:
        st.metric("Concordants", f"{matches}/{len(df_results)}")
    with col3:
        st.metric("Discordants", len(df_results) - matches)
    
    st.markdown("### 📊 Par grade")
    
    conc_data = []
    for g in ['A','B','C','D','E']:
        gdf = df_results[df_results['nutriscore_grade'] == g]
        if len(gdf) > 0:
            gm = gdf['match'].sum()
            conc_data.append({'Grade': g, 'Concordants': gm, 'Total': len(gdf), 
                             'Pct': gm/len(gdf)*100})
    
    cdf = pd.DataFrame(conc_data)
    
    fig = go.Figure(go.Bar(x=cdf['Grade'], y=cdf['Pct'],
                           marker_color=[COLORS[x] for x in cdf['Grade']],
                           text=cdf['Pct'].round(1), texttemplate='%{text}%'))
    fig.update_layout(showlegend=False, yaxis_title="Taux (%)", height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(cdf, use_container_width=True, hide_index=True)

# PAGE 4: Analyse détaillée
elif page == "🔍 Analyse détaillée":
    st.header("🔍 Analyse détaillée")
    
    st.subheader("🔎 Recherche")
    search = st.text_input("Nom du produit:")
    
    if search:
        found = df_results[df_results['product_name'].str.contains(search, case=False, na=False)]
        if len(found) > 0:
            st.success(f"✅ {len(found)} produit(s) trouvé(s)")
            for _, row in found.iterrows():
                with st.expander(f"📦 {row['product_name']}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**Nutri-Score**")
                        st.markdown(f"<h2 style='text-align:center; color:{COLORS[row['nutriscore_grade']]}'>{row['nutriscore_grade']}</h2>", 
                                   unsafe_allow_html=True)
                    with col2:
                        st.markdown("**λ=0.6**")
                        st.write(f"Pess: {row['Classe_Pessimiste_λ=0.6']}")
                        st.write(f"Opt: {row['Classe_Optimiste_λ=0.6']}")
                    with col3:
                        st.markdown("**λ=0.7**")
                        st.write(f"Pess: {row['Classe_Pessimiste_λ=0.7']}")
                        st.write(f"Opt: {row['Classe_Optimiste_λ=0.7']}")
        else:
            st.warning("Aucun produit trouvé")
    
    st.markdown("---")
    st.subheader("⚖️ Pessimiste vs Optimiste")
    
    lam = st.radio("λ:", ["0.6", "0.7"], horizontal=True)
    cp = f"Classe_Pessimiste_λ={lam}"
    co = f"Classe_Optimiste_λ={lam}"
    
    df_results['diff'] = df_results[cp] != df_results[co]
    ndiff = df_results['diff'].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Identiques", len(df_results)-ndiff, f"{((len(df_results)-ndiff)/len(df_results)*100):.1f}%")
    with col2:
        st.metric("Différentes", ndiff, f"{(ndiff/len(df_results)*100):.1f}%")
    
    if ndiff > 0:
        ddf = df_results[df_results['diff']]
        st.dataframe(ddf[['product_name', 'nutriscore_grade', cp, co]],
                    use_container_width=True, hide_index=True)

# PAGE 5: Visualisations avancées
elif page == "📈 Visualisations avancées":
    st.header("📈 Visualisations avancées")
    
    st.subheader("🌊 Diagramme de Sankey")
    
    lam = st.selectbox("λ:", ["0.6", "0.7"])
    col = f"Classe_Pessimiste_λ={lam}"
    
    flow = df_results.groupby(['nutriscore_grade', col]).size().reset_index(name='count')
    
    nutri_g = sorted(df_results['nutriscore_grade'].unique())
    elec_g = sorted(df_results[col].unique())
    labels = nutri_g + elec_g
    node_colors = [COLORS[g] for g in nutri_g] + [COLORS[c] for c in elec_g]
    
    src, tgt, val = [], [], []
    for _, row in flow.iterrows():
        src.append(labels.index(row['nutriscore_grade']))
        tgt.append(labels.index(row[col]))
        val.append(row['count'])
    
    fig = go.Figure(go.Sankey(
        node=dict(pad=15, thickness=20, label=labels, color=node_colors),
        link=dict(source=src, target=tgt, value=val)))
    
    fig.update_layout(title=f"Nutri-Score → ELECTRE (λ={lam})", height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📊 Taux de concordance")
    
    trends = []
    for p in ['Pessimiste', 'Optimiste']:
        for l in ['0.6', '0.7']:
            c = f"Classe_{p}_λ={l}"
            mapping = {'A':'A\'','B':'B\'','C':'C\'','D':'D\'','E':'E\''}
            m = df_results.apply(lambda r: r['nutriscore_grade'] in mapping and 
                                r[c] == mapping[r['nutriscore_grade']], axis=1).sum()
            trends.append({'Proc': p, 'Lambda': l, 'Conc': m/len(df_results)*100})
    
    tdf = pd.DataFrame(trends)
    
    fig = go.Figure()
    for p in ['Pessimiste', 'Optimiste']:
        pdata = tdf[tdf['Proc'] == p]
        fig.add_trace(go.Bar(name=p, x=pdata['Lambda'], y=pdata['Conc'],
                            text=pdata['Conc'].round(1), texttemplate='%{text}%'))
    
    fig.update_layout(barmode='group', yaxis_title="Concordance (%)",
                     xaxis_title="λ", height=400)
    st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    <p><strong>ELECTRE TRI</strong> - Analyse multicritère des produits alimentaires</p>
    <p style='font-size: 0.9rem;'>Classification en 5 catégories | 8 critères nutritionnels</p>
</div>
""", unsafe_allow_html=True)
