# Adapters (chưa code — placeholder cho tuần 2-5)

Thư mục này sẽ chứa các Adapter Python theo Adapter Pattern đã thiết kế:

```
adapters/
├── interfaces.py          # IModelRegistryAdapter, IInferenceAdapter, ...
├── mlflow_adapter.py       # implement bằng MLflow SDK (mock/thật)
├── viettel_adapter.py      # implement khi có API thật của Viettel (tuần 4-5)
├── factory.py               # AdapterFactory — chọn đúng class theo config
└── mock/
    └── mock_registry_adapter.py  # trả data giả cố định, dùng khi demo offline
```

## Nguyên tắc khi bắt đầu code (tuần 2-3)

1. Viết `interfaces.py` TRƯỚC — định nghĩa contract, chưa cần implement.
2. Viết `mlflow_adapter.py` — dùng MLflow đã dựng ở `scripts/setup-mlflow.sh`.
3. Chỉ viết `viettel_adapter.py` SAU KHI mentor xác nhận thông tin hệ thống
   thật (xem checklist hỏi mentor trong playbook mục 10).

## Ví dụ interface (tham khảo, không phải code thật)

```python
from abc import ABC, abstractmethod

class IModelRegistryAdapter(ABC):
    @abstractmethod
    def register_model(self, name: str, version: str, artifact_uri: str) -> dict:
        ...

    @abstractmethod
    def list_models(self, project: str | None = None) -> list[dict]:
        ...
```
