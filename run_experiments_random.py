from sklearn.neighbors import NearestNeighbors
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from skopt import BayesSearchCV
from skopt.space import Integer, Real, Categorical
from sklearn.metrics import make_scorer
from sklearn.model_selection import train_test_split
from sklearn.model_selection import RandomizedSearchCV
import streamlit as st
from trimap import TRIMAP
from umap.umap_ import UMAP
from sklearn.manifold import TSNE
from pacmap import PaCMAP


# Metryki
def compute_cf_nn(data_2d, labels, nn_max=100):
    data_2d = np.asarray(data_2d, dtype=np.float64)
    nbrs = NearestNeighbors(n_neighbors=nn_max, algorithm='auto').fit(data_2d)
    distances, indices = nbrs.kneighbors(data_2d)

    cf_nn_values = []
    for i in range(len(data_2d)):
        label = labels[i]
        neighbors_labels = labels[indices[i]]
        cf_nn = np.sum(neighbors_labels == label) / nn_max
        cf_nn_values.append(cf_nn)

    return np.array(cf_nn_values)


def compute_cf(cf_nn_values):
    return np.mean(cf_nn_values)


# Eksperymenty
techniques_dict = {
    't-SNE': TSNE(),
    'UMAP': UMAP(),
    # 'TRIMAP': TRIMAP(),
    # 'PaCMAP': PaCMAP()
}

techniques_params = {
    't-SNE': {
        "dimension_reduction__perplexity": np.arange(5, 100, dtype=np.int32),
        "dimension_reduction__early_exaggeration": np.arange(5, 10, dtype=np.int32),
        "dimension_reduction__learning_rate": np.arange(10, 102, dtype=np.int32),
        "dimension_reduction__n_iter": np.arange(250, 301, dtype=np.int32),
        "dimension_reduction__metric": ["euclidean", "manhattan", "cosine"]
    },
    'UMAP': {
        "dimension_reduction__n_neighbors": np.arange(10, 12, dtype=np.int32),
        "dimension_reduction__metric": ["euclidean", "manhattan", "chebyshev", "minkowski", "canberra"]
    }
    # 'TRIMAP': {
    #     "n_inliers": Integer(2, 100),
    #     "n_outliers": Integer(1, 50),
    #     "n_random": Integer(1, 50),
    #     "weight_adj": Integer(100, 1000),
    #     "n_iters": Integer(50, 1200)
    # },
    # 'PaCMAP': {
    #     "n_neighbors": Integer(10, 200),
    #     "mn_ratio": Real(0.1, 1.0),
    #     "fp_ratio": Real(1.0, 5.0)
    # }
}


# W teorii ten kod powinien przyjmować dataset, sam wyciągać sobie label, a następnie zależy, jaka lista do niego
# przeprowadzać eksperymenty w ilości 'n_iter' przy maksymalizacji metryki 'cf' (ale to tylko teoria)
def perform_experiments(dataset, labels, technique_names_list, n_iter, verbose=False):
    if verbose:
        st.write('Loading techniques...')
    x_train, x_test, y_train, y_test = train_test_split(dataset, labels, test_size=0.2, random_state=42)

    results = []
    for technique_name in technique_names_list:
        technique = techniques_dict.get(technique_name)
        if technique is None:
            if verbose:
                st.write(f'Unknown technique name: {technique_name}')
            continue

        if verbose:
            st.write(f'Running experiments for {technique_name}, parameters: {techniques_params[technique_name]}')
        pipe = Pipeline([('scaler', StandardScaler()), ('dimension_reduction', technique)])

        try:
            def custom_scorer(pipe, x, y):
                if verbose:
                    st.write(f"Transforming data with {technique_name}")
                transformed_data = pipe.fit_transform(x)
                cf_nn_values = compute_cf_nn(transformed_data, y, nn_max=100)
                return compute_cf(cf_nn_values)

            searcher = RandomizedSearchCV(
                estimator=pipe,
                param_distributions=techniques_params[technique_name],
                n_iter=n_iter,
                scoring=make_scorer(custom_scorer, greater_is_better=True),
                verbose=int(verbose),
                random_state=42
            )

            searcher.fit(x_train, y_train)
            if verbose:
                st.write(f'Best score for {technique_name}: {searcher.best_score_}')
                st.write(f'Best params for {technique_name}: {searcher.best_params_}')

            results.append({
                'Model': technique_name,
                'Score': searcher.best_score_,
                **searcher.best_params_,
                'estimator': searcher.best_estimator_
            })
        except Exception as e:
            if verbose:
                st.write(f"Error during processing {technique_name}: {str(e)}")

    return results