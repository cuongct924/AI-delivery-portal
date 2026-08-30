"""Neural network architectures — a separate module (not
algorithm_registry.py) because neural nets don't share sklearn's uniform
fit/predict interface; each architecture's hyperparameter shape is
fundamentally different.
"""

import torch
from torch import nn


class MLPModel(nn.Module):
    """Feedforward network for flat (non-sequential) feature vectors."""

    def __init__(
        self, input_size: int, hidden_layers: list[int], dropout: float, output_size: int
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        previous_size = input_size
        for hidden_size in hidden_layers:
            layers.append(nn.Linear(previous_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            previous_size = hidden_size
        layers.append(nn.Linear(previous_size, output_size))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class LSTMModel(nn.Module):
    """Sequence model for time-ordered windows (`requires_time_column=True`
    entry). Predicts from the last timestep's hidden state, the standard
    "many-to-one" LSTM shape."""

    def __init__(
        self, input_size: int, hidden_size: int, num_layers: int, output_size: int
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.head = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, sequence_length, input_size)
        output, _ = self.lstm(x)
        last_step = output[:, -1, :]
        return self.head(last_step)
