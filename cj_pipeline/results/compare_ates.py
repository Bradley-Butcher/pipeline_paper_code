import json
import pathlib
import pandas as pd
from cj_pipeline.config import SCORES, BASE_DIR

from typing import List

DEFAULT_DIR = BASE_DIR / pathlib.Path('cj_pipeline/results/data')


def aggregate(
    data_path: str | pathlib.Path = DEFAULT_DIR,
    drop_constant_cols: bool = True,
    ignore_cols: List = None,
) -> pd.DataFrame:
  data_path = pathlib.Path(data_path)
  if not data_path.is_absolute():
    data_path = BASE_DIR / data_path

  results = []
  for path_object in data_path.rglob('*.json'):
    with open(path_object, 'r') as f:
      experiment = json.load(f)
      experiment['crime_bins'] = ' '.join(experiment['crime_bins'])
    fname = path_object.name[:path_object.name.rfind('.')]
    ate = pd.read_csv(path_object.parents[0] / f'{fname}-ate.csv')
    experiment.update({s: ate[ate.score == s]['ate'].iloc[0] for s in SCORES})
    results.append(experiment)
  results = pd.DataFrame(results)

  if ignore_cols is not None:
    if 'seed' in ignore_cols:
      raise ValueError('Never drop the seed column')
    results = results.drop(columns=ignore_cols)

  const_cols = results.columns[results.nunique() == 1]
  varying_cols = results.columns.difference(const_cols)
  if drop_constant_cols:
    results = results[varying_cols.to_list() + ['seed']]
  # if 'seed' in varying_cols:  # always compute
  gcols = results.columns.difference(SCORES + ['seed']).to_list()
  results = pd.merge(
    results.groupby(gcols, dropna=False, as_index=False)[SCORES].mean(),
    results.groupby(gcols, dropna=False, as_index=False)[SCORES].sem(),
    how='left', on=gcols, suffixes=('_mean', '_sem'),
  )
  return results


if __name__ == '__main__':
  data_path = DEFAULT_DIR
  results = aggregate(data_path=data_path, drop_constant_cols=True)
  results.to_csv(data_path / 'results_ate.csv', index=False)