from __future__ import annotations

import operator
from dataclasses import dataclass, fields
from statistics import mean
from typing import Generic, List, Optional, TypeVar

import pandas as pd

# Metrics take on float or integer values
NumericType = TypeVar('NumericType', float, int)


@dataclass
class MetricValue(Generic[NumericType]):
    '''A rich object that is the output of any langcheck.metrics function.'''
    metric_name: str
    metric_values: List[NumericType]
    prompts: Optional[List[str]]
    generated_outputs: List[str]
    reference_outputs: Optional[List[str]]
    sources: Optional[List[str]]
    language: Optional[str]

    def to_df(self) -> pd.DataFrame:
        '''Returns a DataFrame of metric values for each data point.'''
        dataframe_cols = {
            'prompt': self.prompts,
            'source': self.sources,
            'generated_output': self.generated_outputs,
            'reference_output': self.reference_outputs,
            'metric_value': self.metric_values,
        }

        return pd.DataFrame(dataframe_cols)

    def __str__(self) -> str:
        '''Returns a string representation of an
        :class:`~langcheck.metrics.metric_value.MetricValue` object.
        '''
        return (f'Metric: {self.metric_name}\n'
                f'{self.to_df()}')

    def __repr__(self) -> str:
        '''Returns a string representation of an
        :class:`~langcheck.metrics.metric_value.MetricValue` object.
        '''
        return str(self)

    def _repr_html_(self) -> str:
        '''Returns an HTML representation of an
        :class:`~langcheck.metrics.metric_value.MetricValue`, which is
        automatically called by Jupyter notebooks.
        '''
        return (f'Metric: {self.metric_name}<br>'
                f'{self.to_df()._repr_html_()}'  # type: ignore
               )

    def __lt__(self, threshold: float | int) -> MetricValueWithThreshold:
        '''Allows the user to write a `metric_value < 0.5` expression.'''
        all_fields = {f.name: getattr(self, f.name) for f in fields(self)}
        return MetricValueWithThreshold(**all_fields,
                                        threshold=threshold,
                                        threshold_op='<')

    def __le__(self, threshold: float | int) -> MetricValueWithThreshold:
        '''Allows the user to write a `metric_value <= 0.5` expression.'''
        all_fields = {f.name: getattr(self, f.name) for f in fields(self)}
        return MetricValueWithThreshold(**all_fields,
                                        threshold=threshold,
                                        threshold_op='<=')

    def __gt__(self, threshold: float | int) -> MetricValueWithThreshold:
        '''Allows the user to write a `metric_value > 0.5` expression.'''
        all_fields = {f.name: getattr(self, f.name) for f in fields(self)}
        return MetricValueWithThreshold(**all_fields,
                                        threshold=threshold,
                                        threshold_op='>')

    def __ge__(self, threshold: float | int) -> MetricValueWithThreshold:
        '''Allows the user to write a `metric_value >= 0.5` expression.'''
        all_fields = {f.name: getattr(self, f.name) for f in fields(self)}
        return MetricValueWithThreshold(**all_fields,
                                        threshold=threshold,
                                        threshold_op='>=')

    def __eq__(self, threshold: float | int) -> MetricValueWithThreshold:
        '''Allows the user to write a `metric_value == 0.5` expression.'''
        all_fields = {f.name: getattr(self, f.name) for f in fields(self)}
        return MetricValueWithThreshold(**all_fields,
                                        threshold=threshold,
                                        threshold_op='==')

    def __ne__(self, threshold: float | int) -> MetricValueWithThreshold:
        '''Allows the user to write a `metric_value != 0.5` expression.'''
        all_fields = {f.name: getattr(self, f.name) for f in fields(self)}
        return MetricValueWithThreshold(**all_fields,
                                        threshold=threshold,
                                        threshold_op='!=')

    def all(self) -> bool:
        '''Equivalent to all(metric_value.metric_values). This is mostly useful
        for binary metric functions.
        '''
        return all(self.metric_values)

    def any(self) -> bool:
        '''Equivalent to any(metric_value.metric_values). This is mostly useful
        for binary metric functions.
        '''
        return any(self.metric_values)

    def __bool__(self):
        raise ValueError(
            'A MetricValue cannot be used as a boolean. '
            'Try an expression like `metric_value > 0.5`, '
            '`metric_value.all()`, or `metric_value.any()` instead.')

    def scatter(self, jupyter_mode: str = 'inline'):
        '''Shows an interactive scatter plot of all data points in MetricValue.
        Intended to be used in a Jupyter notebook.

        This is a convenience function that calls
        :func:`langcheck.plot.scatter()`.
        '''
        from langcheck.plot import scatter
        return scatter(self, jupyter_mode=jupyter_mode)

    def histogram(self, jupyter_mode: str = 'inline'):
        '''Shows an interactive histogram of all data points in MetricValue.
        Intended to be used in a Jupyter notebook.

        This is a convenience function that calls
        :func:`langcheck.plot.histogram()`.
        '''
        from langcheck.plot import histogram
        return histogram(self, jupyter_mode=jupyter_mode)


@dataclass
class MetricValueWithThreshold(MetricValue):
    '''A rich object that is the output of comparing an
    :class:`~langcheck.metrics.metric_value.MetricValue` object,
    e.g. `metric_value >= 0.5`.
    '''
    threshold: float | int
    threshold_op: str  # One of '<', '<=', '>', '>=', '==', '!='

    def __post_init__(self):
        '''Computes self.pass_rate and self.threshold_results based on the
        constructor arguments.
        '''
        operators = {
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
            '==': operator.eq,
            '!=': operator.ne
        }

        if self.threshold_op not in operators:
            raise ValueError(f'Invalid threshold operator: {self.threshold_op}')

        self._threshold_results = [
            operators[self.threshold_op](x, self.threshold)
            for x in self.metric_values
        ]

        self._pass_rate = mean(self._threshold_results)

    @property
    def pass_rate(self) -> float:
        '''Returns the proportion of data points that pass the threshold.'''
        return self._pass_rate

    @property
    def threshold_results(self) -> List[bool]:
        '''Returns a list of booleans indicating whether each data point passes
        the threshold.
        '''
        return self._threshold_results

    def to_df(self) -> pd.DataFrame:
        '''Returns a DataFrame of metric values for each data point.'''
        dataframe = super().to_df()

        dataframe['threshold_test'] = [
            f'{self.threshold_op} {self.threshold}' for _ in self.metric_values
        ]
        dataframe['threshold_result'] = self.threshold_results

        return dataframe

    def __str__(self) -> str:
        '''Returns a string representation of an
        :class:`~langcheck.metrics.metric_value.MetricValue`.
        '''
        return (f'Metric: {self.metric_name}\n'
                f'Pass Rate: {round(self.pass_rate*100, 2)}%\n'
                f'{self.to_df()}')

    def __repr__(self) -> str:
        '''Returns a string representation of an
        :class:`~langcheck.metrics.metric_value.MetricValue` object.
        '''
        return str(self)

    def _repr_html_(self) -> str:
        '''Returns an HTML representation of an
        :class:`~langcheck.metrics.metric_value.MetricValue`, which is
        automatically called by Jupyter notebooks.
        '''
        return (f'Metric: {self.metric_name}<br>'
                f'Pass Rate: {round(self.pass_rate*100, 2)}%<br>'
                f'{self.to_df()._repr_html_()}'  # type: ignore
               )

    def all(self) -> bool:
        '''Returns True if all data points pass the threshold.'''
        return all(self.threshold_results)

    def any(self) -> bool:
        '''Returns True if any data points pass the threshold.'''
        return any(self.threshold_results)

    def __bool__(self) -> bool:
        '''Allows the user to write an `assert metric_value > 0.5` or
        `if metric_value > 0.5:` expression. This is shorthand for
        `assert (metric_value > 0.5).all()`.
        '''
        return self.all()
