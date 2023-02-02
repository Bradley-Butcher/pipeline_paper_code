import json
import pathlib
import pandas as pd

from cj_pipeline.config import SCORES
RESULTS_DIR = pathlib.Path(__file__).parents[0] / 'data'


def main():
  results = []
  for path_object in RESULTS_DIR.rglob('*.json'):
    with open(path_object, 'r') as f:
      experiment = json.load(f)
      experiment['crime_bins'] = ' '.join(experiment['crime_bins'])
    fname = path_object.name[:path_object.name.rfind('.')]
    ate = pd.read_csv(path_object.parents[0] / f'{fname}-ate.csv')
    experiment.update({s: ate[ate.score == s]['ate'].iloc[0] for s in SCORES})
    results.append(experiment)
  results = pd.DataFrame(results)

  results = results[results.columns[results.nunique() > 1]]  # .to_list() + ['seed']
  if 'seed' in results.columns:
    gcols = results.columns.difference(['seed'] + SCORES).to_list()
    results = pd.merge(
      results.groupby(gcols, dropna=False, as_index=False)[SCORES].mean(),
      results.groupby(gcols, dropna=False, as_index=False)[SCORES].std(),
      how='left', on=gcols, suffixes=('_mean', '_std'),
    )

  results.to_csv(RESULTS_DIR / 'results.csv', index=False)


if __name__ == '__main__':
  main()