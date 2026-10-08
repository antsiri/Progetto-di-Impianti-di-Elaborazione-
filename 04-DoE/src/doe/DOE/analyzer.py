"""
 * author Antonio Sirignano
 * created on 07-10-2026-20h-31m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns

from statsmodels.formula.api import ols

class DOEAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        page_order = ['Low', 'Mid-Low', 'Mid', 'Mid-High', 'High']
        self.df['PageType'] = pd.Categorical(self.df['PageType'],
                                             categories=page_order,
                                             ordered=True,
                                             )
        self.df['Intensity'] = pd.Categorical(self.df['Intensity'])
        self.model = None
        self.anova_table = None

    def fit_linear_model(self):
        self.model = ols('ResponseTime ~ C(Intensity) * C(PageType)', data=self.df).fit()
        self.anova_table = sm.stats.anova_lm(self.model, typ=1)

        print('\n======================== REVIEW OLS MODEL ========================')
        print(f'R-squared:                  {self.model.rsquared:.6f}')
        print(f'Correct R-squared:          {self.model.rsquared_adj:.6f}')
        print(f'RMSE:                       {np.sqrt(self.model.mse_resid):.6f}')
        print(f'Mean Answear:               {self.df['ResponseTime'].mean():.2f}')

        print('\n======================== ANOVA TABLE ========================')
        print(self.anova_table)

    def compute_importance(self):
        ss_int = self.anova_table.loc['C(Intensity)', 'sum_sq']
        ss_page = self.anova_table.loc['C(PageType)', 'sum_sq']
        ss_inter = self.anova_table.loc['C(Intensity):C(PageType)', 'sum_sq']
        ss_err = self.anova_table.loc['Residual', 'sum_sq']
        sst = ss_int + ss_page + ss_inter + ss_err

        print('\n================ IMPORTANCE ANALYSIS (SS / SST) ================')
        print(f'PageType:          {ss_page / sst * 100:.2f}%')
        print(f'Intensity:         {ss_int / sst * 100:.2f}%')
        print(f'Interazione:       {ss_inter / sst * 100:.2f}%')
        print(f'Errore (Residui):  {ss_err / sst * 100:.2f}%')

    def check_normality_shapiro(self):
        res = self.model.resid
        w, p = stats.shapiro(res)
        print('\n================ NORMALITY TEST (SHAPIRO-WILK) ================')
        print(f'Statistic W: {w:.6f}')
        print(f'p-value:      {p:.6e}')
        if p < 0.05:
            print('Result: Null hypothesis rejected -> Residuals not normal.')


    def check_significance_kruskal(self):
        kw_int = stats.kruskal(
            *[
                group['ResponseTime'].values
                for _, group in self.df.groupby('Intensity')
            ]
        )
        kw_page = stats.kruskal(
            *[
                group['ResponseTime'].values
                for _, group in self.df.groupby('PageType')
            ]
        )

        print(
            '\n================ KRUSKAL-WALLIS TEST (SIGNIFICATIVITY) ================'
        )
        print(f'Intensity -> Statistic: {kw_int.statistic:.4f}, p-value:'
            f' {kw_int.pvalue:.4f}')
        print(f'PageType  -> Statistic: {kw_page.statistic:.4f}, p-value:'
            f' {kw_page.pvalue:.6e}')

    def plot_diagnostics(self):
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # 1. Osservati vs Previsti
        axes[0].scatter(self.model.fittedvalues, self.df['ResponseTime'], color='red')
        axes[0].plot(
            [self.df['ResponseTime'].min(), self.df['ResponseTime'].max()],
            [self.df['ResponseTime'].min(), self.df['ResponseTime'].max()],
            'k--',
        )
        axes[0].set_title('Observed vs Expected')
        axes[0].set_xlabel('ResponseTime Expected')
        axes[0].set_ylabel('ResponseTime Observed')

        # 2. QQ-Plot
        sm.qqplot(self.model.resid, line='s', ax=axes[1])
        axes[1].set_title('Residual QQ-Plot')

        # 3. Residui vs PageType
        sns.stripplot(
            x='PageType',
            y=self.model.resid,
            data=self.df,
            ax=axes[2],
            jitter=True,
            color='black',
        )
        axes[2].axhline(0, color='red', linestyle='--')
        axes[2].set_title('Residual for PageType')

        plt.tight_layout()
        plt.savefig('Graphics_analysis.png')
        plt.show()
        plt.close()