"""infra/argo-workflows/training-image/pyfunc_wrapper.py — GenericPyfuncWrapper
delegates predict() to the wrapped model unchanged. mlflow is a real
(installed) dependency here, same as tests/test_train_dl.py — no need to
stub it."""

from unittest.mock import MagicMock

from pyfunc_wrapper import GenericPyfuncWrapper


def test_predict_delegates_to_wrapped_model() -> None:
    inner_model = MagicMock()
    inner_model.predict.return_value = "predictions"
    wrapper = GenericPyfuncWrapper(inner_model)

    result = wrapper.predict(context=None, model_input="some-input")

    inner_model.predict.assert_called_once_with("some-input")
    assert result == "predictions"
