import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

from cj_pipeline.config import BASE_DIR
DATA_DIR = BASE_DIR / 'data' / 'processed'


def _mean_and_var(df, n_years):
  def _sem(group):
    weights = group['count'] / group['count'].sum()
    errors = weights * (group['arrest_rate'] - group['arrest_rate_smooth'])**2
    return (errors.mean() / n_years)**0.5

  groups = ['offender_race', 'offender_age', 'offender_sex', 'crime_recode']
  means = df.groupby(groups)['arrest_rate_smooth'].mean().to_frame('mean').reset_index()
  sems = df.groupby(groups).apply(_sem).to_frame('sem').reset_index()
  df = pd.merge(means, sems, how='inner', on=groups)

  return df


def _load_ncvs():
  # ncvs = pd.read_csv(DATA_DIR / 'ncvs_arrest_rates.csv')
  ncvs = pd.read_csv(DATA_DIR / 'ncvs.csv')
  ncvs = ncvs[ncvs['offender_age'] != '< 18']
  ncvs = _mean_and_var(ncvs, n_years=ncvs['ncvs_year'].nunique())
  ncvs['crime_recode'] = ncvs['crime_recode'].str.capitalize()
  return ncvs


def _load_nsduh():
  nsduh = pd.read_csv(DATA_DIR / 'nsduh.csv')
  nsduh = nsduh[[c for c in nsduh.columns if not '_lam_' in c]]
  nsduh = nsduh[nsduh['offender_age'] != '< 18']

  def _melt(id_vars, suffix, value_name):
    df = nsduh.melt(
      id_vars=id_vars,
      value_vars=[c for c in nsduh if c not in id_vars and c.endswith(suffix)],
      var_name='crime_recode', value_name=value_name,
    )
    df['crime_recode'].replace(
      {v: v[:v.rfind('_')] for v in df['crime_recode'].unique()}, inplace=True
    )
    return df

  id_vars = ['offender_race', 'offender_age', 'offender_sex', 'YEAR', 'count']
  nsduh = pd.merge(
    _melt(id_vars, suffix='_ar', value_name='arrest_rate'),
    _melt(id_vars, suffix='_sar', value_name='arrest_rate_smooth'),
    how='inner', on=id_vars + ['crime_recode']
  )
  nsduh = nsduh[nsduh['crime_recode'] != 'drugs_any']

  nsduh = _mean_and_var(nsduh, n_years=nsduh['YEAR'].nunique())
  nsduh['crime_recode'].replace(
    {
      'dui': 'DUI',
      'drugs_use': 'Drugs use',
      'drugs_sell': 'Drugs sell',
    },
    inplace=True,
  )

  return nsduh


def plot_ncvs():
  ncvs = _load_ncvs()
  grid = plot_arrests(ncvs, age_label_order=['18-29', '> 29'])
  grid.figure.savefig(BASE_DIR / 'data' / 'scratch' / 'ncvs_arrests.pdf')


def plot_nsduh():
  nsduh = _load_nsduh()
  grid = plot_arrests(nsduh, age_label_order=['18-34', '> 34'])
  grid.figure.savefig(BASE_DIR / 'data' / 'scratch' / 'nsduh_arrests.pdf')


def plot_arrests(df, age_label_order, gap=0.2, width=0.3):
  sns.set_style('whitegrid')
  sns.set(font_scale=1.25)

  df['ci'] = 1.96 * df['sem']

  grid = sns.FacetGrid(
    df,
    row='offender_race',
    col='crime_recode',
    hue='offender_age',
    margin_titles=True,
    despine=True,
  )

  def errplot(x, y, yerr, **kwargs):
    ax = plt.gca()
    data = kwargs.pop('data')
    positions = {
      'Female': {
        '18-29': 0, '18-34': 0,
        '> 29': width, '> 34': width
      },
      'Male': {
        '18-29': 2 * width + gap, '18-34': 2 * width + gap,
        '> 29': 3 * width + gap, '> 34': 3 * width + gap,
      }
    }
    for _, row in data.iterrows():
      xpos = positions[row[x]][row['offender_age']]
      ax.bar(xpos, row[y], yerr=row[yerr], width=width, **kwargs)
    ax.set_xticks([width / 2, 2.5 * width + gap])
    ax.set_xticklabels(['Female', 'Male'])

  grid.map_dataframe(
    errplot, x='offender_sex', y='mean', yerr='ci',
  )

  grid.fig.supxlabel('Gender')
  grid.set_axis_labels(x_var='', y_var='Estimated arrest rate')
  grid.set_titles(row_template='{row_name}', col_template='{col_name}')
  grid.add_legend(title='Age', label_order=age_label_order)

  # grid.tight_layout()
  return grid


if __name__ == '__main__':
  plot_ncvs()
  plot_nsduh()