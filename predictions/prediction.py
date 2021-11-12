"""Contains the generic Prediction class. This class should represent any kind
of prediction interpreted as fitted array X hoping to be close to real array Y.

The Prediction class allows to compute some metrics concerning the accuracy
without needing to know how the prediction was computed."""

from typing import Any, Union

import numpy as np
import pandas as pd


class Prediction:
    def __init__(
        self,
        fitted_values: Union[np.ndarray, pd.Series, list],
        real_values: Union[np.ndarray, pd.Series, list],
    ):
        """Class to represent a generic prediction.

        Arguments
        -------
        fitted_values: Union[np.ndarray, pd.Series, list]
            The array-like object of length N containing the fitted values. If list,
            it will be turned into np.array.
        real_values: Union[np.ndarray, pd.Series, list]
            The array-like object containing the real values. It must have the same
            length of fitted_values. If list, it will be turned into np.array.
        """
        self.fitted_values = fitted_values
        self.real_values = real_values

        # Processing appening at __init__
        self._check_lengths_match()
        self._lists_to_nparray()

    def _lists_to_nparray(self) -> None:
        """Turn lists into numpy arrays."""
        if isinstance(self.fitted_values, list):
            self.fitted_values = np.array(self.fitted_values)
        if isinstance(self.real_values, list):
            self.real_values = np.array(self.real_values)

    def _check_lengths_match(self) -> None:
        """Check that fitted values and real values have the same length."""
        if self.real_values is None:
            return

        len_fit, len_real = len(self.fitted_values), len(self.real_values)
        if len_fit != len_real:
            raise ValueError(
                "Fitted values and real values must have the same length.\n"
                + f"Fitted values has length: {len_fit}.\n"
                + f"Real values has length: {len_real}."
            )

    def __str__(self):
        return self.fitted_values.__str__()

    def __len__(self):
        return len(self.fitted_values)

    @property
    def is_numeric(self) -> bool:
        """Return True if fitted values are numeric, False otherwise."""
        return pd.api.types.is_numeric_dtype(self.fitted_values)

    @property
    def percentage_correctly_classified(self) -> float:
        """Return a float representing the percent of items which are equal
        between the real and the fitted values."""
        return np.mean(self.real_values == self.fitted_values)

    # DEFYINING ALIAS
    pcc = percentage_correctly_classified

    def matches(self) -> Union[np.ndarray, pd.Series]:
        """Return a boolean array of length N with True where fitted value is
        equal to real value."""
        return self.real_values == self.fitted_values

    def as_dataframe(self) -> pd.DataFrame:
        """Return prediction as a dataframe containing various information over
        the prediction quality."""
        data = {
            "Fitted Values": self.fitted_values,
            "Real Values": self.real_values,
            "Prediction Matches": self.matches(),
        }
        return pd.DataFrame(data)


class NumericPrediction(Prediction):
    @property
    def r_squared(self) -> float:
        """Returns the r squared calculated as the square of the correlation
        coefficient."""
        return np.corrcoef(self.real_values, self.fitted_values)[0, 1] ** 2

    def residuals(
        self, squared: bool = False, absolute_value: bool = False
    ) -> Union[np.ndarray, pd.Series]:
        """Return an array with the difference between the real values and the
        fitted values."""
        residuals = self.real_values - self.fitted_values
        if squared:
            return residuals ** 2
        if absolute_value:
            return abs(residuals)
        return residuals

    def matches(self, tolerance: float = 0.0) -> Union[np.ndarray, pd.Series]:
        """Return a boolean array of length N with True where fitted value is
        equal to real value."""
        return abs(self.real_values - self.fitted_values) <= tolerance

    def as_dataframe(self) -> pd.DataFrame:
        """Return prediction as a dataframe containing various information over
        the prediction quality."""
        residuals = self.residuals()
        data = {
            "Fitted Values": self.fitted_values,
            "Real Values": self.real_values,
            "Prediction Matches": self.matches(),
            "Absolute difference": residuals,
            "Relative difference": residuals / self.real_values,
        }
        return pd.DataFrame(data)


class BinaryPrediction(Prediction):
    def __init__(
        self,
        fitted_values: Union[np.ndarray, pd.Series, list],
        real_values: Union[np.ndarray, pd.Series, list],
        value_positive: Any = 1,
    ):
        """Class to represent a generic prediction.

        Arguments
        -------
        fitted_values: Union[np.ndarray, pd.Series, list]
            The array-like object of length N containing the fitted values. If list,
            it will be turned into np.array.

        real_values: Union[np.ndarray, pd.Series, list]
            The array-like object containing the real values. It must have the same
            length of fitted_values. If list, it will be turned into np.array.

        value_positive: Any
            The value in the data that corresponds to 1 in the boolean logic.
            It is generally associated with the idea of "positive" or being in
            the "treatment" group. By default is 1.
        """
        super().__init__(fitted_values, real_values)
        self.value_positive = value_positive

    @property
    def value_negative(self):
        other_only = self.real_values[self.real_values != self.value_positive]
        if isinstance(self.real_values, np.ndarray):
            return other_only[0].copy()
        return other_only.reset_index(drop=True)[0]

    @property
    def false_positive_rate(self):
        pred_pos = self.fitted_values == self.value_positive
        real_neg = self.real_values != self.value_positive

        false_positive = pred_pos & real_neg
        return false_positive.sum() / real_neg.sum()

    @property
    def false_negative_rate(self):
        pred_neg = self.fitted_values != self.value_positive
        real_pos = self.real_values == self.value_positive

        false_negative = pred_neg & real_pos
        return false_negative.sum() / real_pos.sum()

    @property
    def sensitivity(self):
        pred_pos = self.fitted_values == self.value_positive
        real_pos = self.real_values == self.value_positive

        caught_positive = pred_pos & real_pos
        return caught_positive.sum() / (pred_pos | real_pos).sum()

    @property
    def specificity(self):
        pred_neg = self.fitted_values != self.value_positive
        real_neg = self.real_values != self.value_positive

        caught_negative = pred_neg & real_neg
        return caught_negative.sum() / (pred_neg | real_neg).sum()

    def confusion_matrix(
        self, as_dataframe: bool = False
    ) -> Union[np.ndarray, pd.DataFrame]:
        pred_pos = self.fitted_values == self.value_positive
        pred_neg = self.fitted_values != self.value_positive
        real_pos = self.real_values == self.value_positive
        real_neg = self.real_values != self.value_positive

        conf = np.array(
            [
                [(pred_neg & real_neg).sum(), (pred_pos & real_neg).sum()],
                [(pred_neg & real_pos).sum(), (pred_pos & real_pos).sum()],
            ]
        )
        if not as_dataframe:
            return conf
