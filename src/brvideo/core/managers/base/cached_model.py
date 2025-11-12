from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound="BaseCachedModel")


class BaseCachedModel(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_model(cls: Type[ModelT], model: Any) -> ModelT:
        field_names = set(cls.model_fields.keys())
        init_data = {}
        for name in field_names:
            value = getattr(model, name, None)
            if isinstance(value, list):
                value = list(value)
            init_data[name] = value

        try:
            return cls.model_validate(init_data)
        except ValidationError as e:
            raise TypeError(f"Invalid data for {cls.__name__}: {e}") from e
