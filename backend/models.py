from pydantic import BaseModel, model_validator
from typing import Literal


class JobCreate(BaseModel):
    job_type: Literal["simulate_work", "sum_numbers"] # expect specific job types
    payload: dict

    @model_validator(mode="after") # a model checker for the recently created object, checks more specific requirments
    def validate_payload(self): # self becomes job object
        if self.job_type == "simulate_work": # check that under specific condiotns, the model is valid
            if "seconds" not in self.payload:
                raise ValueError(
                    "simulate_work payload must contain 'seconds'"
                )

            if not isinstance(self.payload["seconds"], (int, float)):
                raise ValueError(
                    "'seconds' must be a number"
                )

            if self.payload["seconds"] <= 0:
                raise ValueError(
                    "'seconds' must be greater than 0"
                )

        elif self.job_type == "sum_numbers":
            if "numbers" not in self.payload:
                raise ValueError(
                    "sum_numbers payload must contain 'numbers'"
                )

            if not isinstance(self.payload["numbers"], list):
                raise ValueError(
                    "'numbers' must be a list"
                )

            # all here uses an expression, then supplies the variable in that expression next, here it checks if all values in numbers is actuall a number 
            if not all(
                isinstance(number, (int, float))
                for number in self.payload["numbers"]
            ):
                raise ValueError(
                    "'numbers' must contain only numbers"
                )

        return self
