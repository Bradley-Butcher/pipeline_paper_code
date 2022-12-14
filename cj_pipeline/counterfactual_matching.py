from typing import List
from cj_pipeline.neulaw.assignment_preprocessing import init_offence_counting
import pandas as pd
from cj_pipeline.neulaw.preprocess import init_rai_year_range
from cj_pipeline.config import logger

import dame_flame

offenses = [
    'aggravated assault',
    'drugs', 
    'robbery',
    'sex offense',
    'simple assault',
    'dui',
    'property'
]

scores = [
    'nca',
    'nvca',
    'ogrs3',
    'vprai',
    'fta'
]

demographics = [
    "def.race",
    "age_cat",
    "def.gender"
]


def _binarize_treatment(
    df: pd.DataFrame,
    treatment: str,
    binary_treatment_set: dict[str, int]
) -> pd.DataFrame:
    assert len(binary_treatment_set) == 2, "binary_treatment_set must have 2 keys"
    df = df.copy()
    if "Rest" in binary_treatment_set.keys():
        values = df[treatment].unique()
        other = set(values) - set(binary_treatment_set.keys())
        for o_i in other:
            binary_treatment_set[o_i] = binary_treatment_set["Rest"]
    df = df[df[treatment].isin(list(binary_treatment_set.keys()))]
    df[treatment] = df[treatment].map(binary_treatment_set)
    return df

def average_treatment_effect(
    start_year: int, 
    window: int, 
    treatment: str, 
    binary_treatment_set: dict[str, int],
    span:int=1, 
    set_years: list = None
    ) -> pd.DataFrame:
    offense_count_func, max_year = init_offence_counting(start_year=start_year, window=window)
    rai_func = init_rai_year_range(start_year=start_year, window=window)
    max_year = max_year - window
    years = range(start_year, max_year, span) if set_years is None else set_years
    results = []
    for year in years:
        logger.info(f"Getting ATE for {year}")
        offense_dfs = offense_count_func(start_year)
        rai_dfs = rai_func(start_year)
        df = pd.merge(offense_dfs, rai_dfs, on=['def.uid'])
        df = df[scores + offenses + demographics]
        df = _binarize_treatment(df, treatment, binary_treatment_set)
        for dem in set(demographics) - set([treatment]):
            df[dem] = pd.Categorical(df[dem]).codes
        all_score_df = df[scores]
        df = df.drop(columns=scores)
        df = df.rename(columns={
            treatment: 'treated'
        })
        for score in scores:
            logger.info(f"Calculating ATE for {year}, treatment: {treatment}. outcome: {score}")
            score_df = df.copy()
            score_df["outcome"] = all_score_df[score]
            before_len = len(score_df)
            score_df = score_df.dropna(subset=["outcome"])
            after_len = len(score_df)
            logger.info(f"Dropped {before_len - after_len} rows with missing values for {score}")
            model = dame_flame.matching.DAME()
            model.fit(score_df)
            _ = model.predict(score_df)
            ate = dame_flame.utils.post_processing.ATE(matching_object=model)
            logger.info(f"ATE for {year}-{year + window}, treatment: {treatment}. outcome: {score} is {ate}")
            results.append({
                'year': f"{year}-{year+window}",
                'score': score,
                'ate': ate
            })
    return pd.DataFrame(results)


def main():
    df = average_treatment_effect(
        start_year=2000,
        window=3, 
        treatment='def.race',
        binary_treatment_set={
            "Black": 1,
            "White": 0,
        },
        set_years=[2000])
    print(df)

if __name__ == "__main__":
    main()
