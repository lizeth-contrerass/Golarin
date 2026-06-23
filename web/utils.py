# web/utils.py
import math
import pandas as pd
import numpy as np


def es_continuo(valor):
    try:
        float(valor)
        return True
    except (ValueError, TypeError):
        return False


# ==========================================
# FUNCIONES NAIVE BAYES
# ==========================================

def nb_prob_clases(df, col_clases, clases):
    no_entradas = len(df)
    return {str(clase): len(df[df[col_clases] == clase]) / no_entradas for clase in clases}


def nb_prob_cond_discreta(df, cols_discretas, col_clases, clases):
    prob_cond = {}
    for cat in cols_discretas:
        prob_cond[cat] = {}
        for clase in clases:
            df_clase = df[df[col_clases] == clase]
            total_clase = len(df_clase)
            conteos = df_clase[cat].value_counts()
            prob_cond[cat][str(clase)] = {str(k): v / total_clase for k, v in conteos.to_dict().items()}
    return prob_cond


def nb_parametros_continuos(df, cols_continuas, col_clases, clases):
    param_cont = {}
    for col in cols_continuas:
        param_cont[col] = {}
        for clase in clases:
            data = df[df[col_clases] == clase][col].astype(float)
            std_val = data.std(ddof=1)
            param_cont[col][str(clase)] = {
                'media': float(data.mean()) if not pd.isna(data.mean()) else 0.0,
                'desvE': float(std_val) if not pd.isna(std_val) else 0.0
            }
    return param_cont


def gaussiana(x, media, desvE):
    if desvE == 0:
        return 1.0 if x == media else 0.0
    exp_component = math.exp(-((x - media) ** 2) / (2 * (desvE ** 2)))
    return (1 / (desvE * math.sqrt(2 * math.pi))) * exp_component


def calcular_naive_bayes(entrada, cols_caracteristicas, clases, prob_clases, prob_cond, param_cont, cols_discretas,
                         cols_continuas):
    prob_p_clase = {}
    for clase in clases:
        clase_str = str(clase)
        p_previa = prob_clases[clase_str]
        for i, cat in enumerate(cols_caracteristicas):
            valor = entrada[i]
            if cat in cols_discretas:
                pr = prob_cond[cat].get(clase_str, {})
                prob = pr.get(str(valor), 0)
                p_previa *= prob
            elif cat in cols_continuas:
                try:
                    x = float(valor)
                    media = param_cont[cat][clase_str]['media']
                    desvE = param_cont[cat][clase_str]['desvE']
                    p_previa *= gaussiana(x, media, desvE)
                except:
                    p_previa *= 0
        prob_p_clase[clase_str] = p_previa
    return prob_p_clase


def verificar_naive_bayes(df, cols_caracteristicas, col_clases, clases, prob_clases, prob_cond, param_cont,
                          cols_discretas, cols_continuas):
    reales, predichas = [], []
    for _, fila in df.iterrows():
        entrada = []
        for cat in cols_caracteristicas:
            val = fila[cat]
            if cat in cols_discretas:
                val = str(val).capitalize()
            entrada.append(val)
        probs = calcular_naive_bayes(entrada, cols_caracteristicas, clases, prob_clases, prob_cond, param_cont,
                                     cols_discretas, cols_continuas)
        clase_pred = max(probs, key=probs.get)
        reales.append(str(fila[col_clases]))
        predichas.append(clase_pred)
    return calcular_metricas_macro(reales, predichas, [str(c) for c in clases])


# ==========================================
# MÉTRICAS COMUNES MÁCRO-AVERAGE
# ==========================================

def calcular_metricas_macro(reales, predichas, clases):
    prec_clases, rec_clases, esp_clases = [], [], []
    for c in clases:
        tp = sum(1 for r, p in zip(reales, predichas) if r == c and p == c)
        fp = sum(1 for r, p in zip(reales, predichas) if r != c and p == c)
        fn = sum(1 for r, p in zip(reales, predichas) if r == c and p != c)
        tn = sum(1 for r, p in zip(reales, predichas) if r != c and p != c)

        prec_clases.append(tp / (tp + fp) if (tp + fp) > 0 else 0.0)
        rec_clases.append(tp / (tp + fn) if (tp + fn) > 0 else 0.0)
        esp_clases.append(tn / (tn + fp) if (tn + fp) > 0 else 0.0)

    correctos = sum(1 for r, p in zip(reales, predichas) if r == p)
    total = len(reales)
    acc = correctos / total if total > 0 else 0.0

    return (
        acc,
        1.0 - acc,
        sum(prec_clases) / len(clases),
        sum(rec_clases) / len(clases),
        sum(esp_clases) / len(clases)
    )